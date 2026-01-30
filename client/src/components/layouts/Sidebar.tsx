"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { projects } from "@/data"
import { cn } from "@/lib/utils/cn"
import { useUIStore } from "@/stores/ui-store"
import type { ProjectStatus } from "@/types/data/project"
import { PROJECT_STATUS_LABELS, SANDBOX_TYPE_LABELS } from "@/types/data/project"
import { FolderOpen, PanelLeft, PanelRight, Plus, Search } from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import * as React from "react"

type SortOrder = "newest" | "oldest"

const statusBadgeVariant: Record<ProjectStatus, "success" | "warning" | "info" | "draft" | "done" | "direct"> = {
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
    const [selectedStatus, setSelectedStatus] = React.useState<ProjectStatus | "all">("all")
    const [sortOrder, setSortOrder] = React.useState<SortOrder>("newest")

    const filteredProjects = React.useMemo(() => {
        let result = projects.filter((projectItem) => {
            const matchesSearch =
                searchQuery === "" ||
                projectItem.company.toLowerCase().includes(searchQuery.toLowerCase()) ||
                projectItem.service.toLowerCase().includes(searchQuery.toLowerCase())

            const matchesStatus = selectedStatus === "all" || projectItem.status === selectedStatus

            return matchesSearch && matchesStatus
        })

        result = [...result].sort((a, b) => {
            const dateA = new Date(a.updatedAt).getTime()
            const dateB = new Date(b.updatedAt).getTime()
            return sortOrder === "newest" ? dateB - dateA : dateA - dateB
        })

        return result
    }, [searchQuery, selectedStatus, sortOrder])

    // 닫혔을 때는 버튼만 떠있도록
    if (!sidebarOpen) {
        return (
            <Button
                variant="ghost"
                size="icon"
                className="absolute left-4 top-4 z-50 h-8 w-8 bg-background shadow-sm border border-border text-teal-600 hover:text-teal-700 hover:bg-teal-50"
                onClick={toggleSidebar}
                aria-label="사이드바 열기"
            >
                <PanelRight className="h-4 w-4" />
            </Button>
        )
    }

    return (
        <aside className="w-72 border-r border-border bg-muted/30 flex flex-col transition-all duration-300">
            <div className="p-4 pb-2 border-b border-border">
                <div className="flex items-center gap-2">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 shrink-0 text-teal-600 hover:text-teal-700 hover:bg-teal-50"
                        onClick={toggleSidebar}
                        aria-label="사이드바 닫기"
                    >
                        <PanelLeft className="h-4 w-4" />
                    </Button>
                    <div className="flex-1">
                        <Button variant="gradient" className="w-full gap-2 h-8" onClick={openNewCaseModal}>
                            <Plus className="h-4 w-4" />새 프로젝트
                        </Button>
                    </div>
                </div>

                <div className="pt-3">
                    <div className="flex items-center justify-between">
                        <div className="flex gap-2">
                            <Select value={selectedStatus} onValueChange={(value) => setSelectedStatus(value as ProjectStatus | "all")}>
                                <SelectTrigger className="w-fit h-auto border-none shadow-none bg-transparent p-0 text-muted-foreground hover:text-foreground font-medium focus:ring-0 focus:ring-offset-0 gap-1">
                                    <SelectValue placeholder="상태 필터" />
                                </SelectTrigger>
                                <SelectContent sideOffset={4} className="min-w-[115px] border-neutral-200">
                                    <SelectItem value="all">전체 상태</SelectItem>
                                    <SelectItem value="consult">{PROJECT_STATUS_LABELS.consult}</SelectItem>
                                    <SelectItem value="draft">{PROJECT_STATUS_LABELS.draft}</SelectItem>
                                    <SelectItem value="waiting">{PROJECT_STATUS_LABELS.waiting}</SelectItem>
                                    <SelectItem value="done">{PROJECT_STATUS_LABELS.done}</SelectItem>
                                    <SelectItem value="direct">{PROJECT_STATUS_LABELS.direct}</SelectItem>
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
                                    placeholder="프로젝트 검색..."
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

            <div className="flex-1 overflow-y-auto">
                {filteredProjects.length === 0 ? (
                    <div className="p-4 text-center text-muted-foreground text-sm">
                        <FolderOpen className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        프로젝트가 없습니다
                    </div>
                ) : (
                    <ul className="divide-y divide-border">
                        {filteredProjects.map((projectItem) => (
                            <li key={projectItem.id}>
                                <Link
                                    href={`/projects/${projectItem.id}`}
                                    className={cn(
                                        "block p-4 hover:bg-muted/50 transition-colors",
                                        pathname?.startsWith(`/projects/${projectItem.id}`) && "bg-muted"
                                    )}
                                >
                                    <div className="flex items-start justify-between gap-2 mb-1">
                                        <span className="font-medium text-sm truncate">{projectItem.company}</span>
                                        <Badge variant={statusBadgeVariant[projectItem.status]} className="shrink-0">
                                            {PROJECT_STATUS_LABELS[projectItem.status]}
                                        </Badge>
                                    </div>
                                    <p className="text-xs text-muted-foreground truncate mb-2">{projectItem.service}</p>
                                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                                        <span>{projectItem.sandboxType && SANDBOX_TYPE_LABELS[projectItem.sandboxType]}</span>
                                        <span>{projectItem.progress}%</span>
                                    </div>
                                    <div className="mt-1.5 h-1 bg-muted rounded-full overflow-hidden">
                                        <div
                                            className="h-full bg-primary transition-all"
                                            style={{
                                                width: `${projectItem.progress}%`,
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
