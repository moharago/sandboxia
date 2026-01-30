/**
 * Service Mutation Hook
 *
 * 서비스 정보 파싱 API를 호출하는 mutation 훅
 */

import { agentsApi } from "@/lib/api/agents"
import type { ServiceParseRequest, ServiceParseResponse } from "@/types/api/structure"
import { useMutation } from "@tanstack/react-query"

interface UseServiceMutationOptions {
    onSuccess?: (data: ServiceParseResponse) => void
    onError?: (error: Error) => void
}

/**
 * 서비스 정보 파싱 mutation 훅
 *
 * HWP 파일을 서버로 전송하고 파싱된 결과를 반환합니다.
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
 *   requestedTrack: "temporary",
 *   consultantInput: { ... },
 *   files: [file1, file2],
 * })
 * ```
 */
export function useServiceMutation(options?: UseServiceMutationOptions) {
    return useMutation<ServiceParseResponse, Error, ServiceParseRequest>({
        mutationFn: agentsApi.parseService,
        onSuccess: (data) => {
            console.log("HWP 파싱 결과:", data)
            options?.onSuccess?.(data)
        },
        onError: (error) => {
            console.error("서비스 파싱 오류:", error)
            options?.onError?.(error)
        },
    })
}
