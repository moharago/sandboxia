/**
 * Track API Client
 *
 * Supabase에서 track_results 조회
 */

import { createClient } from "@/lib/supabase/client"
import type { TrackRecommendResponse } from "@/types/api/track"

export const trackApi = {
    /**
     * 프로젝트의 트랙 추천 결과 조회
     * 결과가 없으면 null 반환
     */
    getByProjectId: async (projectId: string): Promise<TrackRecommendResponse | null> => {
        const supabase = createClient()

        const { data, error } = await supabase
            .from("track_results")
            .select("*")
            .eq("project_id", projectId)
            .order("created_at", { ascending: false })
            .limit(1)
            .maybeSingle()

        if (error) {
            throw new Error(error.message)
        }

        return data as TrackRecommendResponse | null
    },
}
