/**
 * 신청서 초안 생성 뮤테이션 훅
 */

import { useMutation } from "@tanstack/react-query"
import { agentsApi } from "@/lib/api/agents"
import type { DraftGenerateRequest, DraftGenerateResponse } from "@/types/api/draft"

export function useDraftGenerateMutation() {
    return useMutation<DraftGenerateResponse, Error, DraftGenerateRequest>({
        mutationFn: agentsApi.generateDraft,
    })
}
