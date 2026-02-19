"use client"

import { Input } from "@/components/ui/input"
import { TiptapEditor } from "@/components/ui/tiptap-editor"
import { Button } from "@/components/ui/button"
import { Plus, Trash2 } from "lucide-react"
import { useState, useEffect } from "react"
import { convertToISODate, formatNumber, parseNumber } from "@/lib/utils/form"

interface TemporaryBusinessPlanFormProps {
    values: Record<string, string>
    onValueChange: (key: string, value: string) => void
}

/**
 * 임시허가를 위한 사업계획서 (temporary-2)
 */
export function TemporaryBusinessPlanForm({ values, onValueChange }: TemporaryBusinessPlanFormProps) {
    const getValue = (key: string) => values[key] ?? ""
    const getDateValue = (key: string) => convertToISODate(values[key] ?? "")

    // 설립일은 여러 키 패턴으로 저장될 수 있음
    const getEstablishmentDate = () => {
        const rawDate = values["organizationProfile.generalInfo.establishmentDate"]
            || values["generalInfo.establishmentDate"]
            || values["establishmentDate"]
            || values["organizationProfile.establishmentDate"]
            || ""
        return convertToISODate(rawDate)
    }

    // 동적 배열 행 수 관리
    const [orgRowCount, setOrgRowCount] = useState(1)
    const [submissionRowCount, setSubmissionRowCount] = useState(1)
    const [personnelRowCount, setPersonnelRowCount] = useState(1)

    // values에서 배열 행 수 계산
    useEffect(() => {
        const countRows = (prefix: string) => {
            let maxIndex = 0
            Object.keys(values).forEach((key) => {
                const match = key.match(new RegExp(`^${prefix}\\.(\\d+)\\.`))
                if (match) {
                    const index = parseInt(match[1], 10)
                    if (index >= maxIndex) maxIndex = index + 1
                }
            })
            return Math.max(maxIndex, 1)
        }
        setOrgRowCount(countRows("applicantOrganizations"))
        setSubmissionRowCount(countRows("submission"))
        setPersonnelRowCount(countRows("keyPersonnel"))
    }, [values])

    return (
        <div className="bg-white text-sm space-y-8">
            {/* 임시허가를 위한 사업계획서 */}
            <section>
                <h3 className="text-lg font-bold text-center border-b-2 border-gray-800 pb-2 mb-4">임시허가를 위한 사업계획서</h3>

                {/* 메인 테이블 - PDF 양식 스타일 */}
                <table className="w-full border-collapse text-sm mb-4">
                    <colgroup>
                        <col style={{ width: "10%" }} />
                        <col style={{ width: "18%" }} />
                        <col style={{ width: "10%" }} />
                        <col style={{ width: "14%" }} />
                        <col style={{ width: "10%" }} />
                        <col style={{ width: "14%" }} />
                        <col style={{ width: "18%" }} />
                        <col style={{ width: "6%" }} />
                    </colgroup>
                    <tbody>
                        {/* 사업명 */}
                        <tr>
                            <td className="border border-gray-400 bg-gray-100 px-3 py-2 font-medium text-center">사업명</td>
                            <td colSpan={7} className="border border-gray-400 px-1 py-1">
                                <Input
                                    value={getValue("projectInfo.projectName")}
                                    onChange={(e) => onValueChange("projectInfo.projectName", e.target.value)}
                                    className="border-transparent hover:border-primary focus:border-primary h-8 text-sm shadow-none transition-colors"
                                />
                            </td>
                        </tr>

                        {/* 신청기관 헤더 */}
                        <tr>
                            <td rowSpan={orgRowCount + 1} className="border border-gray-400 bg-gray-100 px-3 py-2 font-medium text-center align-middle">
                                신청기관
                                <div className="mt-2">
                                    <Button
                                        type="button"
                                        variant="outline"
                                        size="sm"
                                        className="gap-1 h-6 text-xs px-2"
                                        onClick={() => setOrgRowCount(prev => prev + 1)}
                                    >
                                        <Plus className="h-3 w-3" />
                                    </Button>
                                </div>
                            </td>
                            <td className="border border-gray-400 bg-gray-100 px-2 py-1.5 text-center font-medium text-xs">기관명</td>
                            <td className="border border-gray-400 bg-gray-100 px-2 py-1.5 text-center font-medium text-xs">유형</td>
                            <td className="border border-gray-400 bg-gray-100 px-2 py-1.5 text-center font-medium text-xs">책임자 성명</td>
                            <td className="border border-gray-400 bg-gray-100 px-2 py-1.5 text-center font-medium text-xs">직위</td>
                            <td className="border border-gray-400 bg-gray-100 px-2 py-1.5 text-center font-medium text-xs">전화</td>
                            <td className="border border-gray-400 bg-gray-100 px-2 py-1.5 text-center font-medium text-xs">E-mail</td>
                            <td className="border border-gray-400 bg-gray-100 px-1 py-1.5 text-center font-medium text-xs"></td>
                        </tr>

                        {/* 신청기관 데이터 행 */}
                        {Array.from({ length: orgRowCount }).map((_, idx) => (
                            <tr key={idx}>
                                <td className="border border-gray-400 px-1 py-1">
                                    <Input
                                        value={getValue(`applicantOrganizations.${idx}.organizationName`)}
                                        onChange={(e) => onValueChange(`applicantOrganizations.${idx}.organizationName`, e.target.value)}
                                        className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                    />
                                </td>
                                <td className="border border-gray-400 px-1 py-1">
                                    <Input
                                        value={getValue(`applicantOrganizations.${idx}.organizationType`)}
                                        onChange={(e) => onValueChange(`applicantOrganizations.${idx}.organizationType`, e.target.value)}
                                        className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                    />
                                </td>
                                <td className="border border-gray-400 px-1 py-1">
                                    <Input
                                        value={getValue(`applicantOrganizations.${idx}.responsiblePersonName`)}
                                        onChange={(e) => onValueChange(`applicantOrganizations.${idx}.responsiblePersonName`, e.target.value)}
                                        className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                    />
                                </td>
                                <td className="border border-gray-400 px-1 py-1">
                                    <Input
                                        value={getValue(`applicantOrganizations.${idx}.position`)}
                                        onChange={(e) => onValueChange(`applicantOrganizations.${idx}.position`, e.target.value)}
                                        className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                    />
                                </td>
                                <td className="border border-gray-400 px-1 py-1">
                                    <Input
                                        value={getValue(`applicantOrganizations.${idx}.phoneNumber`)}
                                        onChange={(e) => onValueChange(`applicantOrganizations.${idx}.phoneNumber`, e.target.value)}
                                        className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                    />
                                </td>
                                <td className="border border-gray-400 px-1 py-1">
                                    <Input
                                        value={getValue(`applicantOrganizations.${idx}.email`)}
                                        onChange={(e) => onValueChange(`applicantOrganizations.${idx}.email`, e.target.value)}
                                        className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                    />
                                </td>
                                <td className="border border-gray-400 px-1 py-1 text-center">
                                    <Button
                                        type="button"
                                        variant="ghost"
                                        size="icon"
                                        className="h-6 w-6 text-muted-foreground hover:text-destructive"
                                        onClick={() => setOrgRowCount(prev => Math.max(1, prev - 1))}
                                        disabled={orgRowCount <= 1}
                                    >
                                        <Trash2 className="h-3 w-3" />
                                    </Button>
                                </td>
                            </tr>
                        ))}

                        {/* 기간 */}
                        <tr>
                            <td className="border border-gray-400 bg-gray-100 px-3 py-2 font-medium text-center">기간</td>
                            <td colSpan={7} className="border border-gray-400 px-2 py-2">
                                <div className="flex items-center gap-2">
                                    <Input
                                        type="date"
                                        value={getDateValue("projectInfo.period.startDate")}
                                        onChange={(e) => onValueChange("projectInfo.period.startDate", e.target.value)}
                                        className="w-36 h-8 text-sm"
                                    />
                                    <span>~</span>
                                    <Input
                                        type="date"
                                        value={getDateValue("projectInfo.period.endDate")}
                                        onChange={(e) => onValueChange("projectInfo.period.endDate", e.target.value)}
                                        className="w-36 h-8 text-sm"
                                    />
                                    <span>(</span>
                                    <Input
                                        value={getValue("projectInfo.period.durationMonths")}
                                        onChange={(e) => onValueChange("projectInfo.period.durationMonths", e.target.value)}
                                        className="w-14 h-8 text-sm text-center"
                                    />
                                    <span>개월)</span>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>

                {/* 확약 문구 */}
                <p className="text-sm leading-relaxed mb-4">
                    과학기술정보통신부 소관의 임시허가 신청을 위하여 사업계획서를 다음과 같이 제출하오며, 신청함에 있어 정보통신 진흥 및 융합 활성화 등에 관한 특별법 및 시행령, 시행규칙 등 제반사항을 준수하며 위약시 어떠한 조치도 감수할 것을 확약합니다.
                </p>

                {/* 제출일자 및 서명 */}
                <div className="flex flex-col items-end gap-4 mb-4">
                    <Input
                        type="date"
                        value={getDateValue("submissionDate.submissionDate")}
                        onChange={(e) => onValueChange("submissionDate.submissionDate", e.target.value)}
                        className="w-36 h-8 text-sm"
                    />
                    <div className="text-sm font-medium">신청기관의 장</div>
                    {Array.from({ length: submissionRowCount }).map((_, idx) => (
                        <div key={idx} className="flex items-center gap-2">
                            <span>(기관명)</span>
                            <Input
                                value={getValue(`submission.${idx}.organizationName`)}
                                onChange={(e) => onValueChange(`submission.${idx}.organizationName`, e.target.value)}
                                className="w-28 h-8 text-sm"
                            />
                            <span>(성명)</span>
                            <Input
                                value={getValue(`submission.${idx}.name`)}
                                onChange={(e) => onValueChange(`submission.${idx}.name`, e.target.value)}
                                className="w-24 h-8 text-sm"
                            />
                            <span>(인)</span>
                        </div>
                    ))}
                    <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="gap-1 h-7 text-xs"
                        onClick={() => setSubmissionRowCount(prev => prev + 1)}
                    >
                        <Plus className="h-3.5 w-3.5" />
                        서명란 추가
                    </Button>
                </div>
                <p className="font-medium">과학기술정보통신부장관 귀하</p>
            </section>

            {/* 1. 기술·서비스 내용 */}
            <section>
                <h3 className="text-base font-bold mb-4">1. 기술·서비스 내용</h3>

                <h4 className="text-sm font-bold mb-2">가. 기술·서비스 세부 내용</h4>
                <div className="border border-gray-300 hover:border-primary transition-colors mb-4">
                    <TiptapEditor
                        content={getValue("technologyService.detailedDescription")}
                        onChange={(content) => onValueChange("technologyService.detailedDescription", content)}
                        placeholder="임시허가를 신청하는 기술·서비스에 대한 구체적인 내용을 작성하세요."
                        className="border-none rounded-none min-h-[150px]"
                    />
                </div>

                <h4 className="text-sm font-bold mb-2">나. 기술·서비스 관련 시장 현황 및 전망</h4>
                <div className="border border-gray-300 hover:border-primary transition-colors mb-4">
                    <TiptapEditor
                        content={getValue("technologyService.marketStatusAndOutlook")}
                        onChange={(content) => onValueChange("technologyService.marketStatusAndOutlook", content)}
                        placeholder="국내·외 관련 기술서비스 현황 및 시장 규모, 전망을 작성하세요."
                        className="border-none rounded-none min-h-[150px]"
                    />
                </div>
            </section>

            {/* 2. 임시허가 신청 내용(법률) */}
            <section>
                <h3 className="text-base font-bold mb-4">2. 임시허가 신청 내용(법률)</h3>

                <h4 className="text-sm font-bold mb-2">가. 규제 내용</h4>
                <div className="border border-gray-300 hover:border-primary transition-colors mb-4">
                    <TiptapEditor
                        content={getValue("temporaryPermitRequest.regulationDetails")}
                        onChange={(content) => onValueChange("temporaryPermitRequest.regulationDetails", content)}
                        placeholder="임시허가의 대상이 되는 규제를 규정하고 있는 법령 체계 및 규제 내용을 작성하세요."
                        className="border-none rounded-none min-h-[150px]"
                    />
                </div>

                <h4 className="text-sm font-bold mb-2">나. 임시허가의 필요성 및 내용</h4>
                <div className="border border-gray-300 hover:border-primary transition-colors mb-4">
                    <TiptapEditor
                        content={getValue("temporaryPermitRequest.necessityAndRequest")}
                        onChange={(content) => onValueChange("temporaryPermitRequest.necessityAndRequest", content)}
                        placeholder="임시허가의 필요성 및 신청 내용을 작성하세요."
                        className="border-none rounded-none min-h-[150px]"
                    />
                </div>
            </section>

            {/* 3. 사업 계획 */}
            <section>
                <h3 className="text-base font-bold mb-4">3. 사업 계획</h3>

                <h4 className="text-sm font-bold mb-2">가. 사업 목표 및 범위</h4>
                <div className="border border-gray-300 hover:border-primary transition-colors mb-4">
                    <TiptapEditor
                        content={getValue("businessPlan.objectivesAndScope")}
                        onChange={(content) => onValueChange("businessPlan.objectivesAndScope", content)}
                        placeholder="사업 목표 및 범위를 작성하세요."
                        className="border-none rounded-none min-h-[150px]"
                    />
                </div>

                <h4 className="text-sm font-bold mb-2">나. 사업 내용</h4>
                <div className="border border-gray-300 hover:border-primary transition-colors mb-4">
                    <TiptapEditor
                        content={getValue("businessPlan.businessContent")}
                        onChange={(content) => onValueChange("businessPlan.businessContent", content)}
                        placeholder="사업에 대한 구체적인 내용을 작성하세요."
                        className="border-none rounded-none min-h-[150px]"
                    />
                </div>

                <h4 className="text-sm font-bold mb-2">다. 사업 기간 및 일정 계획</h4>
                <div className="border border-gray-300 hover:border-primary transition-colors mb-4">
                    <TiptapEditor
                        content={getValue("businessPlan.schedule")}
                        onChange={(content) => onValueChange("businessPlan.schedule", content)}
                        placeholder="전체 임시허가 기간 및 일정계획을 작성하세요."
                        className="border-none rounded-none min-h-[120px]"
                    />
                </div>
            </section>

            {/* 4. 사업 운영 계획 */}
            <section>
                <h3 className="text-base font-bold mb-4">4. 사업 운영 계획</h3>
                <div className="border border-gray-300 hover:border-primary transition-colors mb-4">
                    <TiptapEditor
                        content={getValue("operationPlan.operationPlan")}
                        onChange={(content) => onValueChange("operationPlan.operationPlan", content)}
                        placeholder="사업 환경 구성, 이용자 확보 방법, 모니터링 및 통제 방법 등 운영 계획을 작성하세요."
                        className="border-none rounded-none min-h-[150px]"
                    />
                </div>
            </section>

            {/* 5. 기대효과 */}
            <section>
                <h3 className="text-base font-bold mb-4">5. 기대효과</h3>

                <h4 className="text-sm font-bold mb-2">가. 정량적 기대효과</h4>
                <div className="border border-gray-300 hover:border-primary transition-colors mb-4">
                    <TiptapEditor
                        content={getValue("expectedEffects.quantitative")}
                        onChange={(content) => onValueChange("expectedEffects.quantitative", content)}
                        placeholder="사회적, 경제적 정량적 기대효과를 근거와 함께 작성하세요."
                        className="border-none rounded-none min-h-[120px]"
                    />
                </div>

                <h4 className="text-sm font-bold mb-2">나. 정성적 기대효과</h4>
                <div className="border border-gray-300 hover:border-primary transition-colors mb-4">
                    <TiptapEditor
                        content={getValue("expectedEffects.qualitative")}
                        onChange={(content) => onValueChange("expectedEffects.qualitative", content)}
                        placeholder="사회적, 경제적 정성적 기대효과를 작성하세요."
                        className="border-none rounded-none min-h-[120px]"
                    />
                </div>
            </section>

            {/* 6. 사업 확대·확산 계획 */}
            <section>
                <h3 className="text-base font-bold mb-4">6. 사업 확대·확산 계획</h3>
                <div className="border border-gray-300 hover:border-primary transition-colors mb-4">
                    <TiptapEditor
                        content={getValue("expansionPlan.expansionPlan")}
                        onChange={(content) => onValueChange("expansionPlan.expansionPlan", content)}
                        placeholder="확산 로드맵, 투자 및 인력고용 계획, 확산시 기대효과를 작성하세요."
                        className="border-none rounded-none min-h-[150px]"
                    />
                </div>
            </section>

            {/* 7. 추진 체계 및 예산 */}
            <section>
                <h3 className="text-base font-bold mb-4">7. 추진 체계 및 예산</h3>

                <h4 className="text-sm font-bold mb-2">가. 추진 체계</h4>
                <div className="border border-gray-300 hover:border-primary transition-colors mb-4">
                    <TiptapEditor
                        content={getValue("organizationAndBudget.organizationStructure")}
                        onChange={(content) => onValueChange("organizationAndBudget.organizationStructure", content)}
                        placeholder="사업 추진을 위한 조직 구성 방안, 조직별 책임과 역할을 작성하세요."
                        className="border-none rounded-none min-h-[120px]"
                    />
                </div>

                <h4 className="text-sm font-bold mb-2">나. 추진 예산</h4>
                <div className="border border-gray-300 hover:border-primary transition-colors mb-4">
                    <TiptapEditor
                        content={getValue("organizationAndBudget.budget")}
                        onChange={(content) => onValueChange("organizationAndBudget.budget", content)}
                        placeholder="연차별 추진 운영예산, 이용자 보호를 위한 보험금 등을 작성하세요."
                        className="border-none rounded-none min-h-[120px]"
                    />
                </div>
            </section>

            {/* 붙임 1. 신청기관 현황자료 */}
            <section>
                <h3 className="text-base font-bold mb-4">붙임 1. 신청기관 현황자료</h3>

                <table className="w-full border-collapse text-sm mb-4">
                    <tbody>
                        <tr>
                            <td className="border border-gray-400 bg-gray-100 px-3 py-2 font-medium w-32">기관·단체명</td>
                            <td colSpan={3} className="border border-gray-400 px-1 py-1">
                                <Input
                                    value={getValue("organizationProfile.organizationName")}
                                    onChange={(e) => onValueChange("organizationProfile.organizationName", e.target.value)}
                                    className="border-transparent hover:border-primary focus:border-primary h-8 text-sm shadow-none"
                                />
                            </td>
                        </tr>
                        <tr>
                            <td rowSpan={3} className="border border-gray-400 bg-gray-100 px-3 py-2 font-medium align-middle">일반현황</td>
                            <td className="border border-gray-400 bg-gray-100 px-3 py-2 font-medium w-24">설립일</td>
                            <td colSpan={2} className="border border-gray-400 px-1 py-1">
                                <Input
                                    type="date"
                                    value={getEstablishmentDate()}
                                    onChange={(e) => onValueChange("organizationProfile.generalInfo.establishmentDate", e.target.value)}
                                    className="w-40 h-8 text-sm"
                                />
                            </td>
                        </tr>
                        <tr>
                            <td className="border border-gray-400 bg-gray-100 px-3 py-2 font-medium">대표자</td>
                            <td colSpan={2} className="border border-gray-400 px-1 py-1">
                                <Input
                                    value={getValue("organizationProfile.generalInfo.representativeName")}
                                    onChange={(e) => onValueChange("organizationProfile.generalInfo.representativeName", e.target.value)}
                                    className="border-transparent hover:border-primary focus:border-primary h-8 text-sm shadow-none"
                                />
                            </td>
                        </tr>
                        <tr>
                            <td className="border border-gray-400 bg-gray-100 px-3 py-2 font-medium">주소</td>
                            <td colSpan={2} className="border border-gray-400 px-1 py-1">
                                <Input
                                    value={getValue("organizationProfile.generalInfo.address")}
                                    onChange={(e) => onValueChange("organizationProfile.generalInfo.address", e.target.value)}
                                    className="border-transparent hover:border-primary focus:border-primary h-8 text-sm shadow-none"
                                />
                            </td>
                        </tr>
                        <tr>
                            <td className="border border-gray-400 bg-gray-100 px-3 py-2 font-medium align-top">주요 사업</td>
                            <td colSpan={3} className="border border-gray-300 p-0 hover:border-primary transition-colors">
                                <TiptapEditor
                                    content={getValue("organizationProfile.mainBusiness")}
                                    onChange={(content) => onValueChange("organizationProfile.mainBusiness", content)}
                                    placeholder="주요 사업 내용을 작성하세요."
                                    className="border-none rounded-none min-h-[80px]"
                                />
                            </td>
                        </tr>
                        <tr>
                            <td className="border border-gray-400 bg-gray-100 px-3 py-2 font-medium align-top">주요 인허가 사항</td>
                            <td colSpan={3} className="border border-gray-300 p-0 hover:border-primary transition-colors">
                                <TiptapEditor
                                    content={getValue("organizationProfile.licensesAndPermits")}
                                    onChange={(content) => onValueChange("organizationProfile.licensesAndPermits", content)}
                                    placeholder="주요 인허가 사항을 작성하세요."
                                    className="border-none rounded-none min-h-[80px]"
                                />
                            </td>
                        </tr>
                        <tr>
                            <td className="border border-gray-400 bg-gray-100 px-3 py-2 font-medium align-top">보유기술 및 특허</td>
                            <td colSpan={3} className="border border-gray-300 p-0 hover:border-primary transition-colors">
                                <TiptapEditor
                                    content={getValue("organizationProfile.technologiesAndPatents")}
                                    onChange={(content) => onValueChange("organizationProfile.technologiesAndPatents", content)}
                                    placeholder="보유기술 및 특허를 작성하세요."
                                    className="border-none rounded-none min-h-[80px]"
                                />
                            </td>
                        </tr>
                    </tbody>
                </table>

                {/* 재무현황 테이블 */}
                <h4 className="text-sm font-bold mb-2">재무현황</h4>
                <table className="w-full border-collapse text-sm mb-4">
                    <thead>
                        <tr className="bg-gray-100">
                            <th className="border border-gray-400 px-3 py-2 font-medium">구분</th>
                            <th className="border border-gray-400 px-3 py-2 font-medium">M-2년도</th>
                            <th className="border border-gray-400 px-3 py-2 font-medium">M-1년도</th>
                            <th className="border border-gray-400 px-3 py-2 font-medium">평균</th>
                        </tr>
                    </thead>
                    <tbody>
                        {[
                            { key: "totalAssets", label: "총자산" },
                            { key: "equity", label: "자기자본" },
                            { key: "currentLiabilities", label: "유동부채" },
                            { key: "fixedLiabilities", label: "고정부채" },
                            { key: "currentAssets", label: "유동자산" },
                            { key: "netIncome", label: "당기순이익" },
                            { key: "totalRevenue", label: "총매출액" },
                            { key: "returnOnEquity", label: "자기자본 이익률" },
                            { key: "debtRatio", label: "부채비율" },
                        ].map((row) => (
                            <tr key={row.key}>
                                <td className="border border-gray-400 bg-gray-50 px-3 py-2 font-medium">{row.label}</td>
                                {["yearM2", "yearM1", "average"].map((col) => (
                                    <td key={col} className="border border-gray-400 px-1 py-1">
                                        <Input
                                            value={formatNumber(getValue(`financialStatus.${row.key}.${col}`))}
                                            onChange={(e) => onValueChange(`financialStatus.${row.key}.${col}`, parseNumber(e.target.value))}
                                            className="border-transparent hover:border-primary focus:border-primary h-8 text-sm text-right shadow-none"
                                        />
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>

                {/* 조직도 및 인력현황 */}
                <h4 className="text-sm font-bold mb-2">조직도</h4>
                <div className="border border-gray-300 hover:border-primary transition-colors mb-4">
                    <TiptapEditor
                        content={getValue("humanResources.organizationChart")}
                        onChange={(content) => onValueChange("humanResources.organizationChart", content)}
                        placeholder="조직도를 작성하세요."
                        className="border-none rounded-none min-h-[100px]"
                    />
                </div>

                <div className="flex items-center gap-4 mb-4">
                    <span className="font-medium">소속 직원 수</span>
                    <Input
                        value={getValue("humanResources.totalEmployees")}
                        onChange={(e) => onValueChange("humanResources.totalEmployees", e.target.value)}
                        className="w-32 h-8 text-sm"
                        placeholder="명"
                    />
                </div>

                {/* 주요인력 현황 */}
                <div className="mb-4">
                    <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">주요인력 현황</span>
                        <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="gap-1 h-7 text-xs"
                            onClick={() => setPersonnelRowCount(prev => prev + 1)}
                        >
                            <Plus className="h-3.5 w-3.5" />
                            행 추가
                        </Button>
                    </div>
                    <table className="w-full border-collapse text-sm">
                        <thead>
                            <tr className="bg-gray-100">
                                <th className="border border-gray-400 px-2 py-2 font-medium">이름</th>
                                <th className="border border-gray-400 px-2 py-2 font-medium">부서명</th>
                                <th className="border border-gray-400 px-2 py-2 font-medium">직책</th>
                                <th className="border border-gray-400 px-2 py-2 font-medium">담당업무</th>
                                <th className="border border-gray-400 px-2 py-2 font-medium">주요 자격/보유기술</th>
                                <th className="border border-gray-400 px-2 py-2 font-medium">해당업무 경력(년)</th>
                                <th className="border border-gray-400 px-2 py-2 font-medium w-10"></th>
                            </tr>
                        </thead>
                        <tbody>
                            {Array.from({ length: personnelRowCount }).map((_, idx) => (
                                <tr key={idx}>
                                    <td className="border border-gray-400 px-1 py-1">
                                        <Input
                                            value={getValue(`keyPersonnel.${idx}.name`)}
                                            onChange={(e) => onValueChange(`keyPersonnel.${idx}.name`, e.target.value)}
                                            className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                        />
                                    </td>
                                    <td className="border border-gray-400 px-1 py-1">
                                        <Input
                                            value={getValue(`keyPersonnel.${idx}.department`)}
                                            onChange={(e) => onValueChange(`keyPersonnel.${idx}.department`, e.target.value)}
                                            className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                        />
                                    </td>
                                    <td className="border border-gray-400 px-1 py-1">
                                        <Input
                                            value={getValue(`keyPersonnel.${idx}.position`)}
                                            onChange={(e) => onValueChange(`keyPersonnel.${idx}.position`, e.target.value)}
                                            className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                        />
                                    </td>
                                    <td className="border border-gray-400 px-1 py-1">
                                        <Input
                                            value={getValue(`keyPersonnel.${idx}.responsibilities`)}
                                            onChange={(e) => onValueChange(`keyPersonnel.${idx}.responsibilities`, e.target.value)}
                                            className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                        />
                                    </td>
                                    <td className="border border-gray-400 px-1 py-1">
                                        <Input
                                            value={getValue(`keyPersonnel.${idx}.qualificationsOrSkills`)}
                                            onChange={(e) => onValueChange(`keyPersonnel.${idx}.qualificationsOrSkills`, e.target.value)}
                                            className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                        />
                                    </td>
                                    <td className="border border-gray-400 px-1 py-1">
                                        <Input
                                            value={getValue(`keyPersonnel.${idx}.experienceYears`)}
                                            onChange={(e) => onValueChange(`keyPersonnel.${idx}.experienceYears`, e.target.value)}
                                            className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none text-center"
                                        />
                                    </td>
                                    <td className="border border-gray-400 px-1 py-1 text-center">
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="icon"
                                            className="h-7 w-7 text-muted-foreground hover:text-destructive"
                                            onClick={() => setPersonnelRowCount(prev => Math.max(1, prev - 1))}
                                            disabled={personnelRowCount <= 1}
                                        >
                                            <Trash2 className="h-3.5 w-3.5" />
                                        </Button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    )
}
