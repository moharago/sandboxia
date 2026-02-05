/**
 * Track Mutation Hooks
 *
 * 트랙 추천 및 선택 API를 호출하는 mutation 훅
 */

import { agentsApi } from "@/lib/api/agents"
import { projectsApi } from "@/lib/api/projects"
import type { ProjectResponse } from "@/types/api/project"
import type { RecommendableTrack, TrackRecommendRequest, TrackRecommendResponse } from "@/types/api/track"
import { useMutation, useQueryClient } from "@tanstack/react-query"

interface UseTrackRecommendMutationOptions {
    onSuccess?: (data: TrackRecommendResponse) => void
    onError?: (error: Error) => void
}

/**
 * 트랙 추천 mutation 훅
 *
 * 프로젝트의 canonical 데이터를 분석하여
 * 3개 트랙(demo/temp_permit/quick_check) 적합도를 추천합니다.
 */
export function useTrackRecommendMutation(options?: UseTrackRecommendMutationOptions) {
    const queryClient = useQueryClient()

    return useMutation<TrackRecommendResponse, Error, TrackRecommendRequest>({
        mutationFn: agentsApi.recommendTrack,
        onSuccess: (data, variables) => {
            console.log("트랙 추천 결과:", data)
            queryClient.setQueryData(["track", variables.project_id], data)
            options?.onSuccess?.(data)
        },
        onError: (error) => {
            console.error("트랙 추천 오류:", error)
            options?.onError?.(error)
        },
    })
}

interface UseTrackSelectMutationOptions {
    onSuccess?: (data: ProjectResponse) => void
    onError?: (error: Error) => void
}

interface TrackSelectVariables {
    projectId: string
    track: RecommendableTrack
}

/**
 * 트랙 선택 저장 mutation 훅
 *
 * 사용자가 선택한 트랙을 프로젝트에 저장합니다.
 */
export function useTrackSelectMutation(options?: UseTrackSelectMutationOptions) {
    const queryClient = useQueryClient()

    return useMutation<ProjectResponse, Error, TrackSelectVariables>({
        mutationFn: ({ projectId, track }) => projectsApi.updateProjectTrack(projectId, track),
        onSuccess: (data, variables) => {
            queryClient.setQueryData(["project", variables.projectId], data)
            options?.onSuccess?.(data)
        },
        onError: (error) => {
            console.error("트랙 선택 저장 오류:", error)
            options?.onError?.(error)
        },
    })
}
