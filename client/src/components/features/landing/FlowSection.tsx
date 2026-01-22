import { FileText, Search, ListChecks, Send, ArrowRight } from "lucide-react";

interface FlowStep {
  icon: React.ReactNode;
  step: number;
  title: string;
  description: string;
}

const steps: FlowStep[] = [
  {
    icon: <FileText className="h-6 w-6" />,
    step: 1,
    title: "기업 정보 입력",
    description: "서비스 개요 및 기술 설명 입력",
  },
  {
    icon: <Search className="h-6 w-6" />,
    step: 2,
    title: "AI 분석",
    description: "대상성 판단 및 최적 트랙 추천",
  },
  {
    icon: <ListChecks className="h-6 w-6" />,
    step: 3,
    title: "신청서 작성",
    description: "신청서 초안 자동 생성",
  },
  {
    icon: <Send className="h-6 w-6" />,
    step: 4,
    title: "검토 및 제출",
    description: "리스크 점검 및 최종 검토",
  },
];

export function FlowSection() {
  return (
    <section className="py-20">
      <div className="container mx-auto px-4">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            간단한 4단계 프로세스
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            복잡한 규제 샌드박스 신청을 단순화했습니다.
          </p>
        </div>

        <div className="relative max-w-4xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 relative">
            {steps.map((step, index) => (
              <div key={step.step} className="relative">
                <div className="flex flex-col items-center text-center">
                  <div className="relative z-10 w-16 h-16 rounded-full gradient-primary flex items-center justify-center text-white mb-4 shadow-lg">
                    {step.icon}
                  </div>
                  <div className="text-xs font-medium text-primary mb-2">
                    STEP {step.step}
                  </div>
                  <h3 className="font-semibold mb-2">{step.title}</h3>
                  <p className="text-sm text-muted-foreground">
                    {step.description}
                  </p>
                </div>

                {index < steps.length - 1 && (
                  <div className="hidden md:flex absolute top-8 right-0 translate-x-1/2 z-20">
                    <ArrowRight className="h-5 w-5 text-muted-foreground" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
