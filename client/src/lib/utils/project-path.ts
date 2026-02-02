/**
 * 프로젝트 경로 생성 유틸리티
 *
 * current_step에 따라 적절한 페이지 경로를 반환
 * status=5 (바로출시)인 경우는 항상 eligibility 페이지로
 */

import type { ProjectStep, ProjectStatus } from "@/types/data/project"
import { PROJECT_STATUS } from "@/types/data/project"

export const STEP_PATHS: Record<ProjectStep, string> = {
    1: "service",
    2: "eligibility",
    3: "track",
    4: "draft",
}

/**
 * 프로젝트 ID와 현재 단계를 받아 해당 페이지 경로 반환
 */
export function getProjectPath(projectId: string, currentStep: ProjectStep): string {
    return `/projects/${projectId}/${STEP_PATHS[currentStep]}`
}

/**
 * 프로젝트 객체를 받아 해당 페이지 경로 반환
 * status가 5(바로출시)인 경우는 항상 eligibility 페이지로 이동
 */
export function getProjectPathFromProject(project: { id: string; current_step: ProjectStep; status: ProjectStatus }): string {
    // 바로출시(status=5)인 경우 항상 eligibility 페이지로
    if (project.status === PROJECT_STATUS.DIRECT_LAUNCH) {
        return `/projects/${project.id}/eligibility`
    }
    return getProjectPath(project.id, project.current_step)
}
