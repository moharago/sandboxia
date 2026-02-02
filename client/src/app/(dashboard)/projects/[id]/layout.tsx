"use client"

import { use, type ReactNode } from "react"
import { notFound } from "next/navigation"
import { StepNav } from "@/components/features/project/StepNav"
import { useProjectQuery } from "@/hooks/queries/use-projects-query"

interface ProjectLayoutProps {
    children: ReactNode
    params: Promise<{ id: string }>
}

export default function ProjectLayout({ children, params }: ProjectLayoutProps) {
    const { id } = use(params)
    const { data: project, isLoading, error } = useProjectQuery(id)

    if (isLoading) {
        return (
            <div className="flex flex-col h-full">
                <div className="h-14 border-b bg-background" /> {/* StepNav placeholder */}
                <div className="flex-1 flex items-center justify-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                </div>
            </div>
        )
    }

    if (error || !project) {
        notFound()
    }

    return (
        <div className="flex flex-col h-full">
            <StepNav projectId={id} company={project.company_name} service={project.service_name || ""} />
            {children}
        </div>
    )
}
