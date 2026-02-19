"use client"

import { TiptapEditor } from "@/components/ui/tiptap-editor"

interface TemporarySafetyProtectionFormProps {
    values: Record<string, string>
    onValueChange: (key: string, value: string) => void
}

/**
 * 안전성 검증 자료 및 이용자 보호방안 (temporary-4)
 */
export function TemporarySafetyProtectionForm({ values, onValueChange }: TemporarySafetyProtectionFormProps) {
    const getValue = (key: string) => values[key] ?? ""

    return (
        <div className="bg-white text-sm">
            {/* 제목 */}
            <h2 className="text-xl font-bold text-center border-b-2 border-gray-800 pb-3 mb-6">
                기술·서비스의 안전성 검증 자료 및 이용자 보호방안
            </h2>

            {/* 1. 안전성 검증 자료 */}
            <section className="mb-6">
                <h3 className="text-base font-bold mb-3">1. 안전성 검증 자료</h3>
                <div className="border border-gray-300 hover:border-primary transition-colors">
                    <TiptapEditor
                        content={getValue("safetyVerification.safetyVerification")}
                        onChange={(content) => onValueChange("safetyVerification.safetyVerification", content)}
                        placeholder="ㅇ 당해 기술·서비스에 대해 안전성을 검증한 방법, 근거, 결과 등을 구체적으로 제시&#10;ㅇ 시험기관 등을 통해 시험, 검사 등을 수행한 경우, 해당 내용을 제시하고, 그 결과를 첨부할 것&#10;ㅇ 시험기관 등을 통해 가능한 부분의 시험, 검사 등을 수행한 경우, 해당 내용을 제시하고, 그 결과를 첨부할 것&#10;ㅇ 시험기관 등을 통해 시험, 검사 등의 수행을 요청하였으나, 세부 기준이 없어 수행이 불가능하다고 의견을 제시받은 자료 등"
                        className="border-none rounded-none min-h-[200px]"
                    />
                </div>
            </section>

            {/* 2. 이용자 보호 및 대응 계획 */}
            <section className="mb-6">
                <h3 className="text-base font-bold mb-3">2. 이용자 보호 및 대응 계획</h3>
                <div className="border border-gray-300 hover:border-primary transition-colors">
                    <TiptapEditor
                        content={getValue("userProtectionPlan.userProtectionPlan")}
                        onChange={(content) => onValueChange("userProtectionPlan.userProtectionPlan", content)}
                        placeholder="ㅇ 임시허가를 통해 실시되는 기술·서비스 이용자에 대한 금전적, 물질적, 생명, 개인정보 등에 대한 보호 계획 제시&#10;  - 이용자에 대한 임시허가 통지 방법&#10;  - 발생 가능한 이용자 피해 및 대응 방안(회피, 대응, 피해 최소화, 피해 구제 등)&#10;  - 피해 발생시 이용자 구제 방법(책임보험, 손해보험, 이외의 기타 방안 등)&#10;ㅇ 이용자의 이의 제기·개선 요구 처리 방법을 구체적으로 제시"
                        className="border-none rounded-none min-h-[200px]"
                    />
                </div>
            </section>

            {/* 3. 임시허가에 따른 위험 및 대응 방안 */}
            <section className="mb-6">
                <h3 className="text-base font-bold mb-3">3. 임시허가에 따른 위험 및 대응 방안</h3>
                <div className="border border-gray-300 hover:border-primary transition-colors">
                    <TiptapEditor
                        content={getValue("riskAndResponse.riskAndResponse")}
                        onChange={(content) => onValueChange("riskAndResponse.riskAndResponse", content)}
                        placeholder="ㅇ 해당 기술·서비스에 규제특례를 지정함에 따라 발생할 수 있는 국민의 생명·건강·안전(3자 피해 포함), 환경, 개인정보의 안전한 보호 및 처리 등을 저해할 가능성 및 대응 방안을 가능한 시나리오별로 구체적으로 제시할 것&#10;ㅇ 발생 가능한 손해항목을 구체적으로 나열하고 손해배상 방안을 제시할 것(책임보험, 손해보험 이외의 기타 손해배상 방안 등)"
                        className="border-none rounded-none min-h-[200px]"
                    />
                </div>
            </section>

            {/* 4. 기존 시장 및 이용자 등의 이해관계 충돌 가능성 및 해소 방안 */}
            <section className="mb-6">
                <h3 className="text-base font-bold mb-3">4. 기존 시장 및 이용자 등의 이해관계 충돌 가능성 및 해소 방안</h3>
                <div className="border border-gray-300 hover:border-primary transition-colors">
                    <TiptapEditor
                        content={getValue("stakeholderConflictResolution.stakeholderConflictResolution")}
                        onChange={(content) => onValueChange("stakeholderConflictResolution.stakeholderConflictResolution", content)}
                        placeholder="ㅇ 임시허가로 인해 해당 규제를 준수하고 있던 기존 시장 참여자들에 대한 형평성 문제 및 기득권 등에 대한 침범으로 인해 발생할 수 있는 이해충돌 가능성에 대한 면밀한 분석과 해소방안을 제시하고, 이해관계 충돌 가능성이 있는 참여자들과의 이해충돌 해소를 위한 협의, 논의 계획 또는 결과를 제시"
                        className="border-none rounded-none min-h-[200px]"
                    />
                </div>
            </section>
        </div>
    )
}
