"use client";

import { use, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { notFound } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Sparkles,
  Check,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { AILoadingOverlay } from "@/components/ui/ai-loading-overlay";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cases, tracks } from "@/data";
import { useWizardStore } from "@/stores";
import { cn } from "@/lib/utils/cn";
import type { Track, TrackType } from "@/types/data";

interface TrackPageProps {
  params: Promise<{ id: string }>;
}

// 더미 AI 트랙 추천 데이터 (RAG 1,2,3 툴 활용 시뮬레이션)
const dummyTrackAnalysis = {
  summary:
    "서비스 특성과 규제 현황을 분석한 결과, 실증특례 트랙이 가장 적합합니다. 시장성 검증을 위한 테스트가 필요하고 규제 면제가 필요한 상황에 적합합니다.",
  recommendations: [
    {
      trackId: "track-demonstration",
      rank: 1,
      score: 92,
      verdict: "추천" as const,
      reasons: [
        {
          type: "positive" as const,
          text: "자율주행 배달로봇은 실제 환경에서의 시장성 검증이 필수적이며, 실증특례를 통해 제한된 구역에서 테스트가 가능합니다.",
          source: "R1. 규제제도 & 절차 RAG",
        },
        {
          type: "positive" as const,
          text: "뉴빌리티, 배달의민족 등 유사 사례가 실증특례로 승인받은 선례가 있어 승인 가능성이 높습니다.",
          source: "R2. 승인 사례 RAG",
        },
        {
          type: "neutral" as const,
          text: "실증 기간 내 안전성 데이터 확보가 필요하며, 이후 임시허가 또는 정식 규제 개선으로 연결 가능합니다.",
          source: "R1. 규제제도 & 절차 RAG",
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
          source: "R1. 규제제도 & 절차 RAG",
        },
        {
          type: "negative" as const,
          text: "현재 단계에서는 충분한 안전성 검증 데이터가 부족합니다. 실증특례 이후 신청이 적합합니다.",
          source: "R2. 승인 사례 RAG",
        },
        {
          type: "neutral" as const,
          text: "기존 임시허가 사례는 대부분 실증특례를 거친 후 신청한 경우입니다.",
          source: "R2. 승인 사례 RAG",
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
          source: "R3. 도메인별 규제·법령 RAG",
        },
        {
          type: "negative" as const,
          text: "신속확인은 규제 적용 여부가 불분명한 경우에만 해당됩니다.",
          source: "R1. 규제제도 & 절차 RAG",
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
  추천: {
    bg: "bg-green-50",
    text: "text-green-700",
    border: "border-green-200",
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
    trackSelection?.id ||
    dummyTrackAnalysis.recommendations.find((r) => r.rank === 1)?.trackId ||
    null;

  const [selectedTrackId, setSelectedTrackId] = useState<string | null>(
    defaultTrackId
  );
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (trackSelection) {
      setSelectedTrackId(trackSelection.id);
    }
  }, [trackSelection]);

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
        <Card className="border-primary/30 bg-gradient-to-r from-blue-50/50 to-teal-50/50">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              <CardTitle>AI 분석 결과</CardTitle>
            </div>
            <CardDescription className="text-base mt-2">
              {dummyTrackAnalysis.summary}
            </CardDescription>
          </CardHeader>
        </Card>

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
                  isSelected && "ring-2 ring-primary",
                  isRecommended && "border-primary"
                )}
                onClick={() => handleSelectTrack(track.id)}
              >
                {/* 상단 컬러 바 */}
                <div
                  className={cn(
                    "h-1.5 bg-gradient-to-r",
                    trackColors[track.type]
                  )}
                />

                {/* 추천 배지 */}
                {isRecommended && (
                  <div className="absolute top-1.5 right-0">
                    <Badge className="rounded-none rounded-bl-lg bg-primary">
                      AI 추천
                    </Badge>
                  </div>
                )}

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
                      <div>
                        <h3 className="text-lg font-semibold">{track.name}</h3>
                        <p className="text-sm text-muted-foreground">
                          {track.description}
                        </p>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <div className="text-right">
                        <div className="text-2xl font-bold text-primary">
                          {rec.score}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          적합도
                        </div>
                      </div>
                      <Badge
                        variant="outline"
                        className={cn(style.bg, style.text, style.border)}
                      >
                        {rec.verdict}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="space-y-4">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Clock className="h-4 w-4" />
                    <span>{track.duration}</span>
                  </div>

                  {/* 추천/비추천 이유 */}
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium">분석 결과</h4>
                    <ul className="space-y-2">
                      {rec.reasons.map((reason, index) => (
                        <li
                          key={index}
                          className="flex items-start gap-2 text-sm"
                        >
                          {getReasonIcon(reason.type)}
                          <div>
                            <span className="text-muted-foreground">
                              {reason.text}
                            </span>
                            <span className="text-xs text-muted-foreground/70 ml-1">
                              ({reason.source})
                            </span>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* 주요 요건 */}
                  <div className="pt-2 border-t">
                    <h4 className="text-sm font-medium mb-2">주요 요건</h4>
                    <ul className="grid grid-cols-1 md:grid-cols-2 gap-1">
                      {track.requirements.slice(0, 4).map((req, index) => (
                        <li
                          key={index}
                          className="flex items-start gap-2 text-sm text-muted-foreground"
                        >
                          <Check className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                          {req}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* 선택 버튼 */}
                  <Button
                    variant={isSelected ? "default" : "outline"}
                    className="w-full"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSelectTrack(track.id);
                    }}
                  >
                    {isSelected ? (
                      <>
                        <Check className="h-4 w-4 mr-2" />
                        선택됨
                      </>
                    ) : (
                      "이 트랙 선택"
                    )}
                  </Button>
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
  );
}
