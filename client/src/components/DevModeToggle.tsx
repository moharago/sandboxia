"use client";

import { useState } from "react";
import { Settings, X, User, LogIn } from "lucide-react";
import { useUIStore } from "@/stores";
import { cn } from "@/lib/utils/cn";

export function DevModeToggle() {
  const [isOpen, setIsOpen] = useState(false);
  const { devMode, isAuthenticated, toggleDevMode, setAuthenticated } =
    useUIStore();

  // devMode가 꺼져있으면 작은 버튼만 표시 (다시 켤 수 있도록)
  if (!devMode) {
    return (
      <button
        onClick={toggleDevMode}
        className="fixed bottom-4 right-4 z-50 p-2 bg-gray-200 hover:bg-gray-300 rounded-full shadow opacity-50 hover:opacity-100 transition-opacity"
        title="개발 모드 켜기"
      >
        <Settings className="h-4 w-4 text-gray-500" />
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {isOpen ? (
        <div className="bg-card border border-border rounded-lg shadow-lg p-4 w-64">
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-semibold">DEV MODE</span>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 hover:bg-muted rounded"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm">
                {isAuthenticated ? (
                  <User className="h-4 w-4 text-grass-500" />
                ) : (
                  <LogIn className="h-4 w-4 text-muted-foreground" />
                )}
                <span>로그인 상태</span>
              </div>
              <button
                onClick={() => setAuthenticated(!isAuthenticated)}
                className={cn(
                  "relative inline-flex h-6 w-11 items-center rounded-full transition-colors bg-gray-300"
                )}
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
  );
}
