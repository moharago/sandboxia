"use client"

import { TiptapEditor } from "@/components/ui/tiptap-editor"
import type { DraftFormProps } from "@/types/draft"

/**
 * 신규 정보통신융합 등 기술·서비스에 대한 설명서 (fastcheck-2)
 */
export function FastcheckDescriptionForm({ values, onValueChange }: DraftFormProps) {
    const getValue = (key: string) => values[key] ?? ""

    return (
        <div className="bg-white text-sm">
            {/* 제목 */}
            <h2 className="text-xl font-bold text-center mb-6 border-b-2 border-gray-800 pb-3">
                신규 정보통신융합 등 기술·서비스에 대한 설명서
            </h2>

            {/* 1. 기술·서비스 세부내용 */}
            <section className="mb-6">
                <h3 className="text-base font-bold mb-3">1. 기술·서비스 세부내용</h3>
                <div className="border border-gray-300 hover:border-primary transition-colors">
                    <TiptapEditor
                        content={getValue("technologyServiceDetails.technologyServiceDetails")}
                        onChange={(content) => onValueChange("technologyServiceDetails.technologyServiceDetails", content)}
                        placeholder="기술·서비스에 대한 구체적인 내용을 작성하세요. (이용자, 서비스 제공자를 포함한 서비스 흐름도, 핵심 기술 설명 등)"
                        className="border-none rounded-none min-h-[200px]"
                    />
                </div>
            </section>

            {/* 2. 법·제도 이슈 사항 */}
            <section className="mb-6">
                <h3 className="text-base font-bold mb-3">2. 법·제도 이슈 사항</h3>
                <div className="border border-gray-300 hover:border-primary transition-colors">
                    <TiptapEditor
                        content={getValue("legalIssues.legalIssues")}
                        onChange={(content) => onValueChange("legalIssues.legalIssues", content)}
                        placeholder="확인하고 싶은 규제사항을 법적논점/소관부처로 나누어서 작성하세요.&#10;&#10;예시:&#10;ㅇ (도로교통법 xx조) 국토교통부에 ○○규제를 확인해주기를 요망&#10;ㅇ (식품위생법 xx조) 식품의약품안전처에 ○○규제를 확인해주기를 요망"
                        className="border-none rounded-none min-h-[150px]"
                    />
                </div>
            </section>

            {/* 3. 기타 질의 사항 */}
            <section className="mb-6">
                <h3 className="text-base font-bold mb-3">3. 기타 질의 사항</h3>
                <div className="border border-gray-300 hover:border-primary transition-colors">
                    <TiptapEditor
                        content={getValue("additionalQuestions.additionalQuestions")}
                        onChange={(content) => onValueChange("additionalQuestions.additionalQuestions", content)}
                        placeholder="명확한 규제 관련 법령 등을 모를 경우, 확인하고자 하는 내용을 기술·서비스와 연결하여 서술하세요."
                        className="border-none rounded-none min-h-[120px]"
                    />
                </div>
            </section>
        </div>
    )
}
