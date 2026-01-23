"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import { notFound } from "next/navigation";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { cases } from "@/data";
import { useWizardStore } from "@/stores";

interface MarketPageProps {
  params: Promise<{ id: string }>;
}

export default function MarketPage({ params }: MarketPageProps) {
  const { id } = use(params);
  const router = useRouter();
  const caseData = cases.find((c) => c.id === id);

  const { markStepComplete, setCurrentStep } = useWizardStore();

  if (!caseData) {
    notFound();
  }

  const handleBack = () => {
    setCurrentStep(1);
    router.push(`/cases/${id}/service`);
  };

  const handleNext = () => {
    markStepComplete(2);
    setCurrentStep(3);
    router.push(`/cases/${id}/track`);
  };

  return (
    <div className="py-6">
      <div className="container mx-auto px-4 space-y-6">
        <div>
          <h1 className="text-2xl font-bold mb-2">시장출시 진단</h1>
          <p className="text-muted-foreground">
            서비스의 시장성과 경쟁 환경을 분석합니다
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>시장 정보</CardTitle>
            <CardDescription>
              타겟 시장과 규모에 대한 정보를 입력해주세요
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="marketSize">예상 시장 규모</Label>
                <Input id="marketSize" placeholder="예: 연 1,000억원" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="targetCustomers">타겟 고객</Label>
                <Input id="targetCustomers" placeholder="예: 20-40대 직장인" />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="competitors">경쟁사 분석</Label>
              <Textarea
                id="competitors"
                placeholder="주요 경쟁사와 차별점을 설명해주세요"
                rows={3}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="differentiators">핵심 차별화 요소</Label>
              <Textarea
                id="differentiators"
                placeholder="기존 서비스 대비 차별화되는 점을 설명해주세요"
                rows={3}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>규제 현황</CardTitle>
            <CardDescription>
              현재 서비스 출시에 걸림돌이 되는 규제를 파악합니다
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="regulations">관련 규제</Label>
              <Textarea
                id="regulations"
                placeholder="서비스 제공에 제한이 되는 규제 법령을 입력해주세요"
                rows={3}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="regulationImpact">규제 영향</Label>
              <Textarea
                id="regulationImpact"
                placeholder="해당 규제로 인한 사업 영향을 설명해주세요"
                rows={3}
              />
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-between">
          <Button variant="outline" onClick={handleBack} className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            이전 단계
          </Button>
          <Button onClick={handleNext} className="gap-2">
            다음 단계
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
