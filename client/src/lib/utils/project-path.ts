/**
 * 프로젝트 경로 생성 유틸리티
 *
 * current_step에 따라 적절한 페이지 경로를 반환
 */

import type { ProjectStep } from "@/types/data/project"

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
 */
export function getProjectPathFromProject(project: { id: string; current_step: ProjectStep }): string {
    return getProjectPath(project.id, project.current_step)
}
