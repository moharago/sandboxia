"use client"

import { useState } from "react"
import { BookOpen, Scale, ChevronDown, ChevronUp, ExternalLink, PanelLeft, PanelRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { cn } from "@/lib/utils/cn"

// 임시 승인사례 데이터
const approvedCases = [
    {
        id: 1,
        title: "자율주행 배달로봇 실증특례",
        company: "뉴빌리티",
        approvedDate: "2023-06-15",
        track: "실증특례",
        summary: "보도 위 자율주행 배달로봇 운행을 위한 도로교통법 특례 승인",
        relevance: 92,
    },
    {
        id: 2,
        title: "드론 배송 서비스 임시허가",
        company: "마켓컬리",
        approvedDate: "2023-04-20",
        track: "임시허가",
        summary: "도심 내 드론을 활용한 신선식품 배송 서비스 임시허가",
        relevance: 85,
    },
    {
        id: 3,
        title: "전동킥보드 공유서비스 실증특례",
        company: "킥고잉",
        approvedDate: "2022-11-10",
        track: "실증특례",
        summary: "전동킥보드 공유 서비스의 도로교통법 특례 승인",
        relevance: 78,
    },
]

// 임시 법령/제도 데이터
const regulations = [
    {
        id: 1,
        title: "정보통신융합법 제36조",
        category: "실증특례",
        summary: "신규 정보통신융합등 기술·서비스의 실증을 위한 규제특례",
        link: "#",
    },
    {
        id: 2,
        title: "정보통신융합법 제37조",
        category: "임시허가",
        summary: "신규 정보통신융합등 기술·서비스에 대한 임시허가",
        link: "#",
    },
    {
        id: 3,
        title: "규제샌드박스 운영지침",
        category: "절차",
        summary: "규제샌드박스 신청 절차 및 심사 기준 안내",
        link: "#",
    },
    {
        id: 4,
        title: "ICT 규제샌드박스 FAQ",
        category: "참고",
        summary: "자주 묻는 질문과 답변 모음",
        link: "#",
    },
]

interface CaseItemProps {
    caseData: (typeof approvedCases)[0]
}

function CaseItem({ caseData }: CaseItemProps) {
    const [isExpanded, setIsExpanded] = useState(false)

    return (
        <div className="border border-border rounded-lg p-3 hover:bg-muted/50 transition-colors">
            <div className="flex items-start justify-between gap-2 cursor-pointer" onClick={() => setIsExpanded(!isExpanded)}>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                        <Badge variant="outline" className="text-xs shrink-0">
                            {caseData.track}
                        </Badge>
                        <span className="text-xs text-muted-foreground">{caseData.approvedDate}</span>
                    </div>
                    <h4 className="font-medium text-sm truncate">{caseData.title}</h4>
                    <p className="text-xs text-muted-foreground">{caseData.company}</p>
                </div>
                <div className="flex flex-col items-end gap-1">
                    <Badge variant="success" className="text-xs">
                        {caseData.relevance}% 유사
                    </Badge>
                    {isExpanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
                </div>
            </div>
            {isExpanded && (
                <div className="mt-3 pt-3 border-t border-border">
                    <p className="text-sm text-muted-foreground">{caseData.summary}</p>
                    <button type="button" className="mt-2 text-xs text-primary hover:underline flex items-center gap-1">
                        상세보기 <ExternalLink className="h-3 w-3" />
                    </button>
                </div>
            )}
        </div>
    )
}

interface RegulationItemProps {
    regulation: (typeof regulations)[0]
}

function RegulationItem({ regulation }: RegulationItemProps) {
    return (
        <div className="border border-border rounded-lg p-3 hover:bg-muted/50 transition-colors">
            <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                        <Badge variant="secondary" className="text-xs">
                            {regulation.category}
                        </Badge>
                    </div>
                    <h4 className="font-medium text-sm">{regulation.title}</h4>
                    <p className="text-xs text-muted-foreground mt-1">{regulation.summary}</p>
                </div>
            </div>
            <a href={regulation.link} className="mt-2 text-xs text-primary hover:underline flex items-center gap-1">
                원문보기 <ExternalLink className="h-3 w-3" />
            </a>
        </div>
    )
}

interface ReferencePanelProps {
    isOpen: boolean
    onToggle: () => void
}

export function ReferencePanel({ isOpen, onToggle }: ReferencePanelProps) {
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
                    {approvedCases.map((caseData) => (
                        <CaseItem key={caseData.id} caseData={caseData} />
                    ))}
                </TabsContent>

                <TabsContent value="regulations" className="mt-3 max-h-[calc(100vh-200px)] overflow-y-auto space-y-3">
                    {regulations.map((regulation) => (
                        <RegulationItem key={regulation.id} regulation={regulation} />
                    ))}
                </TabsContent>
            </Tabs>
        </div>
    )
}
