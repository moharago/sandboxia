/**
 * Agents API Client
 *
 * AI 에이전트 관련 API 호출 함수
 */

import type { ServiceParseRequest, ServiceParseResponse } from "@/types/api/structure"

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"

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
}
