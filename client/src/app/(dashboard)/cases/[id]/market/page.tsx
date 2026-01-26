"use client"

import { use, useState } from "react"
import { useRouter } from "next/navigation"
import { notFound } from "next/navigation"
import { ArrowLeft, ArrowRight, CheckCircle2, AlertTriangle, Scale } from "lucide-react"
import { Button } from "@/components/ui/button"
import { AILoadingOverlay } from "@/components/ui/ai-loading-overlay"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { AIAnalysisCard } from "@/components/features/analysis/AIAnalysisCard"
import { cases } from "@/data"
import { useWizardStore } from "@/stores/wizard-store"
import { useCaseStore } from "@/stores/case-store"
import { cn } from "@/lib/utils/cn"

type ReasonCategory = "law" | "regulation" | "case"

interface AnalysisReason {
    category: ReasonCategory
    title: string
    description: string
    source: string
}

const CATEGORY_CONFIG: Record<ReasonCategory, { label: string; badgeClass: string }> = {
    law: {
        label: "법령 기준",
        badgeClass: "bg-purple-100 text-purple-700 border-purple-300",
    },
    regulation: {
        label: "규제 기준",
        badgeClass: "bg-blue-100 text-blue-700 border-blue-300",
    },
    case: {
        label: "사례 기준",
        badgeClass: "bg-green-100 text-green-700 border-green-300",
    },
}

interface MarketPageProps {
    params: Promise<{ id: string }>
}

// 더미 AI 분석 결과 데이터 (RAG 1,2,3 툴 활용 시뮬레이션)
interface AIAnalysisData {
    recommendation: "direct" | "sandbox"
    confidence: number
    summary: string
    reasons: AnalysisReason[]
    directLaunchRisks: string[]
}

// 규제 샌드박스 필요 케이스용 더미 데이터
const sandboxAnalysis: AIAnalysisData = {
    recommendation: "sandbox",
    confidence: 87,
    summary: "본 서비스는 현행 규제 체계에서 즉시 시장 출시가 어려우며, 규제 샌드박스를 통한 실증이 필요합니다.",
    reasons: [
        {
            category: "law",
            title: "규제 저촉 사항 발견",
            description: "자율주행 배달로봇의 보도 운행은 현행법상 명확한 법적 근거가 부재하며, 도로 운행 시 운전자 탑승 의무 조항에 저촉됩니다.",
            source: "「여객자동차 운수사업법」 제3조 제1항, 「도로교통법」 제2조 제26호",
        },
        {
            category: "case",
            title: "유사 승인 사례 존재",
            description: "동일 서비스 유형의 실증특례 승인 선례가 있어 승인 가능성이 높으나, 안전성 검증 자료 보강이 필요합니다.",
            source: "실증특례 제2023-ICT융합-0147호 '뉴빌리티 자율주행 배달로봇 서비스'",
        },
        {
            category: "regulation",
            title: "신속확인 대상 아님",
            description:
                "해당 서비스는 규제 적용 여부가 명확하므로 신속확인 트랙 요건에 해당하지 않습니다. 실증특례 또는 임시허가 트랙이 적합합니다.",
            source: "「정보통신융합법」 제36조 (신속확인), 「규제 샌드박스 운영지침」 제4조",
        },
    ],
    directLaunchRisks: [
        "「도로교통법」 제156조에 따른 무허가 운행 과태료 (최대 300만원)",
        "「제조물책임법」 제3조에 따른 사고 발생 시 손해배상 책임",
        "자율주행 로봇 관련 보험 상품 부재로 인한 리스크 전가 불가",
    ],
}

// 바로 출시 가능 케이스용 더미 데이터
const directAnalysis: AIAnalysisData = {
    recommendation: "direct",
    confidence: 94,
    summary: "본 서비스는 현행 규제 체계 내에서 별도의 규제 특례 없이 즉시 시장 출시가 가능합니다.",
    reasons: [
        {
            category: "law",
            title: "규제 저촉 사항 없음",
            description: "대형 시설 내 자율주행 청소 로봇은 「도로교통법」 적용 대상이 아니며, 사유지 내 운행으로 별도 허가가 불필요합니다.",
            source: "「도로교통법」 제2조 (정의), 「산업안전보건법」 제93조 (안전인증 대상)",
        },
        {
            category: "regulation",
            title: "기존 인허가 체계 적용 가능",
            description: "전기용품 안전인증(KC) 및 전자파 적합성 인증만 취득하면 현행법 내에서 서비스 제공이 가능합니다.",
            source: "「전기용품 및 생활용품 안전관리법」 제5조, 「전파법」 제58조의2",
        },
        {
            category: "case",
            title: "유사 서비스 정상 운영 중",
            description: "LG전자, 네이버랩스 등 다수 기업이 동일 유형의 서비스를 규제 특례 없이 상업 운영 중입니다.",
            source: "LG CLOi 로봇 시리즈 상용화 사례, 네이버랩스 루키(Rookie) 서비스 운영 사례",
        },
    ],
    directLaunchRisks: [],
}

// 케이스 상태에 따라 적절한 더미 데이터 선택
const getAnalysisData = (caseStatus?: string): AIAnalysisData => {
    if (caseStatus === "direct") {
        return directAnalysis
    }
    return sandboxAnalysis
}

type DecisionType = "direct" | "sandbox"

export default function MarketPage({ params }: MarketPageProps) {
    const { id } = use(params)
    const router = useRouter()
    const caseData = cases.find((c) => c.id === id)

    const { marketAnalysis, setMarketAnalysis, markStepComplete, setCurrentStep } = useWizardStore()

    const { updateCaseStatus, getCaseStatus } = useCaseStore()

    // 오버라이드된 상태가 있으면 사용, 없으면 원본 상태 사용 (single source of truth)
    const currentStatus = getCaseStatus(id, (caseData?.status as "consult" | "draft" | "waiting" | "done" | "direct") ?? "consult")

    // 케이스 상태에 따른 AI 분석 데이터 선택 (오버라이드된 상태 반영)
    const analysisData = getAnalysisData(currentStatus)

    const [selectedDecision, setSelectedDecision] = useState<DecisionType>(analysisData.recommendation)
    const [prevId, setPrevId] = useState(id)
    const [isSaving, setIsSaving] = useState(false)

    // 케이스가 변경되면 AI 추천값으로 초기화 (렌더링 중 조건부 업데이트)
    if (id !== prevId) {
        setPrevId(id)
        setSelectedDecision(analysisData.recommendation)
    }

    if (!caseData) {
        notFound()
    }

    const handleBack = () => {
        setCurrentStep(1)
        router.push(`/cases/${id}/service`)
    }

    const handleSave = async () => {
        setIsSaving(true)

        // AI 분석 시뮬레이션
        await new Promise((resolve) => setTimeout(resolve, 2000))

        setMarketAnalysis({
            decision: selectedDecision,
            aiRecommendation: analysisData.recommendation,
        })

        if (selectedDecision === "direct") {
            // 바로출시 선택 시 - 케이스 상태를 'direct'로 변경하고 대시보드로 이동
            updateCaseStatus(id, "direct")
            markStepComplete(2)
            router.push("/dashboard")
        } else {
            // 규제 샌드박스 선택 시 - 트랙 선택 페이지로 이동
            markStepComplete(2)
            setCurrentStep(3)
            router.push(`/cases/${id}/track`)
        }
        // 페이지 전환 후 컴포넌트가 언마운트되면서 로딩이 자연스럽게 사라짐
    }

    return (
        <div className="py-6">
            {isSaving && <AILoadingOverlay message={selectedDecision === "direct" ? "저장 중" : "AI 분석 중"} />}
            <div className="container mx-auto px-4 space-y-6">
                <div>
                    <h1 className="text-2xl font-bold mb-2">시장출시 진단</h1>
                    <p className="text-muted-foreground">AI가 서비스의 규제 현황을 분석하여 시장 출시 가능 여부를 판단합니다</p>
                </div>

                {/* AI 분석 요약 */}
                <AIAnalysisCard
                    summary={analysisData.summary}
                    confidence={analysisData.confidence}
                    recommendation={analysisData.recommendation === "sandbox" ? "규제 샌드박스 필요" : "바로 시장 출시 가능"}
                />

                {/* 판단 근거 */}
                <Card>
                    <CardHeader>
                        <CardTitle>판단 근거</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="divide-y divide-border">
                            {analysisData.reasons.map((reason: AnalysisReason, index) => {
                                const config = CATEGORY_CONFIG[reason.category]
                                return (
                                    <div
                                        key={index}
                                        className={cn(
                                            "flex items-start gap-3 py-4",
                                            index === 0 && "pt-0",
                                            index === analysisData.reasons.length - 1 && "pb-0"
                                        )}
                                    >
                                        <Badge variant="outline" className={cn("shrink-0 mt-0.5 text-xs font-medium", config.badgeClass)}>
                                            {config.label}
                                        </Badge>
                                        <div className="flex-1">
                                            <h4 className="font-medium">{reason.title}</h4>
                                            <p className="text-sm text-foreground mt-1">{reason.description}</p>
                                            <p className="text-sm text-foreground/70 mt-2">근거: {reason.source}</p>
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    </CardContent>
                </Card>

                {/* 바로 출시 시 리스크 */}
                {analysisData.recommendation === "sandbox" && (
                    <Card className="border-amber-200">
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <AlertTriangle className="h-5 w-5 text-amber-500" />
                                <CardTitle className="text-amber-700">바로 출시 시 예상 리스크</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <ul className="space-y-2">
                                {analysisData.directLaunchRisks.map((risk, index) => (
                                    <li key={index} className="flex items-start gap-2 text-sm">
                                        <span className="h-1.5 w-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                                        {risk}
                                    </li>
                                ))}
                            </ul>
                        </CardContent>
                    </Card>
                )}

                {/* 컨설턴트 최종 결정 */}
                <Card>
                    <CardHeader>
                        <CardTitle>최종 결정</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <button
                                type="button"
                                onClick={() => setSelectedDecision("direct")}
                                className={cn(
                                    "p-4 rounded-lg border-2 text-left transition-all",
                                    selectedDecision === "direct" ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
                                )}
                            >
                                <div className="flex items-center gap-3">
                                    <CheckCircle2
                                        className={cn("h-6 w-6", selectedDecision === "direct" ? "text-primary" : "text-muted-foreground")}
                                    />
                                    <div>
                                        <h4 className="font-medium">바로 시장 출시</h4>
                                        <p className="text-sm text-muted-foreground">현행 규제 내에서 서비스 출시가 가능합니다</p>
                                    </div>
                                </div>
                            </button>

                            <button
                                type="button"
                                onClick={() => setSelectedDecision("sandbox")}
                                className={cn(
                                    "p-4 rounded-lg border-2 text-left transition-all",
                                    selectedDecision === "sandbox" ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
                                )}
                            >
                                <div className="flex items-center gap-3">
                                    <Scale className={cn("h-6 w-6", selectedDecision === "sandbox" ? "text-primary" : "text-muted-foreground")} />
                                    <div>
                                        <h4 className="font-medium">규제 샌드박스 신청</h4>
                                        <p className="text-sm text-muted-foreground">규제 특례를 통한 실증이 필요합니다</p>
                                    </div>
                                </div>
                            </button>
                        </div>

                        {selectedDecision !== analysisData.recommendation && (
                            //   <div className="p-3 rounded-lg border border-amber-200 text-sm">
                            <div className="text-sm flex gap-2 items-center px-2">
                                <AlertTriangle className="h-4 w-4 text-amber-500" />
                                <span className="text-amber-700">AI 추천과 다른 선택입니다. 선택에 대한 근거를 확인해주세요.</span>
                            </div>
                        )}
                    </CardContent>
                </Card>

                <div className="flex justify-between">
                    <Button variant="outline" onClick={handleBack} className="gap-2">
                        <ArrowLeft className="h-4 w-4" />
                        이전 단계
                    </Button>
                    <Button onClick={handleSave} disabled={isSaving} className="gap-2">
                        저장 및 다음 단계
                        <ArrowRight className="h-4 w-4" />
                    </Button>
                </div>
            </div>
        </div>
    )
}
