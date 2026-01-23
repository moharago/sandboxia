import * as React from "react";
import { ChevronLeft, ChevronRight, MoreHorizontal } from "lucide-react";
import { cn } from "@/lib/utils/cn";

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  className?: string;
}

export function Pagination({
  currentPage,
  totalPages,
  onPageChange,
  className,
}: PaginationProps) {
  const getPageNumbers = () => {
    const pages: (number | "ellipsis")[] = [];

    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Expand window to show 2 pages on each side of current
      const start = Math.max(2, currentPage - 2);
      const end = Math.min(totalPages - 1, currentPage + 2);

      // Derive ellipsis flags from the window
      const showEllipsisStart = start > 2;
      const showEllipsisEnd = end < totalPages - 1;

      pages.push(1);

      if (showEllipsisStart) {
        pages.push("ellipsis");
      }

      for (let i = start; i <= end; i++) {
        pages.push(i);
      }

      if (showEllipsisEnd) {
        pages.push("ellipsis");
      }

      pages.push(totalPages);
    }

    return pages;
  };

  if (totalPages <= 1) return null;

  const baseButtonClass =
    "flex h-9 w-9 items-center justify-center rounded-full text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500";

  const arrowButtonClass = cn(
    baseButtonClass,
    "border border-neutral-200 text-neutral-600 hover:bg-neutral-100 disabled:opacity-40 disabled:pointer-events-none"
  );

  const pageButtonClass = (isActive: boolean) =>
    cn(
      baseButtonClass,
      isActive
        ? "border-2 border-teal-500 text-teal-600 bg-transparent"
        : "border border-neutral-200 text-neutral-600 hover:bg-neutral-100"
    );

  return (
    <nav
      className={cn("flex items-center justify-center", className)}
      aria-label="페이지네이션"
    >
      <button
        type="button"
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        aria-label="이전 페이지"
        className={cn(arrowButtonClass, "mr-6")}
      >
        <ChevronLeft className="h-4 w-4" />
      </button>

      <div className="flex items-center gap-2">
        {getPageNumbers().map((page, index) =>
          page === "ellipsis" ? (
            <span
              key={`ellipsis-${index}`}
              className="flex h-9 w-9 items-center justify-center"
            >
              <MoreHorizontal className="h-4 w-4 text-neutral-400" />
            </span>
          ) : (
            <button
              type="button"
              key={page}
              onClick={() => onPageChange(page)}
              aria-label={`${page} 페이지`}
              aria-current={currentPage === page ? "page" : undefined}
              className={pageButtonClass(currentPage === page)}
            >
              {page}
            </button>
          )
        )}
      </div>

      <button
        type="button"
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        aria-label="다음 페이지"
        className={cn(arrowButtonClass, "ml-6")}
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    </nav>
  );
}
