# Client (Frontend)

규제 샌드박스 컨설팅 시스템의 Next.js 프론트엔드

## Tech Stack

| 영역 | 기술 |
|------|------|
| Framework | Next.js 16 (App Router) |
| Language | TypeScript 5 |
| UI | React 19, TailwindCSS 4, Radix UI |
| State | Zustand 5 (Client), TanStack Query 5 (Server) |
| Form | React Hook Form + Zod |
| Editor | TipTap (Rich Text) |
| Auth | Supabase Auth |

## Getting Started

### Prerequisites

- Node.js 20+
- pnpm 9+

### Installation

```bash
cd client
pnpm install
```

### Environment Variables

`.env.local` 파일 생성:

```env
# Backend API (개발)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### Development

```bash
# 개발 서버 실행
pnpm run dev

# 빌드
pnpm run build

# 린트
pnpm run lint
```

**Local:** http://localhost:3000

## Project Structure

```
client/
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── (marketing)/              # Public pages (landing, login, signup)
│   │   │   ├── page.tsx              # Landing page
│   │   │   ├── login/
│   │   │   ├── signup/
│   │   │   └── onboarding/
│   │   ├── (dashboard)/              # Protected pages
│   │   │   ├── dashboard/            # Project list
│   │   │   ├── projects/[id]/        # Project detail
│   │   │   │   ├── service/          # Step 1: Service structuring
│   │   │   │   ├── eligibility/      # Step 2: Eligibility evaluation
│   │   │   │   ├── track/            # Step 3: Track recommendation
│   │   │   │   └── draft/            # Step 4: Application drafting
│   │   │   └── my-account/           # User profile
│   │   ├── auth/callback/            # OAuth callback
│   │   ├── layout.tsx                # Root layout
│   │   └── globals.css               # Global styles
│   │
│   ├── components/
│   │   ├── ui/                       # Reusable UI primitives (20+)
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── modal.tsx
│   │   │   ├── select.tsx
│   │   │   ├── tabs.tsx
│   │   │   ├── ai-loader.tsx         # Agent progress indicator
│   │   │   ├── file-upload.tsx
│   │   │   ├── tiptap-editor.tsx     # Rich text editor
│   │   │   └── ...
│   │   ├── features/                 # Feature components
│   │   │   ├── analysis/             # AI analysis cards
│   │   │   ├── dashboard/            # Dashboard (Pipeline, ProjectCard)
│   │   │   ├── draft/                # Draft forms (FormSectionList, ReferencePanel)
│   │   │   ├── landing/              # Landing page sections
│   │   │   ├── project/              # Project (ServiceForm, StepNav)
│   │   │   └── wizard/               # Navigation components
│   │   └── layouts/                  # Layout components
│   │       ├── DashboardLayout.tsx
│   │       ├── Header.tsx
│   │       ├── Sidebar.tsx
│   │       └── Footer.tsx
│   │
│   ├── hooks/
│   │   ├── queries/                  # TanStack Query (Read)
│   │   │   ├── use-projects-query.ts
│   │   │   ├── use-eligibility-query.ts
│   │   │   ├── use-track-query.ts
│   │   │   └── use-draft-query.ts
│   │   ├── mutations/                # TanStack Mutation (Write)
│   │   │   ├── use-service-mutation.ts
│   │   │   ├── use-eligibility-mutation.ts
│   │   │   ├── use-track-mutation.ts
│   │   │   └── use-draft-mutation.ts
│   │   └── streaming/
│   │       └── use-agent-progress.ts # SSE subscription
│   │
│   ├── lib/
│   │   ├── api/                      # API client functions
│   │   │   ├── agents.ts
│   │   │   ├── projects.ts
│   │   │   ├── draft.ts
│   │   │   ├── eligibility.ts
│   │   │   └── track.ts
│   │   ├── supabase/
│   │   │   ├── client.ts             # Browser client
│   │   │   └── server.ts             # Server client
│   │   └── utils/
│   │       ├── cn.ts                 # Class name utility
│   │       ├── date.ts
│   │       └── step-utils.ts
│   │
│   ├── stores/                       # Zustand stores
│   │   ├── auth-store.ts             # Authentication state
│   │   ├── project-store.ts          # Project status
│   │   ├── ui-store.ts               # UI state (sidebar, loader)
│   │   ├── user-store.ts             # User profile
│   │   └── wizard-store.ts           # Step navigation & form data
│   │
│   ├── types/
│   │   ├── api/                      # API types
│   │   │   ├── project.ts
│   │   │   ├── eligibility.ts
│   │   │   ├── track.ts
│   │   │   └── draft.ts
│   │   └── data/                     # Internal types
│   │       └── project.ts            # Enums (ProjectStatus, Track)
│   │
│   └── data/                         # Static data
│       ├── formData.json             # Form schemas
│       └── tracks.json               # Track definitions
│
├── next.config.mjs                   # Next.js config (API rewrites)
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

## Key Features

### 1. Dashboard

프로젝트 목록 관리 (필터링, 검색, 정렬, 페이지네이션)

**경로:** `/dashboard`

```
┌─────────────────────────────────────────────────┐
│  Pipeline Filter (상담중 → 작성중 → 검토중 → 완료)  │
├─────────────────────────────────────────────────┤
│  [Search] [Sort] [Grid/List]                    │
├─────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ Project │ │ Project │ │ Project │           │
│  │ Card    │ │ Card    │ │ Card    │           │
│  └─────────┘ └─────────┘ └─────────┘           │
├─────────────────────────────────────────────────┤
│  Pagination                                     │
└─────────────────────────────────────────────────┘
```

### 2. Service Structuring (Step 1)

HWP 파일 업로드 및 서비스 정보 입력

**경로:** `/projects/[id]/service`

- 파일 드래그 앤 드롭 (react-dropzone)
- 회사명, 서비스명, 서비스 설명 폼
- SSE 기반 실시간 진행 상태 표시

### 3. Eligibility Evaluation (Step 2)

규제 샌드박스 대상 여부 판단 결과

**경로:** `/projects/[id]/eligibility`

- 판정 결과 (필요/불필요/불명확)
- 신뢰도 점수
- 직접 출시 시 리스크 분석
- 유사 승인 사례 & 관련 규제 참조

### 4. Track Recommendation (Step 3)

최적 트랙 추천 (3종 비교)

**경로:** `/projects/[id]/track`

| 트랙 | 설명 |
|------|------|
| 신속확인 (quick_check) | 규제 적용 여부 신속 확인 |
| 실증특례 (demo) | 제한된 조건에서 실증 |
| 임시허가 (temp_permit) | 조건부 시장 진입 허용 |

### 5. Application Drafting (Step 4)

신청서 초안 자동 작성 및 편집

**경로:** `/projects/[id]/draft`

- 트랙별 동적 폼 렌더링
- TipTap 기반 리치 텍스트 편집
- 카드별 자동 저장 (PATCH)
- 유사 사례 참조 패널
- DOCX 다운로드

## Architecture Patterns

### State Management

```
┌─────────────────────────────────────────────────────┐
│                    State Layer                      │
├─────────────────────────────────────────────────────┤
│  Server State        │  Client State                │
│  (TanStack Query)    │  (Zustand)                   │
│  ─────────────────   │  ───────────────             │
│  • Project list      │  • Auth user                 │
│  • Eligibility       │  • UI state (sidebar)        │
│  • Track results     │  • Wizard step               │
│  • Draft data        │  • Global loader             │
├─────────────────────────────────────────────────────┤
│  Form State (React Hook Form + Zod)                 │
│  • Field values, validation, dirty state            │
└─────────────────────────────────────────────────────┘
```

### API Client Pattern

```typescript
// lib/api/agents.ts
const response = await fetch(`${API_BASE}/agents/structure`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  },
  body: JSON.stringify(data),
});
```

### TanStack Query Pattern

```typescript
// hooks/queries/use-projects-query.ts
export const projectKeys = {
  all: ["projects"] as const,
  list: () => [...projectKeys.all, "list"] as const,
  detail: (id: string) => [...projectKeys.all, "detail", id] as const,
};

export function useProjectsQuery() {
  return useQuery({
    queryKey: projectKeys.list(),
    queryFn: fetchProjects,
  });
}
```

### SSE Progress Streaming

```typescript
// hooks/streaming/use-agent-progress.ts
export function useAgentProgress({
  projectId,
  useGlobalLoader,
  globalLoaderMessage,
}: Options) {
  useEffect(() => {
    const eventSource = new EventSource(
      `${API_BASE}/agents/progress/subscribe/${projectId}`
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // Update progress state
    };

    return () => eventSource.close();
  }, [projectId]);
}
```

## UI Components

shadcn/ui 스타일 기반 Radix UI 컴포넌트:

| 컴포넌트 | 용도 |
|----------|------|
| `Button` | 버튼 (variant, size) |
| `Card` | 카드 컨테이너 |
| `Modal` | 모달 다이얼로그 |
| `Select` | 드롭다운 선택 |
| `Tabs` | 탭 네비게이션 |
| `AILoader` | 에이전트 진행 상태 표시 |
| `FileUpload` | 파일 드래그 앤 드롭 |
| `TiptapEditor` | 리치 텍스트 편집기 |

## Authentication

Supabase Auth를 사용한 인증:

1. `AuthProvider`가 앱 초기화 시 세션 복원
2. `auth-store`에서 토큰 관리
3. API 요청 시 `Authorization: Bearer {token}` 헤더 추가
4. Protected route는 `user` 존재 여부로 접근 제어

## Performance Optimizations

- **React Compiler**: 자동 메모이제이션 (babel-plugin-react-compiler)
- **TanStack Query**: 캐싱, 중복 요청 제거, 백그라운드 리페치
- **Zustand Persist**: 로컬 스토리지 기반 상태 복원
- **Next.js Image**: 이미지 자동 최적화
- **Code Splitting**: 동적 import로 번들 분할

## Configuration

### next.config.mjs

```javascript
// API 프록시 설정 (CORS 우회)
async rewrites() {
  return [
    { source: "/api/v1/:path*", destination: `${BACKEND_URL}/api/v1/:path*` },
    { source: "/api/users/:path*", destination: `${BACKEND_URL}/api/users/:path*` },
  ];
}
```

### Path Aliases

```json
// tsconfig.json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

## Scripts

| 명령어 | 설명 |
|--------|------|
| `pnpm run dev` | 개발 서버 (http://localhost:3000) |
| `pnpm run build` | 프로덕션 빌드 |
| `pnpm run start` | 프로덕션 서버 |
| `pnpm run lint` | ESLint 실행 |

## Deployment

### Vercel 배포

#### 1. Vercel CLI 배포

```bash
# Vercel CLI 설치
npm i -g vercel

# 로그인
vercel login

# 프로덕션 배포
cd client
vercel --prod
```

#### 2. GitHub 연동 (권장)

1. [Vercel Dashboard](https://vercel.com/dashboard)에서 "New Project" 클릭
2. GitHub 저장소 연결
3. Root Directory를 `client`로 설정
4. 환경 변수 설정 후 Deploy

**빌드 설정:**
| 설정 | 값 |
|------|-----|
| Framework Preset | Next.js |
| Root Directory | `client` |
| Build Command | `pnpm run build` |
| Output Directory | `.next` |
| Install Command | `pnpm install` |

#### 환경 변수 (Vercel Dashboard)

```env
# Backend API
NEXT_PUBLIC_API_BASE_URL=https://api.your-domain.com

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

#### 배포 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                      Vercel Platform                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   Edge Network (CDN)                 │   │
│  │        Global distribution for static assets         │   │
│  └───────────────────────┬─────────────────────────────┘   │
│                          │                                  │
│  ┌───────────────────────▼─────────────────────────────┐   │
│  │                  Next.js Runtime                     │   │
│  │   ┌─────────────┐  ┌─────────────┐  ┌───────────┐   │   │
│  │   │ Static Gen  │  │    SSR      │  │   ISR     │   │   │
│  │   │  (pages)    │  │ (dynamic)   │  │ (revalid) │   │   │
│  │   └─────────────┘  └─────────────┘  └───────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Features:                                                  │
│  • Automatic HTTPS                                          │
│  • Preview Deployments (PR별 자동 배포)                      │
│  • Analytics & Web Vitals                                   │
│  • Edge Functions                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
           │
           │ API Requests (HTTPS)
           ▼
┌─────────────────────────────────────────────────────────────┐
│                   AWS EC2 (Backend)                          │
│                   FastAPI + ChromaDB                         │
└─────────────────────────────────────────────────────────────┘
```

#### Preview Deployments

GitHub PR 생성 시 자동으로 Preview URL 생성:
- `https://sandboxia-<branch>-<team>.vercel.app`
- PR 머지 전 기능 테스트 가능
- PR 코멘트에 자동으로 Preview URL 추가

#### 도메인 설정

```bash
# 커스텀 도메인 추가
vercel domains add your-domain.com

# DNS 설정 후 SSL 자동 발급
```

#### 트러블슈팅

**빌드 실패 시:**
```bash
# 로컬에서 빌드 테스트
pnpm run build

# 환경 변수 확인
vercel env ls
```

**API 연결 오류 시:**
- `NEXT_PUBLIC_API_BASE_URL`이 올바르게 설정되었는지 확인
- Backend CORS 설정에 Vercel 도메인 추가 필요
