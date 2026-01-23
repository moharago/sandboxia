"use client";

import { use, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { notFound } from "next/navigation";
import { ArrowRight, Upload } from "lucide-react";
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
  CardFooter,
} from "@/components/ui/card";
import { cases, domains } from "@/data";
import { useWizardStore } from "@/stores";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

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
  const [domain, setDomain] = useState("");
  const [description, setDescription] = useState("");
  const [technology, setTechnology] = useState("");

  useEffect(() => {
    if (serviceData) {
      // Restore from saved wizard state
      setCompanyName(serviceData.companyName);
      setServiceName(serviceData.serviceName);
      setDescription(serviceData.description);
      setTechnology(serviceData.technology);
      setDomain(serviceData.targetMarket);
    } else if (caseData) {
      // Initialize from case data
      setCompanyName(caseData.company);
      setServiceName(caseData.service);
      setDescription(caseData.description || "");
      setDomain(caseData.domain);
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
      technology,
      targetMarket: domain,
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
            기업의 서비스에 대한 기본 정보를 입력해주세요
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
              <Label htmlFor="domain">분야</Label>
              <Select value={domain} onValueChange={setDomain}>
                <SelectTrigger>
                  <SelectValue placeholder="분야를 선택하세요" />
                </SelectTrigger>
                <SelectContent>
                  {domains.map((d) => (
                    <SelectItem key={d.id} value={d.id}>
                      {d.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
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
              <Label htmlFor="technology">핵심 기술</Label>
              <Textarea
                id="technology"
                placeholder="서비스에 사용되는 핵심 기술을 설명해주세요"
                rows={3}
                value={technology}
                onChange={(e) => setTechnology(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>관련 서류 업로드</CardTitle>
            <CardDescription>
              사업계획서, 기술 설명서 등 관련 서류를 업로드해주세요 (선택)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="border-2 border-dashed border-border rounded-lg p-8 text-center">
              <Upload className="h-10 w-10 mx-auto text-muted-foreground mb-4" />
              <p className="text-sm text-muted-foreground mb-2">
                파일을 드래그하거나 클릭하여 업로드하세요
              </p>
              <p className="text-xs text-muted-foreground">
                PDF, DOCX, HWP (최대 10MB)
              </p>
              <Button variant="outline" className="mt-4">
                파일 선택
              </Button>
            </div>
          </CardContent>
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
