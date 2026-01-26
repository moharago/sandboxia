import { FileSearch, Scale, Route, FileEdit, Lightbulb, ShieldCheck } from "lucide-react"
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"

interface Feature {
    icon: React.ReactNode
    title: string
    description: string
}

const features: Feature[] = [
    {
        icon: <FileSearch className="h-6 w-6 text-teal-9" />,
        title: "서비스 구조화",
        description: "신청서 양식을 파싱하고 비즈니스 서비스를 체계적으로 구조화합니다.",
    },
    {
        icon: <Scale className="h-6 w-6 text-grass-9" />,
        title: "대상성 판단",
        description: "규제 샌드박스 적용 대상 여부를 AI가 자동으로 판단합니다.",
    },
    {
        icon: <Route className="h-6 w-6 text-teal-9" />,
        title: "트랙 추천",
        description: "실증특례, 임시허가, 신속확인 중 최적의 트랙을 추천합니다.",
    },
    {
        icon: <FileEdit className="h-6 w-6 text-grass-9" />,
        title: "신청서 초안",
        description: "승인 사례를 학습한 AI가 신청서 초안을 자동 생성합니다.",
    },
    {
        icon: <Lightbulb className="h-6 w-6 text-teal-9" />,
        title: "전략 추천",
        description: "유사 승인 사례 기반의 전략적 조언을 제공합니다.",
    },
    {
        icon: <ShieldCheck className="h-6 w-6 text-grass-9" />,
        title: "리스크 체크",
        description: "심사 관점에서 잠재적 리스크를 사전에 점검합니다.",
    },
]

export function FeatureSection() {
    return (
        <section id="features" className="py-20 bg-muted/30">
            <div className="container mx-auto px-4">
                <div className="text-center mb-12">
                    <h2 className="text-3xl md:text-4xl font-bold mb-4">AI 에이전트가 도와드립니다</h2>
                    <p className="text-muted-foreground max-w-2xl mx-auto">6개의 전문 AI 에이전트가 규제 샌드박스 신청의 모든 단계를 지원합니다.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {features.map((feature, index) => (
                        <Card key={index} className="hover:shadow-lg transition-shadow">
                            <CardHeader>
                                <div className="w-12 h-12 rounded-lg bg-muted flex items-center justify-center mb-4">{feature.icon}</div>
                                <CardTitle className="text-lg">{feature.title}</CardTitle>
                                <CardDescription>{feature.description}</CardDescription>
                            </CardHeader>
                        </Card>
                    ))}
                </div>
            </div>
        </section>
    )
}
