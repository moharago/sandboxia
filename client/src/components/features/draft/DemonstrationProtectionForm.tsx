"use client"

import { TiptapEditor } from "@/components/ui/tiptap-editor"
import type { DraftFormProps } from "@/types/draft"

/**
 * 기술·서비스의 이용자 보호방안 (demonstration-4)
 */
export function DemonstrationProtectionForm({ values, onValueChange }: DraftFormProps) {
    const getValue = (key: string) => values[key] ?? ""

    return (
        <div className="bg-white text-sm space-y-6">
            {/* 제목 */}
            <div className="text-center border-b-2 border-gray-800 pb-3 mb-4">
                <h2 className="text-xl font-bold mb-2">기술·서비스의 이용자 보호방안</h2>
                <p className="text-sm text-gray-600">(실증 기간 동안 이용자 보호 및 위험관리 등에 관한 계획)</p>
            </div>

            {/* 1. 이용자 보호 및 대응 계획 */}
            <section>
                <h3 className="text-base font-bold mb-3">1. 이용자 보호 및 대응 계획</h3>
                <TiptapEditor
                    content={getValue("protectionAndResponse.protectionAndResponse")}
                    onChange={(content) => onValueChange("protectionAndResponse.protectionAndResponse", content)}
                    placeholder="이용자 보호를 위한 구체적인 계획과 문제 발생 시 대응 방안을 작성하세요..."
                    className="min-h-[150px] border border-gray-300 hover:border-primary transition-colors rounded"
                />
            </section>

            {/* 2. 규제특례에 따른 위험 및 대응 방안 */}
            <section>
                <h3 className="text-base font-bold mb-3">2. 규제특례에 따른 위험 및 대응 방안</h3>
                <TiptapEditor
                    content={getValue("riskAndMitigation.riskAndMitigation")}
                    onChange={(content) => onValueChange("riskAndMitigation.riskAndMitigation", content)}
                    placeholder="규제특례 적용으로 인해 발생할 수 있는 위험 요소와 이에 대한 대응 방안을 작성하세요..."
                    className="min-h-[150px] border border-gray-300 hover:border-primary transition-colors rounded"
                />
            </section>

            {/* 3. 기존 시장 및 이용자 등의 이해관계 충돌 가능성 및 해소 방안 */}
            <section>
                <h3 className="text-base font-bold mb-3">3. 기존 시장 및 이용자 등의 이해관계 충돌 가능성 및 해소 방안</h3>
                <TiptapEditor
                    content={getValue("stakeholderConflict.stakeholderConflict")}
                    onChange={(content) => onValueChange("stakeholderConflict.stakeholderConflict", content)}
                    placeholder="기존 시장 참여자 및 이용자와의 이해관계 충돌 가능성과 이를 해소하기 위한 방안을 작성하세요..."
                    className="min-h-[150px] border border-gray-300 hover:border-primary transition-colors rounded"
                />
            </section>
        </div>
    )
}
