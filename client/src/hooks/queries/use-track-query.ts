/**
 * Track Query Hook
 *
 * 프로젝트의 트랙 추천 결과를 조회하는 쿼리 훅
 */

import { trackApi } from "@/lib/api/track"
import type { TrackRecommendResponse } from "@/types/api/track"
import { useQuery } from "@tanstack/react-query"

export const trackKeys = {
    all: ["track"] as const,
    byProject: (projectId: string) => [...trackKeys.all, projectId] as const,
}

/**
 * 프로젝트의 트랙 추천 결과 조회
 *
 * @example
 * ```tsx
 * const { data: trackResult, isLoading } = useTrackQuery(projectId)
 * ```
 */
export function useTrackQuery(projectId: string) {
    return useQuery<TrackRecommendResponse | null>({
        queryKey: trackKeys.byProject(projectId),
        queryFn: () => trackApi.getByProjectId(projectId),
        enabled: !!projectId,
        staleTime: 1000 * 30, // 30초간 캐시 유지
        refetchOnMount: "always", // 컴포넌트 마운트 시 항상 refetch
        retry: 2,
    })
}
