"use client"

import { useEffect, useRef } from "react"
import { usePathname } from "next/navigation"
import { Header } from "./Header"
import { Sidebar } from "./Sidebar"
import { Footer } from "./Footer"
import { NewCaseModal } from "@/components/features/projects/NewCaseModal"
import { AILoader } from "@/components/ui/ai-loader"
import { useUIStore } from "@/stores/ui-store"

interface DashboardLayoutProps {
    children: React.ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
    const pathname = usePathname()
    const mainRef = useRef<HTMLElement>(null)
    const globalAILoader = useUIStore((state) => state.globalAILoader)

    // 페이지 전환 시 스크롤 초기화
    useEffect(() => {
        if (mainRef.current) {
            mainRef.current.scrollTo(0, 0)
        }
    }, [pathname])

    return (
        <div className="flex h-screen overflow-hidden flex-col">
            <Header />
            <div className="flex flex-1 overflow-hidden relative">
                <Sidebar />
                <main ref={mainRef} className="flex-1 overflow-y-auto bg-background flex flex-col">
                    <div className="flex-1">{children}</div>
                    <Footer />
                </main>
            </div>
            <NewCaseModal />

            {/* 전역 AI 로더 */}
            {globalAILoader.isVisible && (
                <AILoader
                    message={globalAILoader.message}
                    nodes={globalAILoader.nodes}
                    completedNodes={globalAILoader.completedNodes}
                    currentNodeId={globalAILoader.currentNodeId}
                    progress={globalAILoader.progress}
                />
            )}
        </div>
    )
}
