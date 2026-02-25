/**
 * 페이지별 단계 상수 및 유틸리티
 *
 * current_step 값:
 * 1 = 서비스분석 (service)
 * 2 = 시장진단 (eligibility)
 * 3 = 트랙선택 (track)
 * 4 = 신청서생성 (draft)
 * 5 = 완료 (completed)
 */

export const PAGE_STEPS = {
    service: 1,
    eligibility: 2,
    track: 3,
    draft: 4,
} as const

export type PageName = keyof typeof PAGE_STEPS

/**
 * current_step 값에 해당하는 페이지 경로 반환
 */
export function getStepPagePath(projectId: string, currentStep: number): string {
    switch (currentStep) {
        case 1:
            return `/projects/${projectId}/service`
        case 2:
            return `/projects/${projectId}/eligibility`
        case 3:
            return `/projects/${projectId}/track`
        case 4:
        case 5:
            return `/projects/${projectId}/draft`
        default:
            return `/projects/${projectId}/service`
    }
}

/**
 * current_step 값에 해당하는 페이지 이름 반환
 */
export function getStepPageName(currentStep: number): string {
    switch (currentStep) {
        case 1:
            return "서비스 분석"
        case 2:
            return "시장출시 진단"
        case 3:
            return "트랙 선택"
        case 4:
        case 5:
            return "신청서 작성"
        default:
            return "서비스 분석"
    }
}
