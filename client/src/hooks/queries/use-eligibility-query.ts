/**
 * Eligibility Query Hook
 *
 * 프로젝트의 eligibility 결과를 조회하는 쿼리 훅
 */

import { eligibilityApi } from "@/lib/api/eligibility"
import type { EligibilityResult } from "@/types/api/eligibility"
import { useQuery } from "@tanstack/react-query"

export const eligibilityKeys = {
    all: ["eligibility"] as const,
    byProject: (projectId: string) => [...eligibilityKeys.all, projectId] as const,
}

/**
 * 프로젝트의 eligibility 결과 조회
 *
 * @example
 * ```tsx
 * const { data: existingResult, isLoading } = useEligibilityQuery(projectId)
 *
 * // 기존 결과 있는지 확인
 * const hasResult = existingResult?.evidence_data &&
 *   Object.keys(existingResult.evidence_data).length > 0
 * ```
 */
export function useEligibilityQuery(projectId: string) {
    return useQuery<EligibilityResult | null>({
        queryKey: eligibilityKeys.byProject(projectId),
        queryFn: () => eligibilityApi.getByProjectId(projectId),
        enabled: !!projectId,
    })
}
