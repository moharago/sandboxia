"use client"

import Link from "next/link"
import { ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useUIStore } from "@/stores/ui-store"

export function CTASection() {
    const isAuthenticated = useUIStore((state) => state.isAuthenticated)
    return (
        <section className="py-20 gradient-primary">
            <div className="container mx-auto px-4">
                <div className="max-w-3xl mx-auto text-center text-white">
                    <h2 className="text-3xl md:text-4xl font-bold mb-4">지금 바로 시작하세요</h2>
                    <p className="text-lg opacity-90 mb-8">
                        AI와 함께 규제 샌드박스 신청을 쉽고 빠르게 준비하세요.
                        <br />
                        무료로 시작할 수 있습니다.
                    </p>
                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                        <Link href={isAuthenticated ? "/dashboard" : "/login"}>
                            <Button size="lg" variant="ghost" className="gap-2 px-8 text-white hover:bg-white/10">
                                시작하기
                                <ArrowRight className="h-4 w-4" />
                            </Button>
                        </Link>
                    </div>
                </div>
            </div>
        </section>
    )
}
