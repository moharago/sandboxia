// DB 스키마와 동일한 타입 정의
export type ProjectStatus = 1 | 2 | 3 | 4 // 1=기업상담, 2=신청서작성, 3=결과대기, 4=완료
export type ProjectStep = 1 | 2 | 3 | 4 // 1=서비스분석, 2=시장진단, 3=트랙선택, 4=신청서생성
export type Track = "quick_check" | "demo" | "temp_permit"

export interface Project {
    id: string
    user_id: string
    company_name: string
    service_name: string | null
    service_description: string | null
    industry: string | null
    status: ProjectStatus
    current_step: ProjectStep
    track: Track | null
    created_at: string
    updated_at: string
}

export const PROJECT_STATUS_LABELS: Record<ProjectStatus, string> = {
    1: "기업상담",
    2: "신청서작성",
    3: "결과대기",
    4: "완료",
}

export const PROJECT_STEP_LABELS: Record<ProjectStep, string> = {
    1: "서비스 분석",
    2: "시장출시 진단",
    3: "트랙 선택",
    4: "신청서 생성",
}

export const TRACK_LABELS: Record<Track, string> = {
    quick_check: "신속확인",
    demo: "실증특례",
    temp_permit: "임시허가",
}

// 진행률 계산 헬퍼
export const calculateProgress = (step: ProjectStep, status: ProjectStatus): number => {
    if (status === 4) return 100
    return Math.min(step * 25, 100)
}
