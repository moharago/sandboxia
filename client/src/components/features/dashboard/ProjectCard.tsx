"use client"

import { DeleteProjectModal } from "@/components/features/projects/DeleteProjectModal"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { ConfirmModal } from "@/components/ui/confirm-modal"
import { projectsApi } from "@/lib/api/projects"
import { getProjectPathFromProject } from "@/lib/utils/project-path"
import type { Project, ProjectStatus } from "@/types/data/project"
import { PROJECT_STATUS, PROJECT_STATUS_LABELS, TRACK_LABELS, calculateProgress } from "@/types/data/project"
import { useQueryClient } from "@tanstack/react-query"
import { CheckCircle2, Trash2 } from "lucide-react"
import Link from "next/link"
import { useState } from "react"

interface ProjectCardProps {
    project: Project
    viewMode?: "grid" | "list"
}

const statusBadgeVariant: Record<ProjectStatus, "success" | "warning" | "info" | "draft" | "done" | "direct"> = {
    1: "info", // 기업상담
    2: "draft", // 신청서작성
    3: "warning", // 결과대기
    4: "done", // 완료
    5: "direct", // 바로출시
}

export function ProjectCard({ project, viewMode = "grid" }: ProjectCardProps) {
    const queryClient = useQueryClient()
    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
    const [isCompleteModalOpen, setIsCompleteModalOpen] = useState(false)
    const [isCompleting, setIsCompleting] = useState(false)
    const isCompleted = project.status === PROJECT_STATUS.COMPLETED || project.status === PROJECT_STATUS.DIRECT_LAUNCH

    const formattedDate = new Date(project.updated_at)
        .toLocaleDateString("ko-KR", {
            year: "2-digit",
            month: "2-digit",
            day: "2-digit",
        })
        .replace(/\. /g, ".")
        .replace(/\.$/, "")

    const progress = calculateProgress(project.current_step, project.status)

    const handleCompleteClick = (e: React.MouseEvent) => {
        e.preventDefault()
        e.stopPropagation()
        setIsCompleteModalOpen(true)
    }

    const handleCompleteConfirm = async () => {
        setIsCompleting(true)
        try {
            await projectsApi.updateStatus(project.id, PROJECT_STATUS.COMPLETED)
            setIsCompleteModalOpen(false)
            queryClient.invalidateQueries({ queryKey: ["projects"] })
        } catch (error) {
            console.error("완료 처리 실패:", error)
        } finally {
            setIsCompleting(false)
        }
    }

    const handleDeleteClick = (e: React.MouseEvent) => {
        e.preventDefault()
        e.stopPropagation()
        setIsDeleteModalOpen(true)
    }

    if (viewMode === "list") {
        return (
            <>
                <Link href={getProjectPathFromProject(project)} className="block">
                    <div className="flex items-center gap-4 p-4 transition-colors hover:bg-muted/30 group">
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                                <h3 className="font-medium truncate">{project.company_name}</h3>
                                <Badge variant={statusBadgeVariant[project.status]} className="shrink-0">
                                    {PROJECT_STATUS_LABELS[project.status]}
                                </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground truncate">{project.service_name}</p>
                        </div>
                        <div className="hidden sm:flex items-center gap-6 text-sm text-muted-foreground">
                            {project.track && <span>{TRACK_LABELS[project.track]}</span>}
                            <span className="w-20 text-right">{formattedDate}</span>
                        </div>
                        <div className="flex items-center gap-1">
                            {!isCompleted && (
                                <Button variant="ghost-success" size="icon-sm" className="h-8 w-8" onClick={handleCompleteClick} title="완료 처리">
                                    <CheckCircle2 className="h-3.5 w-3.5" />
                                </Button>
                            )}
                            <Button variant="ghost-destructive" size="icon-sm" className="h-8 w-8" onClick={handleDeleteClick} title="삭제">
                                <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                        </div>
                    </div>
                </Link>
                <ConfirmModal
                    isOpen={isCompleteModalOpen}
                    onClose={() => setIsCompleteModalOpen(false)}
                    onConfirm={handleCompleteConfirm}
                    title="프로젝트 완료"
                    description={`"${project.company_name}" 프로젝트를 완료 처리하시겠습니까?`}
                    confirmLabel="완료 처리"
                    cancelLabel="취소"
                    isLoading={isCompleting}
                />
                <DeleteProjectModal
                    open={isDeleteModalOpen}
                    onOpenChange={setIsDeleteModalOpen}
                    projectId={project.id}
                    companyName={project.company_name}
                />
            </>
        )
    }

    return (
        <>
            <Link href={getProjectPathFromProject(project)} className="block group h-full">
                <Card className="hover:shadow-lg transition-all h-full flex flex-col">
                    <CardHeader className="pb-3">
                        <div className="flex items-start justify-between gap-2 overflow-hidden">
                            <h3 className="font-semibold truncate">{project.company_name}</h3>
                            <Badge variant={statusBadgeVariant[project.status]} className="shrink-0">
                                {PROJECT_STATUS_LABELS[project.status]}
                            </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground truncate">{project.service_name}</p>
                    </CardHeader>
                    <CardContent className="pb-3 flex-1">
                        <div className="space-y-3">
                            <div className="flex items-center justify-between text-sm">
                                <div>
                                    {project.track && <span className="px-2 py-1 bg-muted rounded text-xs">{TRACK_LABELS[project.track]}</span>}
                                </div>
                                <span className="font-medium">{progress}%</span>
                            </div>
                            <div className="h-1 w-full bg-gray-200 rounded-full overflow-hidden mb-0">
                                <div className="h-full bg-teal-600 transition-all duration-300 ease-in-out" style={{ width: `${progress}%` }} />
                            </div>

                            <div className="flex items-center justify-between text-sm pt-2">
                                <span className="text-muted-foreground">{formattedDate}</span>
                                <div className="flex items-center">
                                    {!isCompleted && (
                                        <Button variant="ghost-success" size="icon-sm" onClick={handleCompleteClick} title="완료 처리">
                                            <CheckCircle2 className="h-3.5 w-3.5" />
                                        </Button>
                                    )}
                                    <Button variant="ghost-destructive" size="icon-sm" onClick={handleDeleteClick} title="삭제">
                                        <Trash2 className="h-3.5 w-3.5" />
                                    </Button>
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </Link>
            <ConfirmModal
                isOpen={isCompleteModalOpen}
                onClose={() => setIsCompleteModalOpen(false)}
                onConfirm={handleCompleteConfirm}
                title="프로젝트 완료"
                description={`"${project.company_name}" 프로젝트를 완료 처리하시겠습니까?`}
                confirmLabel="완료 처리"
                cancelLabel="취소"
            />
            <DeleteProjectModal
                open={isDeleteModalOpen}
                onOpenChange={setIsDeleteModalOpen}
                projectId={project.id}
                companyName={project.company_name}
            />
        </>
    )
}
