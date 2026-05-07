# AGENTS.md

이 문서는 본 리포지토리에서 작업하는 **AI 코딩 에이전트** (Claude Code, Codex, Cursor, Continue 등)와 인간 기여자 모두를 위한 운영 지침입니다.

> **에이전트 사용 시**: 작업 시작 전 본 문서 전체를 읽어 주세요. 그다음 `docs/PRD.md`와 `docs/DEVELOPMENT_PLAN.md`를 순서대로 읽고 task를 선택합니다.

---

## 1. 프로젝트 한 줄 요약

**SecureScope** — 사내 코드 정적 분석 대시보드. 레드팀이 보안 검수의 전 과정 (공수 산정 → GitLab 코드 적재 → LLM 기반 정적 분석 → 결과 검증 → 이력 관리)을 단일 웹에서 수행한다.

상세는 `docs/PRD.md` §1-3 참조.

## 2. 우선 읽어야 할 문서

작업 시작 전 다음 순서로 읽을 것:

| 순서 | 문서 | 무엇을 얻나 |
|---|---|---|
| 1 | `AGENTS.md` (이 문서) | 작업 방식, 컨벤션, 금지 사항 |
| 2 | `docs/PRD.md` | 제품·기능 요구사항 (Single Source of Truth) |
| 3 | `docs/DEVELOPMENT_PLAN.md` | 스프린트별 task 큐 |

각 task에는 PRD의 `§N` 또는 `부록 X` 참조가 명시되어 있다. **작업 시작 전 해당 섹션을 반드시 읽을 것.**

## 3. 기술 스택 (요약)

| 영역 | 선택 |
|---|---|
| 백엔드 언어 | Python 3.12+ |
| 백엔드 프레임워크 | FastAPI |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| 검증 | Pydantic v2 |
| 워크플로 | Temporal (Python SDK) |
| 프론트엔드 | TypeScript, Next.js 15 (App Router) |
| 스타일 | TailwindCSS + shadcn/ui |
| 데이터 페칭 | TanStack Query |
| 코드 뷰어 | Monaco Editor (read-only) |
| 데이터베이스 | PostgreSQL 16 |
| 캐시·큐 | Redis |
| 객체 저장소 | S3 호환 (MinIO 등) |
| 인프라 | Kubernetes, Helm, Terraform |
| CI/CD | GitLab CI |
| 인증 | OIDC/SAML SSO (Authlib) |
| 시크릿 | HashiCorp Vault + ExternalSecrets |
| 관찰성 | Prometheus + Grafana, Loki, OpenTelemetry |

상세 결정 근거는 PRD 부록 C 참조.

## 4. 리포지토리 구조

```
securescope/
├── apps/
│   ├── backend/                  # FastAPI 본체 + Temporal workflow 정의
│   │   ├── app/
│   │   │   ├── api/v1/           # REST 라우터
│   │   │   ├── models/           # SQLAlchemy 모델
│   │   │   ├── schemas/          # Pydantic 스키마
│   │   │   ├── services/         # 비즈니스 로직
│   │   │   │   └── repositories/ # DB 접근 (repository 패턴)
│   │   │   ├── workflows/        # Temporal Workflow 정의
│   │   │   ├── activities/       # Temporal Activity 정의
│   │   │   ├── auth/             # SSO, JWT, RBAC
│   │   │   └── core/             # 설정, 공통 유틸, 로깅
│   │   ├── tests/                # pytest (unit + integration)
│   │   ├── alembic/              # DB 마이그레이션
│   │   └── pyproject.toml
│   ├── frontend/                 # Next.js
│   │   ├── app/                  # App Router 페이지
│   │   ├── components/           # 재사용 컴포넌트
│   │   ├── lib/                  # API 클라이언트, hooks, utils
│   │   ├── styles/
│   │   └── package.json
│   ├── worker/                   # Temporal worker (분석 실행)
│   └── agents/                   # 에이전트 플러그인
│       ├── claude-code/
│       ├── codex/
│       └── mock/
├── packages/
│   └── shared-schemas/           # 공유 OpenAPI 타입 (생성됨)
├── infra/
│   ├── helm/                     # K8s Helm 차트
│   ├── terraform/                # 인프라 코드
│   └── k8s/                      # 매니페스트
├── docs/
│   ├── PRD.md
│   ├── DEVELOPMENT_PLAN.md
│   └── ...
├── AGENTS.md                     # 이 파일
└── README.md
```

신규 파일은 위 구조에 따라 배치할 것. 새 폴더 추가 시 PR 본문에 정당화 기재.

## 5. 코딩 컨벤션

### 5.1 Python (백엔드)
- **Formatter**: Black (line length 100)
- **Linter**: Ruff (rule set: `E, F, I, N, B, A, C4, T20, RET, SIM, UP`)
- **Type checker**: mypy strict 모드. 모든 public 함수 type hint 필수
- **Test framework**: pytest + pytest-asyncio. 파일은 `tests/`에 미러 구조
- **Import 순서**: 표준 → 서드파티 → 로컬 (Ruff `I` 룰이 자동)
- **DB 접근**: 직접 ORM 호출 금지. `app/services/repositories/`의 repository 패턴 사용
- **에러 응답**: HTTP는 RFC 7807 Problem Details 포맷 (`type`, `title`, `status`, `detail`, `instance`)
- **로깅**: structlog, JSON 포맷, `traceId` 필수
- **시크릿**: 코드/로그/예외 메시지에 절대 노출 금지. Pydantic `SecretStr` 사용
- **비동기**: I/O는 무조건 `async def`. 동기 함수가 필요한 경우 `asyncio.to_thread()`로 격리

### 5.2 TypeScript (프론트엔드)
- **Formatter**: Prettier (`semi: true, singleQuote: true, tabWidth: 2`)
- **Linter**: ESLint (`@typescript-eslint/recommended` + `react-hooks`)
- **Type**: `tsc --strict`. `any` 금지. 외부 데이터는 `unknown`으로 받고 좁히기
- **Naming**: 컴포넌트 PascalCase, 훅 `useXxx`, 파일명 kebab-case
- **상태 관리**: 서버 상태는 TanStack Query, UI 로컬 상태만 `useState`/`useReducer`. Zustand 등 전역 상태 라이브러리는 합의 후 도입
- **API 호출**: 자동 생성된 OpenAPI 클라이언트 사용 (직접 `fetch` 금지)
- **스타일**: Tailwind 우선. 동적/조건부는 `clsx` + `cva`. CSS 모듈/styled-components 금지

### 5.3 공통
- 함수/컴포넌트 주석은 **왜**를 쓸 것 (**무엇**은 코드가 말함)
- TODO 주석은 GitLab 이슈 링크 포함: `# TODO(#123): 회귀 매칭 정확도 개선`
- 외부 의존성 추가는 PR 본문에 라이선스/사이즈/대안 고려 명시
- 모든 시간은 UTC `datetime` (timezone-aware), 표시만 사용자 로컬

## 6. 작업 워크플로

### 6.1 Task 선택과 진행

1. `docs/DEVELOPMENT_PLAN.md`에서 **다음 미체크 task** 선택 (sprint 순서 준수)
2. Task ID로 브랜치 생성: `feat/BE-05-db-schema`, `fix/FE-12-overflow` 등
3. PRD의 해당 § 또는 부록 읽기. 모호하면 §7 (질문해야 하는 경우)
4. 구현 + 단위 테스트
5. 로컬에서 `make lint test` 통과 확인
6. PR 생성 (다음 §6.2 참조)
7. CI 그린 + 리뷰 1인 이상 승인 후 머지
8. `DEVELOPMENT_PLAN.md`의 task 체크박스 갱신 (별도 PR 또는 머지 PR에 포함)

### 6.2 PR 본문 템플릿

```markdown
## 관련 Task
- DEVELOPMENT_PLAN.md → BE-05

## PRD 참조
- PRD.md → 부록 E (데이터 모델)

## 변경 요약
- User, Project, AnalysisSession 등 8개 테이블 마이그레이션 추가
- SQLAlchemy 모델 + Pydantic 스키마 정의
- 단위 테스트: 모델 생성/조회/제약조건 검증

## 인수 기준 체크리스트 (DEVELOPMENT_PLAN.md에서 복사)
- [x] `alembic upgrade head` 통과
- [x] 8개 테이블 모두 생성됨
- [x] `regression_status` 등 enum 정의됨

## 스크린샷 (UI 변경 시)
N/A

## 영향 범위
- DB 스키마 (신규)
- 다른 서비스에는 영향 없음
```

## 7. 질문해야 하는 경우 (추측 금지)

다음 상황에서는 작업을 멈추고 질문할 것:

- PRD가 모호하거나 두 부록이 모순될 때
- Task가 다른 sprint의 미완료 task에 의존할 때
- 명시된 기술 스택에서 벗어나야 할 때
- 보안/권한과 관련된 결정 (격리, 외부 호출, 시크릿)
- 데이터 모델 변경 (특히 immutable 위반 가능성)
- UX 결정에서 와이어프레임이 명확하지 않을 때
- LLM 호출 비용에 영향을 주는 변경

**질문 채널**: GitLab Issue + `@redteam-lead` 태그.

## 8. 절대 하지 말 것 (Hard NOs)

- ❌ 시크릿/API 키/자격증명을 코드 또는 commit에 포함
- ❌ `.env`, `.envrc` 등 시크릿 포함 가능 파일을 git에 추가
- ❌ `AnalysisSession`을 mutable로 변경 (생성 후 변경 금지)
- ❌ `FindingStatus`를 update/delete로 처리 (반드시 append-only)
- ❌ Temporal Workflow 시그니처를 호환성 깨면서 변경 (반드시 새 버전 클래스 + 마이그레이션 워크플로)
- ❌ K8s 격리 Pod의 NetworkPolicy 우회 (외부 egress는 허용 도메인만)
- ❌ 외부 LLM 호출에 raw 코드 전달 시 secrets/PII 마스킹 누락
- ❌ 회차 메타데이터 (커밋 SHA, 모델 버전, 컨테이너 이미지 SHA) 누락 — 재현성의 근본
- ❌ DB 마이그레이션을 backward incompatible로 작성 (drop column, type 변경 등 → 두 단계 마이그레이션 사용)
- ❌ 권한 검사 없는 엔드포인트 추가 (모든 라우터에 RBAC 데코레이터)
- ❌ `console.log`, `print` 등 디버그 출력을 main 브랜치에 머지

## 9. 흔히 쓰는 패턴

### 9.1 FastAPI 라우터 (RBAC + Repository)
```python
# app/api/v1/projects.py
from fastapi import APIRouter, Depends, status
from app.auth import require_role, Role, CurrentUser
from app.schemas import ProjectCreate, ProjectRead
from app.services.repositories import ProjectRepository

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    user: CurrentUser = Depends(require_role(Role.LEAD)),
    repo: ProjectRepository = Depends(),
) -> ProjectRead:
    project = await repo.create(payload, owner_id=user.id)
    return project
```

### 9.2 Temporal Activity (with heartbeat)
```python
# app/activities/clone.py
from temporalio import activity

@activity.defn(name="clone_repository")
async def clone_repository(env: EnvHandle, scope: CodeScope) -> None:
    activity.heartbeat({"phase": "init"})
    # ...
    activity.heartbeat({"phase": "cloning", "progress": 0.5})
    # ...
```

### 9.3 Next.js 페이지 (TanStack Query)
```tsx
// app/projects/[id]/page.tsx
'use client';

import { useProject } from '@/lib/api/projects';
import { ProjectDetail, ProjectSkeleton } from '@/components/project';

export default function ProjectDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const { data, isLoading, error } = useProject(params.id);
  if (isLoading) return <ProjectSkeleton />;
  if (error) throw error; // ErrorBoundary가 처리
  return <ProjectDetail project={data} />;
}
```

### 9.4 Repository 패턴
```python
# app/services/repositories/project.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Project

class ProjectRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, project_id: UUID) -> Project | None:
        return await self._session.scalar(
            select(Project).where(Project.id == project_id)
        )

    async def create(self, payload: ProjectCreate, owner_id: UUID) -> Project:
        project = Project(**payload.model_dump(), owner_id=owner_id)
        self._session.add(project)
        await self._session.flush()
        return project
```

## 10. 테스트 가이드

| 종류 | 도구 | 대상 | 커버리지 목표 |
|---|---|---|---|
| 단위 | pytest | services/, activities/, utils | 80%+ |
| 통합 | pytest + testcontainers | API 엔드포인트 happy path + 권한 거부 | 핵심 경로 100% |
| Workflow | Temporal time-skip | 분석 라이프사이클 (성공/실패/취소) | 모든 분기 |
| e2e | Playwright | 핵심 사용자 플로 (로그인 → 분석 → 검증) | 5개 주요 시나리오 |
| 에이전트 | MockAgent | 결정론적 시나리오 | 실제 LLM은 e2e만 |

테스트 데이터는 `tests/fixtures/`에 격리. CI에서 격리된 PG/Redis 사용 (testcontainers).

**LLM을 호출하는 단위 테스트는 작성 금지** — 비용·재현성 모두 깨짐. 대신 mock + e2e 야간 잡(스케줄)으로 검증.

## 11. 시크릿 관리

- **로컬 개발**: `.env.local` (gitignore됨), `direnv` 권장
- **dev/stage/prod**: Vault → ExternalSecrets → K8s Secret → Pod env
- **신규 시크릿 추가 시**: PR에 Vault path 명시 (`secret/securescope/<env>/<name>`)
- **노출 사고**: 즉시 회전 + 감사 로그 점검 + 인시던트 보고

## 12. 변경 사항을 PRD에 반영해야 하는 경우

다음은 **PRD 업데이트 동반 필수**:

- 데이터 모델 변경 → 부록 E
- API 엔드포인트 추가/변경 → 부록 G
- 에이전트 인터페이스 변경 → 부록 F
- 워크플로 단계 변경 → 부록 H
- 새 화면 추가 → 부록 D, I 등
- 비기능 요구사항 변경 (성능, 보안) → §7

PR에 PRD 변경분을 함께 포함. 큰 변경은 분리 PR로 먼저 PRD 합의 → 구현 PR.

## 13. 자주 묻는 질문

**Q. 새 의존성을 추가하고 싶은데?**  
A. PR 본문에 (1) 왜 필요한지, (2) 라이선스, (3) 번들 사이즈/메모리 영향, (4) 대안 검토 결과를 적을 것. 보안 의존성은 항상 검토.

**Q. PRD에 없는 화면을 추가해야 할 것 같다**  
A. 먼저 GitLab 이슈에 제안 → PRD 업데이트 PR → 구현 PR 순서. 추측으로 만들지 말 것.

**Q. 테스트가 너무 오래 걸린다**  
A. 단위 테스트는 모두 합쳐 1분 이내가 목표. 느린 테스트는 `@pytest.mark.slow`로 마크하고 nightly만 실행.

**Q. Claude Code / Codex / Cursor를 어떻게 효과적으로 쓸까?**  
A. 한 번에 한 task만 작업시킬 것. PRD 해당 §과 본 문서 §5 (컨벤션), §8 (금지 사항), §9 (패턴)를 컨텍스트로 항상 함께 제공할 것.

---

## 부록: Make 명령어

| 명령 | 설명 |
|---|---|
| `make setup` | 모든 워크스페이스 의존성 설치 |
| `make lint` | Black, Ruff, ESLint, Prettier, mypy, tsc 전부 실행 |
| `make test` | 단위 + 통합 테스트 (pytest + vitest) |
| `make test-e2e` | Playwright e2e (사전 docker compose up 필요) |
| `make migrate` | Alembic 마이그레이션 적용 |
| `make dev` | docker compose로 backend + frontend + postgres + redis + temporal 기동 |
| `make worker` | Temporal worker 단독 실행 |
| `make openapi` | OpenAPI 스펙 export + 프론트 타입 생성 |
