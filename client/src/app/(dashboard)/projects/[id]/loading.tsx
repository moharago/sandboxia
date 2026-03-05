import { PageLoader } from "@/components/ui/page-loader"

/**
 * Project Layout Loading Skeleton
 *
 * Layout의 Suspense fallback으로 사용
 * children이 로딩 중일 때 표시됩니다
 */
export function ProjectLayoutSkeleton() {
    return <PageLoader className="flex-1" />
}

/**
 * Next.js 자동 loading.tsx
 *
 * 페이지 전환 시 자동으로 표시됩니다
 */
export default function Loading() {
    return <ProjectLayoutSkeleton />
}
