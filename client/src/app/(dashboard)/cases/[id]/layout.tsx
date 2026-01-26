"use client"

import { use, type ReactNode } from "react"
import { notFound } from "next/navigation"
import { StepNav } from "@/components/features/case/StepNav"
import { cases } from "@/data"

interface CaseLayoutProps {
    children: ReactNode
    params: Promise<{ id: string }>
}

export default function CaseLayout({ children, params }: CaseLayoutProps) {
    const { id } = use(params)
    const caseData = cases.find((c) => c.id === id)

    if (!caseData) {
        notFound()
    }

    return (
        <div className="flex flex-col h-full">
            <StepNav caseId={id} company={caseData.company} service={caseData.service} />
            <div className="flex-1 overflow-y-auto">{children}</div>
        </div>
    )
}
