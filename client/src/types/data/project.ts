import type { FormType } from "@/stores/wizard-store"

// DB 스키마와 동일한 타입 정의
export type ProjectStatus = 1 | 2 | 3 | 4 | 5 // 1=기업상담, 2=신청서작성, 3=결과대기, 4=완료, 5=바로출시
export type ProjectStep = 1 | 2 | 3 | 4 // 1=서비스분석, 2=시장진단, 3=트랙선택, 4=신청서생성

// 상태 상수
export const PROJECT_STATUS = {
    CONSULTING: 1,
    DRAFTING: 2,
    PENDING: 3,
    COMPLETED: 4,
    DIRECT_LAUNCH: 5,
} as const
export type Track = "counseling" | "quick_check" | "temp_permit" | "demo"

// 기본 트랙 (상담신청)
export const DEFAULT_TRACK: Track = "counseling"

/**
 * Track 관련 매핑
 *
 * NOTE: 서버(structure_service.py)와 클라이언트에서 TRACK_LABELS가 중복 정의되어 있습니다.
 * 향후 통합 고려 시 API 응답에 라벨을 포함하거나 공유 설정 파일을 도입할 수 있습니다.
 */

// track → formData.json id 매핑
export const TRACK_TO_FORM_ID: Record<Track, FormType> = {
    counseling: "counseling",
    quick_check: "fastcheck",
    temp_permit: "temporary",
    demo: "demonstration",
}

// formData.json id → track 매핑 (역방향)
export const FORM_ID_TO_TRACK: Record<string, Track> = {
    counseling: "counseling",
    fastcheck: "quick_check",
    temporary: "temp_permit",
    demonstration: "demo",
}

export interface Project {
    id: string
    user_id: string
    company_name: string
    service_name: string | null
    service_description: string | null
    industry: string | null
    additional_notes: string | null
    status: ProjectStatus
    current_step: ProjectStep
    track: Track | null
    created_at: string
    updated_at: string
    application_draft: Record<string, unknown> | null // 에이전트 결과 데이터
}

export const PROJECT_STATUS_LABELS: Record<ProjectStatus, string> = {
    1: "기업상담",
    2: "신청서작성",
    3: "결과대기",
    4: "완료",
    5: "바로출시",
}

export const PROJECT_STEP_LABELS: Record<ProjectStep, string> = {
    1: "서비스 분석",
    2: "시장출시 진단",
    3: "트랙 선택",
    4: "신청서 생성",
}

export const TRACK_LABELS: Record<Track, string> = {
    counseling: "상담신청",
    quick_check: "신속확인",
    temp_permit: "임시허가",
    demo: "실증특례",
}

// 진행률 계산 헬퍼 (6단계: 20, 40, 60, 80, 90, 100)
export const calculateProgress = (step: ProjectStep, status: ProjectStatus): number => {
    if (status === PROJECT_STATUS.CONSULTING) return ({ 1: 20, 2: 40, 3: 60, 4: 80 } as Record<number, number>)[step] ?? 0
    if (status === PROJECT_STATUS.DRAFTING) return 80
    if (status === PROJECT_STATUS.PENDING) return 90
    return 100
}

// 상태 필터링 헬퍼 (완료 필터는 4, 5 모두 포함)
export const matchesStatusFilter = (projectStatus: ProjectStatus, filterStatus: ProjectStatus | "all"): boolean => {
    if (filterStatus === "all") return true
    if (filterStatus === PROJECT_STATUS.COMPLETED) {
        return projectStatus === PROJECT_STATUS.COMPLETED || projectStatus === PROJECT_STATUS.DIRECT_LAUNCH
    }
    return projectStatus === filterStatus
}
