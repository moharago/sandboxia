import { StepNav } from "@/components/features/project/StepNav"
import { getProject } from "@/lib/api/projects.server"
import { notFound } from "next/navigation"
import { Suspense, type ReactNode } from "react"
import { ProjectLayoutSkeleton } from "./loading"

interface ProjectLayoutProps {
    children: ReactNode
    params: Promise<{ id: string }>
}

/**
 * Project Layout (Server Component)
 *
 * async-suspense-boundaries: 서버에서 프로젝트 데이터를 fetch하고
 * Suspense로 children을 감싸서 waterfall을 제거합니다.
 */
export default async function ProjectLayout({ children, params }: ProjectLayoutProps) {
    const { id } = await params

    // 서버에서 프로젝트 데이터 fetch
    const project = await getProject(id)

    // 프로젝트가 없으면 404
    if (!project) {
        notFound()
    }

    return (
        <div className="flex flex-col h-full">
            <StepNav
                projectId={id}
                company={project.company_name}
                service={project.service_name || ""}
            />
            <Suspense fallback={<ProjectLayoutSkeleton />}>
                {children}
            </Suspense>
        </div>
    )
}
