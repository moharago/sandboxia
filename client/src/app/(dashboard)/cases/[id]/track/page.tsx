"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { notFound } from "next/navigation";
import { ArrowLeft, ArrowRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { TrackCard } from "@/components/features/case";
import { cases, tracks } from "@/data";
import { useWizardStore } from "@/stores";

interface TrackPageProps {
  params: Promise<{ id: string }>;
}

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
  const [selectedTrackId, setSelectedTrackId] = useState<string | null>(
    trackSelection?.id || null
  );

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

  const handleNext = () => {
    if (selectedTrackId) {
      markStepComplete(3);
      setCurrentStep(4);
      router.push(`/cases/${id}/draft`);
    }
  };

  const trackScores = {
    "track-demonstration": 85,
    "track-temporary": 72,
    "track-fastcheck": 45,
  };

  return (
    <div className="py-6">
      <div className="container mx-auto px-4 space-y-6">
        <div>
          <h1 className="text-2xl font-bold mb-2">트랙 선택</h1>
          <p className="text-muted-foreground">
            AI가 분석한 결과를 바탕으로 최적의 트랙을 선택하세요
          </p>
        </div>

        <Card className="bg-gradient-to-r from-blue-50 to-grass-50 border-primary/20">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              <CardTitle>AI 추천</CardTitle>
            </div>
            <CardDescription>
              입력하신 서비스 정보를 분석한 결과, <strong>실증특례</strong>{" "}
              트랙이 가장 적합합니다. 시장성 검증을 위한 테스트가 필요하고 규제
              면제가 필요한 상황에 적합합니다.
            </CardDescription>
          </CardHeader>
        </Card>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {tracks.map((track) => (
            <TrackCard
              key={track.id}
              track={track}
              isRecommended={track.id === "track-demonstration"}
              isSelected={selectedTrackId === track.id}
              onSelect={handleSelectTrack}
              score={trackScores[track.id as keyof typeof trackScores]}
            />
          ))}
        </div>

        <div className="flex justify-between">
          <Button variant="outline" onClick={handleBack} className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            이전 단계
          </Button>
          <Button
            onClick={handleNext}
            disabled={!selectedTrackId}
            className="gap-2"
          >
            다음 단계
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
