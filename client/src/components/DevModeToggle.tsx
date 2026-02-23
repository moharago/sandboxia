"use client"

import { useState } from "react"
import { Settings, X, User, LogIn, FileText, FlaskConical, Loader } from "lucide-react"
import { useUIStore } from "@/stores/ui-store"
import { AILoader } from "@/components/ui/ai-loader"
import { useUserStore } from "@/stores/user-store"
import { useWizardStore, FORM_TYPE_LABELS, type FormType } from "@/stores/wizard-store"
import { cn } from "@/lib/utils/cn"

export function DevModeToggle() {
    const [isOpen, setIsOpen] = useState(false)
    const {
        devMode,
        isAuthenticated,
        devIsAnalyzed,
        devHasChanges,
        devShowAILoader,
        toggleDevMode,
        setAuthenticated,
        setDevIsAnalyzed,
        setDevHasChanges,
        setDevShowAILoader,
    } = useUIStore()
    const setUser = useUserStore((state) => state.setUser)

    const handleToggleAuth = () => {
        const newAuth = !isAuthenticated
        setAuthenticated(newAuth)

        if (newAuth) {
            // 로그인 ON → 더미 유저 설정
            setUser({
                email: 'hong@company.com',
                name: '홍길동',
                company: '스마트모빌리티',
                phone: '010-1234-5678'
            })
        } else {
            // 로그인 OFF → 유저 초기화
            setUser(null)
        }
    }

    const handleClose = () => {
        setIsOpen(false)
        // 로그인 모드가 꺼진 상태면 devMode도 끄기 (회색 버튼으로)
        if (!isAuthenticated) {
            toggleDevMode()
        }
    }
    const { selectedFormType, setSelectedFormType } = useWizardStore()

    const formTypes: FormType[] = ["counseling", "fastcheck", "temporary", "demonstration"]

    // devMode가 꺼져있으면 작은 버튼만 표시 (다시 켤 수 있도록)
    if (!devMode) {
        return (
            <button
                onClick={toggleDevMode}
                className="fixed bottom-4 right-4 z-[110] p-2 bg-gray-200 hover:bg-gray-300 rounded-full shadow opacity-50 hover:opacity-100 transition-opacity"
                title="개발 모드 켜기"
            >
                <Settings className="h-4 w-4 text-gray-500" />
            </button>
        )
    }

    return (
        <>
            {devShowAILoader && <AILoader message="로더 미리보기 모드입니다..." />}
            <div className="fixed bottom-4 right-4 z-[110]">
            {isOpen ? (
                <div className="bg-card border border-border rounded-lg shadow-lg p-4 w-64">
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-sm font-semibold">DEV MODE</span>
                        <button onClick={handleClose} className="p-1 hover:bg-muted rounded">
                            <X className="h-4 w-4" />
                        </button>
                    </div>

                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2 text-sm">
                                {isAuthenticated ? <User className="h-4 w-4 text-grass-500" /> : <LogIn className="h-4 w-4 text-muted-foreground" />}
                                <span>로그인 상태</span>
                            </div>
                            <button
                                onClick={handleToggleAuth}
                                className={cn("relative inline-flex h-6 w-11 items-center rounded-full transition-colors bg-gray-300")}
                            >
                                <span
                                    className={cn(
                                        "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
                                        isAuthenticated ? "translate-x-6" : "translate-x-1"
                                    )}
                                />
                            </button>
                        </div>

                        {isAuthenticated && (
                            <div className="text-xs text-muted-foreground bg-muted p-2 rounded">
                                <p>
                                    <strong>사용자:</strong> 홍길동
                                </p>
                                <p>
                                    <strong>회사:</strong> 스마트모빌리티
                                </p>
                            </div>
                        )}

                        <div className="border-t border-border pt-3">
                            <div className="flex items-center gap-2 text-sm mb-2">
                                <FileText className="h-4 w-4 text-muted-foreground" />
                                <span>신청서 유형</span>
                            </div>
                            <div className="grid grid-cols-2 gap-1">
                                {formTypes.map((type) => (
                                    <button
                                        key={type}
                                        onClick={() => setSelectedFormType(type)}
                                        className={cn(
                                            "text-xs px-2 py-1.5 rounded transition-colors",
                                            selectedFormType === type
                                                ? "bg-primary text-primary-foreground"
                                                : "bg-muted hover:bg-muted/80 text-muted-foreground"
                                        )}
                                    >
                                        {FORM_TYPE_LABELS[type]}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="border-t border-border pt-3">
                            <div className="flex items-center gap-2 text-sm mb-2">
                                <FlaskConical className="h-4 w-4 text-muted-foreground" />
                                <span>분석 상태 시뮬레이션</span>
                            </div>
                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs text-muted-foreground">분석 완료</span>
                                    <button
                                        onClick={() => setDevIsAnalyzed(!devIsAnalyzed)}
                                        className={cn("relative inline-flex h-5 w-9 items-center rounded-full transition-colors", devIsAnalyzed ? "bg-primary" : "bg-gray-300")}
                                    >
                                        <span
                                            className={cn(
                                                "inline-block h-3 w-3 transform rounded-full bg-white transition-transform",
                                                devIsAnalyzed ? "translate-x-5" : "translate-x-1"
                                            )}
                                        />
                                    </button>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className={cn("text-xs", devIsAnalyzed ? "text-muted-foreground" : "text-muted-foreground/50")}>데이터 변경됨</span>
                                    <button
                                        onClick={() => setDevHasChanges(!devHasChanges)}
                                        disabled={!devIsAnalyzed}
                                        className={cn(
                                            "relative inline-flex h-5 w-9 items-center rounded-full transition-colors",
                                            !devIsAnalyzed ? "bg-gray-200 cursor-not-allowed" : devHasChanges ? "bg-amber-500" : "bg-gray-300"
                                        )}
                                    >
                                        <span
                                            className={cn(
                                                "inline-block h-3 w-3 transform rounded-full bg-white transition-transform",
                                                devHasChanges ? "translate-x-5" : "translate-x-1"
                                            )}
                                        />
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div className="border-t border-border pt-3">
                            <div className="flex items-center gap-2 text-sm mb-2">
                                <Loader className="h-4 w-4 text-muted-foreground" />
                                <span>로더 미리보기</span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-muted-foreground">AI Loader</span>
                                <button
                                    onClick={() => setDevShowAILoader(!devShowAILoader)}
                                    className={cn(
                                        "relative inline-flex h-5 w-9 items-center rounded-full transition-colors",
                                        devShowAILoader ? "bg-primary" : "bg-gray-300"
                                    )}
                                >
                                    <span
                                        className={cn(
                                            "inline-block h-3 w-3 transform rounded-full bg-white transition-transform",
                                            devShowAILoader ? "translate-x-5" : "translate-x-1"
                                        )}
                                    />
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            ) : (
                <button
                    onClick={() => setIsOpen(true)}
                    className="flex items-center gap-2 bg-orange-500 hover:bg-orange-600 text-white px-3 py-2 rounded-full shadow-lg transition-colors"
                >
                    <Settings className="h-4 w-4" />
                    <span className="text-sm font-medium">DEV</span>
                </button>
            )}
        </div>
        </>
    )
}
