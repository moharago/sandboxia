# Client (Frontend)

## Tech Stack

- **Libraries**: React 19
- **Language**: TypeScript 5
- **Framework**: Next.js 16 (App Router)
- **Package**: pnpm
- **UI**: TailwindCSS 4
- **State**: Zustand (persist), TanStack Query 5
- **Build**: React Compiler (babel-plugin-react-compiler)

## Repository Structure

```text
client/
├── src/
│   ├── app/                # App Router 페이지
│   ├── components/         # React 컴포넌트
│   ├── hooks/              # Custom React Hooks
│   ├── lib/                # API/유틸리티
│   └── types/              # TypeScript 타입 정의
│       ├── api/            # API 요청/응답 타입
│       ├── components/     # 컴포넌트 타입
│       └── pages/          # 페이지 타입
├── .env.example
├── eslint.config.mjs
├── next.config.mjs
├── pnpm-lock.yaml
├── pnpm-workspace.yaml
├── package.json
├── postcss.config.mjs
├── tsconfig.json
└── README.md
```

## Quickstart

### Install

```bash
cd client
pnpm install
```

### Environment Variables

`.env` 설정

```env
NEXT_PUBLIC_API_BASE_URL="..."
```

## Run

### Dev Server

```bash
pnpm run dev
```

**Local:**

```
http://localhost:3000/
```
