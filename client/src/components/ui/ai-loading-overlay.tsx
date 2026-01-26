"use client";

import { Sparkles } from "lucide-react";

interface AILoadingOverlayProps {
    message?: string;
}

export function AILoadingOverlay({
    message = "AI 분석 중",
}: AILoadingOverlayProps) {
    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-white/60 backdrop-blur-sm">
            <div className="flex flex-col items-center gap-4 rounded-lg bg-white p-8 shadow-lg border border-gray-200">
                <div className="relative">
                    <div className="h-12 w-12 rounded-full border-4 border-primary/20 border-t-primary animate-spin" />
                    <Sparkles className="absolute inset-0 m-auto h-5 w-5 text-primary" />
                </div>
                <div className="flex flex-col items-center gap-1">
                    <p className="text-lg font-medium text-foreground">
                        {message}
                    </p>
                    <p className="text-sm text-muted-foreground">
                        잠시만 기다려주세요...
                    </p>
                </div>
            </div>
        </div>
    );
}
