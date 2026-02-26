/**
 * 신청서 초안 데이터 조회 훅
 */

import { useQuery } from "@tanstack/react-query"
import { draftApi } from "@/lib/api/draft"
import type { ApplicationDraft } from "@/types/api/draft"

export const draftKeys = {
    all: ["draft"] as const,
    byProject: (projectId: string) => ["draft", projectId] as const,
}

export function useDraftQuery(projectId: string | undefined) {
    return useQuery<ApplicationDraft | null>({
        queryKey: draftKeys.byProject(projectId ?? ""),
        queryFn: () => draftApi.getByProjectId(projectId!),
        enabled: !!projectId,
    })
}
