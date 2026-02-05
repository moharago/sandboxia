/**
 * Agents API Client
 *
 * AI 에이전트 관련 API 호출 함수
 */

import { createClient } from "@/lib/supabase/client"
import type { EligibilityRequest, EligibilityResponse } from "@/types/api/eligibility"
import type { ServiceParseRequest, ServiceParseResponse } from "@/types/api/structure"
import type { DraftGenerateRequest, DraftGenerateResponse } from "@/types/api/draft"
import type { TrackRecommendRequest, TrackRecommendResponse } from "@/types/api/track"

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"

/**
 * Supabase 세션에서 인증 토큰 가져오기
 */
async function getAuthToken(): Promise<string | null> {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    return session?.access_token ?? null
}

export const agentsApi = {
    /**
     * 서비스 정보 파싱 (HWP 파일)
     *
     * FormData로 HWP 파일을 전송하고 파싱된 결과를 반환합니다.
     * requestedTrack: counseling/quick_check/temp_permit/demo
     */
    parseService: async (request: ServiceParseRequest): Promise<ServiceParseResponse> => {
        const formData = new FormData()
        formData.append("session_id", request.sessionId)
        formData.append("requested_track", request.requestedTrack)
        formData.append("consultant_input", JSON.stringify(request.consultantInput))

        // 파일 추가
        for (const file of request.files) {
            formData.append("files", file)
        }

        const response = await fetch(`${API_BASE}/api/v1/agents/structure`, {
            method: "POST",
            body: formData,
        })

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: "Unknown error" }))
            throw new Error(errorData.detail || `Request failed: ${response.status}`)
        }

        return response.json()
    },

    /**
     * 대상성 판단 (Step 2)
     *
     * 프로젝트의 canonical 데이터를 분석하여 규제 샌드박스 신청 필요 여부를 판단합니다.
     */
    evaluateEligibility: async (request: EligibilityRequest): Promise<EligibilityResponse> => {
        const token = await getAuthToken()

        if (!token) {
            throw new Error("로그인이 필요합니다.")
        }

        const response = await fetch(`${API_BASE}/api/v1/agents/eligibility`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(request),
        })

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: "Unknown error" }))
            throw new Error(errorData.detail || `Request failed: ${response.status}`)
        }

        return response.json()
    },

    /**
     * 트랙 추천 결과 조회 (캐시)
     *
     * 이미 분석된 결과가 있으면 반환, 없으면 null
     */
    getTrackResult: async (projectId: string): Promise<TrackRecommendResponse | null> => {
        const token = await getAuthToken()

        const response = await fetch(`${API_BASE}/api/v1/agents/track/${projectId}`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                ...(token && { Authorization: `Bearer ${token}` }),
            },
        })

        if (!response.ok) {
            if (response.status === 404) {
                return null
            }
            const errorData = await response.json().catch(() => ({ detail: "Unknown error" }))
            throw new Error(errorData.detail || `Request failed: ${response.status}`)
        }

        const data = await response.json()
        return data // null이면 캐시 없음
    },

    /**
     * 트랙 추천 (Track Recommender Agent)
     *
     * 프로젝트의 canonical 데이터를 분석하여 적합한 트랙을 추천합니다.
     * - 3개 트랙 비교 (demo/temp_permit/quick_check)
     * - 신뢰도 점수 및 추천 사유 제공
     */
    recommendTrack: async (request: TrackRecommendRequest): Promise<TrackRecommendResponse> => {
        const token = await getAuthToken()

        const response = await fetch(`${API_BASE}/api/v1/agents/track`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...(token && { Authorization: `Bearer ${token}` }),
            },
            body: JSON.stringify(request),
        })

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: "Unknown error" }))
            throw new Error(errorData.detail || `Request failed: ${response.status}`)
        }

        return response.json()
    },

    /**
     * 신청서 초안 생성 (Application Drafter Agent, Step 4)
     *
     * canonical 데이터와 선택된 트랙을 기반으로 신청서 초안을 생성합니다.
     */
    generateDraft: async (request: DraftGenerateRequest): Promise<DraftGenerateResponse> => {
        const response = await fetch(`${API_BASE}/api/v1/agents/draft`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(request),
        })

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: "Unknown error" }))
            throw new Error(errorData.detail || `Request failed: ${response.status}`)
        }

        return response.json()
    },
}
