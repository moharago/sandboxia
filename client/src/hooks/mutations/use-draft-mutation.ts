/**
 * 신청서 초안 관련 뮤테이션 훅
 */

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { agentsApi } from "@/lib/api/agents"
import { draftKeys } from "@/hooks/queries/use-draft-query"
import type {
    DraftGenerateRequest,
    DraftGenerateResponse,
    DraftCardUpdateRequest,
    DraftCardUpdateResponse,
} from "@/types/api/draft"

/**
 * AI 초안 생성 뮤테이션
 */
export function useDraftGenerateMutation() {
    return useMutation<DraftGenerateResponse, Error, DraftGenerateRequest>({
        mutationFn: agentsApi.generateDraft,
    })
}

interface UseDraftCardUpdateMutationOptions {
    onSuccess?: (data: DraftCardUpdateResponse) => void
    onError?: (error: Error) => void
}

/**
 * 카드별 부분 저장 뮤테이션
 *
 * 특정 카드만 서버에 저장하고 나머지 카드 데이터는 유지합니다.
 */
export function useDraftCardUpdateMutation(options?: UseDraftCardUpdateMutationOptions) {
    const queryClient = useQueryClient()

    return useMutation<DraftCardUpdateResponse, Error, DraftCardUpdateRequest>({
        mutationFn: agentsApi.updateDraftCard,
        onSuccess: (data, variables) => {
            // 성공 시 draft query 캐시 무효화하여 최신 데이터 반영
            queryClient.invalidateQueries({ queryKey: draftKeys.byProject(variables.project_id) })
            options?.onSuccess?.(data)
        },
        onError: (error) => {
            options?.onError?.(error)
        },
    })
}
