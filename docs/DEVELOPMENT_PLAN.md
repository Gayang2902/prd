# SecureScope — 개발 계획 (Development Plan)

본 문서는 PRD를 기반으로 한 18주 스프린트 플랜이다. 각 task에는 PRD 참조와 인수 기준이 명시되어 있어, 개발 에이전트가 단위 작업으로 바로 집어 들 수 있도록 구성되었다.

---

## 1. 개요

| 항목 | 값 |
|---|---|
| 총 기간 | 18주 (~4.5개월) |
| 스프린트 | 2주씩 9회 |
| 페이즈 | 기반(2주) → MVP(8주) → Beta(4주) → GA(4주) |
| 권장 팀 | 백엔드 2명 + 프론트 2명 + 데브옵스 1명 + 레드팀 협업 |

## 2. 워크스트림 코드

| 코드 | 영역 | 주 담당 |
|---|---|---|
| `BE` | 백엔드 (FastAPI, DB, Temporal, Agent 통합) | 백엔드 |
| `FE` | 프론트엔드 (Next.js, UI) | 프론트 |
| `IN` | 인프라 (K8s, CI/CD, Vault, 모니터링) | 데브옵스 |
| `DI` | Discovery (인터뷰, 검증) | PM/리드 |

## 3. 마일스톤

| 마일스톤 | 끝나는 시점 | 인수 기준 |
|---|---|---|
| **MVP-α** (내부 데모) | Sprint 3 (W8) | Mock 에이전트로 e2e 분석 1회 완료, 결과 화면 진입 |
| **MVP-β** (알파 유저) | Sprint 5 (W12) | 실제 Claude Code/Codex 분석, 검증 워크플로 동작, 다수 검수자 동시 작업 |
| **Beta** | Sprint 7 (W16) | 이력·회귀 추적·비용 가시화·RBAC 완전, 알림 |
| **GA** | Sprint 8 (W18) | 안정화, 감사 로그, 운영 룰북, 다크 런치 |

## 4. 의존성 핵심 흐름

```
Sprint 0 (Foundation)
    ↓
Sprint 1 (Core Models, Mock Agent)
    ↓
Sprint 2 (Project + Session)
    ↓
Sprint 3 (E2E with Mock) ──────── MVP-α
    ↓
Sprint 4 (Real Agents)
    ↓
Sprint 5 (Verification UI) ────── MVP-β
    ↓
Sprint 6 (History + Queue)
    ↓
Sprint 7 (Cost + RBAC) ────────── Beta
    ↓
Sprint 8 (Polish + GA prep) ───── GA
```

## 5. Task 표기법

`- [ ] {ID}: {제목} | PRD 참조 | 사이즈 | 인수 기준`

- 사이즈: `S` (1일 이내), `M` (1~3일), `L` (3~5일)
- PRD 참조는 `§N` (본문 섹션) 또는 `부록 X` (Appendix)

---

## Sprint 0 — Foundation (W1-2)

**목표**: 모든 워크스트림이 다음 스프린트부터 풀 가동할 수 있도록 골격 완비. Discovery 병행 진행.

### Backend
- [x] **BE-01**: 모노레포 셋업 (`apps/`, `packages/`, `infra/`, `docs/`) | 부록 C | S | `make setup` 한 번에 의존성 설치, README에 시작 가이드
- [x] **BE-02**: FastAPI 프로젝트 구조 + `/api/v1/health` 엔드포인트 | 부록 G | S | 200 응답, OpenAPI 자동 생성 활성화
- [x] **BE-03**: Alembic 베이스라인 마이그레이션 | 부록 E | S | `alembic upgrade head` 통과
- [x] **BE-04**: SSO/OIDC 인증 미들웨어 (Authlib) + 로컬 mock IdP | §F7, 부록 C | L | 로컬에서 로그인 e2e, JWT 발급, refresh token

### Frontend
- [x] **FE-01**: Next.js (App Router) + TypeScript + Tailwind + shadcn/ui 셋업 | 부록 C | M | 빌드 통과, Storybook 셋업
- [x] **FE-02**: 디자인 토큰 정리 (색·타이포·간격), 다크모드 토글 | M | 토큰 페이지에서 시각 확인
- [x] **FE-03**: 인증 플로 (SSO 리다이렉트, 세션 쿠키, 401 처리) | §F7 | M | 로그인-로그아웃 e2e

### Infra
- [x] **IN-01**: GitHub Actions CI 파이프라인 (lint, test, build) | §C.9 | M | main push 시 그린
- [ ] **IN-02**: K8s dev 네임스페이스 + 기본 NetworkPolicy | §C.6 | M | dev 클러스터에 backend Pod 배포 성공
- [ ] **IN-03**: Vault dev 인스턴스 + ExternalSecrets Operator | §C.7 | M | API 키 1건을 Vault → Pod env로 주입 검증
- [x] **IN-04**: Temporal dev 클러스터 (또는 매니지드) 셋업 | §C.5 | M | hello-world workflow 1건 동작

### Discovery (병행)
- [ ] **DI-01**: 검수자 3-5명 인터뷰 일정 확보 | S
- [ ] **DI-02**: 베이스라인 측정 — 현재 검수 1건당 평균 시간·취약점 수 (과거 6개월 데이터) | M | 숫자 1세트 확보
- [ ] **DI-03**: 검증 가설 5개 인터뷰 진행 | M | 결과 노트 정리
- [ ] **DI-04**: 인터뷰 인사이트를 PRD §9 KPI 베이스라인에 반영 | S

### Acceptance demo
1. 로컬에서 backend + frontend 기동, SSO 로그인 후 빈 대시보드 진입
2. dev 클러스터에 health check Pod 배포 확인
3. CI 그린, Storybook에서 디자인 토큰 페이지 확인

---

## Sprint 1 — Core Models & Mock Agent (W3-4)

**목표**: DB 스키마 완성, 에이전트 인터페이스 + MockAgent 동작, 프로젝트 CRUD API + UI

### Backend
- [x] **BE-05**: 부록 E의 8개 테이블 마이그레이션 (User, Project, AnalysisSession, Finding, FindingStatus, Comment, Agent, Preset) | 부록 E | M
- [x] **BE-06**: SQLAlchemy 2.0 async 모델 + Pydantic v2 스키마 | 부록 E, F | M
- [x] **BE-07**: 부록 F의 Agent ABC + 데이터 스키마 (AgentMetadata, CodeScope, Preset, Finding 등) 구현 | 부록 F | M
- [x] **BE-08**: MockAgent 구현 (랜덤 finding 생성, 결정론적 시나리오) | 부록 F | M | `MockAgent().analyze()`가 5건 mock finding 반환
- [x] **BE-09**: Entry-point 기반 에이전트 디스커버리 | 부록 F | S | `pyproject.toml` entry_points로 등록 → 부팅 시 자동 발견
- [x] **BE-10**: Project CRUD 엔드포인트 (`GET/POST /projects`, `GET/PATCH /projects/{id}`) | 부록 G | M
- [x] **BE-11**: User CRUD + RBAC 데코레이터 베이스 (Reviewer/Lead/Admin) | §F7 | M

### Frontend
- [x] **FE-04**: 프로젝트 목록 페이지 (필터: 상태, 담당) | F1 | M
- [x] **FE-05**: 프로젝트 상세 페이지 — 개요 탭 (와이어프레임 기준) | 와이어프레임 #1 | M
- [x] **FE-06**: 프로젝트 신규 등록 폼 | F1-1, F1-2 | M
- [x] **FE-07**: 디자인 시스템 컴포넌트 (Card, Badge, StatCard, Button, Input) | M

### Infra
- [ ] **IN-05**: stage 클러스터 셋업 (dev와 동일 구성) | M
- [ ] **IN-06**: Postgres 매니지드 인스턴스 (dev/stage) | M
- [x] **IN-07**: 모니터링 기본 (Prometheus + Grafana, 헬스 메트릭) | §C.8 | M

### Discovery
- [ ] **DI-05**: 인터뷰 결과 → KPI 베이스라인 확정, 잔여 가설 리스트 정리

### Acceptance demo
- UI에서 프로젝트 등록 → 목록 → 상세 진입
- API 콘솔에서 MockAgent로 한 회차 시뮬레이션 (DB에 결과 저장 확인)

---

## Sprint 2 — Project + Session Basic Flow (W5-6)

**목표**: 프로젝트와 분석 회차의 기본 라이프사이클 + GitLab 연동 시작

### Backend
- [x] **BE-12**: GitLab API 클라이언트 (인증, 프로젝트/브랜치 검색) | F2-1, F2-2 | M
- [x] **BE-13**: 코드 적재 서비스 (격리 환경에 클론) — 우선 임시 디렉토리, K8s Job은 Sprint 3 | F2-4 | L
- [x] **BE-14**: AnalysisSession CRUD + 상태 전이 검증 (`QUEUED → PREPARING → RUNNING → ...`) | 부록 A | M
- [x] **BE-15**: 새 분석 회차 시작 엔드포인트 (`POST /projects/{id}/sessions`) — 우선 동기 실행 (Mock) | 부록 G | M
- [x] **BE-16**: 세션 로그 SSE 엔드포인트 | 부록 G | M

### Frontend
- [x] **FE-08**: 프로젝트 상세 — 회차 탭 + 새 분석 실행 모달 | F1, F3 | L
- [x] **FE-09**: GitLab 브랜치 선택 컴포넌트 (자동완성) | F2-2 | M
- [x] **FE-10**: 회차 진행 화면 (SSE 로그 스트림 표시) | F3-3 | M

### Infra
- [ ] **IN-08**: GitLab API 자격증명 Vault 저장 + 백엔드 주입 | §C.7 | S
- [ ] **IN-09**: 격리 환경 베이스 컨테이너 이미지 (Python + git + 에이전트 의존성) | §C.6 | M

### Acceptance demo
- 프로젝트 등록 → GitLab 브랜치 선택 → "분석 실행" → MockAgent 결과가 로그 스트림으로 흐름 → 완료 후 회차 #1 표시

---

## Sprint 3 — End-to-End with Mock (W7-8) → **MVP-α**

**목표**: Temporal 워크플로로 분석을 비동기 실행, K8s Job 격리 환경에서 MockAgent 동작, 검증 화면 골격

### Backend
- [x] **BE-17**: Temporal Activity 6종 구현 (부록 H) — Mock 버전 | 부록 H | L
- [x] **BE-18**: AnalysisWorkflow 본 코드 + 단위 테스트 | 부록 H | L
- [x] **BE-19**: K8s Job 프로비저닝 Activity (실제 Pod 생성) | §C.6 | L
- [x] **BE-20**: Finding fingerprint 산출 로직 | §B.2 | M
- [x] **BE-21**: Finding API (`GET /sessions/{id}/findings`, `GET /findings/{id}`) | 부록 G | M
- [x] **BE-22**: Finding 상태 변경 (`PATCH /findings/{id}/status`) + FindingStatus append | 부록 G | M

### Frontend
- [x] **FE-11**: 검증 화면 골격 (좌: Monaco 코드 뷰어, 우: 사이드 패널) | 와이어프레임 #2 | L
- [x] **FE-12**: 취약점 리스트 + 인라인 코드 점프 | 부록 D | L
- [x] **FE-13**: 검증 액션 버튼 (확정/오탐/검토) + 낙관적 업데이트 | 부록 D | M
- [x] **FE-14**: 단축키 핸들러 (j/k/c/f/r/e/?) | §D.3 | S

### Infra
- [ ] **IN-10**: Temporal 워커 Deployment (분리된 Pool) | §C.5 | M
- [ ] **IN-11**: K8s Job 실행 권한 (RBAC, ServiceAccount) | §C.6 | M
- [ ] **IN-12**: 격리 Pod NetworkPolicy 검증 (외부 egress 차단 → 허용 도메인만) | §C.6 | M

### Acceptance demo (**MVP-α**)
- 분석 실행 버튼 클릭 → 격리 Pod 생성 → MockAgent 실행 → 결과 17건 → 검증 화면에서 코드/취약점 동시 보기 → 검증 액션 부여 → 회차 상태 `완료`

---

## Sprint 4 — Real Agents (W9-10)

**목표**: Claude Code, Codex 실제 통합. LLM 호출, 토큰/비용 추적.

### Backend
- [x] **BE-23**: ClaudeCodeAgent 구현 (Anthropic API + Claude Code CLI 격리 실행) | 부록 F | L
- [x] **BE-24**: CodexAgent 구현 (OpenAI API + Codex CLI 격리 실행) | 부록 F | L
- [x] **BE-25**: 토큰 사용량/비용 추적 — `LogEvent.tokens_used` 누적, 회차 종료 시 집계 | §A.5 | M
- [x] **BE-26**: ResourceLimits 강제 (시간/토큰/비용 한도 초과 시 자체 중단) | §A.5 | M
- [x] **BE-27**: 프리셋 CRUD + 빌트인 프리셋 3종 (표준 보안 검수, Quick Diff Scan, PII 집중) | §A.3 | M

### Frontend
- [x] **FE-15**: 분석 실행 모달 — 에이전트 선택 + 프리셋 선택 + 스코프 (브랜치/diff/include path) | F3-1, F3-2 | M
- [x] **FE-16**: 회차 상세 — 메타데이터 표시 (에이전트, 모델 버전, 토큰, 비용) | §A.1 | S
- [x] **FE-17**: 프리셋 관리 페이지 (목록 + 편집) | F3-2 | M

### Infra
- [ ] **IN-13**: LLM API 키 (Anthropic, OpenAI) Vault 저장 + Pod 주입 | §C.7 | S
- [ ] **IN-14**: 격리 Pod 리소스 한도 (CPU, mem, runtime) 정책 | §C.6 | S

### Acceptance demo
- 실제 GitLab 프로젝트의 한 브랜치를 Claude Code로 분석 → 진짜 LLM 호출 발생 → 실제 취약점 검출 → 토큰/비용이 회차 메타에 기록

---

## Sprint 5 — Verification + Status Workflow (W11-12) → **MVP-β**

**목표**: 검증 워크플로 완성, 다수 검수자 동시 작업, 코멘트, 리포트.

### Backend
- [x] **BE-28**: Comment CRUD (`/findings/{id}/comments`) | 부록 G | M
- [x] **BE-29**: 동시 편집 충돌 감지 (낙관적 락 또는 last-writer-wins + 알림) | §D.4 | M
- [x] **BE-30**: WebSocket 핸들러 — 검증 화면 실시간 동기화 | §D.4 | M
- [x] **BE-31**: 리포트 생성 (PDF, Markdown, CSV, JSON) | §B.3 | L
- [x] **BE-32**: `POST /sessions/{id}/reports` 엔드포인트 | 부록 G | M

### Frontend
- [x] **FE-18**: 코멘트 UI (작성, 표시, mention) | F4-4 | M
- [x] **FE-19**: 동시 편집 충돌 UI (다른 검수자가 변경 시 표시) | §D.4 | M
- [x] **FE-20**: 리포트 내보내기 모달 (템플릿 선택, 포맷 선택) | §B.3 | M
- [x] **FE-21**: 필터 바 (심각도, 카테고리, 상태) | F4-1 | M

### Infra
- [ ] **IN-15**: WebSocket sticky session 또는 sub/pub 백엔드 (Redis) | §C.5 | M
- [ ] **IN-16**: PDF 생성 인프라 (headless Chromium 또는 wkhtmltopdf) | §B.3 | M

### Acceptance demo (**MVP-β**, 알파 유저 투입)
- 검수자 2명이 동시 접속 → 같은 회차 검증 → 코멘트 교환 → PDF 리포트 생성 → 개발팀에 공유

---

## Sprint 6 — History, Regression, Queue Monitoring (W13-14)

**목표**: 회차 이력, 회귀 추적, 분석 큐 가시화

### Backend
- [x] **BE-33**: 회귀 매칭 알고리즘 (fingerprint 기반 NEW/RECURRING/RESOLVED/CARRIED_OVER 라벨링) | §B.2 | L
- [x] **BE-34**: `GET /findings/{id}/timeline` (회귀 이력) | 부록 G | M
- [x] **BE-35**: `GET /queue` (실행 중·대기 중 통합) | 부록 G | M
- [x] **BE-36**: 작업 우선순위 큐 (URGENT/NORMAL/BACKGROUND) | §A.5 | M
- [x] **BE-37**: 검색·필터 API (기간, 담당, 심각도, 상태) | F5-4 | M

### Frontend
- [x] **FE-22**: 프로젝트 상세 — 이력 탭 (회차 비교) | F5-1 | M
- [x] **FE-23**: 회귀 추적 타임라인 화면 | 와이어프레임 #4 | M
- [x] **FE-24**: 분석 큐 모니터링 화면 | 와이어프레임 #3 | L
- [x] **FE-25**: 실시간 큐 갱신 (5초 polling 또는 WebSocket) | §F6 | S

### Acceptance demo
- 같은 프로젝트를 3회 분석 → 회귀 추적 화면에서 한 취약점의 NEW → RESOLVED → RECURRING 흐름 확인
- 큐 모니터링에서 동시 실행/대기 상태 실시간 표시

---

## Sprint 7 — Cost Dashboard, RBAC, Notifications (W15-16) → **Beta**

**목표**: 비용 가시화, 권한 매트릭스 완성, 알림

### Backend
- [x] **BE-38**: 비용 집계 (일별/에이전트별/프로젝트별 materialized view) | 부록 I | M
- [x] **BE-39**: 비용 가시화 API (`GET /usage/cost`, `/usage/by-project`, `/usage/by-agent`) | 부록 I | M
- [x] **BE-40**: 권한 매트릭스 정식화 (역할 × 엔드포인트 표) + 미들웨어 적용 | §F7 | L
- [x] **BE-41**: 감사 로그 sink (별도 PG 테이블 + 외부 SIEM 연계 인터페이스) | §F7 | M
- [x] **BE-42**: 알림 시스템 (Slack 웹훅 + Email) — 트리거 4종 | §I.5 | M

### Frontend
- [x] **FE-26**: 비용 가시화 화면 | 와이어프레임 #5 | L
- [x] **FE-27**: 설정 — 사용자/권한 페이지 (Admin 전용) | §F7 | M
- [x] **FE-28**: 설정 — 감사 로그 페이지 | §F7 | M
- [x] **FE-29**: 설정 — GitLab 연동, 에이전트/프리셋 페이지 | §F7 | M

### Infra
- [ ] **IN-17**: 알림 채널 시크릿 (Slack 웹훅, SMTP) Vault 저장 | S
- [ ] **IN-18**: 백업 정책 (DB 일일 스냅샷, 보존 30일) | M
- [ ] **IN-19**: prod 클러스터 셋업 + 인프라 코드 정리 (Terraform + Helm) | §C.9 | L

### Acceptance demo (**Beta**)
- 비용 대시보드에서 한 달 사용 현황 확인 (실제 데이터)
- Reviewer 계정으로 Admin 페이지 접근 시 차단됨 확인
- 월 예산 80% 도달 시뮬레이션 → Slack 알림 도달

---

## Sprint 8 — Polish + GA (W17-18) → **GA**

**목표**: 안정화, 운영 룰북, 다크 런치, 외부 노출 준비

### Backend
- [x] **BE-43**: 에러 처리 표준화 (Problem Details RFC 7807) | 부록 G | M
- [x] **BE-44**: rate limiting (사용자/엔드포인트별) | M
- [x] **BE-45**: API 문서 자동 생성 점검 + 외부 공유 가능 형태 정리 | 부록 G | S
- [x] **BE-46**: 부하 테스트 (k6 또는 Locust, 100 동시 검수자 시뮬레이션) | §7.2 | L

### Frontend
- [x] **FE-30**: 접근성 점검 (axe-core, 키보드 내비게이션) | M
- [x] **FE-31**: 에러 바운더리 + 공통 에러 화면 | S
- [x] **FE-32**: 사용자 프로필/설정 페이지 | S
- [x] **FE-33**: 온보딩 모달 (첫 로그인 시 가이드) | M

### Infra
- [ ] **IN-20**: 운영 룰북 (장애 대응 플레이북, 백업 복구 절차, on-call 로테이션) | L
- [ ] **IN-21**: SLO/SLA 정의 + 알림 (가용성 99%, P95 응답 < 2s) | §7.4 | M
- [ ] **IN-22**: 다크 런치 — 일부 팀 우선 오픈 + 피드백 루프 | M
- [ ] **IN-23**: GA 공지 + 사용 가이드 (Notion/Confluence) | M

### Acceptance demo (**GA**)
- 부하 테스트 통과 (P95 < 2s)
- 의도된 장애 시나리오 1건에 대한 대응 시연 (DB 장애 → 백업 복구)
- 외부 팀 1개를 다크 런치 대상으로 온보딩 완료

---

## 6. 모든 Task 공통 — Definition of Done

- [ ] 코드 리뷰 1인 이상 승인
- [ ] 단위 테스트 추가 (변경 코드 커버리지 80% 이상)
- [ ] 통합 테스트 (해당 시)
- [ ] lint + format 통과 (Black, Ruff, ESLint, Prettier)
- [ ] 타입 체크 통과 (mypy strict, tsc strict)
- [ ] CI 그린
- [ ] PR 본문에 PRD 참조 + 변경 요약 + 인수 기준 체크리스트
- [ ] DB 변경 시 backward compatible 마이그레이션

## 7. 우선순위 충돌 시 결정 원칙

1. **MVP-β 시점에 알파 유저가 쓸 수 있어야 함**이 최우선. 그 외 기능은 후순위로 밀려도 됨.
2. **보안 관련 task는 절대 미루지 않음** (격리, 권한, 감사).
3. **데이터 무결성 task 우선** (회차 immutable, FindingStatus append-only).
4. **UX 개선보다 기능 완성도 우선** (Beta 후 polish).

## 8. 위험 신호 (조기 에스컬레이션 대상)

다음이 발생하면 PM/리드에게 즉시 보고:

- 한 sprint에서 task 30% 이상이 미완료로 다음 sprint로 이월
- LLM 비용이 예상치의 2배 이상 발생
- 격리 환경 보안 우회 가능성 발견
- 검수자 인터뷰에서 핵심 가정이 무너지는 피드백 (워크플로 자체 부적합 등)
- GitLab API rate limit에 자주 걸림

## 9. 사용 방법 (개발 에이전트용)

1. 본 문서를 읽기 전 `AGENTS.md`를 먼저 읽을 것
2. 위에서 미체크된 가장 첫 task를 선택
3. 해당 task의 PRD 참조 부분을 읽고 작업 범위 이해
4. 모호한 부분은 `AGENTS.md` §7 (질문해야 하는 경우) 참조
5. 작업 → 테스트 → PR → 머지 후 본 문서의 체크박스 갱신

각 task ID는 GitLab 이슈/브랜치/PR 명에 그대로 사용 (예: `feat/BE-05-db-schema`).
