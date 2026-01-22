import { cn } from "@/lib/utils/cn";
import type { CaseStatus } from "@/types/data";

interface PipelineStepProps {
  step: number;
  label: string;
  count: number;
  isActive?: boolean;
  onClick?: () => void;
  className?: string;
}

export function PipelineStep({
  step,
  label,
  count,
  isActive = false,
  onClick,
  className,
}: PipelineStepProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex flex-col items-center text-center group cursor-pointer relative w-10 shrink-0",
        className
      )}
    >
      <div
        className={cn(
          "w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium transition-colors relative z-10",
          isActive
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-muted-foreground group-hover:bg-muted/80"
        )}
      >
        {step}
      </div>
      <div className="absolute top-full mt-2 left-1/2 -translate-x-1/2 whitespace-nowrap">
        <p
          className={cn(
            "text-sm font-medium transition-colors",
            isActive
              ? "text-foreground"
              : "text-muted-foreground group-hover:text-foreground"
          )}
        >
          {label}
        </p>
        <p className="text-xs text-muted-foreground text-center">{count}건</p>
      </div>
    </button>
  );
}

export type PipelineFilter = "all" | "consult" | "draft" | "waiting" | "done";

interface PipelineProps {
  steps: Array<{
    id: PipelineFilter;
    label: string;
    count: number;
  }>;
  activeFilter: PipelineFilter;
  onFilterChange: (filter: PipelineFilter) => void;
}

export function Pipeline({
  steps,
  activeFilter,
  onFilterChange,
}: PipelineProps) {
  return (
    <div className="flex items-start justify-between relative w-full px-5">
      <div className="absolute top-5 left-5 right-5 h-0.5 bg-muted" />
      {steps.map((step, index) => (
        <PipelineStep
          key={step.id}
          step={index + 1}
          label={step.label}
          count={step.count}
          isActive={activeFilter === step.id}
          onClick={() => onFilterChange(step.id)}
        />
      ))}
    </div>
  );
}
