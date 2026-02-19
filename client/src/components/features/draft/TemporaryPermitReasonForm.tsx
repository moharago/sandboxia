"use client"

import { TiptapEditor } from "@/components/ui/tiptap-editor"

interface TemporaryPermitReasonFormProps {
    values: Record<string, string>
    onValueChange: (key: string, value: string) => void
}

/**
 * 임시허가 신청 사유 해당여부 소명서 (temporary-3)
 */
export function TemporaryPermitReasonForm({ values, onValueChange }: TemporaryPermitReasonFormProps) {
    const getValue = (key: string) => values[key] ?? ""
    const getBooleanValue = (key: string) => values[key] === "true"

    const handleCheckboxChange = (key: string, checked: boolean) => {
        onValueChange(key, checked ? "true" : "false")
    }

    return (
        <div className="bg-white text-sm">
            {/* 제목 */}
            <div className="text-center border-b-2 border-gray-800 pb-3 mb-4">
                <h2 className="text-xl font-bold mb-2">임시허가 신청 사유</h2>
                <p className="text-sm text-gray-600">
                    (법 제37조제1항 각 호의 어느 하나에 해당함을 설명하는 자료)
                </p>
            </div>

            {/* 1. 임시허가 신청 사유 */}
            <section className="mb-6">
                <h3 className="text-base font-bold mb-1">1. 임시허가 신청 사유</h3>
                <p className="text-sm text-gray-600 mb-3">(법 제37조제1항 각 호의 어느 하나에 해당여부)</p>

                <table className="w-full border-collapse text-sm">
                    <thead>
                        <tr className="bg-gray-100">
                            <th className="border border-gray-400 px-3 py-2 font-medium text-left">사유</th>
                            <th className="border border-gray-400 px-3 py-2 font-medium text-center w-24">해당여부</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td className="border border-gray-400 px-3 py-3">
                                허가등의 근거가 되는 법령에 해당 신규 정보통신융합등 기술·서비스에 맞는 기준·규격·요건 등이 없는 경우
                            </td>
                            <td className="border border-gray-400 px-3 py-3 text-center">
                                <input
                                    type="checkbox"
                                    checked={getBooleanValue("eligibility.noApplicableStandards")}
                                    onChange={(e) => handleCheckboxChange("eligibility.noApplicableStandards", e.target.checked)}
                                    className="h-5 w-5 accent-primary cursor-pointer"
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
                                    checked={getBooleanValue("eligibility.unclearOrUnreasonableStandards")}
                                    onChange={(e) => handleCheckboxChange("eligibility.unclearOrUnreasonableStandards", e.target.checked)}
                                    className="h-5 w-5 accent-primary cursor-pointer"
                                />
                            </td>
                        </tr>
                    </tbody>
                </table>
            </section>

            {/* 2. 해당여부에 대한 근거 */}
            <section className="mb-6">
                <h3 className="text-base font-bold mb-3">2. 해당여부에 대한 근거</h3>
                <div className="border border-gray-300 hover:border-primary transition-colors">
                    <TiptapEditor
                        content={getValue("justification.justification")}
                        onChange={(content) => onValueChange("justification.justification", content)}
                        placeholder="위에서 선택한 사유에 해당하는 근거를 구체적으로 작성하세요."
                        className="border-none rounded-none min-h-[150px]"
                    />
                </div>
            </section>
        </div>
    )
}
