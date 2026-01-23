"use client";

import { use, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { notFound } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { FileUpload } from "@/components/ui/file-upload";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { cases } from "@/data";
import { useWizardStore } from "@/stores";
import formData from "@/data/formData.json";

interface ServicePageProps {
  params: Promise<{ id: string }>;
}

export default function ServicePage({ params }: ServicePageProps) {
  const { id } = use(params);
  const router = useRouter();
  const caseData = cases.find((c) => c.id === id);

  const { serviceData, setServiceData, markStepComplete, setCurrentStep } =
    useWizardStore();

  // Initialize form state from serviceData or caseData
  const [companyName, setCompanyName] = useState("");
  const [serviceName, setServiceName] = useState("");
  const [description, setDescription] = useState("");
  const [memo, setMemo] = useState("");
  const [selectedFormType, setSelectedFormType] = useState("counseling");
  const [uploadedFiles, setUploadedFiles] = useState<
    Record<string, File | null>
  >({});

  const selectedForm = formData.find((f) => f.id === selectedFormType);

  const handleFileChange = (appId: string, file: File | null) => {
    setUploadedFiles((prev) => ({ ...prev, [appId]: file }));
  };

  useEffect(() => {
    if (serviceData) {
      // Restore from saved wizard state
      setCompanyName(serviceData.companyName);
      setServiceName(serviceData.serviceName);
      setDescription(serviceData.description);
      setMemo(serviceData.memo);
    } else if (caseData) {
      // Initialize from case data
      setCompanyName(caseData.company);
      setServiceName(caseData.service);
      setDescription(caseData.description || "");
    }
  }, [serviceData, caseData]);

  if (!caseData) {
    notFound();
  }

  const handleNext = () => {
    // Save form data to wizard store
    setServiceData({
      companyName,
      serviceName,
      description,
      memo,
    });

    markStepComplete(1);
    setCurrentStep(2);
    router.push(`/cases/${id}/market`);
  };

  return (
    <div className="py-6">
      <div className="container mx-auto px-4 space-y-6">
        <div>
          <h1 className="text-2xl font-bold mb-2">기업 정보 입력</h1>
          <p className="text-muted-foreground">
            기업과 서비스에 대한 기본 정보를 입력해주세요
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>서비스 정보</CardTitle>
            <CardDescription>
              규제 샌드박스 신청을 위한 서비스 기본 정보를 입력합니다
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="company">회사명</Label>
                <Input
                  id="company"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="service">서비스명</Label>
                <Input
                  id="service"
                  value={serviceName}
                  onChange={(e) => setServiceName(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">서비스 설명</Label>
              <Textarea
                id="description"
                placeholder="서비스에 대해 상세히 설명해주세요"
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="memo">추가 메모</Label>
              <Textarea
                id="memo"
                placeholder="추가로 기록할 내용이 있다면 작성해주세요"
                rows={3}
                value={memo}
                onChange={(e) => setMemo(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>신청 유형 선택 및 신청서 업로드</CardTitle>
            <CardDescription>
              상담신청, 신속확인, 임시허가, 실증특례 중 하나를 선택하고 신청서를
              업로드하세요
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-x-6 gap-y-2">
              {formData.map((form) => (
                <label
                  key={form.id}
                  className="flex items-center gap-2 cursor-pointer"
                >
                  <input
                    type="radio"
                    name="formType"
                    value={form.id}
                    checked={selectedFormType === form.id}
                    onChange={(e) => setSelectedFormType(e.target.value)}
                    className="h-4 w-4 text-primary accent-primary"
                  />
                  <span className="text-sm">{form.name}</span>
                </label>
              ))}
            </div>
          </CardContent>

          {selectedForm && (
            <CardContent className="space-y-4">
              {selectedForm.application.map((app) => (
                <div key={app.id} className="space-y-2">
                  <Label>{app.name}</Label>
                  <FileUpload
                    value={uploadedFiles[app.id] ?? null}
                    onChange={(file) => handleFileChange(app.id, file)}
                  />
                </div>
              ))}
            </CardContent>
          )}
        </Card>

        <div className="flex justify-end">
          <Button onClick={handleNext} className="gap-2">
            다음 단계
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
