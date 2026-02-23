"use client"

import { Pipeline, type PipelineFilter } from "@/components/features/dashboard/PipelineStep"
import { ProjectCard } from "@/components/features/dashboard/ProjectCard"
import { Button } from "@/components/ui/button"
import { PageLoader } from "@/components/ui/page-loader"
import { Pagination } from "@/components/ui/pagination"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useProjectsQuery } from "@/hooks/queries/use-projects-query"
import { cn } from "@/lib/utils/cn"
import { useUIStore } from "@/stores/ui-store"
import { PROJECT_STATUS, PROJECT_STATUS_LABELS, matchesStatusFilter } from "@/types/data/project"
import { LayoutGrid, List, Plus, Search } from "lucide-react"
import { useMemo, useState } from "react"

type SortOrder = "newest" | "oldest"

const ITEMS_PER_PAGE = 9

export default function DashboardPage() {
    const viewMode = useUIStore((state) => state.viewMode)
    const setViewMode = useUIStore((state) => state.setViewMode)
    const openNewCaseModal = useUIStore((state) => state.openNewCaseModal)
    const [statusFilter, setStatusFilter] = useState<PipelineFilter>("all")
    const [sortOrder, setSortOrder] = useState<SortOrder>("newest")
    const [currentPage, setCurrentPage] = useState(1)
    const [searchQuery, setSearchQuery] = useState("")
    const [isSearchOpen, setIsSearchOpen] = useState(false)

    // Supabase에서 프로젝트 조회
    const { data: projects = [], isLoading, error } = useProjectsQuery()

    // 이전 필터 값 추적 (렌더링 중 조건부 업데이트 패턴용)
    const [prevFilters, setPrevFilters] = useState({
        searchQuery,
        statusFilter,
        sortOrder,
    })

    // 상태별 통계
    const stats = {
        1: projects.filter((p) => p.status === PROJECT_STATUS.CONSULTING).length,
        2: projects.filter((p) => p.status === PROJECT_STATUS.DRAFTING).length,
        3: projects.filter((p) => p.status === PROJECT_STATUS.PENDING).length,
        4: projects.filter((p) => p.status === PROJECT_STATUS.COMPLETED || p.status === PROJECT_STATUS.DIRECT_LAUNCH).length,
    }

    const pipelineSteps = [
        { id: 1 as PipelineFilter, label: "기업상담", count: stats[1] },
        { id: 2 as PipelineFilter, label: "신청서작성", count: stats[2] },
        { id: 3 as PipelineFilter, label: "결과대기", count: stats[3] },
        { id: 4 as PipelineFilter, label: "완료", count: stats[4] },
    ]

    const filteredProjects = useMemo(() => {
        let result = projects.filter((projectItem) => {
            // 1. Search Filter
            const matchesSearch =
                searchQuery === "" ||
                projectItem.company_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                (projectItem.service_name?.toLowerCase().includes(searchQuery.toLowerCase()) ?? false)

            // 2. Status Filter
            const matchesStatus = matchesStatusFilter(projectItem.status, statusFilter)

            return matchesSearch && matchesStatus
        })

        // 3. Sort
        result = [...result].sort((a, b) => {
            const dateA = new Date(a.updated_at).getTime()
            const dateB = new Date(b.updated_at).getTime()
            return sortOrder === "newest" ? dateB - dateA : dateA - dateB
        })

        return result
    }, [projects, searchQuery, statusFilter, sortOrder])

    const totalPages = Math.ceil(filteredProjects.length / ITEMS_PER_PAGE)

    const paginatedProjects = useMemo(() => {
        const startIndex = (currentPage - 1) * ITEMS_PER_PAGE
        return filteredProjects.slice(startIndex, startIndex + ITEMS_PER_PAGE)
    }, [filteredProjects, currentPage])

    // 필터가 변경되면 첫 페이지로 리셋 (렌더링 중 조건부 업데이트)
    if (prevFilters.searchQuery !== searchQuery || prevFilters.statusFilter !== statusFilter || prevFilters.sortOrder !== sortOrder) {
        setPrevFilters({ searchQuery, statusFilter, sortOrder })
        setCurrentPage(1)
    }

    const toggleViewMode = () => {
        setViewMode(viewMode === "grid" ? "list" : "grid")
    }

    if (isLoading) {
        return (
            <div className="py-6">
                <div className="container">
                    <PageLoader />
                </div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="py-6">
                <div className="container flex flex-col items-center justify-center min-h-[400px] gap-4">
                    <p className="text-destructive">프로젝트를 불러오는데 실패했습니다</p>
                    <Button variant="outline" onClick={() => window.location.reload()}>
                        다시 시도
                    </Button>
                </div>
            </div>
        )
    }

    return (
        <div className="py-6">
            <div className="container space-y-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold">대시보드</h1>
                    </div>
                </div>

                <div className="mb-16">
                    <div className="py-4">
                        <Pipeline steps={pipelineSteps} activeFilter={statusFilter} onFilterChange={setStatusFilter} />
                    </div>
                </div>

                <div className="flex items-center justify-between">
                    <div className="flex items-center">
                        <h2 className="text-lg font-semibold">프로젝트 목록</h2>
                        <Button variant="ghost-muted" size="icon-sm" className="ml-2" onClick={() => setIsSearchOpen(!isSearchOpen)}>
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
                            value={String(statusFilter)}
                            onValueChange={(value) => setStatusFilter(value === "all" ? "all" : (Number(value) as PipelineFilter))}
                        >
                            <SelectTrigger className="w-fit border-none shadow-none bg-transparent p-0 h-auto text-muted-foreground hover:text-foreground font-medium focus:ring-0 focus:ring-offset-0 gap-1">
                                <SelectValue placeholder="상태 필터" />
                            </SelectTrigger>
                            <SelectContent sideOffset={4} className="min-w-[115px] border-neutral-200">
                                <SelectItem value="all">전체 상태</SelectItem>
                                <SelectItem value="1">{PROJECT_STATUS_LABELS[1]}</SelectItem>
                                <SelectItem value="2">{PROJECT_STATUS_LABELS[2]}</SelectItem>
                                <SelectItem value="3">{PROJECT_STATUS_LABELS[3]}</SelectItem>
                                <SelectItem value="4">{PROJECT_STATUS_LABELS[4]}</SelectItem>
                            </SelectContent>
                        </Select>

                        <Select value={sortOrder} onValueChange={(value) => setSortOrder(value as SortOrder)}>
                            <SelectTrigger className="w-fit border-none shadow-none bg-transparent p-0 h-auto text-muted-foreground hover:text-foreground font-medium focus:ring-0 focus:ring-offset-0 gap-1">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent sideOffset={4} className="min-w-[115px] border-neutral-200">
                                <SelectItem value="newest">최신순</SelectItem>
                                <SelectItem value="oldest">오래된순</SelectItem>
                            </SelectContent>
                        </Select>

                        <Button variant="outline" size="icon-sm" onClick={toggleViewMode}>
                            {viewMode === "grid" ? <List className="h-4 w-4" /> : <LayoutGrid className="h-4 w-4" />}
                        </Button>

                        <Button variant="gradient" size="icon-sm" onClick={openNewCaseModal}>
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
                    {filteredProjects.length === 0 ? (
                        <div className="col-span-full text-center py-12 text-muted-foreground">해당 상태의 프로젝트가 없습니다</div>
                    ) : (
                        paginatedProjects.map((projectItem) => <ProjectCard key={projectItem.id} project={projectItem} viewMode={viewMode} />)
                    )}
                </div>

                <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={setCurrentPage} className="mt-15" />
            </div>
        </div>
    )
}
