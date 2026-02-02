"use client"

import { use } from "react"
import { notFound } from "next/navigation"
import { ServiceForm } from "@/components/features/project/ServiceForm"
import { useProjectQuery } from "@/hooks/queries/use-projects-query"

interface ServicePageProps {
    params: Promise<{ id: string }>
}

export default function ServicePage({ params }: ServicePageProps) {
    const { id } = use(params)
    const { data: projectData, isLoading, error } = useProjectQuery(id)

    if (isLoading) {
        return (
            <div className="py-6">
                <div className="container mx-auto px-4 flex items-center justify-center min-h-[50vh]">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                </div>
            </div>
        )
    }

    if (error || !projectData) {
        notFound()
    }

    // key로 projectData.id를 사용하여 프로젝트 변경 시 폼 리셋
    return <ServiceForm key={projectData.id} project={projectData} id={id} />
}
