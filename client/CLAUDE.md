# Client CLAUDE.md

Next.js + React 기반 클라이언트 개발 가이드.

## 프로젝트 구조

```
client/src/
├── app/                        # App Router 페이지
│   ├── (auth)/                 # 인증 관련 Route Group
│   ├── consultation/           # 컨설팅 메인 페이지
│   │   ├── new/               # 새 컨설팅 시작
│   │   ├── [id]/              # 컨설팅 상세
│   │   │   ├── structure/     # 1. 서비스 구조화
│   │   │   ├── eligibility/   # 2. 대상성 판단
│   │   │   ├── track/         # 3. 트랙 추천
│   │   │   ├── draft/         # 4. 신청서 초안
│   │   │   ├── strategy/      # 5. 전략 추천
│   │   │   └── risk/          # 6. 리스크 체크
│   │   └── page.tsx           # 컨설팅 목록
│   ├── api/                    # Route Handlers
│   └── layout.tsx
├── components/
│   ├── ui/                     # 재사용 UI (Button, Input, Modal, Card)
│   ├── features/               # 기능별 컴포넌트
│   │   ├── consultation/       # 컨설팅 관련
│   │   ├── form-builder/       # 동적 폼 렌더링
│   │   ├── document-viewer/    # 문서 뷰어
│   │   └── agent-status/       # 에이전트 상태 표시
│   └── layouts/                # 레이아웃 컴포넌트
├── hooks/
│   ├── queries/                # TanStack Query 훅
│   │   ├── use-consultation-query.ts
│   │   ├── use-agent-status-query.ts
│   │   └── use-draft-query.ts
│   └── mutations/              # TanStack Mutation 훅
│       ├── use-structure-mutation.ts
│       ├── use-eligibility-mutation.ts
│       └── use-draft-mutation.ts
├── lib/
│   ├── api/                    # API 클라이언트
│   │   ├── client.ts           # 기본 fetch 클라이언트
│   │   ├── agents.ts           # 에이전트 API
│   │   └── consultations.ts    # 컨설팅 API
│   └── utils/                  # 유틸리티
├── stores/                     # Zustand 스토어
│   ├── consultation-store.ts   # 현재 컨설팅 상태
│   └── ui-store.ts             # UI 상태
└── types/
    ├── api/                    # API 응답 타입
    │   ├── agent.ts
    │   └── consultation.ts
    └── components/             # 컴포넌트 Props 타입
```

## 에이전트 연동 패턴

### API 클라이언트

```typescript
// lib/api/agents.ts
export const agentsApi = {
  // 1. 서비스 구조화
  structure: (data: StructureRequest) =>
    apiClient.post<StructureResponse>('/agents/structure', data),

  // 2. 대상성 판단
  evaluateEligibility: (data: EligibilityRequest) =>
    apiClient.post<EligibilityResponse>('/agents/eligibility', data),

  // 3. 트랙 추천
  recommendTrack: (data: TrackRequest) =>
    apiClient.post<TrackResponse>('/agents/track', data),

  // 4. 신청서 초안
  generateDraft: (data: DraftRequest) =>
    apiClient.post<DraftResponse>('/agents/draft', data),

  // 5. 전략 추천
  adviseStrategy: (data: StrategyRequest) =>
    apiClient.post<StrategyResponse>('/agents/strategy', data),

  // 6. 리스크 체크
  checkRisk: (data: RiskRequest) =>
    apiClient.post<RiskResponse>('/agents/risk', data),

  // 비동기 상태 확인
  getStatus: (taskId: string) =>
    apiClient.get<AgentStatus>(`/agents/status/${taskId}`),
};
```

### TanStack Query 훅

```typescript
// hooks/mutations/use-structure-mutation.ts
export function useStructureMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: agentsApi.structure,
    onSuccess: (data, variables) => {
      // 구조화 결과를 캐시에 저장
      queryClient.setQueryData(
        consultationKeys.structure(variables.consultationId),
        data
      );
    },
  });
}
```

## 주요 컴포넌트

### 동적 폼 렌더링

서버에서 생성된 Form Schema를 기반으로 폼 렌더링:

```typescript
// components/features/form-builder/DynamicForm.tsx
interface DynamicFormProps {
  schema: FormSchema;           // 서버에서 받은 스키마
  initialValues?: FormData;     // 자동 채움 값
  onSubmit: (data: FormData) => void;
  onFieldChange?: (fieldId: string, value: unknown) => void;
}
```

### 에이전트 상태 표시

```typescript
// components/features/agent-status/AgentProgress.tsx
interface AgentProgressProps {
  taskId: string;
  agentType: AgentType;  // 'structure' | 'eligibility' | ...
  onComplete?: (result: AgentResult) => void;
}
```

## 개발 명령어

```bash
# 의존성 설치
pnpm install

# 개발 서버 실행
pnpm run dev

# 빌드
pnpm run build

# 린트
pnpm run lint
```

## 환경 변수

```bash
# .env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## 페이지별 에이전트 연동

| 페이지 | 에이전트 | 주요 기능 |
|--------|----------|----------|
| `/consultation/[id]/structure` | 1. Structurer | 파일 업로드, 동적 폼, 필드 수정 |
| `/consultation/[id]/eligibility` | 2. Evaluator | 대상성 판단 결과, 유사 사례 표시 |
| `/consultation/[id]/track` | 3. Recommender | 트랙별 점수, 추천 사유 |
| `/consultation/[id]/draft` | 4. Drafter | 초안 에디터, 섹션별 편집, 내보내기 |
| `/consultation/[id]/strategy` | 5. Advisor | 승인 패턴, 인용 후보 |
| `/consultation/[id]/risk` | 6. Checker | 체크리스트, 리스크 알림, 개선 제안 |

## 상태 관리 전략

- **서버 상태**: TanStack Query (캐싱, 리페칭)
- **클라이언트 상태**: Zustand (UI 상태, 현재 컨설팅 컨텍스트)
- **폼 상태**: React Hook Form + Zod (validation)

## UI 컴포넌트

Tailwind CSS 기반, shadcn/ui 스타일 참고:
- Button, Input, Select, Checkbox
- Card, Modal, Toast
- Table, Tabs, Accordion
- Progress, Badge, Alert
