# SecureScope 운영 룰북

## 1. 서비스 아키텍처 요약

| 컴포넌트 | 기술 | 포트 | 헬스체크 |
|---|---|---|---|
| Frontend | Next.js 15 | 3000 | `GET /` |
| Backend | FastAPI | 8000 | `GET /api/v1/health` |
| Postgres | PostgreSQL 16 | 5432 | `pg_isready` |
| Redis | Redis 7 | 6379 | `redis-cli ping` |
| Temporal | Temporal 1.24 | 7233 | `nc -z <host> 7233` |
| Prometheus | Prometheus | 9090 | `GET /-/healthy` |
| Grafana | Grafana | 3000 | `GET /api/health` |

## 2. 장애 대응 플레이북

### 2.1 Backend 응답 불가 (5xx 급증)

**증상**: Prometheus `HighErrorRate` 알림, 사용자 API 호출 실패

**진단 순서**:
1. `kubectl get pods -n securescope -l app=backend` — Pod 상태 확인
2. `kubectl logs -n securescope -l app=backend --tail=100` — 에러 로그 확인
3. `kubectl top pods -n securescope -l app=backend` — 리소스 사용량 확인
4. DB 연결 확인: `kubectl exec -it <pod> -- python -c "from app.core.database import engine; print('ok')"`

**조치**:
- OOM 발생 시: `kubectl rollout restart deployment/backend -n securescope`
- DB 연결 풀 고갈 시: Pod 재시작 후 연결 수 확인 (`pg_stat_activity`)
- 코드 버그 시: 이전 버전으로 롤백 `helm rollback securescope <revision>`

### 2.2 Database 장애

**증상**: Backend 로그에 `ConnectionRefusedError`, `OperationalError`

**진단 순서**:
1. RDS 콘솔 → 인스턴스 상태 확인
2. CloudWatch → CPU, 연결 수, 디스크 I/O 확인
3. `pg_stat_activity` 쿼리로 활성 연결 확인

**조치**:
- 연결 수 초과: 유휴 연결 정리 `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND query_start < now() - interval '10 minutes'`
- 디스크 풀: `rds_allocated_storage` 증가 (Terraform apply)
- 인스턴스 장애: 자동 페일오버 확인, 필요 시 수동 페일오버

### 2.3 Redis 장애

**증상**: WebSocket 브로드캐스트 실패, Rate limiter 오류

**진단 순서**:
1. `redis-cli -h <host> ping` — 연결 확인
2. `redis-cli info memory` — 메모리 사용량 확인
3. `redis-cli info clients` — 클라이언트 연결 수 확인

**조치**:
- 메모리 초과: `FLUSHDB` 후 원인 분석 (캐시 TTL 미설정 등)
- 연결 초과: 클라이언트 풀 설정 확인, maxclients 조정

### 2.4 Temporal 워크플로 실패

**증상**: 분석 세션이 `RUNNING`에서 진행되지 않음

**진단 순서**:
1. Temporal UI (`temporal:8080`) → 워크플로 상태 확인
2. 워커 로그: `kubectl logs -n securescope -l app=temporal-worker --tail=100`
3. Activity 실패 원인 확인 (타임아웃, OOM, API 오류)

**조치**:
- 워커 다운: `kubectl rollout restart deployment/temporal-worker`
- Activity 타임아웃: ResourceLimits 설정 검토
- LLM API 오류: API 키 유효성 확인, rate limit 확인

### 2.5 P95 응답 시간 SLO 위반 (> 2초)

**증상**: Prometheus `HighP95Latency` 알림

**진단 순서**:
1. Grafana 대시보드 → 느린 엔드포인트 식별
2. 해당 엔드포인트의 DB 쿼리 실행 계획 확인
3. `kubectl top pods` → 리소스 병목 확인

**조치**:
- 쿼리 느림: 인덱스 추가 또는 쿼리 최적화
- Pod 부족: HPA min replicas 증가
- 단발성: 모니터링 지속, 재발 시 조치

## 3. 백업 및 복구

### 3.1 자동 백업

- **RDS**: 자동 스냅샷 매일, 보존 30일
- **CronJob**: `postgres-backup` CronJob이 매일 03:00 UTC pg_dump 실행, 30일 보존
- **확인**: `kubectl get jobs -n securescope | grep postgres-backup`

### 3.2 수동 백업

```bash
# RDS 스냅샷
aws rds create-db-snapshot \
  --db-instance-identifier securescope-prod \
  --db-snapshot-identifier securescope-manual-$(date +%Y%m%d)

# pg_dump (직접)
kubectl run pg-backup --rm -it --image=postgres:16-alpine -- \
  pg_dump "$DATABASE_URL" | gzip > backup_$(date +%Y%m%d).sql.gz
```

### 3.3 복구 절차

**RDS 스냅샷 복구**:
1. AWS 콘솔 → RDS → 스냅샷 → 복원
2. 새 인스턴스 엔드포인트로 Vault 시크릿 업데이트
3. Backend Pod 재시작
4. 데이터 정합성 확인

**pg_dump 복구**:
```bash
gunzip -c backup_YYYYMMDD.sql.gz | psql "$DATABASE_URL"
```

**복구 후 확인 사항**:
- `GET /api/v1/health` 정상 응답
- 최근 프로젝트/세션 데이터 존재 여부
- Alembic 마이그레이션 버전 일치 확인

## 4. 배포 절차

### 4.1 일반 배포

```bash
# 1. 이미지 빌드 및 푸시
docker build -t securescope-backend:v<VERSION> -f apps/backend/Dockerfile .
docker push <registry>/securescope-backend:v<VERSION>

# 2. Helm 업그레이드
helm upgrade securescope infra/helm/securescope \
  -n securescope \
  -f infra/helm/securescope/values.yaml \
  --set backend.tag=v<VERSION>

# 3. 롤아웃 확인
kubectl rollout status deployment/backend -n securescope
```

### 4.2 롤백

```bash
# 직전 버전으로
helm rollback securescope -n securescope

# 특정 리비전으로
helm history securescope -n securescope
helm rollback securescope <REVISION> -n securescope
```

### 4.3 DB 마이그레이션

- 마이그레이션은 Backend 컨테이너 시작 시 `entrypoint.sh`에서 자동 실행
- **주의**: 파괴적 마이그레이션(컬럼 삭제 등)은 2단계로 분리
  1. 코드에서 해당 컬럼 미사용 배포
  2. 다음 배포에서 컬럼 삭제 마이그레이션

## 5. On-Call 로테이션

### 5.1 구조

| 레벨 | 대상 | 응답 시간 |
|---|---|---|
| L1 | 당번 엔지니어 | 15분 |
| L2 | 시니어 엔지니어 | 30분 |
| L3 | 테크 리드 | 1시간 |

### 5.2 에스컬레이션 기준

- **Critical 알림** (ServiceDown, HighErrorRate): L1 즉시 대응, 15분 내 미해결 시 L2
- **Warning 알림** (HighP95Latency, HighMemoryUsage): L1 확인, 업무 시간 내 대응
- **30분 이상 장애 지속**: L3 에스컬레이션 + 전사 공지

### 5.3 로테이션 주기

- 주간 단위 교대 (월요일 09:00 인수인계)
- 최소 2인 1조 (백엔드 1 + 인프라 1)
- 연속 2주 금지, 최소 2주 간격

## 6. 알림 채널

| 채널 | 용도 |
|---|---|
| `#securescope-alerts` | Prometheus 알림 자동 전달 |
| `#securescope-oncall` | On-call 커뮤니케이션 |
| Email | 장애 보고서 (사후) |

## 7. 주기적 점검 사항

| 주기 | 항목 |
|---|---|
| 매일 | 백업 CronJob 성공 여부, 알림 채널 정상 |
| 매주 | 리소스 사용 추이, 에러 로그 패턴 |
| 매월 | 비용 리뷰, 보안 패치 적용, 인증서 만료 확인 |
| 분기 | 장애 복구 훈련 (DR drill), SLO 달성률 리뷰 |
