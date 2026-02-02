/**
 * Service Mutation Hook
 *
 * 서비스 정보 파싱 API를 호출하는 mutation 훅
 */

import { agentsApi } from "@/lib/api/agents"
import { projectKeys } from "@/hooks/queries/use-projects-query"
import type { ServiceParseRequest, ServiceParseResponse } from "@/types/api/structure"
import { useMutation, useQueryClient } from "@tanstack/react-query"

interface UseServiceMutationOptions {
    onSuccess?: (data: ServiceParseResponse) => void
    onError?: (error: Error) => void
}

/**
 * 서비스 정보 파싱 mutation 훅
 *
 * HWP 파일을 서버로 전송하고 파싱된 결과를 반환합니다.
 * 성공 시 프로젝트 관련 캐시를 무효화하여 최신 데이터가 표시되도록 합니다.
 *
 * @example
 * ```tsx
 * const { mutate, isPending } = useServiceMutation({
 *   onSuccess: (data) => {
 *     console.log("파싱 결과:", data)
 *     router.push(`/projects/${id}/eligibility`)
 *   },
 *   onError: (error) => {
 *     alert(error.message)
 *   },
 * })
 *
 * // 호출
 * mutate({
 *   sessionId: "case-123",
 *   requestedTrack: 1,
 *   consultantInput: { ... },
 *   files: [file1, file2],
 * })
 * ```
 */
export function useServiceMutation(options?: UseServiceMutationOptions) {
    const queryClient = useQueryClient()

    return useMutation<ServiceParseResponse, Error, ServiceParseRequest>({
        mutationFn: agentsApi.parseService,
        onSuccess: (data, variables) => {
            console.log("HWP 파싱 결과:", data)

            // 프로젝트 상세 캐시 무효화 (서비스 정보, current_step 등 업데이트됨)
            queryClient.invalidateQueries({
                queryKey: projectKeys.detail(variables.sessionId),
            })

            // 프로젝트 파일 목록 캐시 무효화 (새 파일 업로드됨)
            queryClient.invalidateQueries({
                queryKey: projectKeys.files(variables.sessionId),
            })

            // 프로젝트 목록 캐시도 무효화 (상태 변경 반영)
            queryClient.invalidateQueries({
                queryKey: projectKeys.list(),
            })

            options?.onSuccess?.(data)
        },
        onError: (error) => {
            console.error("서비스 파싱 오류:", error)
            options?.onError?.(error)
        },
    })
}
