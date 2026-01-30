/**
 * Create Project Mutation Hook
 *
 * 새 프로젝트 생성 API를 호출하는 mutation 훅
 */

import { projectsApi } from "@/lib/api/projects"
import type { CreateProjectRequest, ProjectResponse } from "@/types/api/project"
import { useMutation, useQueryClient } from "@tanstack/react-query"

interface UseCreateProjectMutationOptions {
    onSuccess?: (data: ProjectResponse) => void
    onError?: (error: Error) => void
}

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
export function useCreateProjectMutation(options?: UseCreateProjectMutationOptions) {
    const queryClient = useQueryClient()

    return useMutation<ProjectResponse, Error, CreateProjectRequest>({
        mutationFn: projectsApi.createProject,
        onSuccess: (data) => {
            // 프로젝트 목록 캐시 무효화
            queryClient.invalidateQueries({ queryKey: ["projects"] })
            console.log("프로젝트 생성 완료:", data)
            options?.onSuccess?.(data)
        },
        onError: (error) => {
            console.error("프로젝트 생성 오류:", error)
            options?.onError?.(error)
        },
    })
}
