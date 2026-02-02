"use client"

import { use } from "react"
import { ServiceForm } from "@/components/features/project/ServiceForm"
import { useProjectQuery } from "@/hooks/queries/use-projects-query"

interface ServicePageProps {
    params: Promise<{ id: string }>
}

export default function ServicePage({ params }: ServicePageProps) {
    const { id } = use(params)
    // Layout에서 이미 프로젝트 유효성 검사를 수행하므로
    // 여기서는 캐시된 데이터를 사용 (TanStack Query 캐싱)
    const { data: projectData } = useProjectQuery(id)

    // Layout이 로딩/에러 상태를 처리하므로 projectData는 항상 존재
    if (!projectData) {
        return null
    }

    // key로 projectData.id를 사용하여 프로젝트 변경 시 폼 리셋
    return <ServiceForm key={projectData.id} project={projectData} id={id} />
}
