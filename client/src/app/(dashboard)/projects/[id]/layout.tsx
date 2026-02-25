"use client"

import { StepNav } from "@/components/features/project/StepNav"
import { PageLoader } from "@/components/ui/page-loader"
import { useProjectQuery } from "@/hooks/queries/use-projects-query"
import { usePathname, useRouter } from "next/navigation"
import { use, useEffect, type ReactNode } from "react"

interface ProjectLayoutProps {
    children: ReactNode
    params: Promise<{ id: string }>
}

export default function ProjectLayout({ children, params }: ProjectLayoutProps) {
    const { id } = use(params)
    const router = useRouter()
    const pathname = usePathname()
    const { data: project, isPending, error, refetch } = useProjectQuery(id)

    // StepNav로 페이지 이동 시 프로젝트 데이터 refetch
    useEffect(() => {
        refetch()
    }, [pathname, refetch])

    useEffect(() => {
        if (!isPending && (error || !project)) {
            router.replace("/not-found")
        }
    }, [isPending, error, project, router])

    if (isPending || !project) {
        return (
            <div className="flex flex-col h-full">
                <StepNav projectId={id} company="" service="" />
                <PageLoader className="flex-1" />
            </div>
        )
    }

    return (
        <div className="flex flex-col h-full">
            <StepNav projectId={id} company={project.company_name} service={project.service_name || ""} />
            {children}
        </div>
    )
}
