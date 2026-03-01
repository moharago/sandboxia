/**
 * Projects Server API
 *
 * 서버 컴포넌트에서 사용하는 프로젝트 API
 * Supabase 서버 클라이언트를 사용하여 RLS 적용
 */

import { createClient } from "@/lib/supabase/server"
import type { ProjectResponse } from "@/types/api/project"

/**
 * 서버에서 단일 프로젝트 조회 (RLS 적용)
 * Layout 서버 컴포넌트에서 사용
 */
export async function getProject(id: string): Promise<ProjectResponse | null> {
    const supabase = await createClient()

    const { data, error } = await supabase
        .from("projects")
        .select("*")
        .eq("id", id)
        .single()

    if (error) {
        // PGRST116: 결과 없음 (not found)
        if (error.code === "PGRST116") {
            return null
        }
        console.error("프로젝트 조회 오류:", error)
        return null
    }

    return data as ProjectResponse
}
