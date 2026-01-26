"use client"

import Link from "next/link"
import { ArrowRight, FileText, Shield, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useUIStore } from "@/stores/ui-store"

export function HeroSection() {
    const isAuthenticated = useUIStore((state) => state.isAuthenticated)
    return (
        <section className="relative overflow-hidden py-20 md:py-32">
            <div className="absolute inset-0 bg-gradient-to-br from-teal-50 via-grass-50 to-teal-50" />
            <div className="absolute inset-0">
                <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-teal-200/30 rounded-full blur-3xl" />
                <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-grass-200/30 rounded-full blur-3xl" />
            </div>

            <div className="container relative mx-auto px-4">
                <div className="max-w-3xl mx-auto text-center">
                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium mb-6">
                        <Sparkles className="h-4 w-4" />
                        AI 기반 규제 샌드박스 컨설팅 지원
                    </div>

                    <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-6">
                        <span className="gradient-text">규제 샌드박스</span>
                        <br />
                        신청이 쉬워집니다
                    </h1>

                    <p className="text-lg md:text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
                        AI가 서비스 분석부터 신청서 작성까지 도와드립니다.
                        <br />
                        복잡한 규제 샌드박스 신청 절차를 간편하게 진행하세요.
                    </p>

                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                        <Link href={isAuthenticated ? "/dashboard" : "/login"}>
                            <Button size="lg" variant="gradient" className="gap-2 px-8">
                                시작하기
                                <ArrowRight className="h-4 w-4" />
                            </Button>
                        </Link>
                    </div>

                    <div className="flex items-center justify-center gap-8 mt-12 text-sm text-muted-foreground">
                        <div className="flex items-center gap-2">
                            <Shield className="h-5 w-5 text-grass-9" />
                            <span>트랙 추천</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <FileText className="h-5 w-5 text-teal-9" />
                            <span>AI 신청서 작성</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <Sparkles className="h-5 w-5 text-teal-9" />
                            <span>사례 분석</span>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    )
}
