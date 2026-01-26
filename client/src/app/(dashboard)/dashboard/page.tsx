"use client";

import { useState, useMemo } from "react";
import { LayoutGrid, List, Search, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { CaseCard } from "@/components/features/dashboard/CaseCard";
import {
    Pipeline,
    type PipelineFilter,
} from "@/components/features/dashboard/PipelineStep";
import { cases } from "@/data";
import { useUIStore } from "@/stores/ui-store";
import { useCaseStore } from "@/stores/case-store";
import { cn } from "@/lib/utils/cn";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Pagination } from "@/components/ui/pagination";
import { CASE_STATUS_LABELS } from "@/types/data/case";

type SortOrder = "newest" | "oldest";

const ITEMS_PER_PAGE = 9;

export default function DashboardPage() {
    const viewMode = useUIStore((state) => state.viewMode);
    const setViewMode = useUIStore((state) => state.setViewMode);
    const openNewCaseModal = useUIStore((state) => state.openNewCaseModal);
    const statusOverrides = useCaseStore((state) => state.statusOverrides);
    const [statusFilter, setStatusFilter] = useState<PipelineFilter>("all");
    const [sortOrder, setSortOrder] = useState<SortOrder>("newest");
    const [currentPage, setCurrentPage] = useState(1);
    const [searchQuery, setSearchQuery] = useState("");
    const [isSearchOpen, setIsSearchOpen] = useState(false);
    const [prevFilters, setPrevFilters] = useState({
        searchQuery,
        statusFilter,
        sortOrder,
    });

    // 케이스 상태 오버라이드 적용
    const casesWithOverrides = useMemo(() => {
        return cases.map((c) => ({
            ...c,
            status: statusOverrides[c.id]?.status || c.status,
            updatedAt: statusOverrides[c.id]?.updatedAt || c.updatedAt,
        }));
    }, [statusOverrides]);

    const stats = {
        consult: casesWithOverrides.filter((c) => c.status === "consult")
            .length,
        draft: casesWithOverrides.filter((c) => c.status === "draft").length,
        waiting: casesWithOverrides.filter((c) => c.status === "waiting")
            .length,
        done: casesWithOverrides.filter(
            (c) => c.status === "done" || c.status === "direct"
        ).length,
    };

    const pipelineSteps = [
        {
            id: "consult" as PipelineFilter,
            label: "기업상담",
            count: stats.consult,
        },
        {
            id: "draft" as PipelineFilter,
            label: "신청서작성",
            count: stats.draft,
        },
        {
            id: "waiting" as PipelineFilter,
            label: "결과대기",
            count: stats.waiting,
        },
        { id: "done" as PipelineFilter, label: "완료", count: stats.done },
    ];

    const filteredCases = useMemo(() => {
        let result = casesWithOverrides.filter((caseItem) => {
            // 1. Search Filter
            const matchesSearch =
                searchQuery === "" ||
                caseItem.company
                    .toLowerCase()
                    .includes(searchQuery.toLowerCase()) ||
                caseItem.service
                    .toLowerCase()
                    .includes(searchQuery.toLowerCase());

            // 2. Status Filter (unified for pipeline and dropdown)
            let matchesStatus = true;
            if (statusFilter !== "all") {
                if (statusFilter === "done") {
                    matchesStatus =
                        caseItem.status === "done" ||
                        caseItem.status === "direct";
                } else {
                    matchesStatus = caseItem.status === statusFilter;
                }
            }

            return matchesSearch && matchesStatus;
        });

        // 3. Sort
        result = [...result].sort((a, b) => {
            const dateA = new Date(a.updatedAt).getTime();
            const dateB = new Date(b.updatedAt).getTime();
            return sortOrder === "newest" ? dateB - dateA : dateA - dateB;
        });

        return result;
    }, [casesWithOverrides, searchQuery, statusFilter, sortOrder]);

    const totalPages = Math.ceil(filteredCases.length / ITEMS_PER_PAGE);

    const paginatedCases = useMemo(() => {
        const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
        return filteredCases.slice(startIndex, startIndex + ITEMS_PER_PAGE);
    }, [filteredCases, currentPage]);

    // 필터가 변경되면 첫 페이지로 리셋 (렌더링 중 조건부 업데이트)
    if (
        prevFilters.searchQuery !== searchQuery ||
        prevFilters.statusFilter !== statusFilter ||
        prevFilters.sortOrder !== sortOrder
    ) {
        setPrevFilters({ searchQuery, statusFilter, sortOrder });
        setCurrentPage(1);
    }

    const getFilterLabel = () => {
        if (statusFilter === "all") return "전체";
        const step = pipelineSteps.find((s) => s.id === statusFilter);
        return step?.label || "";
    };

    const toggleViewMode = () => {
        setViewMode(viewMode === "grid" ? "list" : "grid");
    };

    return (
        <div className="p-6 space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">대시보드</h1>
                </div>
            </div>

            <div className="mb-16">
                <div className="py-4">
                    <Pipeline
                        steps={pipelineSteps}
                        activeFilter={statusFilter}
                        onFilterChange={setStatusFilter}
                    />
                </div>
            </div>

            <div className="flex items-center justify-between">
                <div className="flex items-center">
                    <h2 className="text-lg font-semibold">케이스 목록</h2>
                    <Button
                        variant="ghost-muted"
                        size="icon-sm"
                        className="ml-2"
                        onClick={() => setIsSearchOpen(!isSearchOpen)}
                    >
                        <Search className="h-4 w-4" />
                    </Button>
                    <div
                        className={cn(
                            "overflow-hidden transition-all duration-200 ease-out",
                            isSearchOpen ? "w-48 opacity-100" : "w-0 opacity-0"
                        )}
                    >
                        <input
                            type="text"
                            placeholder="회사명, 서비스명으로 검색..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full px-2 py-1 bg-transparent border-0 border-b border-neutral-300 focus:border-teal-500 focus:outline-none text-sm placeholder:text-muted-foreground"
                            autoFocus={isSearchOpen}
                        />
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <Select
                        value={statusFilter}
                        onValueChange={(value) =>
                            setStatusFilter(value as PipelineFilter)
                        }
                    >
                        <SelectTrigger className="w-fit border-none shadow-none bg-transparent p-0 h-auto text-muted-foreground hover:text-foreground font-medium focus:ring-0 focus:ring-offset-0 gap-1">
                            <SelectValue placeholder="상태 필터" />
                        </SelectTrigger>
                        <SelectContent
                            sideOffset={4}
                            className="min-w-[115px] border-neutral-200"
                        >
                            <SelectItem value="all">전체 상태</SelectItem>
                            <SelectItem value="consult">
                                {CASE_STATUS_LABELS.consult}
                            </SelectItem>
                            <SelectItem value="draft">
                                {CASE_STATUS_LABELS.draft}
                            </SelectItem>
                            <SelectItem value="waiting">
                                {CASE_STATUS_LABELS.waiting}
                            </SelectItem>
                            <SelectItem value="done">
                                {CASE_STATUS_LABELS.done}
                            </SelectItem>
                        </SelectContent>
                    </Select>

                    <Select
                        value={sortOrder}
                        onValueChange={(value) =>
                            setSortOrder(value as SortOrder)
                        }
                    >
                        <SelectTrigger className="w-fit border-none shadow-none bg-transparent p-0 h-auto text-muted-foreground hover:text-foreground font-medium focus:ring-0 focus:ring-offset-0 gap-1">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent
                            sideOffset={4}
                            className="min-w-[115px] border-neutral-200"
                        >
                            <SelectItem value="newest">최신순</SelectItem>
                            <SelectItem value="oldest">오래된순</SelectItem>
                        </SelectContent>
                    </Select>

                    <Button
                        variant="outline"
                        size="icon-sm"
                        onClick={toggleViewMode}
                    >
                        {viewMode === "grid" ? (
                            <List className="h-4 w-4" />
                        ) : (
                            <LayoutGrid className="h-4 w-4" />
                        )}
                    </Button>

                    <Button
                        variant="gradient"
                        size="icon-sm"
                        onClick={openNewCaseModal}
                    >
                        <Plus className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            <div
                className={cn(
                    viewMode === "grid"
                        ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
                        : "space-y-0 divide-y divide-gray-200 border-y border-gray-200"
                )}
            >
                {filteredCases.length === 0 ? (
                    <div className="col-span-full text-center py-12 text-muted-foreground">
                        해당 상태의 케이스가 없습니다
                    </div>
                ) : (
                    paginatedCases.map((caseItem) => (
                        <CaseCard
                            key={caseItem.id}
                            caseData={caseItem}
                            viewMode={viewMode}
                        />
                    ))
                )}
            </div>

            <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={setCurrentPage}
                className="mt-15"
            />
        </div>
    );
}
