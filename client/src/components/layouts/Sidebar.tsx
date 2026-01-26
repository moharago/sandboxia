"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Plus, Search, FolderOpen, PanelLeft, PanelRight } from "lucide-react"
import { useUIStore } from "@/stores/ui-store"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { cn } from "@/lib/utils/cn"
import { cases } from "@/data"
import type { Case, CaseStatus } from "@/types/data/case"
import { CASE_STATUS_LABELS, SANDBOX_TYPE_LABELS } from "@/types/data/case"

type SortOrder = "newest" | "oldest"

const statusBadgeVariant: Record<CaseStatus, "success" | "warning" | "info" | "draft" | "done" | "direct"> = {
    consult: "info",
    draft: "draft",
    waiting: "warning",
    done: "done",
    direct: "direct",
}

export function Sidebar() {
    const pathname = usePathname()
    const { sidebarOpen, toggleSidebar, openNewCaseModal } = useUIStore()
    const [searchQuery, setSearchQuery] = React.useState("")
    const [isSearchOpen, setIsSearchOpen] = React.useState(false)
    const [selectedStatus, setSelectedStatus] = React.useState<CaseStatus | "all">("all")
    const [sortOrder, setSortOrder] = React.useState<SortOrder>("newest")

    const filteredCases = React.useMemo(() => {
        let result = cases.filter((caseItem) => {
            const matchesSearch =
                searchQuery === "" ||
                caseItem.company.toLowerCase().includes(searchQuery.toLowerCase()) ||
                caseItem.service.toLowerCase().includes(searchQuery.toLowerCase())

            const matchesStatus = selectedStatus === "all" || caseItem.status === selectedStatus

            return matchesSearch && matchesStatus
        })

        result = [...result].sort((a, b) => {
            const dateA = new Date(a.updatedAt).getTime()
            const dateB = new Date(b.updatedAt).getTime()
            return sortOrder === "newest" ? dateB - dateA : dateA - dateB
        })

        return result
    }, [searchQuery, selectedStatus, sortOrder])

    return (
        <aside
            className={cn(
                "border-r border-border bg-muted/30 flex flex-col transition-all duration-300 relative",
                sidebarOpen ? "w-72 delay-0" : "w-12 h-screen delay-150"
            )}
        >
            <div className={cn("border-b border-border transition-all duration-300", sidebarOpen ? "p-4 pb-2" : "p-2")}>
                <div className="flex items-center gap-2">
                    <Button
                        variant="ghost"
                        size="icon"
                        className={cn("h-8 w-8 shrink-0 text-teal-600 hover:text-teal-700 hover:bg-teal-50", !sidebarOpen && "mx-auto")}
                        onClick={toggleSidebar}
                        aria-label={sidebarOpen ? "사이드바 닫기" : "사이드바 열기"}
                    >
                        {sidebarOpen ? <PanelLeft className="h-4 w-4" /> : <PanelRight className="h-4 w-4" />}
                    </Button>
                    <div
                        className={cn(
                            "flex-1 transition-opacity duration-150 overflow-hidden",
                            sidebarOpen ? "opacity-100 delay-300" : "opacity-0 w-0 delay-0"
                        )}
                    >
                        <Button variant="gradient" className="w-full gap-2 h-8" onClick={openNewCaseModal}>
                            <Plus className="h-4 w-4" />새 케이스
                        </Button>
                    </div>
                </div>

                <div
                    className={cn(
                        "transition-all duration-150 overflow-hidden",
                        sidebarOpen ? "opacity-100 pt-3 max-h-40 delay-300" : "opacity-0 max-h-0 delay-0"
                    )}
                >
                    <div className="flex items-center justify-between">
                        <div className="flex gap-2">
                            <Select value={selectedStatus} onValueChange={(value) => setSelectedStatus(value as CaseStatus | "all")}>
                                <SelectTrigger className="w-fit h-auto border-none shadow-none bg-transparent p-0 text-muted-foreground hover:text-foreground font-medium focus:ring-0 focus:ring-offset-0 gap-1">
                                    <SelectValue placeholder="상태 필터" />
                                </SelectTrigger>
                                <SelectContent sideOffset={4} className="min-w-[115px] border-neutral-200">
                                    <SelectItem value="all">전체 상태</SelectItem>
                                    <SelectItem value="consult">{CASE_STATUS_LABELS.consult}</SelectItem>
                                    <SelectItem value="draft">{CASE_STATUS_LABELS.draft}</SelectItem>
                                    <SelectItem value="waiting">{CASE_STATUS_LABELS.waiting}</SelectItem>
                                    <SelectItem value="done">{CASE_STATUS_LABELS.done}</SelectItem>
                                    <SelectItem value="direct">{CASE_STATUS_LABELS.direct}</SelectItem>
                                </SelectContent>
                            </Select>

                            <Select value={sortOrder} onValueChange={(value) => setSortOrder(value as SortOrder)}>
                                <SelectTrigger className="w-fit h-auto border-none shadow-none bg-transparent p-0 text-muted-foreground hover:text-foreground font-medium focus:ring-0 focus:ring-offset-0 gap-1">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent sideOffset={4} className="min-w-[115px] border-neutral-200">
                                    <SelectItem value="newest">최신순</SelectItem>
                                    <SelectItem value="oldest">오래된순</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <Button
                            variant="ghost-muted"
                            size="icon-sm"
                            onClick={() => setIsSearchOpen(!isSearchOpen)}
                            aria-label={isSearchOpen ? "검색 닫기" : "검색 열기"}
                        >
                            <Search className="h-4 w-4" />
                        </Button>
                    </div>

                    <div
                        className={cn(
                            "grid transition-all duration-200 ease-out",
                            isSearchOpen ? "grid-rows-[1fr] opacity-100 mt-1" : "grid-rows-[0fr] opacity-0"
                        )}
                    >
                        <div className="overflow-hidden">
                            <div className="relative">
                                <Search className="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <input
                                    type="text"
                                    placeholder="케이스 검색..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="w-full pl-6 pr-2 py-2 bg-transparent border-0 focus:outline-none text-sm placeholder:text-muted-foreground"
                                    autoFocus={isSearchOpen}
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div
                className={cn(
                    "flex-1 transition-all duration-150 overflow-hidden",
                    sidebarOpen ? "opacity-100 overflow-y-auto delay-300" : "opacity-0 delay-0"
                )}
            >
                {filteredCases.length === 0 ? (
                    <div className="p-4 text-center text-muted-foreground text-sm">
                        <FolderOpen className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        케이스가 없습니다
                    </div>
                ) : (
                    <ul className="divide-y divide-border">
                        {filteredCases.map((caseItem) => (
                            <li key={caseItem.id}>
                                <Link
                                    href={`/cases/${caseItem.id}`}
                                    className={cn(
                                        "block p-4 hover:bg-muted/50 transition-colors",
                                        pathname?.startsWith(`/cases/${caseItem.id}`) && "bg-muted"
                                    )}
                                >
                                    <div className="flex items-start justify-between gap-2 mb-1">
                                        <span className="font-medium text-sm truncate">{caseItem.company}</span>
                                        <Badge variant={statusBadgeVariant[caseItem.status]} className="shrink-0">
                                            {CASE_STATUS_LABELS[caseItem.status]}
                                        </Badge>
                                    </div>
                                    <p className="text-xs text-muted-foreground truncate mb-2">{caseItem.service}</p>
                                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                                        <span>{caseItem.sandboxType && SANDBOX_TYPE_LABELS[caseItem.sandboxType]}</span>
                                        <span>{caseItem.progress}%</span>
                                    </div>
                                    <div className="mt-1.5 h-1 bg-muted rounded-full overflow-hidden">
                                        <div
                                            className="h-full bg-primary transition-all"
                                            style={{
                                                width: `${caseItem.progress}%`,
                                            }}
                                        />
                                    </div>
                                </Link>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </aside>
    )
}
