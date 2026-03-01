"use client"

import { Loader2 } from "lucide-react"
import { cn } from "@/lib/utils/cn"

interface PageLoaderProps {
    className?: string
}

export function PageLoader({ className }: PageLoaderProps) {
    return (
        <div className={cn("flex items-center justify-center min-h-[400px]", className)}>
            <Loader2 className="h-8 w-8 animate-spin text-teal-500" />
        </div>
    )
}
