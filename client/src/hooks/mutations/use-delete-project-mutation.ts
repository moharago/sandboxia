/**
 * Delete Project Mutation Hook
 *
 * 프로젝트 삭제 API를 호출하는 mutation 훅
 */

import { projectsApi } from "@/lib/api/projects"
import type { MutationOptions } from "@/types/hooks"
import { useMutation, useQueryClient } from "@tanstack/react-query"

/**
 * 프로젝트 삭제 mutation 훅
 *
 * @example
 * ```tsx
 * const { mutate, isPending } = useDeleteProjectMutation({
 *   onSuccess: () => {
 *     console.log("프로젝트 삭제 완료")
 *   },
 *   onError: (error) => {
 *     alert(error.message)
 *   },
 * })
 *
 * // 호출
 * mutate("project-id")
 * ```
 */
export function useDeleteProjectMutation(options?: MutationOptions) {
    const queryClient = useQueryClient()

    return useMutation<void, Error, string>({
        mutationFn: projectsApi.deleteProject,
        onSuccess: () => {
            // 프로젝트 목록 캐시 무효화
            queryClient.invalidateQueries({ queryKey: ["projects"] })
            options?.onSuccess?.()
        },
        onError: (error) => {
            console.error("프로젝트 삭제 오류:", error)
            options?.onError?.(error)
        },
    })
}
