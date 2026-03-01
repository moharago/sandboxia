"use client"

import { StepNav } from "@/components/features/project/StepNav"
import { PageLoader } from "@/components/ui/page-loader"
import { useProjectQuery } from "@/hooks/queries/use-projects-query"
import { useRouter } from "next/navigation"
import { use, useEffect, type ReactNode } from "react"

interface ProjectLayoutProps {
    children: ReactNode
    params: Promise<{ id: string }>
}

export default function ProjectLayout({ children, params }: ProjectLayoutProps) {
    const { id } = use(params)
    const router = useRouter()
    const { data: project, isPending, error } = useProjectQuery(id)

    // 에러 발생 시에만 not-found로 이동
    useEffect(() => {
        if (!isPending && error) {
            router.replace("/not-found")
        }
    }, [isPending, error, router])

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
