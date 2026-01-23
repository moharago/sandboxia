"use client";

import { use, useEffect } from "react";
import { useRouter } from "next/navigation";
import { notFound } from "next/navigation";
import { ArrowLeft, Download, Save, Sparkles, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cases } from "@/data";
import { useWizardStore } from "@/stores";

interface DraftPageProps {
  params: Promise<{ id: string }>;
}

const draftSections = [
  { id: "overview", title: "서비스 개요" },
  { id: "memo", title: "추가 메모" },
  { id: "regulation", title: "규제 특례 필요 사유" },
  { id: "plan", title: "실증 계획" },
  { id: "safety", title: "안전 조치 계획" },
  { id: "expectation", title: "기대 효과" },
];

export default function DraftPage({ params }: DraftPageProps) {
  const { id } = use(params);
  const router = useRouter();
  const caseData = cases.find((c) => c.id === id);

  const {
    trackSelection,
    markStepComplete,
    setCurrentStep,
    draftData,
    setDraftData,
    updateDraftSection,
  } = useWizardStore();

  // Initialize draftData if not exists
  useEffect(() => {
    if (!draftData && caseData) {
      const overviewDefault = `${caseData.company}에서 제공하는 ${caseData.service}는 ${caseData.description || "혁신적인 서비스입니다."}\n\n본 서비스는 기존 규제 환경에서 제공이 어려운 혁신 서비스로, 규제 샌드박스를 통한 실증이 필요합니다.`;

      setDraftData({
        title: `${caseData.company} - ${caseData.service}`,
        summary: "",
        sections: {
          overview: overviewDefault,
          memo: "",
          regulation: "",
          plan: "",
          safety: "",
          expectation: "",
        },
        lastSaved: new Date().toISOString(),
      });
    }
  }, [draftData, caseData, setDraftData]);

  if (!caseData) {
    notFound();
  }

  const handleBack = () => {
    setCurrentStep(3);
    router.push(`/cases/${id}/track`);
  };

  const handleComplete = () => {
    markStepComplete(4);
    router.push("/dashboard");
  };

  return (
    <div className="py-6">
      <div className="container mx-auto px-4 space-y-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-2">신청서 작성</h1>
            <p className="text-muted-foreground">
              AI가 생성한 초안을 검토하고 수정하세요
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" className="gap-2">
              <Save className="h-4 w-4" />
              저장
            </Button>
            <Button variant="outline" className="gap-2">
              <Download className="h-4 w-4" />
              다운로드
            </Button>
          </div>
        </div>

        <Card className="bg-gradient-to-r from-grass-50 to-emerald-50 border-grass-200">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-grass-600" />
                <CardTitle>신청서 초안 생성 완료</CardTitle>
              </div>
              {trackSelection && (
                <Badge variant="success">{trackSelection.name}</Badge>
              )}
            </div>
            <CardDescription>
              입력하신 정보를 바탕으로 신청서 초안이 생성되었습니다. 각 섹션을
              검토하고 필요한 부분을 수정하세요.
            </CardDescription>
          </CardHeader>
        </Card>

        <Card>
          <CardContent className="p-0">
            <Tabs defaultValue="overview">
              <div className="border-b">
                <TabsList className="h-auto p-0 bg-transparent">
                  {draftSections.map((section) => (
                    <TabsTrigger
                      key={section.id}
                      value={section.id}
                      className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-4 py-3"
                    >
                      {section.title}
                    </TabsTrigger>
                  ))}
                </TabsList>
              </div>

              {draftSections.map((section) => (
                <TabsContent
                  key={section.id}
                  value={section.id}
                  className="p-6"
                >
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-semibold">{section.title}</h3>
                      <Button variant="ghost" size="sm" className="gap-2">
                        <Sparkles className="h-4 w-4" />
                        AI 재생성
                      </Button>
                    </div>
                    <Textarea
                      placeholder={`${section.title} 내용을 입력하세요...`}
                      rows={10}
                      className="resize-none"
                      value={draftData?.sections?.[section.id] ?? ""}
                      onChange={(e) =>
                        updateDraftSection(section.id, e.target.value)
                      }
                    />
                  </div>
                </TabsContent>
              ))}
            </Tabs>
          </CardContent>
        </Card>

        <div className="flex justify-between">
          <Button variant="outline" onClick={handleBack} className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            이전 단계
          </Button>
          <Button onClick={handleComplete} variant="gradient" className="gap-2">
            작성 완료
          </Button>
        </div>
      </div>
    </div>
  );
}
