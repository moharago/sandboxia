# Vibe Coding with Claude Code

Claude Code를 활용한 AI 기반 협업 개발 경험을 정리한 문서입니다.

## Overview

SandboxIA 프로젝트에서 Claude Code를 적극 활용하여 개발 생산성을 극대화했습니다. Skills, Subagents, MCP 서버를 조합하여 코드 컨벤션 유지, 성능 최적화, RAG 평가 자동화 등을 구현했습니다.

### 핵심 활용 영역

| 영역 | 활용 도구 | 효과 |
|------|----------|------|
| 코드 컨벤션 | Custom Skills | 팀원 간 일관된 코드 스타일 유지 |
| 성능 최적화 | Vercel Best Practices Skill | React/Next.js 코드 리팩토링 |
| RAG 평가 | Subagent + Skill | 평가 파이프라인 자동화 |
| DB 개발 | Supabase MCP | 스키마 조회 및 마이그레이션 효율화 |

---

## 1. Code Conventions via Custom Skills

팀 프로젝트에서 여러 개발자가 일관된 코드를 작성할 수 있도록 Custom Skills를 설계하고 적용했습니다.

### 1.1 Client Conventions (`client-conventions`)

React/Next.js/TypeScript 클라이언트 코드 작성 컨벤션을 정의했습니다.

**트리거 조건:**
- `client/` 폴더 내 작업
- React 컴포넌트 생성
- TanStack Query 훅 작성
- Zustand 스토어 생성

**핵심 컨벤션:**

```typescript
// 컴포넌트 네이밍: PascalCase
export function UserCard({ user }: UserCardProps) { ... }

// Query 훅: use + 동작 + Query
export function useUserQuery(id: string) { ... }

// Mutation 훅: use + 동작 + Mutation
export function useLoginMutation() { ... }

// Zustand 스토어: use + 도메인 + Store
export const useAuthStore = create<AuthState>()((set) => ({ ... }))
```

**React 19 호환 패턴 (컴포넌트 분리 + key prop):**

```tsx
// 서버 데이터 → 로컬 상태 초기화 시 useEffect 경고 방지
function ServiceForm({ project }: { project: Project }) {
  const [formState, setFormState] = useState({ name: project.name });
  // ...
}

function ServicePage({ id }: { id: string }) {
  const { data, isLoading } = useProjectQuery(id);
  if (isLoading) return <Loading />;

  // key로 project 변경 시 폼 리셋
  return <ServiceForm key={data.id} project={data} />;
}
```

### 1.2 Server Conventions (`server-conventions`)

Python/FastAPI/LangGraph 서버 코드 작성 컨벤션을 정의했습니다.

**트리거 조건:**
- `server/` 폴더 내 작업
- FastAPI 라우터 생성
- LangGraph 에이전트 구현
- Pydantic 스키마 작성

**핵심 컨벤션:**

```python
# 노드 함수: snake_case + _node 접미사
async def retrieve_node(state: AgentState) -> dict:
    """문서 검색 노드"""
    ...

# Pydantic 스키마: Base → Create/Update → Response 계층
class UserBase(BaseModel):
    email: EmailStr
    name: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: str
    created_at: datetime
    model_config = {"from_attributes": True}
```

**LangGraph 에이전트 패턴:**

```python
# StateGraph 정의
graph = StateGraph(ResearchState)
graph.add_node("retrieve", retrieve_node)
graph.add_node("generate", generate_node)
graph.set_entry_point("retrieve")
graph.add_edge("retrieve", "generate")
graph.add_conditional_edges("generate", should_continue, {...})

research_agent = graph.compile()
```

### 1.3 효과

| Before | After |
|--------|-------|
| 개발자마다 다른 네이밍 규칙 | 일관된 PascalCase/camelCase/snake_case 적용 |
| PR 리뷰에서 스타일 지적 반복 | 스타일 이슈 자동 방지 |
| 새 팀원 온보딩 시간 ↑ | Skills 참조로 빠른 적응 |

---

## 2. Performance Optimization via Vercel Best Practices

Vercel의 공식 React 성능 최적화 가이드라인을 Skill로 통합하여 코드 리팩토링에 활용했습니다.

### 2.1 Skill 구성

57개 규칙, 8개 카테고리로 구성된 성능 최적화 가이드라인:

| Priority | Category | Impact |
|----------|----------|--------|
| 1 | Eliminating Waterfalls | CRITICAL |
| 2 | Bundle Size Optimization | CRITICAL |
| 3 | Server-Side Performance | HIGH |
| 4 | Client-Side Data Fetching | MEDIUM-HIGH |
| 5 | Re-render Optimization | MEDIUM |
| 6 | Rendering Performance | MEDIUM |
| 7 | JavaScript Performance | LOW-MEDIUM |
| 8 | Advanced Patterns | LOW |

### 2.2 적용 사례

**워터폴 제거 (async-parallel):**

```typescript
// Before: 순차 실행 (워터폴)
const user = await getUser(id);
const posts = await getPosts(id);
const comments = await getComments(id);

// After: 병렬 실행
const [user, posts, comments] = await Promise.all([
  getUser(id),
  getPosts(id),
  getComments(id),
]);
```

**번들 최적화 (bundle-dynamic-imports):**

```typescript
// Before: 무거운 라이브러리 직접 import
import { Editor } from '@monaco-editor/react';

// After: 동적 import로 코드 스플리팅
const Editor = dynamic(() => import('@monaco-editor/react'), {
  loading: () => <Skeleton />,
  ssr: false,
});
```

**서버 컴포넌트 캐싱 (server-cache-react):**

```typescript
// React.cache()로 요청 중복 제거
const getUser = cache(async (id: string) => {
  return await db.user.findUnique({ where: { id } });
});
```

### 2.3 리팩토링 워크플로우

```
1. Claude Code에 리팩토링 요청
2. Vercel Best Practices Skill 자동 트리거
3. 우선순위별 규칙 적용 (CRITICAL → HIGH → MEDIUM)
4. 코드 수정 + 설명 제공
```

---

## 3. RAG Evaluation Automation

Subagent와 Skill을 조합하여 RAG 평가 파이프라인을 자동화했습니다.

### 3.1 아키텍처

```
┌──────────────────────────────────────────────────────────┐
│                     /rag-eval 명령어                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐     ┌──────────────────────────┐  │
│  │   rag-eval       │     │    rag-evaluator         │  │
│  │   Skill          │────▶│    Subagent              │  │
│  │   (파싱/라우팅)   │     │    (평가 실행/분석)       │  │
│  └──────────────────┘     └──────────────────────────┘  │
│           │                           │                  │
│           ▼                           ▼                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │              평가 스크립트 실행                    │   │
│  │  uv run python eval/r3/run_evaluation.py         │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 3.2 Skill 기반 명령어 파싱

자연어 명령을 CLI 옵션으로 자동 변환:

| 자연어 | CLI 옵션 |
|--------|----------|
| `top-k 10`, `10개씩` | `--top_k 10` |
| `C1 적용해줘`, `청킹 C1` | `--config C1 --reset` |
| `baseline으로 저장` | `--output 2026-03-02_baseline` |
| `qdrant H1으로` | `--vectordb qdrant --hybrid H1` |

### 3.3 실행 모드

**모드 A: 단일 평가 (직접 실행)**

```bash
# 사용자: "/rag-eval R3 top-k 10"
# Claude가 직접 실행
cd server && uv run python eval/r3/run_evaluation.py --top_k 10
```

**모드 A+: 프리셋 적용 + 평가**

```bash
# 사용자: "/rag-eval R3 C3 E1 평가"
# 1단계: 데이터 수집 + Vector DB 생성
cd server && uv run python scripts/collect_laws.py --config C3 E1 --reset

# 2단계: 평가 실행
uv run python eval/r3/run_evaluation.py --output 2026-03-02_C3_E1
```

**모드 B: A/B 테스트 (Subagent 순차 호출)**

```bash
# 사용자: "/rag-eval R3 C1~C3 각각 평가"
# rag-evaluator Subagent가 순차 실행 (DB 충돌 방지)
# C1 실행 → 완료 대기 → C2 실행 → 완료 대기 → C3 실행
# 결과 비교표 자동 생성
```

**모드 C: 전체 RAG 평가 (병렬 호출)**

```bash
# 사용자: "/rag-eval 전체 RAG"
# R1, R2, R3 각각 별도 Subagent로 병렬 실행
# 종합 리포트 자동 작성
```

### 3.4 평가 결과 자동 분석

```markdown
## 변경요소 분석: chunking (청킹 전략)

| 프리셋 | MH-Recall | Recall | MRR | Latency |
|--------|-----------|--------|-----|---------|
| C0 | 0.43 | 0.34 | 0.49 | 128ms |
| C1 | 0.52 | 0.41 | 0.55 | 142ms |
| C3 | 0.58 | 0.45 | 0.52 | 156ms |

**분석**:
- 최고 성능: C3 (MH-Recall 0.58)
- C0 → C3: +35% 개선
- 권장: C3 (구조 신호 강화형)
```

### 3.5 효과

| Before | After |
|--------|-------|
| 수동으로 CLI 명령어 입력 | 자연어로 평가 요청 |
| 프리셋 변경 시 수집 → 평가 수동 실행 | `--reset` 포함 자동 파이프라인 |
| 결과 파일 직접 열어서 비교 | 자동 비교표 + 권장사항 생성 |
| A/B 테스트 시 순서 관리 필요 | Subagent가 순차/병렬 자동 결정 |

---

## 4. Efficient Development with MCP Servers

Model Context Protocol (MCP) 서버를 연동하여 개발 효율을 높였습니다.

### 4.1 활성화된 MCP 서버

```json
{
  "enabledMcpjsonServers": [
    "supabase",
    "context7",
    "serena"
  ]
}
```

### 4.2 Supabase MCP 활용

**스키마 조회:**

```
Claude: "projects 테이블 스키마 확인해줘"
→ Supabase MCP가 list_tables, execute_sql 호출
→ 테이블 구조, 컬럼 타입, RLS 정책 반환
```

**마이그레이션:**

```
Claude: "user 테이블에 phone 컬럼 추가해줘"
→ apply_migration 호출
→ DDL 자동 생성 및 적용
```

**타입 생성:**

```
Claude: "DB 스키마 기반 TypeScript 타입 생성해줘"
→ generate_typescript_types 호출
→ client/src/types/database.ts 자동 생성
```

### 4.3 Context7 MCP 활용

최신 라이브러리 문서를 실시간 검색:

```
Claude: "Next.js 15에서 새로운 캐싱 전략 알려줘"
→ resolve-library-id("nextjs") → query-docs("caching strategy")
→ 최신 공식 문서 기반 답변 제공
```

**활용 사례:**
- LangGraph 최신 API 확인
- TanStack Query v5 변경사항 조회
- React 19 신규 기능 검색

### 4.4 Serena MCP 활용 (시맨틱 코드 탐색)

대규모 코드베이스에서 심볼 기반 탐색:

```
Claude: "search_domain_law 함수 참조 위치 찾아줘"
→ find_referencing_symbols 호출
→ 모든 import/호출 위치 반환
```

**리팩토링 지원:**

```
Claude: "EligibilityState를 EvaluatorState로 리네이밍"
→ rename_symbol 호출
→ 모든 참조 위치 일괄 변경
```

---

## 5. 통합 워크플로우 예시

실제 개발 시나리오에서 Skills, Subagents, MCP가 어떻게 조합되는지 보여줍니다.

### 시나리오: 새 에이전트 추가

```
1. 요청: "Track Recommender 에이전트 구현해줘"

2. Server Conventions Skill 트리거:
   - agents/track_recommender/ 디렉토리 생성
   - state.py, nodes.py, tools.py, graph.py 스캐폴딩
   - LangGraph 패턴 적용

3. Context7 MCP로 LangGraph 최신 문서 참조:
   - StateGraph 사용법 확인
   - conditional_edges 패턴 적용

4. Supabase MCP로 관련 테이블 스키마 확인:
   - projects 테이블 구조 조회
   - 필요한 컬럼 추가

5. 구현 완료 후 RAG 평가:
   /rag-eval R2 strategy all
   → 전략별 성능 비교표 자동 생성
```

### 시나리오: 프론트엔드 성능 최적화

```
1. 요청: "서비스 목록 페이지 로딩 속도 개선해줘"

2. Vercel Best Practices Skill 트리거:
   - async-parallel: API 병렬 호출
   - bundle-dynamic-imports: 무거운 컴포넌트 지연 로딩
   - server-cache-react: 캐싱 적용

3. Client Conventions Skill 참조:
   - TanStack Query 패턴 적용
   - Query Keys Factory 구현

4. 리팩토링 코드 생성 + 설명 제공
```

---

## 6. 설정 파일 구조

Claude Code 설정 전체 구조:

```
.claude/
├── settings.local.json          # MCP 서버 활성화
├── agents/
│   └── rag-evaluator.md         # RAG 평가 Subagent
└── skills/
    ├── client-conventions/      # 클라이언트 컨벤션
    │   └── SKILL.md
    ├── server-conventions/      # 서버 컨벤션
    │   └── SKILL.md
    ├── rag-eval/                # RAG 평가 실행 (Slash Command)
    │   └── SKILL.md
    └── rag-evaluation/          # RAG 평가 가이드
        └── SKILL.md

.agents/skills/
└── vercel-react-best-practices/ # Vercel 성능 최적화
    ├── SKILL.md
    └── rules/                   # 57개 규칙 파일
```

---

## Key Takeaways

### 1. Custom Skills로 팀 컨벤션 체계화

- 암묵적 규칙을 명시적 Skills로 문서화
- Claude가 자동으로 컨벤션 적용
- 코드 리뷰 부담 감소, 일관성 향상

### 2. Subagent로 복잡한 작업 분리

- 메인 컨텍스트 보호 (대량 분석은 Subagent에서)
- 순차/병렬 실행 자동 결정
- 결과만 요약해서 전달

### 3. MCP로 외부 시스템 연동

- Supabase: DB 스키마 ↔ 코드 동기화
- Context7: 최신 문서 실시간 참조
- Serena: 대규모 코드베이스 탐색

### 4. Skill 조합으로 워크플로우 자동화

- 단일 명령어 → 다단계 파이프라인 실행
- 자연어 → CLI 옵션 자동 변환
- 결과 분석 및 권장사항까지 자동 생성

---

## 포트폴리오 어필 포인트

### 기술적 역량

- **AI 협업 개발**: Claude Code의 Skills, Subagents, MCP를 조합한 워크플로우 설계
- **자동화 설계**: 반복 작업을 자연어 명령으로 자동화
- **코드 품질 관리**: 컨벤션 기반 일관된 코드 생성

### 프로젝트 기여

- 팀원 간 코드 스타일 통일 → PR 리뷰 시간 단축
- RAG 평가 자동화 → 실험 사이클 가속화
- 성능 최적화 패턴 적용 → 번들 사이즈 감소, 로딩 속도 개선

### 학습 자세

- 새로운 도구(MCP, Skills) 적극 도입
- 공식 Best Practices 학습 및 적용 (Vercel)
- 자동화를 통한 개발 생산성 극대화
