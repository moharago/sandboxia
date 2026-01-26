import * as React from "react"
import { cn } from "@/lib/utils/cn"

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
    value?: number
    max?: number
    showLabel?: boolean
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(({ className, value = 0, max = 100, showLabel = false, ...props }, ref) => {
    const percentage = max <= 0 ? 0 : Math.min(Math.max((Math.max(value, 0) / max) * 100, 0), 100)

    return (
        <div className={cn("relative", className)} {...props}>
            <div
                ref={ref}
                className="h-2 w-full overflow-hidden rounded-full bg-secondary"
                role="progressbar"
                aria-valuenow={value}
                aria-valuemin={0}
                aria-valuemax={max}
            >
                <div className="h-full bg-primary transition-all duration-300 ease-in-out" style={{ width: `${percentage}%` }} />
            </div>
            {showLabel && <span className="absolute right-0 top-3 text-xs text-muted-foreground">{Math.round(percentage)}%</span>}
        </div>
    )
})
Progress.displayName = "Progress"

export { Progress }
