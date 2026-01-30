export type ProjectStatus = "consult" | "draft" | "waiting" | "done" | "direct"
export type ProjectStage = 1 | 2 | 3 | 4

export interface Project {
    id: string
    company: string
    service: string
    status: ProjectStatus
    stage: ProjectStage
    progress: number
    description?: string
    createdAt: string
    updatedAt: string
    sandboxType?: SandboxType
}

export const PROJECT_STATUS_LABELS: Record<ProjectStatus, string> = {
    consult: "기업상담",
    draft: "신청서작성",
    waiting: "결과대기",
    done: "완료",
    direct: "바로출시",
}

export const PROJECT_STAGE_LABELS: Record<ProjectStage, string> = {
    1: "기업 정보 입력",
    2: "시장출시 진단",
    3: "트랙 선택",
    4: "신청서 작성",
}

export type SandboxType = "demonstration" | "temporary" | "rapid"

export const SANDBOX_TYPE_LABELS: Record<SandboxType, string> = {
    demonstration: "실증특례",
    temporary: "임시허가",
    rapid: "신속확인",
}
