"use client"

import { use, type ReactNode } from "react"
import { notFound } from "next/navigation"
import { StepNav } from "@/components/features/project/StepNav"
import { projects } from "@/data"

interface ProjectLayoutProps {
    children: ReactNode
    params: Promise<{ id: string }>
}

export default function ProjectLayout({ children, params }: ProjectLayoutProps) {
    const { id } = use(params)
    const projectData = projects.find((p) => p.id === id)

    if (!projectData) {
        notFound()
    }

    return (
        <div className="flex flex-col h-full">
            <StepNav projectId={id} company={projectData.company} service={projectData.service} />
            {children}
        </div>
    )
}
