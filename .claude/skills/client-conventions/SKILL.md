---
name: client-conventions
description: "React/Next.js/TypeScript 클라이언트 코드 작성 컨벤션. 클라이언트 코드 생성, 컴포넌트 작성, API 연동, 상태관리 작업 시 사용. 트리거 - client 폴더 내 작업, React 컴포넌트 생성, Next.js 페이지 작성, TanStack Query 훅 작성, Zustand 스토어 생성"
---

# Client Conventions

React, Next.js, TypeScript, TanStack Query, Zustand, Tailwind CSS 기반 클라이언트 코드 컨벤션.

## 기술 스택

- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS
- **State**: Zustand (client), TanStack Query (server)
- **Package Manager**: pnpm

## 프로젝트 구조

```
client/src/
├── app/                    # App Router 페이지
│   ├── (auth)/            # Route Groups
│   ├── api/               # Route Handlers
│   └── layout.tsx
├── components/
│   ├── ui/                # 재사용 UI (Button, Input, Modal)
│   ├── features/          # 기능별 컴포넌트
│   └── layouts/           # 레이아웃 컴포넌트
├── hooks/
│   ├── queries/           # TanStack Query 훅
│   ├── mutations/         # TanStack Mutation 훅
│   └── use-*.ts           # 커스텀 훅
├── lib/
│   ├── api/               # API 클라이언트
│   ├── utils/             # 유틸리티 함수
│   └── constants/         # 상수
├── stores/                # Zustand 스토어
└── types/
    ├── api/               # API 타입
    └── components/        # 컴포넌트 타입
```

## 네이밍 컨벤션

| 대상 | 컨벤션 | 예시 |
|------|--------|------|
| 컴포넌트 파일 | PascalCase | `UserProfile.tsx` |
| 훅 파일 | kebab-case, use- 접두사 | `use-auth.ts` |
| 유틸리티 | kebab-case | `format-date.ts` |
| 타입 파일 | kebab-case | `user-types.ts` |
| 상수 | SCREAMING_SNAKE_CASE | `API_BASE_URL` |
| 컴포넌트명 | PascalCase | `UserProfile` |
| 함수/변수 | camelCase | `getUserData` |
| 타입/인터페이스 | PascalCase | `UserProfile` |
| Zustand 스토어 | use + 도메인 + Store | `useAuthStore` |
| Query 훅 | use + 동작 + Query | `useUserQuery` |
| Mutation 훅 | use + 동작 + Mutation | `useLoginMutation` |

## 컴포넌트 패턴

### 기본 구조

```tsx
'use client'; // 필요시에만

import { useState } from 'react';
import type { UserCardProps } from '@/types/components';

export function UserCard({ user, onSelect }: UserCardProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div 
      className="rounded-lg border p-4 hover:shadow-md"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <h3 className="text-lg font-semibold">{user.name}</h3>
      <p className="text-gray-600">{user.email}</p>
      {isHovered && (
        <button onClick={() => onSelect(user.id)}>선택</button>
      )}
    </div>
  );
}
```

### 규칙

- named export 사용 (default export 지양)
- Props 타입은 `@/types/components`에 정의
- 'use client'는 실제 필요한 컴포넌트에만 선언
- 이벤트 핸들러: `handle + 동작` (handleClick, handleSubmit)
- 조건부 렌더링: 삼항 연산자보다 `&&` 또는 early return 선호

## TanStack Query 패턴

### Query 훅

```tsx
// hooks/queries/use-user-query.ts
import { useQuery } from '@tanstack/react-query';
import { userApi } from '@/lib/api/user';
import type { User } from '@/types/api';

export const userKeys = {
  all: ['users'] as const,
  lists: () => [...userKeys.all, 'list'] as const,
  list: (filters: UserFilters) => [...userKeys.lists(), filters] as const,
  details: () => [...userKeys.all, 'detail'] as const,
  detail: (id: string) => [...userKeys.details(), id] as const,
};

export function useUserQuery(userId: string) {
  return useQuery({
    queryKey: userKeys.detail(userId),
    queryFn: () => userApi.getUser(userId),
    staleTime: 5 * 60 * 1000,
    enabled: !!userId,
  });
}
```

### Mutation 훅

```tsx
// hooks/mutations/use-update-user-mutation.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { userApi } from '@/lib/api/user';
import { userKeys } from '@/hooks/queries/use-user-query';

export function useUpdateUserMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: userApi.updateUser,
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: userKeys.detail(variables.id) });
      queryClient.invalidateQueries({ queryKey: userKeys.lists() });
    },
  });
}
```

### 규칙

- Query Key는 Factory 패턴으로 관리
- staleTime, gcTime 명시적 설정
- enabled 옵션으로 조건부 fetch 제어
- onSuccess에서 관련 쿼리 invalidate

## Zustand 패턴

```tsx
// stores/auth-store.ts
import { create } from 'zustand';
import { persist, devtools } from 'zustand/middleware';
import type { User } from '@/types/api';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
}

interface AuthActions {
  setUser: (user: User) => void;
  logout: () => void;
}

type AuthStore = AuthState & AuthActions;

export const useAuthStore = create<AuthStore>()(
  devtools(
    persist(
      (set) => ({
        // State
        user: null,
        isAuthenticated: false,

        // Actions
        setUser: (user) => set({ user, isAuthenticated: true }),
        logout: () => set({ user: null, isAuthenticated: false }),
      }),
      { name: 'auth-storage' }
    )
  )
);

// Selector 훅 (리렌더링 최적화)
export const useUser = () => useAuthStore((state) => state.user);
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
```

### 규칙

- State와 Actions 인터페이스 분리 정의
- devtools 미들웨어 적용 (개발 디버깅)
- persist는 필요한 스토어에만 적용
- Selector 훅으로 구독 범위 최소화

## API 클라이언트 패턴

```tsx
// lib/api/client.ts
const BASE_URL = process.env.NEXT_PUBLIC_API_URL;

class ApiClient {
  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new ApiError(response.status, await response.text());
    }

    return response.json();
  }

  get<T>(endpoint: string) {
    return this.request<T>(endpoint);
  }

  post<T>(endpoint: string, data: unknown) {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // put, patch, delete...
}

export const apiClient = new ApiClient();
```

```tsx
// lib/api/user.ts
import { apiClient } from './client';
import type { User, UpdateUserRequest } from '@/types/api';

export const userApi = {
  getUser: (id: string) => apiClient.get<User>(`/users/${id}`),
  getUsers: () => apiClient.get<User[]>('/users'),
  updateUser: (data: UpdateUserRequest) => apiClient.put<User>(`/users/${data.id}`, data),
};
```

## 타입 정의 패턴

```tsx
// types/api/user.ts
export interface User {
  id: string;
  email: string;
  name: string;
  createdAt: string;
}

export interface CreateUserRequest {
  email: string;
  name: string;
  password: string;
}

export interface UpdateUserRequest {
  id: string;
  name?: string;
  email?: string;
}

// types/api/index.ts
export * from './user';
export * from './auth';
```

```tsx
// types/components/user.ts
import type { User } from '@/types/api';

export interface UserCardProps {
  user: User;
  onSelect: (id: string) => void;
  className?: string;
}

export interface UserListProps {
  users: User[];
  isLoading?: boolean;
}
```

## Tailwind 규칙

- 인라인 스타일 사용 금지
- 복잡한 스타일은 `clsx` 또는 `cn` 유틸리티 사용
- 반복되는 스타일 조합은 컴포넌트로 추출
- 다크모드: `dark:` prefix 사용

```tsx
// lib/utils/cn.ts
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

## Import 순서

```tsx
// 1. React/Next.js
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

// 2. 외부 라이브러리
import { useQuery } from '@tanstack/react-query';
import { clsx } from 'clsx';

// 3. 내부 모듈 (절대 경로)
import { useAuthStore } from '@/stores/auth-store';
import { userApi } from '@/lib/api/user';
import { UserCard } from '@/components/features/user/UserCard';

// 4. 타입 (type-only import)
import type { User } from '@/types/api';
import type { UserCardProps } from '@/types/components';

// 5. 스타일/에셋
import './styles.css';
```

## 에러 처리

```tsx
// components/ErrorBoundary.tsx
'use client';

import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback: ReactNode;
}

interface State {
  hasError: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}
```

```tsx
// TanStack Query 에러 처리
function UserProfile({ userId }: { userId: string }) {
  const { data, error, isLoading } = useUserQuery(userId);

  if (isLoading) return <Skeleton />;
  if (error) return <ErrorMessage error={error} />;
  if (!data) return null;

  return <UserCard user={data} />;
}
```
