import Link from "next/link";
import { Calendar, ArrowRight } from "lucide-react";
import {
  Card,
  CardHeader,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Case, CaseStatus } from "@/types/data";
import {
  CASE_STATUS_LABELS,
  CASE_DOMAIN_LABELS,
  CASE_STAGE_LABELS,
  SANDBOX_TYPE_LABELS,
} from "@/types/data";
import { cn } from "@/lib/utils/cn";

interface CaseCardProps {
  caseData: Case;
  viewMode?: "grid" | "list";
}

const statusBadgeVariant: Record<
  CaseStatus,
  "success" | "warning" | "info" | "draft" | "done" | "direct"
> = {
  consult: "info",
  draft: "draft",
  waiting: "warning",
  done: "done",
  direct: "direct",
};

export function CaseCard({ caseData, viewMode = "grid" }: CaseCardProps) {
  const formattedDate = new Date(caseData.updatedAt)
    .toLocaleDateString("ko-KR", {
      year: "2-digit",
      month: "2-digit",
      day: "2-digit",
    })
    .replace(/\. /g, ".")
    .replace(/\.$/, "");

  if (viewMode === "list") {
    return (
      <Link href={`/cases/${caseData.id}`} className="block">
        <div className="flex items-center gap-4 p-4 transition-colors hover:bg-muted/30 group">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-medium truncate">{caseData.company}</h3>
              <Badge
                variant={statusBadgeVariant[caseData.status]}
                className="shrink-0"
              >
                {CASE_STATUS_LABELS[caseData.status]}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground truncate">
              {caseData.service}
            </p>
          </div>
          <div className="hidden sm:flex items-center gap-6 text-sm text-muted-foreground">
            {caseData.sandboxType && (
              <span>{SANDBOX_TYPE_LABELS[caseData.sandboxType]}</span>
            )}
            <span className="w-20 text-right">{formattedDate}</span>
          </div>
          <Button
            variant="text"
            size="sm"
            className="gap-1 group-hover:text-primary transition-colors"
          >
            상세보기 <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </Link>
    );
  }

  return (
    <Link href={`/cases/${caseData.id}`} className="block group h-full">
      <Card className="hover:shadow-lg transition-all h-full flex flex-col">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-2 overflow-hidden">
            <h3 className="font-semibold truncate">{caseData.company}</h3>
            <Badge
              variant={statusBadgeVariant[caseData.status]}
              className="shrink-0"
            >
              {CASE_STATUS_LABELS[caseData.status]}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground truncate">
            {caseData.service}
          </p>
        </CardHeader>
        <CardContent className="pb-3 flex-1">
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <div>
                {caseData.sandboxType && (
                  <span className="px-2 py-1 bg-muted rounded text-xs">
                    {SANDBOX_TYPE_LABELS[caseData.sandboxType]}
                  </span>
                )}
              </div>
              <span className="font-medium">{caseData.progress}%</span>
            </div>
            <div className="h-1 w-full bg-gray-200 rounded-full overflow-hidden mb-0">
              <div
                className="h-full bg-teal-600 transition-all duration-300 ease-in-out"
                style={{ width: `${caseData.progress}%` }}
              />
            </div>

            <div className="flex items-center justify-between text-sm pt-2">
              <span className="text-muted-foreground">{formattedDate}</span>
              <Button
                size="sm"
                variant="text"
                className="px-0 group-hover:text-primary transition-colors"
              >
                상세보기
                <ArrowRight className="h-3 w-3" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
