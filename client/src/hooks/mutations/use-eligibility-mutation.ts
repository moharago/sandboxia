/**
 * Eligibility Mutation Hook
 *
 * 대상성 판단 API를 호출하는 mutation 훅
 */

import { agentsApi } from "@/lib/api/agents"
import type { EligibilityRequest, EligibilityResponse } from "@/types/api/eligibility"
import { useMutation } from "@tanstack/react-query"

interface UseEligibilityMutationOptions {
    onSuccess?: (data: EligibilityResponse) => void
    onError?: (error: Error) => void
}

/**
 * 대상성 판단 mutation 훅
 *
 * 프로젝트의 canonical 데이터를 분석하여
 * 규제 샌드박스 신청 필요 여부를 판단합니다.
 *
 * @example
 * ```tsx
 * const { mutate, isPending, data } = useEligibilityMutation({
 *   onSuccess: (data) => {
 *     console.log("판정 결과:", data.eligibility_label)
 *   },
 *   onError: (error) => {
 *     alert(error.message)
 *   },
 * })
 *
 * // 호출
 * mutate({ project_id: "uuid-..." })
 * ```
 */
export function useEligibilityMutation(options?: UseEligibilityMutationOptions) {
    return useMutation<EligibilityResponse, Error, EligibilityRequest>({
        mutationFn: agentsApi.evaluateEligibility,
        onSuccess: (data) => {
            options?.onSuccess?.(data)
        },
        onError: (error) => {
            console.error("대상성 판단 오류:", error)
            options?.onError?.(error)
        },
    })
}
