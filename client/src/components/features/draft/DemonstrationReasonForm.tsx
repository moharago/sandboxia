"use client"

import { TiptapEditor } from "@/components/ui/tiptap-editor"

interface DemonstrationReasonFormProps {
    values: Record<string, string>
    onValueChange: (key: string, value: string) => void
}

/**
 * 실증을 위한 규제특례 신청 사유 (demonstration-3)
 */
export function DemonstrationReasonForm({ values, onValueChange }: DemonstrationReasonFormProps) {
    const getValue = (key: string) => values[key] ?? ""

    // 체크박스 boolean 값 처리
    const isChecked = (key: string): boolean => {
        const value = values[key]
        return value === "true" || value === true || value === "V" || value === "√"
    }

    const handleCheckboxChange = (key: string, checked: boolean) => {
        onValueChange(key, checked ? "true" : "")
    }

    return (
        <div className="bg-white text-sm space-y-6">
            {/* 제목 */}
            <div className="text-center border-b-2 border-gray-800 pb-3 mb-4">
                <h2 className="text-xl font-bold mb-2">실증을 위한 규제특례 신청 사유</h2>
                <p className="text-sm text-gray-600">(법 제38조의2제1항 각 호의 어느 하나에 해당함을 설명하는 자료)</p>
            </div>

            {/* 1. 실증을 위한 규제특례 신청 사유 */}
            <section>
                <h3 className="text-base font-bold mb-2">1. 실증을 위한 규제특례 신청 사유</h3>
                <p className="text-sm text-gray-600 mb-3">(법 제38조의2제1항 각 호의 어느 하나에 해당여부)</p>

                <table className="w-full border-collapse text-sm">
                    <thead>
                        <tr>
                            <th className="border border-gray-400 bg-gray-100 px-3 py-2 text-left font-medium">사유</th>
                            <th className="border border-gray-400 bg-gray-100 px-3 py-2 text-center font-medium w-24">해당여부</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td className="border border-gray-400 px-3 py-3">
                                신규 정보통신융합등 기술·서비스가 다른 법령의 규정에 의하여 허가등을 신청하는 것이 불가능한 경우
                            </td>
                            <td className="border border-gray-400 px-3 py-3 text-center">
                                <input
                                    type="checkbox"
                                    checked={isChecked("eligibility.impossibleToApplyPermitByOtherLaw")}
                                    onChange={(e) => handleCheckboxChange("eligibility.impossibleToApplyPermitByOtherLaw", e.target.checked)}
                                    className="h-5 w-5 cursor-pointer"
                                />
                            </td>
                        </tr>
                        <tr>
                            <td className="border border-gray-400 px-3 py-3">
                                허가등의 근거가 되는 법령에 따른 기준·규격·요건 등을 적용하는 것이 불명확하거나 불합리한 경우
                            </td>
                            <td className="border border-gray-400 px-3 py-3 text-center">
                                <input
                                    type="checkbox"
                                    checked={isChecked("eligibility.unclearOrUnreasonableCriteria")}
                                    onChange={(e) => handleCheckboxChange("eligibility.unclearOrUnreasonableCriteria", e.target.checked)}
                                    className="h-5 w-5 cursor-pointer"
                                />
                            </td>
                        </tr>
                    </tbody>
                </table>
            </section>

            {/* 2. 해당여부에 대한 근거 */}
            <section>
                <h3 className="text-base font-bold mb-3">2. 해당여부에 대한 근거</h3>
                <TiptapEditor
                    content={getValue("justification.justification")}
                    onChange={(content) => onValueChange("justification.justification", content)}
                    placeholder="규제특례 신청 사유에 해당하는 근거를 구체적으로 작성하세요..."
                    className="min-h-[150px] border border-gray-300 hover:border-primary transition-colors rounded"
                />
            </section>
        </div>
    )
}
