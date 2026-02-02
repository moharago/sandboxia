"use client"

import { cn } from "@/lib/utils/cn"
import { getProjectPath, STEP_PATHS } from "@/lib/utils/project-path"
import type { ProjectStep } from "@/types/data/project"
import { PROJECT_STEP_LABELS } from "@/types/data/project"
import { ChevronRight } from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"

interface StepNavProps {
    projectId: string
    company: string
    service: string
}

export function StepNav({ projectId, company, service }: StepNavProps) {
    const pathname = usePathname()

    const steps = ([1, 2, 3, 4] as ProjectStep[]).map((step) => ({
        step,
        label: PROJECT_STEP_LABELS[step],
        path: getProjectPath(projectId, step),
    }))

    return (
        <nav className="sticky top-0 z-40 bg-background">
            <div className="container">
                <div className="flex items-center justify-between">
                    <ol className="flex items-center">
                        {steps.map((step, index) => {
                            const isActive = pathname?.includes(STEP_PATHS[step.step])

                            return (
                                <li key={step.step} className="flex items-center">
                                    <Link
                                        href={step.path}
                                        className={cn(
                                            "flex items-center gap-3 py-4 text-sm font-medium transition-colors",
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

                                    {index < steps.length - 1 && <ChevronRight className="h-4 w-4 text-muted-foreground mx-6" />}
                                </li>
                            )
                        })}
                    </ol>
                    <div className="hidden md:flex flex-col items-end text-sm">
                        <span className="font-medium truncate max-w-[200px]">{company}</span>
                        <span className="text-muted-foreground truncate max-w-[200px] text-xs">{service}</span>
                    </div>
                </div>
            </div>
        </nav>
    )
}
