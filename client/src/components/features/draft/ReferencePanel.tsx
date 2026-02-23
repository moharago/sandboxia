"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { formatDateIso } from "@/lib/utils/date"
import type { ApprovalCase, Regulation } from "@/types/api/eligibility"
import { BookOpen, ChevronDown, ChevronUp, ExternalLink, PanelLeft, PanelRight, Scale } from "lucide-react"
import { useState } from "react"

export interface CaseData {
    id: string | number
    title: string
    company: string
    approvedDate?: string
    track: string
    summary: string
    relevance?: number
    link?: string
}

interface CaseItemProps {
    caseData: ApprovalCase
    index: number
}

function CaseItem({ caseData, index }: CaseItemProps) {
    const [isExpanded, setIsExpanded] = useState(false)

    const handleToggle = () => setIsExpanded(!isExpanded)
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault()
            handleToggle()
        }
    }

    return (
        <div className="border border-border rounded-lg p-3 hover:bg-muted/50 transition-colors">
            <button
                type="button"
                className="w-full flex items-start justify-between gap-2 cursor-pointer text-left"
                onClick={handleToggle}
                onKeyDown={handleKeyDown}
                aria-expanded={isExpanded}
                aria-controls={`case-content-${index}`}
            >
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                        <Badge variant="outline" className="text-xs shrink-0">
                            {caseData.track}
                        </Badge>
                        {caseData.date && <span className="text-xs text-muted-foreground">{formatDateIso(caseData.date)}</span>}
                    </div>
                    <h4 className="font-medium text-sm">{caseData.title}</h4>
                    <p className="text-xs text-muted-foreground">{caseData.company}</p>
                </div>
                <div className="flex items-center">
                    {isExpanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
                </div>
            </button>
            {isExpanded && (
                <div id={`case-content-${index}`} className="mt-3 pt-3 border-t border-border">
                    <p className="text-sm text-muted-foreground">{caseData.summary}</p>
                    {caseData.source_url && (
                        <a
                            href={caseData.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-2 text-xs text-primary hover:underline flex items-center gap-1"
                        >
                            상세보기 <ExternalLink className="h-3 w-3" />
                        </a>
                    )}
                </div>
            )}
        </div>
    )
}

interface RegulationItemProps {
    regulation: Regulation
    index: number
}

function RegulationItem({ regulation, index }: RegulationItemProps) {
    const [isExpanded, setIsExpanded] = useState(false)

    const handleToggle = () => setIsExpanded(!isExpanded)
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault()
            handleToggle()
        }
    }

    return (
        <div className="border border-border rounded-lg p-3 hover:bg-muted/50 transition-colors">
            <button
                type="button"
                className="w-full flex items-start justify-between gap-2 cursor-pointer text-left"
                onClick={handleToggle}
                onKeyDown={handleKeyDown}
                aria-expanded={isExpanded}
                aria-controls={`reg-content-${index}`}
            >
                <div className="flex-1 min-w-0">
                    <h4 className="font-medium text-sm">{regulation.title}</h4>
                </div>
                <div className="flex items-center">
                    {isExpanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
                </div>
            </button>
            {isExpanded && (
                <div id={`reg-content-${index}`} className="mt-3 pt-3 border-t border-border">
                    <p className="text-sm text-muted-foreground">{regulation.summary}</p>
                    {regulation.source_url && (
                        <a
                            href={regulation.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-2 text-xs text-primary hover:underline flex items-center gap-1"
                        >
                            원문보기 <ExternalLink className="h-3 w-3" />
                        </a>
                    )}
                </div>
            )}
        </div>
    )
}

interface ReferencePanelProps {
    isOpen: boolean
    onToggle: () => void
    approvalCases?: ApprovalCase[]
    regulations?: Regulation[]
    cases?: CaseData[] // track 페이지 호환용
    track?: string // 트랙 정보 (신속확인 메시지용)
}

export function ReferencePanel({ isOpen, onToggle, approvalCases, regulations, cases, track }: ReferencePanelProps) {
    // cases (CaseData[])를 ApprovalCase[]로 변환
    const convertedCases: ApprovalCase[] | undefined = cases?.map((c) => ({
        track: c.track,
        date: c.approvedDate || "",
        similarity: c.relevance,
        title: c.title,
        company: c.company,
        summary: c.summary,
        source_url: c.link || null,
    }))

    // 실제 데이터만 사용 (더미 데이터 없음)
    const displayCases = approvalCases ?? convertedCases ?? []
    const regs = regulations ?? []

    // 닫힌 상태: 토글 버튼만 표시
    if (!isOpen) {
        return (
            <Button
                variant="ghost"
                size="icon"
                onClick={onToggle}
                className="h-8 w-8 bg-background shadow-sm border border-border text-teal-600 hover:text-teal-700 hover:bg-teal-50"
                aria-label="참고자료 패널 열기"
            >
                <PanelLeft className="h-4 w-4" />
            </Button>
        )
    }

    // 법령/제도 탭을 기본으로
    const defaultTab = "regulations"

    return (
        <div className="space-y-4 min-w-0">
            <Tabs defaultValue={defaultTab} className="w-full">
                <div className="flex items-center gap-3">
                    <TabsList className="h-8 flex-1 grid grid-cols-2 py-0 px-0.5 bg-gray-100">
                        <TabsTrigger
                            value="regulations"
                            className="h-7 gap-1.5 text-xs px-2 data-[state=active]:bg-white data-[state=active]:text-black"
                        >
                            <Scale className="h-3.5 w-3.5" />
                            법령·제도
                        </TabsTrigger>
                        <TabsTrigger value="cases" className="h-7 gap-1.5 text-xs px-2 data-[state=active]:bg-white data-[state=active]:text-black">
                            <BookOpen className="h-3.5 w-3.5" />
                            승인사례
                        </TabsTrigger>
                    </TabsList>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={onToggle}
                        className="h-8 w-8 text-teal-600 hover:text-teal-700 hover:bg-teal-50"
                        aria-label="참고자료 패널 닫기"
                    >
                        <PanelRight className="h-4 w-4" />
                    </Button>
                </div>

                <TabsContent value="regulations" className="mt-3 max-h-[calc(100vh-200px)] overflow-y-auto space-y-3">
                    {regs.length > 0 ? (
                        regs.map((regulation, index) => (
                            <RegulationItem key={`${regulation.title}-${index}`} regulation={regulation} index={index} />
                        ))
                    ) : (
                        <div className="text-center py-8 text-muted-foreground text-sm">참고할 관련 법령이 없습니다.</div>
                    )}
                </TabsContent>

                <TabsContent value="cases" className="mt-3 max-h-[calc(100vh-200px)] overflow-y-auto space-y-3">
                    {displayCases.length > 0 ? (
                        displayCases.map((caseData, index) => (
                            <CaseItem key={`${caseData.title}-${caseData.company}-${index}`} caseData={caseData} index={index} />
                        ))
                    ) : track === "quick_check" ? (
                        <div className="text-center py-8 text-muted-foreground text-sm">
                            신속확인은 트랙 판단을 위한 절차로,
                            <br />
                            참고할 유사 승인사례가 없습니다.
                        </div>
                    ) : (
                        <div className="text-center py-8 text-muted-foreground text-sm">참고할 유사 승인사례가 없습니다.</div>
                    )}
                </TabsContent>
            </Tabs>
        </div>
    )
}
