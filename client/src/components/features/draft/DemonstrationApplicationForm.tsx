"use client"

import { Input } from "@/components/ui/input"
import { TiptapEditor } from "@/components/ui/tiptap-editor"
import { convertToISODate } from "@/lib/utils/form"

interface DemonstrationApplicationFormProps {
    values: Record<string, string>
    onValueChange: (key: string, value: string) => void
}

/**
 * 실증을 위한 규제특례 신청서 (demonstration-1) - 실제 양식 디자인
 */
export function DemonstrationApplicationForm({ values, onValueChange }: DemonstrationApplicationFormProps) {
    const getValue = (key: string) => values[key] ?? ""
    const getDateValue = (key: string) => convertToISODate(values[key] ?? "")

    // 체크박스 boolean 값 처리 (서버에서 보내는 필드명 사용)
    const isChecked = (key: string): boolean => {
        return values[key] === "true"
    }

    const handleBooleanChange = (key: string, checked: boolean) => {
        onValueChange(key, checked ? "true" : "")
    }

    return (
        <div className="bg-white text-sm">
            {/* 법령 근거 */}
            <p className="text-xs text-gray-600 mb-3">
                ■ 정보통신 진흥 및 융합 활성화 등에 관한 특별법 시행규칙 [별지 제13호서식]
            </p>

            {/* 제목 */}
            <h2 className="text-xl font-bold text-center mb-4 border-b-2 border-gray-800 pb-3">실증을 위한 규제특례 신청서</h2>

            {/* 안내 */}
            <p className="text-xs text-gray-500 mb-2">※ 색상이 어두운 칸은 신청인이 적지 아니하며, [ ]에는 해당되는 곳에 √표를 합니다.</p>

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

                    {/* 신청인 - 대표자명, 전화번호 */}
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

                    {/* 실증을 위한 규제특례 신청 사유 */}
                    <tr>
                        <td rowSpan={2} className="border border-gray-400 bg-gray-100 px-2 py-2 text-center font-medium align-middle">
                            실증을위한<br />규제 특례<br />신청 사유
                        </td>
                        <td colSpan={3} className="border border-gray-400 px-3 py-2">
                            <label className="flex items-start gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={isChecked("regulatoryExemptionReason.reason1_impossibleToApplyPermit")}
                                    onChange={(e) => handleBooleanChange("regulatoryExemptionReason.reason1_impossibleToApplyPermit", e.target.checked)}
                                    className="h-4 w-4 mt-0.5"
                                />
                                <span className="text-sm">
                                    1. 신규 정보통신융합등 기술·서비스가 다른 법령의 규정에 의하여 허가 등을 신청하는 것이 불가능한 경우(법 제38조의2제1항제1호)
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
                                    checked={isChecked("regulatoryExemptionReason.reason2_unclearOrUnreasonableCriteria")}
                                    onChange={(e) => handleBooleanChange("regulatoryExemptionReason.reason2_unclearOrUnreasonableCriteria", e.target.checked)}
                                    className="h-4 w-4 mt-0.5"
                                />
                                <span className="text-sm">
                                    2. 허가등의 근거가 되는 법령에 따른 기준·규격·요건 등을 적용하는 것이 불명확하거나 불합리한 경우(법 제38조의2제1항제2호)
                                </span>
                            </label>
                        </td>
                    </tr>
                </tbody>
            </table>

            {/* 신청 문구 */}
            <p className="mt-6 text-sm leading-relaxed">
                「정보통신 진흥 및 융합 활성화 등에 관한 특별법」 제38조의2제1항 및 같은 법 시행령 제42조의4제1항에 따라 위와 같이 실증을 위한 규제특례를 신청합니다.
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
                            <p>1. 다음 각 목의 내용을 담은 실증을 위한 규제특례 계획서(실증계획서) 1부</p>
                            <p className="ml-4">가. 신규 정보통신융합등 기술·서비스의 명칭 및 내용</p>
                            <p className="ml-4">나. 신규 정보통신융합등 기술·서비스의 사업범위·추진방법·추진일정</p>
                            <p className="ml-4">다. 신규 정보통신융합등 기술·서비스에 대한 실증과 관련한 신청자의 재정적·기술적 능력</p>
                            <p className="ml-4">라. 신규 정보통신융합등 기술·서비스의 실증을 위하여 필요한 규제특례의 내용·기간 및 관련 법령</p>
                            <p>2. 신규 정보통신융합등 기술·서비스가 법 제38조의2제1항 각 호의 어느 하나에 해당함을 설명하는 자료</p>
                            <p>3. 신규 정보통신융합등 기술·서비스의 이용자 보호방안 1부</p>
                            <p>4. 그 밖에 실증을 위한 규제특례에 필요하다고 인정되는 것으로서 과학기술정보통신부장관이 요구하는 자료</p>
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
                        { title: "신청", sub: "신청자" },
                        { title: "접수", sub: "과학기술\n정보통신부장관" },
                        { title: "신청내용 통지", sub: "과학기술\n정보통신부장관" },
                        { title: "검토 및 결과\n회신", sub: "관계기관의장" },
                        { title: "심의 상정", sub: "과학기술\n정보통신부장관" },
                        { title: "심의·의결", sub: "심의위원회" },
                        { title: "실증을 위한\n규제특례 지정", sub: "과학기술\n정보통신부장관" },
                    ].map((step, i, arr) => (
                        <div key={step.title} className="flex items-center gap-2">
                            <div className="text-center">
                                <div className="border border-gray-300 rounded px-2 py-1 bg-white whitespace-pre-line text-[10px]">
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
