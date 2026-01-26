"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { notFound } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Info,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { AILoadingOverlay } from "@/components/ui/ai-loading-overlay";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AIAnalysisCard } from "@/components/features/analysis/AIAnalysisCard";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cases, tracks } from "@/data";
import { useWizardStore } from "@/stores/wizard-store";
import { cn } from "@/lib/utils/cn";
import type { Track, TrackType } from "@/types/data/track";

interface TrackPageProps {
  params: Promise<{ id: string }>;
}

// 더미 AI 트랙 추천 데이터 (RAG 1,2,3 툴 활용 시뮬레이션)
const dummyTrackAnalysis = {
  confidence: 89,
  summary:
    "서비스 특성과 규제 현황을 분석한 결과, 실증특례 트랙이 가장 적합합니다. 시장성 검증을 위한 테스트가 필요하고 규제 면제가 필요한 상황에 적합합니다.",
  recommendations: [
    {
      trackId: "track-demonstration",
      rank: 1,
      score: 92,
      verdict: "AI 추천" as const,
      reasons: [
        {
          type: "positive" as const,
          text: "자율주행 배달로봇은 실제 환경에서의 시장성 검증이 필수적이며, 실증특례를 통해 제한된 구역에서 테스트가 가능합니다.",
          source:
            "「정보통신융합법」 제38조의2 (실증특례), 「규제 샌드박스 운영지침」 제5조",
        },
        {
          type: "positive" as const,
          text: "뉴빌리티, 배달의민족 등 유사 사례가 실증특례로 승인받은 선례가 있어 승인 가능성이 높습니다.",
          source:
            "실증특례 제2023-ICT융합-0147호 '뉴빌리티 자율주행 배달로봇 서비스'",
        },
        {
          type: "neutral" as const,
          text: "실증 기간 내 안전성 데이터 확보가 필요하며, 이후 임시허가 또는 정식 규제 개선으로 연결 가능합니다.",
          source: "「정보통신융합법」 제38조의2 제4항 (실증특례 기간)",
        },
      ],
    },
    {
      trackId: "track-temporary",
      rank: 2,
      score: 68,
      verdict: "조건부 가능" as const,
      reasons: [
        {
          type: "positive" as const,
          text: "전국 단위 서비스가 가능하며, 정식 허가와 동일한 효력을 가집니다.",
          source:
            "「정보통신융합법」 제37조 (임시허가), 「규제 샌드박스 운영지침」 제6조",
        },
        {
          type: "negative" as const,
          text: "현재 단계에서는 충분한 안전성 검증 데이터가 부족합니다. 실증특례 이후 신청이 적합합니다.",
          source: "임시허가 제2022-ICT융합-0089호 심사 반려 사례",
        },
        {
          type: "neutral" as const,
          text: "기존 임시허가 사례는 대부분 실증특례를 거친 후 신청한 경우입니다.",
          source: "임시허가 제2023-ICT융합-0201호 '자율주행 셔틀버스 서비스'",
        },
      ],
    },
    {
      trackId: "track-fastcheck",
      rank: 3,
      score: 25,
      verdict: "비추천" as const,
      reasons: [
        {
          type: "negative" as const,
          text: "본 서비스는 규제 적용 여부가 명확합니다. 「여객자동차 운수사업법」에 저촉되므로 신속확인 대상이 아닙니다.",
          source:
            "「여객자동차 운수사업법」 제3조 제1항, 「도로교통법」 제2조 제26호",
        },
        {
          type: "negative" as const,
          text: "신속확인은 규제 적용 여부가 불분명한 경우에만 해당됩니다.",
          source:
            "「정보통신융합법」 제36조 (신속확인), 「규제 샌드박스 운영지침」 제4조",
        },
      ],
    },
  ],
};

const trackColors: Record<TrackType, string> = {
  demonstration: "from-blue-500 to-blue-600",
  temporary: "from-teal-500 to-teal-600",
  fastcheck: "from-slate-400 to-slate-500",
};

const verdictStyles: Record<
  string,
  { bg: string; text: string; border: string }
> = {
  "AI 추천": {
    bg: "bg-blue-50",
    text: "text-blue-700",
    border: "border-blue-200",
  },
  "조건부 가능": {
    bg: "bg-amber-50",
    text: "text-amber-700",
    border: "border-amber-200",
  },
  비추천: { bg: "bg-red-50", text: "text-red-700", border: "border-red-200" },
};

export default function TrackPage({ params }: TrackPageProps) {
  const { id } = use(params);
  const router = useRouter();
  const caseData = cases.find((c) => c.id === id);

  const {
    trackSelection,
    setTrackSelection,
    markStepComplete,
    setCurrentStep,
  } = useWizardStore();

  // 가장 적합한 트랙(rank 1)을 기본 선택으로
  const defaultTrackId =
    dummyTrackAnalysis.recommendations.find((r) => r.rank === 1)?.trackId ||
    null;

  const [selectedTrackId, setSelectedTrackId] = useState<string | null>(
    defaultTrackId
  );
  const [prevId, setPrevId] = useState(id);
  const [isSaving, setIsSaving] = useState(false);

  // 케이스가 변경되면 AI 추천 트랙으로 초기화 (렌더링 중 조건부 업데이트)
  if (id !== prevId) {
    setPrevId(id);
    setSelectedTrackId(defaultTrackId);
  }

  if (!caseData) {
    notFound();
  }

  const handleSelectTrack = (trackId: string) => {
    setSelectedTrackId(trackId);
    const track = tracks.find((t) => t.id === trackId);
    if (track) {
      setTrackSelection(track);
    }
  };

  const handleBack = () => {
    setCurrentStep(2);
    router.push(`/cases/${id}/market`);
  };

  const handleSave = async () => {
    if (!selectedTrackId) return;

    setIsSaving(true);

    // AI 분석 시뮬레이션
    await new Promise((resolve) => setTimeout(resolve, 2000));

    const track = tracks.find((t) => t.id === selectedTrackId);
    if (track) {
      setTrackSelection(track);
    }

    markStepComplete(3);
    setCurrentStep(4);
    router.push(`/cases/${id}/draft`);
    // 페이지 전환 후 컴포넌트가 언마운트되면서 로딩이 자연스럽게 사라짐
  };

  // 추천 순서대로 정렬
  const sortedRecommendations = [...dummyTrackAnalysis.recommendations].sort(
    (a, b) => a.rank - b.rank
  );

  const getReasonIcon = (type: string) => {
    switch (type) {
      case "positive":
        return (
          <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0 mt-0.5" />
        );
      case "negative":
        return <XCircle className="h-4 w-4 text-red-500 shrink-0 mt-0.5" />;
      case "neutral":
        return (
          <AlertCircle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
        );
      default:
        return null;
    }
  };

  return (
    <TooltipProvider>
      <div className="py-6">
        {isSaving && <AILoadingOverlay />}
        <div className="container mx-auto px-4 space-y-6">
          <div>
            <h1 className="text-2xl font-bold mb-2">트랙 선택</h1>
            <p className="text-muted-foreground">
              AI가 분석한 결과를 바탕으로 최적의 규제 샌드박스 트랙을 선택하세요
            </p>
          </div>

          {/* AI 분석 요약 */}
          <AIAnalysisCard
            summary={dummyTrackAnalysis.summary}
            confidence={dummyTrackAnalysis.confidence}
          />

          {/* 트랙 카드들 */}
          <div className="space-y-4">
            {sortedRecommendations.map((rec) => {
              const track = tracks.find((t) => t.id === rec.trackId);
              if (!track) return null;

              const isSelected = selectedTrackId === track.id;
              const isRecommended = rec.rank === 1;
              const style = verdictStyles[rec.verdict];

              return (
                <Card
                  key={track.id}
                  className={cn(
                    "relative overflow-hidden transition-all cursor-pointer",
                    isSelected && "ring-2 ring-primary"
                  )}
                  onClick={() => handleSelectTrack(track.id)}
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div
                          className={cn(
                            "flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold",
                            isSelected
                              ? "bg-primary text-white"
                              : "bg-muted text-muted-foreground"
                          )}
                        >
                          {rec.rank}
                        </div>
                        <div className="flex items-center gap-1.5">
                          <h3 className="text-lg font-semibold">
                            {track.name}
                          </h3>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <button
                                type="button"
                                className="text-muted-foreground hover:text-foreground transition-colors"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <Info className="h-4 w-4" />
                              </button>
                            </TooltipTrigger>
                            <TooltipContent
                              side="right"
                              sideOffset={8}
                              className="max-w-sm text-left"
                            >
                              <div className="space-y-2">
                                <p>{track.description}</p>
                                <p className="text-muted-foreground">
                                  <span className="font-medium text-foreground">
                                    소요 기간:
                                  </span>{" "}
                                  {track.duration}
                                </p>
                                <div>
                                  <span className="font-medium">
                                    주요 요건:
                                  </span>
                                  <ul className="mt-1 space-y-0.5 text-muted-foreground">
                                    {track.requirements
                                      .slice(0, 4)
                                      .map((req, i) => (
                                        <li key={i}>• {req}</li>
                                      ))}
                                  </ul>
                                </div>
                              </div>
                            </TooltipContent>
                          </Tooltip>
                        </div>
                      </div>
                      <Badge
                        variant="outline"
                        className={cn(style.bg, style.text, style.border)}
                      >
                        {rec.verdict}
                      </Badge>
                    </div>
                  </CardHeader>

                  <div className="mx-6 border-t border-gray-200" />

                  <CardContent className="space-y-4 mt-3">
                    {/* AI 분석 결과 */}
                    <div className="space-y-2">
                      {/* <h4 className="text-sm font-medium">분석 결과</h4> */}
                      <ul className="space-y-2">
                        {rec.reasons.map((reason, index) => (
                          <li
                            key={index}
                            className="flex items-start gap-2 text-sm"
                          >
                            {getReasonIcon(reason.type)}
                            <div className="flex-1">
                              <p className="text-foreground">{reason.text}</p>
                              <p className="text-muted-foreground/70 mt-1">
                                근거: {reason.source}
                              </p>
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          <div className="flex justify-between">
            <Button variant="outline" onClick={handleBack} className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              이전 단계
            </Button>
            <Button
              onClick={handleSave}
              disabled={!selectedTrackId || isSaving}
              className="gap-2"
            >
              저장 및 다음 단계
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}
