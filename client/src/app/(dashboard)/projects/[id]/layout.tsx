"use client"

import { use, useEffect, type ReactNode } from "react"
import { useRouter } from "next/navigation"
import { StepNav } from "@/components/features/project/StepNav"
import { PageLoader } from "@/components/ui/page-loader"
import { useProjectQuery } from "@/hooks/queries/use-projects-query"

interface ProjectLayoutProps {
    children: ReactNode
    params: Promise<{ id: string }>
}

export default function ProjectLayout({ children, params }: ProjectLayoutProps) {
    const { id } = use(params)
    const router = useRouter()
    const { data: project, isPending, error } = useProjectQuery(id)

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
