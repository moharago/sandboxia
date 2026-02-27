/**
 * Create Project Mutation Hook
 *
 * 새 프로젝트 생성 API를 호출하는 mutation 훅
 */

import { projectsApi } from "@/lib/api/projects"
import type { CreateProjectRequest, ProjectResponse } from "@/types/api/project"
import type { MutationOptions } from "@/types/hooks"
import { useMutation, useQueryClient } from "@tanstack/react-query"

/**
 * 프로젝트 생성 mutation 훅
 *
 * @example
 * ```tsx
 * const { mutate, isPending } = useCreateProjectMutation({
 *   onSuccess: (data) => {
 *     console.log("프로젝트 생성 완료:", data)
 *     router.push(`/projects/${data.id}/structure`)
 *   },
 *   onError: (error) => {
 *     alert(error.message)
 *   },
 * })
 *
 * // 호출
 * mutate({
 *   user_id: "user-123",
 *   company_name: "테스트 기업",
 *   service_name: "테스트 서비스",
 *   service_description: "서비스 설명",
 * })
 * ```
 */
export function useCreateProjectMutation(options?: MutationOptions<ProjectResponse>) {
    const queryClient = useQueryClient()

    return useMutation<ProjectResponse, Error, CreateProjectRequest>({
        mutationFn: projectsApi.createProject,
        onSuccess: (data) => {
            // 캐시만 stale 표시 (백그라운드 refetch 안 함) → 대시보드 복귀 시 자동 갱신
            queryClient.invalidateQueries({ queryKey: ["projects"], refetchType: "none" })
            options?.onSuccess?.(data)
        },
        onError: (error) => {
            console.error("프로젝트 생성 오류:", error)
            options?.onError?.(error)
        },
    })
}
