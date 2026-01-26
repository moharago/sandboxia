"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils/cn"
import type { CaseStage } from "@/types/data/case"
import { CASE_STAGE_LABELS } from "@/types/data/case"

interface StepNavProps {
    caseId: string
    company: string
    service: string
}

const stepPaths: Record<CaseStage, string> = {
    1: "service",
    2: "market",
    3: "track",
    4: "draft",
}

export function StepNav({ caseId, company, service }: StepNavProps) {
    const pathname = usePathname()

    const steps = ([1, 2, 3, 4] as CaseStage[]).map((step) => ({
        step,
        label: CASE_STAGE_LABELS[step],
        path: `/cases/${caseId}/${stepPaths[step]}`,
    }))

    return (
        <nav className="sticky top-0 z-40 bg-background">
            <div className="container mx-auto">
                <div className="flex items-center justify-between">
                    <ol className="flex items-center">
                        {steps.map((step, index) => {
                            const isActive = pathname?.includes(stepPaths[step.step])

                            return (
                                <li key={step.step} className="flex items-center">
                                    <Link
                                        href={step.path}
                                        className={cn(
                                            "flex items-center gap-3 py-3 px-4 text-sm font-medium transition-colors",
                                            isActive ? "text-primary" : "text-muted-foreground hover:text-foreground"
                                        )}
                                    >
                                        <span
                                            className={cn(
                                                "flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold",
                                                isActive ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                                            )}
                                        >
                                            {step.step}
                                        </span>
                                        <span className="hidden sm:inline">{step.label}</span>
                                    </Link>

                                    {index < steps.length - 1 && <ChevronRight className="h-4 w-4 text-muted-foreground mx-2" />}
                                </li>
                            )
                        })}
                    </ol>
                    <div className="hidden md:flex flex-col items-end text-sm pr-4">
                        <span className="font-medium truncate max-w-[200px]">{company}</span>
                        <span className="text-muted-foreground truncate max-w-[200px] text-xs">{service}</span>
                    </div>
                </div>
            </div>
        </nav>
    )
}
