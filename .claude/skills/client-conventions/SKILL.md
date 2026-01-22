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

| 대상            | 컨벤션                  | 예시               |
| --------------- | ----------------------- | ------------------ |
| 컴포넌트 파일   | PascalCase              | `UserProfile.tsx`  |
| 훅 파일         | kebab-case, use- 접두사 | `use-auth.ts`      |
| 유틸리티        | kebab-case              | `format-date.ts`   |
| 타입 파일       | kebab-case              | `user-types.ts`    |
| 상수            | SCREAMING_SNAKE_CASE    | `API_BASE_URL`     |
| 컴포넌트명      | PascalCase              | `UserProfile`      |
| 함수/변수       | camelCase               | `getUserData`      |
| 타입/인터페이스 | PascalCase              | `UserProfile`      |
| Zustand 스토어  | use + 도메인 + Store    | `useAuthStore`     |
| Query 훅        | use + 동작 + Query      | `useUserQuery`     |
| Mutation 훅     | use + 동작 + Mutation   | `useLoginMutation` |

## 컴포넌트 패턴

### 기본 구조

```tsx
"use client"; // 필요시에만

import { useState } from "react";
import type { UserCardProps } from "@/types/components";

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
      {isHovered && <button onClick={() => onSelect(user.id)}>선택</button>}
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
import { useQuery } from "@tanstack/react-query";
import { userApi } from "@/lib/api/user";
import type { User } from "@/types/api";

export const userKeys = {
  all: ["users"] as const,
  lists: () => [...userKeys.all, "list"] as const,
  list: (filters: UserFilters) => [...userKeys.lists(), filters] as const,
  details: () => [...userKeys.all, "detail"] as const,
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
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { userApi } from "@/lib/api/user";
import { userKeys } from "@/hooks/queries/use-user-query";

export function useUpdateUserMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: userApi.updateUser,
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({
        queryKey: userKeys.detail(variables.id),
      });
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
import { create } from "zustand";
import { persist, devtools } from "zustand/middleware";
import type { User } from "@/types/api";

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
      { name: "auth-storage" }
    )
  )
);

// Selector 훅 (리렌더링 최적화)
export const useUser = () => useAuthStore((state) => state.user);
export const useIsAuthenticated = () =>
  useAuthStore((state) => state.isAuthenticated);
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
  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      headers: {
        "Content-Type": "application/json",
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
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // put, patch, delete...
}

export const apiClient = new ApiClient();
```

```tsx
// lib/api/user.ts
import { apiClient } from "./client";
import type { User, UpdateUserRequest } from "@/types/api";

export const userApi = {
  getUser: (id: string) => apiClient.get<User>(`/users/${id}`),
  getUsers: () => apiClient.get<User[]>("/users"),
  updateUser: (data: UpdateUserRequest) =>
    apiClient.put<User>(`/users/${data.id}`, data),
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
export * from "./user";
export * from "./auth";
```

```tsx
// types/components/user.ts
import type { User } from "@/types/api";

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

## UI 컴포넌트 패턴 (shadcn/ui + Radix UI)

### 기본 원칙

- **shadcn/ui 스타일**: Tailwind CSS + Radix UI 조합
- **공통 컴포넌트**: `components/ui/`에 배치, 여러 페이지에서 재사용
- **기능 컴포넌트**: `components/features/`에 배치, 도메인 특화
- **Radix UI 기반**: 접근성(a11y) 내장, 키보드 내비게이션 지원
- **커스텀 시**: 기본 컴포넌트 확장, 새로 만들지 않음

### cn 유틸리티 (필수)

```tsx
// lib/utils/cn.ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

### Button 컴포넌트

```tsx
// components/ui/button.tsx
import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils/cn";

const buttonVariants = cva(
  // 기본 스타일
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground shadow hover:bg-primary/90",
        destructive:
          "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90",
        outline:
          "border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground",
        secondary:
          "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
```

### Input 컴포넌트

```tsx
// components/ui/input.tsx
import * as React from "react";
import { cn } from "@/lib/utils/cn";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
```

### Label 컴포넌트

```tsx
// components/ui/label.tsx
import * as React from "react";
import * as LabelPrimitive from "@radix-ui/react-label";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils/cn";

const labelVariants = cva(
  "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
);

const Label = React.forwardRef<
  React.ElementRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root> &
    VariantProps<typeof labelVariants>
>(({ className, ...props }, ref) => (
  <LabelPrimitive.Root
    ref={ref}
    className={cn(labelVariants(), className)}
    {...props}
  />
));
Label.displayName = LabelPrimitive.Root.displayName;

export { Label };
```

### Select 컴포넌트

```tsx
// components/ui/select.tsx
"use client";

import * as React from "react";
import * as SelectPrimitive from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils/cn";

const Select = SelectPrimitive.Root;
const SelectGroup = SelectPrimitive.Group;
const SelectValue = SelectPrimitive.Value;

const SelectTrigger = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Trigger
    ref={ref}
    className={cn(
      "flex h-9 w-full items-center justify-between whitespace-nowrap rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50 [&>span]:line-clamp-1",
      className
    )}
    {...props}
  >
    {children}
    <SelectPrimitive.Icon asChild>
      <ChevronDown className="h-4 w-4 opacity-50" />
    </SelectPrimitive.Icon>
  </SelectPrimitive.Trigger>
));
SelectTrigger.displayName = SelectPrimitive.Trigger.displayName;

const SelectContent = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Content>
>(({ className, children, position = "popper", ...props }, ref) => (
  <SelectPrimitive.Portal>
    <SelectPrimitive.Content
      ref={ref}
      className={cn(
        "relative z-50 max-h-96 min-w-[8rem] overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md",
        className
      )}
      position={position}
      {...props}
    >
      <SelectPrimitive.Viewport className="p-1">
        {children}
      </SelectPrimitive.Viewport>
    </SelectPrimitive.Content>
  </SelectPrimitive.Portal>
));
SelectContent.displayName = SelectPrimitive.Content.displayName;

const SelectItem = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Item
    ref={ref}
    className={cn(
      "relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 pl-2 pr-8 text-sm outline-none focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
      className
    )}
    {...props}
  >
    <span className="absolute right-2 flex h-3.5 w-3.5 items-center justify-center">
      <SelectPrimitive.ItemIndicator>
        <Check className="h-4 w-4" />
      </SelectPrimitive.ItemIndicator>
    </span>
    <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
  </SelectPrimitive.Item>
));
SelectItem.displayName = SelectPrimitive.Item.displayName;

export {
  Select,
  SelectGroup,
  SelectValue,
  SelectTrigger,
  SelectContent,
  SelectItem,
};
```

### Dialog (모달) 컴포넌트

```tsx
// components/ui/dialog.tsx
"use client";

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/utils/cn";

const Dialog = DialogPrimitive.Root;
const DialogTrigger = DialogPrimitive.Trigger;
const DialogPortal = DialogPrimitive.Portal;
const DialogClose = DialogPrimitive.Close;

const DialogOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      "fixed inset-0 z-50 bg-black/80 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
      className
    )}
    {...props}
  />
));
DialogOverlay.displayName = DialogPrimitive.Overlay.displayName;

const DialogContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>
>(({ className, children, ...props }, ref) => (
  <DialogPortal>
    <DialogOverlay />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        "fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-6 shadow-lg duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%] sm:rounded-lg",
        className
      )}
      {...props}
    >
      {children}
      <DialogPrimitive.Close className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground">
        <X className="h-4 w-4" />
        <span className="sr-only">Close</span>
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </DialogPortal>
));
DialogContent.displayName = DialogPrimitive.Content.displayName;

const DialogHeader = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      "flex flex-col space-y-1.5 text-center sm:text-left",
      className
    )}
    {...props}
  />
);
DialogHeader.displayName = "DialogHeader";

const DialogFooter = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      "flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2",
      className
    )}
    {...props}
  />
);
DialogFooter.displayName = "DialogFooter";

const DialogTitle = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn(
      "text-lg font-semibold leading-none tracking-tight",
      className
    )}
    {...props}
  />
));
DialogTitle.displayName = DialogPrimitive.Title.displayName;

const DialogDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Description
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
));
DialogDescription.displayName = DialogPrimitive.Description.displayName;

export {
  Dialog,
  DialogPortal,
  DialogOverlay,
  DialogTrigger,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
};
```

### 컴포넌트 사용 예시

```tsx
// 사용 예시
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

function MyForm() {
  return (
    <form className="space-y-4">
      {/* Input with Label */}
      <div className="space-y-2">
        <Label htmlFor="name">이름</Label>
        <Input id="name" placeholder="이름을 입력하세요" />
      </div>

      {/* Select */}
      <div className="space-y-2">
        <Label>도메인</Label>
        <Select>
          <SelectTrigger>
            <SelectValue placeholder="선택하세요" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="healthcare">의료</SelectItem>
            <SelectItem value="finance">금융</SelectItem>
            <SelectItem value="mobility">모빌리티</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Button variants */}
      <div className="flex gap-2">
        <Button type="submit">저장</Button>
        <Button variant="outline">취소</Button>
        <Button variant="destructive">삭제</Button>
      </div>

      {/* Dialog (Modal) */}
      <Dialog>
        <DialogTrigger asChild>
          <Button variant="outline">상세 보기</Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>상세 정보</DialogTitle>
          </DialogHeader>
          <p>모달 내용...</p>
        </DialogContent>
      </Dialog>
    </form>
  );
}
```

### 공통 컴포넌트 규칙

1. **위치**: `components/ui/`에 배치
2. **네이밍**: 소문자 kebab-case 파일명 (`button.tsx`, `dialog.tsx`)
3. **확장 시**: 기존 컴포넌트 import 후 래핑
4. **variants**: `class-variance-authority(cva)` 사용
5. **forwardRef**: 모든 컴포넌트에 ref 전달 지원
6. **접근성**: Radix UI 기본 제공, 추가 aria 속성 필요 시 props로 전달

### 커스텀 컴포넌트 확장 예시

```tsx
// components/ui/icon-button.tsx
// 기존 Button을 확장한 아이콘 버튼
import { Button, type ButtonProps } from "@/components/ui/button";
import { cn } from "@/lib/utils/cn";

interface IconButtonProps extends ButtonProps {
  icon: React.ReactNode;
  label: string; // 접근성용
}

export function IconButton({
  icon,
  label,
  className,
  ...props
}: IconButtonProps) {
  return (
    <Button
      size="icon"
      className={cn("", className)}
      aria-label={label}
      {...props}
    >
      {icon}
    </Button>
  );
}
```

### 색상 시스템 (Radix Colors)

프로젝트는 **Radix Colors**의 **Amber + Indigo** 그라데이션을 포인트 색상으로 사용합니다.

```
Amber (노란색 계열) ─────────► Indigo (남색 계열)
     #ffc53d                      #3e63dd
```

#### 색상 스케일 사용법

```tsx
// Radix Colors 12단계 스케일
// 1-2: 배경
// 3-5: UI 요소 배경
// 6-8: 보더, 구분선
// 9-10: 솔리드 배경 (메인 색상)
// 11-12: 텍스트

// Tailwind 클래스로 사용
<div className="bg-amber-9">Amber 메인</div>
<div className="bg-indigo-9">Indigo 메인</div>
<div className="text-amber-11">Amber 텍스트</div>
<div className="border-indigo-6">Indigo 보더</div>
```

#### 그라데이션 유틸리티 클래스

```tsx
// 1. 그라데이션 배경 버튼
<button className="gradient-primary gradient-primary-hover text-white">
  그라데이션 버튼
</button>

// 2. 그라데이션 보더
<div className="gradient-border p-4">
  그라데이션 테두리 카드
</div>

// 3. 그라데이션 텍스트
<h1 className="gradient-text text-4xl font-bold">
  그라데이션 제목
</h1>

// 4. Tailwind 기본 문법으로도 가능
<div className="bg-gradient-to-r from-amber-9 to-indigo-9">
  Tailwind 그라데이션
</div>
```

#### 그라데이션 버튼 컴포넌트

```tsx
// components/ui/gradient-button.tsx
import { cn } from "@/lib/utils/cn";
import { Button, type ButtonProps } from "./button";

export function GradientButton({ className, children, ...props }: ButtonProps) {
  return (
    <Button
      className={cn(
        "gradient-primary gradient-primary-hover border-0 text-white",
        className
      )}
      {...props}
    >
      {children}
    </Button>
  );
}

// 그라데이션 보더 버튼
export function GradientOutlineButton({
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <div className="gradient-border inline-block">
      <Button
        variant="ghost"
        className={cn("bg-background hover:bg-muted", className)}
        {...props}
      >
        {children}
      </Button>
    </div>
  );
}
```

#### shadcn/ui 호환 색상 매핑

| CSS 변수        | 용도            | 기본값   |
| --------------- | --------------- | -------- |
| `--primary`     | 주요 버튼, 링크 | indigo-9 |
| `--secondary`   | 보조 버튼       | amber-9  |
| `--muted`       | 비활성 배경     | gray     |
| `--accent`      | 호버 배경       | gray     |
| `--destructive` | 삭제, 경고      | red      |
| `--border`      | 기본 보더       | gray     |
| `--ring`        | 포커스 링       | indigo-9 |

### Tailwind 추가 규칙

- 인라인 스타일 사용 금지
- 복잡한 조건부 스타일은 `cn()` 유틸리티 사용
- 반복되는 스타일은 공통 컴포넌트로 추출
- 다크모드: 자동 지원 (CSS 변수 기반, `prefers-color-scheme`)
- 색상: CSS 변수 기반 (`bg-primary`, `text-muted-foreground` 등)
- 그라데이션: `gradient-primary`, `gradient-border`, `gradient-text` 클래스 사용

## Import 순서

```tsx
// 1. React/Next.js
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

// 2. 외부 라이브러리
import { useQuery } from "@tanstack/react-query";
import { clsx } from "clsx";

// 3. 내부 모듈 (절대 경로)
import { useAuthStore } from "@/stores/auth-store";
import { userApi } from "@/lib/api/user";
import { UserCard } from "@/components/features/user/UserCard";

// 4. 타입 (type-only import)
import type { User } from "@/types/api";
import type { UserCardProps } from "@/types/components";

// 5. 스타일/에셋
import "./styles.css";
```

## 에러 처리

```tsx
// components/ErrorBoundary.tsx
"use client";

import { Component, type ReactNode } from "react";

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

## 폼 패턴 (React Hook Form + Zod)

### 기본 폼 구조

```tsx
// components/features/form/ServiceForm.tsx
"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

// 1. Zod 스키마 정의
const serviceSchema = z.object({
  serviceName: z.string().min(1, "서비스명을 입력하세요"),
  description: z.string().min(10, "최소 10자 이상 입력하세요"),
  domain: z.enum(["healthcare", "finance", "mobility"], {
    errorMap: () => ({ message: "도메인을 선택하세요" }),
  }),
  hasPersonalData: z.boolean(),
  targetUsers: z.array(z.string()).min(1, "대상 사용자를 선택하세요"),
});

// 2. 타입 추론
type ServiceFormData = z.infer<typeof serviceSchema>;

// 3. 컴포넌트
export function ServiceForm({
  onSubmit,
}: {
  onSubmit: (data: ServiceFormData) => void;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    watch,
    reset,
  } = useForm<ServiceFormData>({
    resolver: zodResolver(serviceSchema),
    defaultValues: {
      serviceName: "",
      description: "",
      hasPersonalData: false,
      targetUsers: [],
    },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {/* 텍스트 입력 */}
      <div>
        <label htmlFor="serviceName" className="block text-sm font-medium">
          서비스명
        </label>
        <input
          id="serviceName"
          {...register("serviceName")}
          className="mt-1 block w-full rounded-md border p-2"
        />
        {errors.serviceName && (
          <p className="mt-1 text-sm text-red-500">
            {errors.serviceName.message}
          </p>
        )}
      </div>

      {/* 셀렉트 */}
      <div>
        <label htmlFor="domain" className="block text-sm font-medium">
          도메인
        </label>
        <select
          id="domain"
          {...register("domain")}
          className="mt-1 block w-full rounded-md border p-2"
        >
          <option value="">선택하세요</option>
          <option value="healthcare">의료</option>
          <option value="finance">금융</option>
          <option value="mobility">모빌리티</option>
        </select>
        {errors.domain && (
          <p className="mt-1 text-sm text-red-500">{errors.domain.message}</p>
        )}
      </div>

      {/* 체크박스 */}
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="hasPersonalData"
          {...register("hasPersonalData")}
        />
        <label htmlFor="hasPersonalData">개인정보 처리 여부</label>
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="rounded-md bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
      >
        {isSubmitting ? "제출 중..." : "제출"}
      </button>
    </form>
  );
}
```

### 동적 폼 렌더링 (서버 스키마 기반)

```tsx
// components/features/form-builder/DynamicForm.tsx
"use client";

import { useForm, Controller } from "react-hook-form";
import type { FormSchema, FormField } from "@/types/api";

interface DynamicFormProps {
  schema: FormSchema;
  initialValues?: Record<string, unknown>;
  onSubmit: (data: Record<string, unknown>) => void;
}

export function DynamicForm({
  schema,
  initialValues,
  onSubmit,
}: DynamicFormProps) {
  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm({
    defaultValues: initialValues,
  });

  const renderField = (field: FormField) => {
    switch (field.type) {
      case "text":
        return (
          <Controller
            name={field.id}
            control={control}
            rules={{ required: field.required && "필수 항목입니다" }}
            render={({ field: f }) => (
              <input
                {...f}
                placeholder={field.placeholder}
                className="w-full rounded border p-2"
              />
            )}
          />
        );

      case "textarea":
        return (
          <Controller
            name={field.id}
            control={control}
            rules={{ required: field.required && "필수 항목입니다" }}
            render={({ field: f }) => (
              <textarea
                {...f}
                rows={4}
                placeholder={field.placeholder}
                className="w-full rounded border p-2"
              />
            )}
          />
        );

      case "select":
        return (
          <Controller
            name={field.id}
            control={control}
            rules={{ required: field.required && "필수 항목입니다" }}
            render={({ field: f }) => (
              <select {...f} className="w-full rounded border p-2">
                <option value="">선택하세요</option>
                {field.options?.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            )}
          />
        );

      case "checkbox":
        return (
          <Controller
            name={field.id}
            control={control}
            render={({ field: f }) => (
              <input type="checkbox" checked={f.value} onChange={f.onChange} />
            )}
          />
        );

      default:
        return null;
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {schema.sections.map((section) => (
        <fieldset key={section.id} className="rounded-lg border p-4">
          <legend className="text-lg font-semibold">{section.title}</legend>
          <div className="mt-4 space-y-4">
            {section.fields.map((field) => (
              <div key={field.id}>
                <label className="block text-sm font-medium">
                  {field.label}
                  {field.required && <span className="text-red-500">*</span>}
                </label>
                {field.helpText && (
                  <p className="text-xs text-gray-500">{field.helpText}</p>
                )}
                <div className="mt-1">{renderField(field)}</div>
                {errors[field.id] && (
                  <p className="mt-1 text-sm text-red-500">
                    {errors[field.id]?.message as string}
                  </p>
                )}
              </div>
            ))}
          </div>
        </fieldset>
      ))}
      <button
        type="submit"
        className="rounded bg-blue-600 px-4 py-2 text-white"
      >
        저장
      </button>
    </form>
  );
}
```

### 폼 타입 정의

```tsx
// types/api/form.ts
export interface FormField {
  id: string;
  type: "text" | "textarea" | "select" | "checkbox" | "radio" | "file";
  label: string;
  placeholder?: string;
  helpText?: string;
  required: boolean;
  options?: { value: string; label: string }[];
  validation?: {
    min?: number;
    max?: number;
    pattern?: string;
  };
}

export interface FormSection {
  id: string;
  title: string;
  description?: string;
  fields: FormField[];
}

export interface FormSchema {
  id: string;
  title: string;
  sections: FormSection[];
}
```

## 스트리밍/실시간 패턴

### SSE (Server-Sent Events) 훅

```tsx
// hooks/use-sse.ts
"use client";

import { useState, useEffect, useCallback } from "react";

interface UseSSEOptions<T> {
  onMessage?: (data: T) => void;
  onError?: (error: Event) => void;
  onComplete?: () => void;
}

interface UseSSEReturn<T> {
  data: T | null;
  chunks: T[];
  isConnected: boolean;
  error: Event | null;
  connect: () => void;
  disconnect: () => void;
}

export function useSSE<T>(
  url: string,
  options?: UseSSEOptions<T>
): UseSSEReturn<T> {
  const [data, setData] = useState<T | null>(null);
  const [chunks, setChunks] = useState<T[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Event | null>(null);
  const [eventSource, setEventSource] = useState<EventSource | null>(null);

  const connect = useCallback(() => {
    const es = new EventSource(url);

    es.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    es.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as T;
        setData(parsed);
        setChunks((prev) => [...prev, parsed]);
        options?.onMessage?.(parsed);
      } catch {
        // 텍스트 데이터인 경우
        setData(event.data as T);
        setChunks((prev) => [...prev, event.data as T]);
        options?.onMessage?.(event.data as T);
      }
    };

    es.onerror = (event) => {
      setError(event);
      setIsConnected(false);
      options?.onError?.(event);
      es.close();
    };

    es.addEventListener("complete", () => {
      options?.onComplete?.();
      es.close();
      setIsConnected(false);
    });

    setEventSource(es);
  }, [url, options]);

  const disconnect = useCallback(() => {
    eventSource?.close();
    setIsConnected(false);
  }, [eventSource]);

  useEffect(() => {
    return () => {
      eventSource?.close();
    };
  }, [eventSource]);

  return { data, chunks, isConnected, error, connect, disconnect };
}
```

### 에이전트 스트리밍 훅

```tsx
// hooks/use-agent-stream.ts
"use client";

import { useState, useCallback } from "react";

interface AgentChunk {
  type: "thinking" | "content" | "tool_call" | "complete" | "error";
  content?: string;
  toolName?: string;
  toolInput?: Record<string, unknown>;
}

interface AgentStreamState {
  status: "idle" | "streaming" | "complete" | "error";
  thinking: string;
  content: string;
  toolCalls: { name: string; input: Record<string, unknown> }[];
  error: string | null;
}

export function useAgentStream(endpoint: string) {
  const [state, setState] = useState<AgentStreamState>({
    status: "idle",
    thinking: "",
    content: "",
    toolCalls: [],
    error: null,
  });

  const stream = useCallback(
    async (input: Record<string, unknown>) => {
      setState((prev) => ({
        ...prev,
        status: "streaming",
        content: "",
        thinking: "",
        toolCalls: [],
      }));

      try {
        const response = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(input),
        });

        if (!response.body) throw new Error("No response body");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const text = decoder.decode(value);
          const lines = text
            .split("\n")
            .filter((line) => line.startsWith("data: "));

          for (const line of lines) {
            const data = JSON.parse(line.slice(6)) as AgentChunk;

            setState((prev) => {
              switch (data.type) {
                case "thinking":
                  return {
                    ...prev,
                    thinking: prev.thinking + (data.content || ""),
                  };
                case "content":
                  return {
                    ...prev,
                    content: prev.content + (data.content || ""),
                  };
                case "tool_call":
                  return {
                    ...prev,
                    toolCalls: [
                      ...prev.toolCalls,
                      { name: data.toolName!, input: data.toolInput! },
                    ],
                  };
                case "complete":
                  return { ...prev, status: "complete" };
                case "error":
                  return {
                    ...prev,
                    status: "error",
                    error: data.content || "Unknown error",
                  };
                default:
                  return prev;
              }
            });
          }
        }
      } catch (err) {
        setState((prev) => ({
          ...prev,
          status: "error",
          error: err instanceof Error ? err.message : "Stream failed",
        }));
      }
    },
    [endpoint]
  );

  const reset = useCallback(() => {
    setState({
      status: "idle",
      thinking: "",
      content: "",
      toolCalls: [],
      error: null,
    });
  }, []);

  return { ...state, stream, reset };
}
```

### 스트리밍 컴포넌트 예시

```tsx
// components/features/agent/AgentResponse.tsx
"use client";

import { useAgentStream } from "@/hooks/use-agent-stream";

export function AgentResponse({ agentType }: { agentType: string }) {
  const { status, thinking, content, toolCalls, stream, reset } =
    useAgentStream(`/api/agents/${agentType}/stream`);

  const handleSubmit = async (input: Record<string, unknown>) => {
    await stream(input);
  };

  return (
    <div className="space-y-4">
      {/* 상태 표시 */}
      {status === "streaming" && (
        <div className="flex items-center gap-2 text-blue-600">
          <span className="animate-pulse">●</span>
          <span>응답 생성 중...</span>
        </div>
      )}

      {/* 생각 과정 (접을 수 있음) */}
      {thinking && (
        <details className="rounded border p-2">
          <summary className="cursor-pointer text-sm text-gray-500">
            생각 과정 보기
          </summary>
          <pre className="mt-2 whitespace-pre-wrap text-xs">{thinking}</pre>
        </details>
      )}

      {/* Tool 호출 표시 */}
      {toolCalls.length > 0 && (
        <div className="space-y-1">
          {toolCalls.map((tool, i) => (
            <div key={i} className="rounded bg-gray-100 px-2 py-1 text-sm">
              🔧 {tool.name}
            </div>
          ))}
        </div>
      )}

      {/* 응답 내용 */}
      {content && (
        <div className="prose max-w-none rounded-lg border p-4">{content}</div>
      )}
    </div>
  );
}
```

## 로딩/상태 UI 패턴

### Skeleton 컴포넌트

```tsx
// components/ui/Skeleton.tsx
import { cn } from "@/lib/utils/cn";

interface SkeletonProps {
  className?: string;
  variant?: "text" | "circular" | "rectangular";
  width?: string | number;
  height?: string | number;
  lines?: number;
}

export function Skeleton({
  className,
  variant = "text",
  width,
  height,
  lines = 1,
}: SkeletonProps) {
  const baseClass = "animate-pulse bg-gray-200";

  const variantClass = {
    text: "rounded",
    circular: "rounded-full",
    rectangular: "rounded-md",
  };

  if (variant === "text" && lines > 1) {
    return (
      <div className={cn("space-y-2", className)}>
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={cn(baseClass, variantClass.text, "h-4")}
            style={{ width: i === lines - 1 ? "60%" : "100%" }}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={cn(baseClass, variantClass[variant], className)}
      style={{
        width,
        height: height || (variant === "text" ? "1em" : undefined),
      }}
    />
  );
}

// 프리셋 Skeleton
export function CardSkeleton() {
  return (
    <div className="rounded-lg border p-4">
      <Skeleton variant="text" className="mb-2 h-6 w-1/3" />
      <Skeleton variant="text" lines={3} />
    </div>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4">
          <Skeleton className="h-10 flex-1" />
          <Skeleton className="h-10 flex-1" />
          <Skeleton className="h-10 flex-1" />
        </div>
      ))}
    </div>
  );
}
```

### 에이전트 진행 상태 컴포넌트

```tsx
// components/features/agent-status/AgentProgress.tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils/cn";

type AgentStep = {
  id: string;
  name: string;
  status: "pending" | "running" | "completed" | "error";
  message?: string;
};

interface AgentProgressProps {
  taskId: string;
  steps: AgentStep[];
  className?: string;
}

export function AgentProgress({
  taskId,
  steps,
  className,
}: AgentProgressProps) {
  const currentStep = steps.find((s) => s.status === "running");
  const completedCount = steps.filter((s) => s.status === "completed").length;
  const progress = (completedCount / steps.length) * 100;

  return (
    <div className={cn("space-y-4", className)}>
      {/* 프로그레스 바 */}
      <div className="h-2 overflow-hidden rounded-full bg-gray-200">
        <div
          className="h-full bg-blue-600 transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* 단계 목록 */}
      <div className="space-y-2">
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-center gap-3">
            {/* 상태 아이콘 */}
            <div
              className={cn(
                "flex h-6 w-6 items-center justify-center rounded-full text-xs",
                step.status === "completed" && "bg-grass-100 text-grass-600",
                step.status === "running" && "bg-blue-100 text-blue-600",
                step.status === "error" && "bg-red-100 text-red-600",
                step.status === "pending" && "bg-gray-100 text-gray-400"
              )}
            >
              {step.status === "completed" && "✓"}
              {step.status === "running" && (
                <span className="animate-spin">⟳</span>
              )}
              {step.status === "error" && "✕"}
              {step.status === "pending" && index + 1}
            </div>

            {/* 단계 정보 */}
            <div className="flex-1">
              <p
                className={cn(
                  "text-sm font-medium",
                  step.status === "pending" && "text-gray-400"
                )}
              >
                {step.name}
              </p>
              {step.message && (
                <p className="text-xs text-gray-500">{step.message}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 에이전트 파이프라인 상태

```tsx
// components/features/agent-status/PipelineStatus.tsx
"use client";

const PIPELINE_STEPS = [
  { id: "structure", name: "서비스 구조화", agent: 1 },
  { id: "eligibility", name: "대상성 판단", agent: 2 },
  { id: "track", name: "트랙 추천", agent: 3 },
  { id: "draft", name: "신청서 초안", agent: 4 },
  { id: "strategy", name: "전략 추천", agent: 5 },
  { id: "risk", name: "리스크 체크", agent: 6 },
];

interface PipelineStatusProps {
  currentStep: string;
  completedSteps: string[];
}

export function PipelineStatus({
  currentStep,
  completedSteps,
}: PipelineStatusProps) {
  return (
    <div className="flex items-center justify-between">
      {PIPELINE_STEPS.map((step, index) => {
        const isCompleted = completedSteps.includes(step.id);
        const isCurrent = currentStep === step.id;
        const isPending = !isCompleted && !isCurrent;

        return (
          <div key={step.id} className="flex items-center">
            {/* 스텝 */}
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-full border-2 text-sm font-bold",
                  isCompleted && "border-grass-500 bg-grass-500 text-white",
                  isCurrent && "border-blue-500 bg-blue-50 text-blue-600",
                  isPending && "border-gray-300 text-gray-400"
                )}
              >
                {isCompleted ? "✓" : step.agent}
              </div>
              <span
                className={cn(
                  "mt-1 text-xs",
                  isCurrent && "font-semibold text-blue-600",
                  isPending && "text-gray-400"
                )}
              >
                {step.name}
              </span>
            </div>

            {/* 연결선 */}
            {index < PIPELINE_STEPS.length - 1 && (
              <div
                className={cn(
                  "mx-2 h-0.5 w-8",
                  isCompleted ? "bg-grass-500" : "bg-gray-300"
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
```

## 파일 업로드 패턴

### 파일 업로드 훅

```tsx
// hooks/use-file-upload.ts
"use client";

import { useState, useCallback } from "react";

interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

interface UploadState {
  status: "idle" | "uploading" | "success" | "error";
  progress: UploadProgress | null;
  error: string | null;
  result: unknown | null;
}

interface UseFileUploadOptions {
  endpoint: string;
  maxSize?: number; // bytes
  allowedTypes?: string[];
  onSuccess?: (result: unknown) => void;
  onError?: (error: string) => void;
}

export function useFileUpload(options: UseFileUploadOptions) {
  const {
    endpoint,
    maxSize = 10 * 1024 * 1024,
    allowedTypes,
    onSuccess,
    onError,
  } = options;

  const [state, setState] = useState<UploadState>({
    status: "idle",
    progress: null,
    error: null,
    result: null,
  });

  const validate = useCallback(
    (file: File): string | null => {
      if (file.size > maxSize) {
        return `파일 크기는 ${Math.round(
          maxSize / 1024 / 1024
        )}MB 이하여야 합니다`;
      }
      if (allowedTypes && !allowedTypes.includes(file.type)) {
        return `허용되지 않는 파일 형식입니다. (${allowedTypes.join(", ")})`;
      }
      return null;
    },
    [maxSize, allowedTypes]
  );

  const upload = useCallback(
    async (file: File) => {
      const validationError = validate(file);
      if (validationError) {
        setState({
          status: "error",
          progress: null,
          error: validationError,
          result: null,
        });
        onError?.(validationError);
        return;
      }

      setState({
        status: "uploading",
        progress: { loaded: 0, total: file.size, percentage: 0 },
        error: null,
        result: null,
      });

      const formData = new FormData();
      formData.append("file", file);

      try {
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener("progress", (e) => {
          if (e.lengthComputable) {
            setState((prev) => ({
              ...prev,
              progress: {
                loaded: e.loaded,
                total: e.total,
                percentage: Math.round((e.loaded / e.total) * 100),
              },
            }));
          }
        });

        const result = await new Promise((resolve, reject) => {
          xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              resolve(JSON.parse(xhr.responseText));
            } else {
              reject(new Error(xhr.statusText));
            }
          };
          xhr.onerror = () => reject(new Error("Upload failed"));
          xhr.open("POST", endpoint);
          xhr.send(formData);
        });

        setState({ status: "success", progress: null, error: null, result });
        onSuccess?.(result);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : "Upload failed";
        setState({
          status: "error",
          progress: null,
          error: errorMsg,
          result: null,
        });
        onError?.(errorMsg);
      }
    },
    [endpoint, validate, onSuccess, onError]
  );

  const reset = useCallback(() => {
    setState({ status: "idle", progress: null, error: null, result: null });
  }, []);

  return { ...state, upload, reset };
}
```

### 드래그앤드롭 업로드 컴포넌트

```tsx
// components/features/upload/FileDropzone.tsx
"use client";

import { useState, useCallback, useRef } from "react";
import { useFileUpload } from "@/hooks/use-file-upload";
import { cn } from "@/lib/utils/cn";

interface FileDropzoneProps {
  endpoint: string;
  accept?: string;
  maxSize?: number;
  onUploadComplete?: (result: unknown) => void;
  className?: string;
}

export function FileDropzone({
  endpoint,
  accept = ".pdf,.hwp,.docx",
  maxSize = 10 * 1024 * 1024,
  onUploadComplete,
  className,
}: FileDropzoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const { status, progress, error, upload, reset } = useFileUpload({
    endpoint,
    maxSize,
    onSuccess: onUploadComplete,
  });

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);

      const file = e.dataTransfer.files[0];
      if (file) upload(file);
    },
    [upload]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) upload(file);
    },
    [upload]
  );

  return (
    <div
      className={cn(
        "relative rounded-lg border-2 border-dashed p-8 text-center transition-colors",
        isDragOver && "border-blue-500 bg-blue-50",
        status === "error" && "border-red-300 bg-red-50",
        status === "success" && "border-grass-300 bg-grass-50",
        !isDragOver &&
          status === "idle" &&
          "border-gray-300 hover:border-gray-400",
        className
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={handleFileSelect}
        className="hidden"
      />

      {status === "idle" && (
        <>
          <div className="mb-2 text-4xl">📄</div>
          <p className="mb-2 text-gray-600">
            파일을 드래그하거나{" "}
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="text-blue-600 underline"
            >
              클릭하여 선택
            </button>
          </p>
          <p className="text-xs text-gray-400">
            {accept} (최대 {Math.round(maxSize / 1024 / 1024)}MB)
          </p>
        </>
      )}

      {status === "uploading" && progress && (
        <div className="space-y-2">
          <div className="text-4xl">⏳</div>
          <p className="text-gray-600">업로드 중... {progress.percentage}%</p>
          <div className="mx-auto h-2 w-full max-w-xs overflow-hidden rounded-full bg-gray-200">
            <div
              className="h-full bg-blue-600 transition-all"
              style={{ width: `${progress.percentage}%` }}
            />
          </div>
        </div>
      )}

      {status === "success" && (
        <div className="space-y-2">
          <div className="text-4xl">✅</div>
          <p className="text-grass-600">업로드 완료!</p>
          <button
            type="button"
            onClick={reset}
            className="text-sm text-blue-600 underline"
          >
            다른 파일 업로드
          </button>
        </div>
      )}

      {status === "error" && (
        <div className="space-y-2">
          <div className="text-4xl">❌</div>
          <p className="text-red-600">{error}</p>
          <button
            type="button"
            onClick={reset}
            className="text-sm text-blue-600 underline"
          >
            다시 시도
          </button>
        </div>
      )}
    </div>
  );
}
```

### 다중 파일 업로드

```tsx
// components/features/upload/MultiFileUpload.tsx
"use client";

import { useState, useCallback } from "react";
import { cn } from "@/lib/utils/cn";

interface FileItem {
  id: string;
  file: File;
  status: "pending" | "uploading" | "success" | "error";
  progress: number;
  error?: string;
}

interface MultiFileUploadProps {
  endpoint: string;
  maxFiles?: number;
  onAllComplete?: (results: unknown[]) => void;
}

export function MultiFileUpload({
  endpoint,
  maxFiles = 5,
  onAllComplete,
}: MultiFileUploadProps) {
  const [files, setFiles] = useState<FileItem[]>([]);

  const addFiles = useCallback(
    (newFiles: FileList) => {
      const remaining = maxFiles - files.length;
      const toAdd = Array.from(newFiles).slice(0, remaining);

      setFiles((prev) => [
        ...prev,
        ...toAdd.map((file) => ({
          id: `${Date.now()}-${file.name}`,
          file,
          status: "pending" as const,
          progress: 0,
        })),
      ]);
    },
    [files.length, maxFiles]
  );

  const removeFile = useCallback((id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  }, []);

  const uploadAll = useCallback(async () => {
    const results: unknown[] = [];

    for (const fileItem of files) {
      if (fileItem.status !== "pending") continue;

      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileItem.id ? { ...f, status: "uploading" } : f
        )
      );

      try {
        const formData = new FormData();
        formData.append("file", fileItem.file);

        const response = await fetch(endpoint, {
          method: "POST",
          body: formData,
        });
        const result = await response.json();

        results.push(result);
        setFiles((prev) =>
          prev.map((f) =>
            f.id === fileItem.id
              ? { ...f, status: "success", progress: 100 }
              : f
          )
        );
      } catch (err) {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === fileItem.id
              ? {
                  ...f,
                  status: "error",
                  error: err instanceof Error ? err.message : "Failed",
                }
              : f
          )
        );
      }
    }

    onAllComplete?.(results);
  }, [files, endpoint, onAllComplete]);

  return (
    <div className="space-y-4">
      {/* 파일 목록 */}
      <div className="space-y-2">
        {files.map((item) => (
          <div
            key={item.id}
            className={cn(
              "flex items-center justify-between rounded border p-2",
              item.status === "success" && "bg-grass-50",
              item.status === "error" && "bg-red-50"
            )}
          >
            <span className="truncate text-sm">{item.file.name}</span>
            <div className="flex items-center gap-2">
              {item.status === "uploading" && (
                <span className="animate-spin">⟳</span>
              )}
              {item.status === "success" && (
                <span className="text-grass-600">✓</span>
              )}
              {item.status === "error" && (
                <span className="text-red-600">✕</span>
              )}
              {item.status === "pending" && (
                <button
                  onClick={() => removeFile(item.id)}
                  className="text-gray-400 hover:text-red-500"
                >
                  ✕
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* 추가 버튼 */}
      {files.length < maxFiles && (
        <label className="block cursor-pointer rounded border-2 border-dashed p-4 text-center text-gray-500 hover:border-gray-400">
          <input
            type="file"
            multiple
            onChange={(e) => e.target.files && addFiles(e.target.files)}
            className="hidden"
          />
          + 파일 추가 ({files.length}/{maxFiles})
        </label>
      )}

      {/* 업로드 버튼 */}
      {files.some((f) => f.status === "pending") && (
        <button
          onClick={uploadAll}
          className="w-full rounded bg-blue-600 py-2 text-white hover:bg-blue-700"
        >
          전체 업로드
        </button>
      )}
    </div>
  );
}
```
