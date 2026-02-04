"use client"

import { useState } from "react"
import { BookOpen, Scale, ChevronDown, ChevronUp, ExternalLink, PanelLeft, PanelRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { cn } from "@/lib/utils/cn"
import type { ApprovalCase, Regulation } from "@/types/api/eligibility"
import { formatDateIso } from "@/lib/utils/date"

// 더미 승인사례 데이터 (props 없을 때 사용)
const dummyApprovedCases: ApprovalCase[] = [
    {
        track: "실증특례",
        date: "2023-06-15",
        similarity: 92,
        title: "자율주행 배달로봇 실증특례",
        company: "뉴빌리티",
        summary: "보도 위 자율주행 배달로봇 운행을 위한 도로교통법 특례 승인",
        source_url: null,
    },
    {
        track: "임시허가",
        date: "2023-04-20",
        similarity: 85,
        title: "드론 배송 서비스 임시허가",
        company: "마켓컬리",
        summary: "도심 내 드론을 활용한 신선식품 배송 서비스 임시허가",
        source_url: null,
    },
    {
        track: "실증특례",
        date: "2022-11-10",
        similarity: 78,
        title: "전동킥보드 공유서비스 실증특례",
        company: "킥고잉",
        summary: "전동킥보드 공유 서비스의 도로교통법 특례 승인",
        source_url: null,
    },
]

// 더미 법령/제도 데이터 (props 없을 때 사용)
const dummyRegulations: Regulation[] = [
    {
        category: "실증특례",
        title: "정보통신융합법 제36조",
        summary: "신규 정보통신융합등 기술·서비스의 실증을 위한 규제특례",
        source_url: null,
    },
    {
        category: "임시허가",
        title: "정보통신융합법 제37조",
        summary: "신규 정보통신융합등 기술·서비스에 대한 임시허가",
        source_url: null,
    },
    {
        category: "절차",
        title: "규제샌드박스 운영지침",
        summary: "규제샌드박스 신청 절차 및 심사 기준 안내",
        source_url: null,
    },
    {
        category: "참고",
        title: "ICT 규제샌드박스 FAQ",
        summary: "자주 묻는 질문과 답변 모음",
        source_url: null,
    },
]

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
                        <span className="text-xs text-muted-foreground">{formatDateIso(caseData.date)}</span>
                    </div>
                    <h4 className="font-medium text-sm truncate">{caseData.title}</h4>
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
                        <a href={caseData.source_url} target="_blank" rel="noopener noreferrer" className="mt-2 text-xs text-primary hover:underline flex items-center gap-1">
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
                        <a href={regulation.source_url} target="_blank" rel="noopener noreferrer" className="mt-2 text-xs text-primary hover:underline flex items-center gap-1">
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
}

export function ReferencePanel({ isOpen, onToggle, approvalCases, regulations }: ReferencePanelProps) {
    // props가 없으면 더미 데이터 사용
    const cases = approvalCases ?? dummyApprovedCases
    const regs = regulations ?? dummyRegulations

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

    return (
        <div className="space-y-4">
            <Tabs defaultValue="cases" className="w-full">
                <div className="flex items-center gap-3">
                    <TabsList className="h-8 flex-1 grid grid-cols-2 py-0 px-0.5 bg-gray-100">
                        <TabsTrigger value="cases" className="h-7 gap-1.5 text-xs px-2 data-[state=active]:bg-white data-[state=active]:text-black">
                            <BookOpen className="h-3.5 w-3.5" />
                            승인사례
                        </TabsTrigger>
                        <TabsTrigger
                            value="regulations"
                            className="h-7 gap-1.5 text-xs px-2 data-[state=active]:bg-white data-[state=active]:text-black"
                        >
                            <Scale className="h-3.5 w-3.5" />
                            법령·제도
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

                <TabsContent value="cases" className="mt-3 max-h-[calc(100vh-200px)] overflow-y-auto space-y-3">
                    {cases.map((caseData, index) => (
                        <CaseItem key={index} caseData={caseData} index={index} />
                    ))}
                </TabsContent>

                <TabsContent value="regulations" className="mt-3 max-h-[calc(100vh-200px)] overflow-y-auto space-y-3">
                    {regs.map((regulation, index) => (
                        <RegulationItem key={index} regulation={regulation} index={index} />
                    ))}
                </TabsContent>
            </Tabs>
        </div>
    )
}
