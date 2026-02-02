/**
 * Projects Query Hook
 *
 * 내 프로젝트 목록을 조회하는 query 훅
 */

import { projectsApi, type ProjectFile } from "@/lib/api/projects"
import { toProject } from "@/types/api/project"
import type { Project } from "@/types/data/project"
import { useQuery } from "@tanstack/react-query"

export const projectKeys = {
    all: ["projects"] as const,
    list: () => [...projectKeys.all, "list"] as const,
    detail: (id: string) => [...projectKeys.all, "detail", id] as const,
    files: (id: string) => [...projectKeys.all, "files", id] as const,
}

/**
 * 내 프로젝트 목록 조회 query 훅
 *
 * @example
 * ```tsx
 * const { data: projects, isLoading, error } = useProjectsQuery()
 *
 * if (isLoading) return <Spinner />
 * if (error) return <Error message={error.message} />
 *
 * return projects.map(p => <ProjectCard key={p.id} project={p} />)
 * ```
 */
export function useProjectsQuery() {
    return useQuery<Project[], Error>({
        queryKey: projectKeys.list(),
        queryFn: async () => {
            const response = await projectsApi.getMyProjects()
            return response.map(toProject)
        },
        staleTime: 1000 * 60 * 5, // 5분간 캐시 유지
    })
}

/**
 * 단일 프로젝트 조회 query 훅
 */
export function useProjectQuery(id: string) {
    return useQuery<Project, Error>({
        queryKey: projectKeys.detail(id),
        queryFn: async () => {
            const response = await projectsApi.getProject(id)
            return toProject(response)
        },
        staleTime: 1000 * 60 * 5,
    })
}

/**
 * 프로젝트 파일 목록 조회 query 훅
 */
export function useProjectFilesQuery(projectId: string) {
    return useQuery<ProjectFile[], Error>({
        queryKey: projectKeys.files(projectId),
        queryFn: () => projectsApi.getProjectFiles(projectId),
        staleTime: 1000 * 60 * 5,
    })
}
