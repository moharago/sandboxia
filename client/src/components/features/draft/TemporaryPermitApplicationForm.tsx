"use client"

import { Input } from "@/components/ui/input"
import { TiptapEditor } from "@/components/ui/tiptap-editor"
import { convertToISODate } from "@/lib/utils/form"

interface TemporaryPermitApplicationFormProps {
    values: Record<string, string>
    onValueChange: (key: string, value: string) => void
}

/**
 * 임시허가 신청서 (temporary-1) - 실제 양식 디자인
 */
export function TemporaryPermitApplicationForm({ values, onValueChange }: TemporaryPermitApplicationFormProps) {
    const getValue = (key: string) => values[key] ?? ""
    const getDateValue = (key: string) => convertToISODate(values[key] ?? "")

    // 체크박스 값 처리 (콤마 구분 문자열 또는 개별 boolean 키)
    const getCheckboxValues = (key: string): string[] => {
        const value = values[key]
        if (value) {
            return value.split(",").filter(Boolean)
        }
        return []
    }

    // 개별 boolean 키로 저장된 경우도 체크 (서버 AI 초안 대응)
    const isReasonChecked = (reason: string): boolean => {
        // 1. 콤마 구분 문자열에서 확인
        const reasons = getCheckboxValues("temporaryPermitReason.temporaryPermitReason")
        if (reasons.includes(reason)) return true

        // 2. 개별 boolean 키로 저장된 경우
        const boolKey = `temporaryPermitReason.${reason}`
        if (values[boolKey] === "true") return true

        return false
    }

    const handleCheckboxChange = (key: string, optionValue: string, checked: boolean) => {
        const currentValues = getCheckboxValues(key)
        const newValues = checked
            ? [...currentValues, optionValue]
            : currentValues.filter((v) => v !== optionValue)
        onValueChange(key, newValues.join(","))
    }

    return (
        <div className="bg-white text-sm">
            {/* 법령 근거 */}
            <p className="text-xs text-gray-600 mb-3">
                ■ 정보통신 진흥 및 융합 활성화 등에 관한 특별법 시행규칙 [별지 제11호서식]
            </p>

            {/* 제목 */}
            <h2 className="text-xl font-bold text-center mb-4 border-b-2 border-gray-800 pb-3">임시허가 신청서</h2>

            {/* 안내 */}
            <p className="text-xs text-gray-500 mb-2">※ []에는 해당되는 곳에 √표를 하고, 색상이 어두운 곳은 신청인이 작성하지 않습니다.</p>

            {/* 메인 테이블 */}
            <table className="w-full border-collapse text-sm" style={{ tableLayout: "fixed" }}>
                <colgroup>
                    <col style={{ width: "12%" }} />
                    <col style={{ width: "13%" }} />
                    <col style={{ width: "25%" }} />
                    <col style={{ width: "15%" }} />
                    <col style={{ width: "35%" }} />
                </colgroup>
                <tbody>
                    {/* 접수번호/접수일시 */}
                    <tr>
                        <td className="border border-gray-400 bg-gray-100 px-2 py-2 text-center font-medium">접수번호</td>
                        <td colSpan={2} className="border border-gray-400 bg-gray-50 px-2 py-2"></td>
                        <td className="border border-gray-400 bg-gray-100 px-2 py-2 text-center font-medium">접수일시</td>
                        <td className="border border-gray-400 bg-gray-50 px-2 py-2"></td>
                    </tr>

                    {/* 신청인 - 회사명, 사업자등록번호 */}
                    <tr>
                        <td rowSpan={4} className="border border-gray-400 bg-gray-100 px-2 py-2 text-center font-medium align-middle">
                            신청인
                        </td>
                        <td className="border border-gray-400 bg-gray-100 px-2 py-2 font-medium">회사명(성명)</td>
                        <td className="border border-gray-400 px-1 py-1">
                            <Input
                                value={getValue("applicant.companyName")}
                                onChange={(e) => onValueChange("applicant.companyName", e.target.value)}
                                className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none transition-colors"
                            />
                        </td>
                        <td className="border border-gray-400 bg-gray-100 px-2 py-2 font-medium">사업자(법인)등록번호</td>
                        <td className="border border-gray-400 px-1 py-1">
                            <Input
                                value={getValue("applicant.businessRegistrationNumber")}
                                onChange={(e) => onValueChange("applicant.businessRegistrationNumber", e.target.value)}
                                className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none transition-colors"
                            />
                        </td>
                    </tr>

                    {/* 신청인 - 주소 */}
                    <tr>
                        <td className="border border-gray-400 bg-gray-100 px-2 py-2 font-medium">주소</td>
                        <td colSpan={3} className="border border-gray-400 px-1 py-1">
                            <Input
                                value={getValue("applicant.address")}
                                onChange={(e) => onValueChange("applicant.address", e.target.value)}
                                className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none transition-colors"
                            />
                        </td>
                    </tr>

                    {/* 신청인 - 대표자명, 전화번호, 전자우편 */}
                    <tr>
                        <td className="border border-gray-400 bg-gray-100 px-2 py-2 font-medium">대표자명</td>
                        <td className="border border-gray-400 px-1 py-1">
                            <Input
                                value={getValue("applicant.representativeName")}
                                onChange={(e) => onValueChange("applicant.representativeName", e.target.value)}
                                className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none transition-colors"
                            />
                        </td>
                        <td className="border border-gray-400 bg-gray-100 px-2 py-2 font-medium">전화번호</td>
                        <td className="border border-gray-400 px-1 py-1">
                            <Input
                                value={getValue("applicant.phoneNumber")}
                                onChange={(e) => onValueChange("applicant.phoneNumber", e.target.value)}
                                className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none transition-colors"
                            />
                        </td>
                    </tr>

                    {/* 신청인 - 전자우편 */}
                    <tr>
                        <td className="border border-gray-400 bg-gray-100 px-2 py-2 font-medium">전자우편</td>
                        <td colSpan={3} className="border border-gray-400 px-1 py-1">
                            <Input
                                value={getValue("applicant.email")}
                                onChange={(e) => onValueChange("applicant.email", e.target.value)}
                                className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none transition-colors"
                            />
                        </td>
                    </tr>

                    {/* 신규 기술·서비스 - 명칭 */}
                    <tr>
                        <td rowSpan={3} className="border border-gray-400 bg-gray-100 px-2 py-2 text-center font-medium align-middle">
                            신규<br />기술·서비스
                        </td>
                        <td className="border border-gray-400 bg-gray-100 px-2 py-2 font-medium">명칭</td>
                        <td colSpan={3} className="border border-gray-400 px-1 py-1">
                            <Input
                                value={getValue("technologyService.name")}
                                onChange={(e) => onValueChange("technologyService.name", e.target.value)}
                                className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none transition-colors"
                            />
                        </td>
                    </tr>

                    {/* 신규 기술·서비스 - 유형 */}
                    <tr>
                        <td className="border border-gray-400 bg-gray-100 px-2 py-2 font-medium align-middle">유형</td>
                        <td colSpan={3} className="border border-gray-400 px-3 py-2">
                            <div className="flex flex-wrap gap-x-6 gap-y-1">
                                <label className="flex items-center gap-1.5 cursor-pointer">
                                    <input
                                        type="radio"
                                        name="technologyService.type"
                                        value="technology"
                                        checked={getValue("technologyService.type") === "technology"}
                                        onChange={(e) => onValueChange("technologyService.type", e.target.value)}
                                        className="h-3.5 w-3.5"
                                    />
                                    <span className="text-sm">기술인 경우</span>
                                </label>
                                <label className="flex items-center gap-1.5 cursor-pointer">
                                    <input
                                        type="radio"
                                        name="technologyService.type"
                                        value="service"
                                        checked={getValue("technologyService.type") === "service"}
                                        onChange={(e) => onValueChange("technologyService.type", e.target.value)}
                                        className="h-3.5 w-3.5"
                                    />
                                    <span className="text-sm">서비스인 경우</span>
                                </label>
                                <label className="flex items-center gap-1.5 cursor-pointer">
                                    <input
                                        type="radio"
                                        name="technologyService.type"
                                        value="technologyAndService"
                                        checked={getValue("technologyService.type") === "technologyAndService"}
                                        onChange={(e) => onValueChange("technologyService.type", e.target.value)}
                                        className="h-3.5 w-3.5"
                                    />
                                    <span className="text-sm">기술과 서비스가 융합된 경우</span>
                                </label>
                            </div>
                            <p className="text-xs text-gray-400 mt-1">※ 해당 난에 표시( √ )</p>
                        </td>
                    </tr>

                    {/* 신규 기술·서비스 - 주요내용 */}
                    <tr>
                        <td className="border border-gray-400 bg-gray-100 px-2 py-2 font-medium align-top">주요내용</td>
                        <td colSpan={3} className="border border-gray-400 p-0">
                            <TiptapEditor
                                content={getValue("technologyService.mainContent")}
                                onChange={(content) => onValueChange("technologyService.mainContent", content)}
                                placeholder="서비스의 주요 내용을 입력하세요..."
                                className="border-transparent hover:border-primary transition-colors rounded-none"
                            />
                        </td>
                    </tr>

                    {/* 임시허가 신청 사유 */}
                    <tr>
                        <td rowSpan={2} className="border border-gray-400 bg-gray-100 px-2 py-2 text-center font-medium align-middle">
                            임시허가<br />신청 사유
                        </td>
                        <td colSpan={3} className="border border-gray-400 px-3 py-2">
                            <label className="flex items-start gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={isReasonChecked("noApplicableStandards")}
                                    onChange={(e) => handleCheckboxChange("temporaryPermitReason.temporaryPermitReason", "noApplicableStandards", e.target.checked)}
                                    className="h-4 w-4 mt-0.5"
                                />
                                <span className="text-sm">
                                    1. 허가등의 근거가 되는 법령에 해당 신규 정보통신융합등 기술·서비스에 맞는 기준·규격·요건 등이 없는 경우(법 제37조제1항제1호)
                                </span>
                            </label>
                        </td>
                        <td rowSpan={2} className="border border-gray-400 bg-gray-100 px-2 py-2 text-xs text-center align-middle w-[60px] whitespace-nowrap">
                            해당 난에 표시( √ )
                        </td>
                    </tr>
                    <tr>
                        <td colSpan={3} className="border border-gray-400 px-3 py-2">
                            <label className="flex items-start gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={isReasonChecked("unclearOrUnreasonableStandards")}
                                    onChange={(e) => handleCheckboxChange("temporaryPermitReason.temporaryPermitReason", "unclearOrUnreasonableStandards", e.target.checked)}
                                    className="h-4 w-4 mt-0.5"
                                />
                                <span className="text-sm">
                                    2. 허가등의 근거가 되는 법령에 따른 기준·규격·요건 등을 적용하는 것이 불명확하거나 불합리한 경우(법 제37조제1항제2호)
                                </span>
                            </label>
                        </td>
                    </tr>
                </tbody>
            </table>

            {/* 신청 문구 */}
            <p className="mt-6 text-sm leading-relaxed">
                「정보통신 진흥 및 융합 활성화 등에 관한 특별법」 제37조제1항 및 같은 법 시행령 제40조제1항에 따라 위와 같이 임시허가를 신청합니다.
            </p>

            {/* 날짜 및 서명 */}
            <div className="mt-6 flex flex-col items-end gap-3">
                <Input
                    type="date"
                    value={getDateValue("application.applicationDate")}
                    onChange={(e) => onValueChange("application.applicationDate", e.target.value)}
                    className="w-36 h-8 text-sm"
                />
                <div className="flex items-center gap-2">
                    <span className="text-sm">신청인</span>
                    <Input
                        value={getValue("application.applicantSignature")}
                        onChange={(e) => onValueChange("application.applicantSignature", e.target.value)}
                        className="w-32 h-8 text-sm"
                        placeholder="성명"
                    />
                    <span className="text-sm">(서명 또는 인)</span>
                </div>
            </div>

            {/* 수신 */}
            <p className="mt-4 font-medium">과학기술정보통신부장관 귀하</p>

            {/* 제출서류 */}
            <table className="w-full border-collapse text-sm mt-6">
                <tbody>
                    <tr>
                        <td className="border border-gray-400 bg-gray-100 px-3 py-2 font-medium w-28 align-top">
                            신청인<br />제출서류
                        </td>
                        <td className="border border-gray-400 px-3 py-2 text-sm leading-relaxed">
                            <p>1. 다음 각 목의 내용을 담은 사업계획서 1부</p>
                            <p className="ml-4">가. 신규 정보통신융합등 기술·서비스의 명칭 및 내용</p>
                            <p className="ml-4">나. 신규 정보통신융합등 기술·서비스의 사업범위·추진방법·추진일정</p>
                            <p>2. 신규 정보통신융합등 기술·서비스가 법 제37조제1항 각 호의 어느 하나에 해당함을 설명하는 자료</p>
                            <p>3. 신규 정보통신융합등 기술·서비스의 안전성 검증 자료 및 이용자 보호방안 1부</p>
                            <p>4. 그 밖에 임시허가에 필요하다고 인정되는 것으로서 과학기술정보통신부장관이 요구하는 자료</p>
                        </td>
                    </tr>
                </tbody>
            </table>

            {/* 처리 절차 */}
            <div className="mt-6 border border-gray-400 text-xs">
                <div className="bg-gray-100 px-3 py-1.5 font-medium text-center border-b border-gray-400">
                    처리 절차
                </div>
                <div className="p-3 flex items-center justify-between gap-2 overflow-x-auto">
                    {[
                        { title: "신청(요청)", sub: "신청자\n(관계기관의 장)" },
                        { title: "접수", sub: "과학기술\n정보통신부 장관" },
                        { title: "협의", sub: "과학기술\n정보통신부 장관\n/ 관계기관의 장" },
                        { title: "시험, 검사 실시", sub: "시험·검사 기관" },
                        { title: "심의·의결", sub: "심의위원회" },
                        { title: "임시허가 통지", sub: "과학기술\n정보통신부 장관" },
                    ].map((step, i, arr) => (
                        <div key={step.title} className="flex items-center gap-2">
                            <div className="text-center">
                                <div className="border border-gray-300 rounded px-2 py-1 bg-white whitespace-nowrap">
                                    {step.title}
                                </div>
                                <div className="text-gray-500 mt-1 text-[10px] leading-tight whitespace-pre-line">{step.sub}</div>
                            </div>
                            {i < arr.length - 1 && <span className="text-gray-400">→</span>}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}
