"use client"

import { Input } from "@/components/ui/input"
import { TiptapEditor } from "@/components/ui/tiptap-editor"
import { Plus, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useState, useEffect, useMemo } from "react"
import { formatDateIso } from "@/lib/utils/date"
import { formatNumber, parseNumber, getArrayCount } from "@/lib/utils/form"
import type { DraftFormProps } from "@/types/draft"

/**
 * 실증을 위한 규제특례 실증계획서 (demonstration-2)
 */
export function DemonstrationPlanForm({ values, onValueChange }: DraftFormProps) {
    const getValue = (key: string) => values[key] ?? ""
    const getDateValue = (key: string) => formatDateIso(values[key] ?? "")

    // 배열 행 수 관리 (서버 데이터 기반 + 사용자 추가)
    const [orgCount, setOrgCount] = useState(1)
    const [sigCount, setSigCount] = useState(1)
    const [personnelCount, setPersonnelCount] = useState(1)

    // values에서 실제 행 수 계산
    const computedOrgCount = useMemo(() => getArrayCount(values, "applicantOrganizations"), [values])
    const computedSigCount = useMemo(() => getArrayCount(values, "submission"), [values])
    const computedPersonnelCount = useMemo(() => getArrayCount(values, "keyPersonnel"), [values])

    // 서버 데이터 로드 시 행 수 동기화
    useEffect(() => {
        if (computedOrgCount > 0) setOrgCount(computedOrgCount)
    }, [computedOrgCount])

    useEffect(() => {
        if (computedSigCount > 0) setSigCount(computedSigCount)
    }, [computedSigCount])

    useEffect(() => {
        if (computedPersonnelCount > 0) setPersonnelCount(computedPersonnelCount)
    }, [computedPersonnelCount])

    // 신청기관 배열 - flat key 사용
    const getOrgValue = (index: number, field: string) => getValue(`applicantOrganizations.${index}.${field}`)
    const setOrgValue = (index: number, field: string, value: string) =>
        onValueChange(`applicantOrganizations.${index}.${field}`, value)

    const addOrganization = () => setOrgCount((c) => c + 1)
    const removeOrganization = (index: number) => {
        if (orgCount <= 1) return
        // 삭제된 행 이후의 데이터를 한 칸씩 앞으로 이동
        const fields = ["organizationName", "organizationType", "responsiblePersonName", "position", "phoneNumber", "email"]
        for (let i = index; i < orgCount - 1; i++) {
            for (const field of fields) {
                const nextValue = getValue(`applicantOrganizations.${i + 1}.${field}`)
                onValueChange(`applicantOrganizations.${i}.${field}`, nextValue)
            }
        }
        // 마지막 행 초기화
        for (const field of fields) {
            onValueChange(`applicantOrganizations.${orgCount - 1}.${field}`, "")
        }
        setOrgCount((c) => c - 1)
    }

    // 서명자 배열 - flat key 사용
    const getSigValue = (index: number, field: string) => getValue(`submission.${index}.${field}`)
    const setSigValue = (index: number, field: string, value: string) =>
        onValueChange(`submission.${index}.${field}`, value)

    const addSignature = () => setSigCount((c) => c + 1)
    const removeSignature = (index: number) => {
        if (sigCount <= 1) return
        const fields = ["organizationName", "name"]
        for (let i = index; i < sigCount - 1; i++) {
            for (const field of fields) {
                const nextValue = getValue(`submission.${i + 1}.${field}`)
                onValueChange(`submission.${i}.${field}`, nextValue)
            }
        }
        for (const field of fields) {
            onValueChange(`submission.${sigCount - 1}.${field}`, "")
        }
        setSigCount((c) => c - 1)
    }

    // 주요인력 배열 - flat key 사용
    const getPersonnelValue = (index: number, field: string) => getValue(`keyPersonnel.${index}.${field}`)
    const setPersonnelValue = (index: number, field: string, value: string) =>
        onValueChange(`keyPersonnel.${index}.${field}`, value)

    const addPersonnel = () => setPersonnelCount((c) => c + 1)
    const removePersonnel = (index: number) => {
        if (personnelCount <= 1) return
        const fields = ["name", "department", "position", "responsibilities", "qualificationsOrSkills", "experienceYears"]
        for (let i = index; i < personnelCount - 1; i++) {
            for (const field of fields) {
                const nextValue = getValue(`keyPersonnel.${i + 1}.${field}`)
                onValueChange(`keyPersonnel.${i}.${field}`, nextValue)
            }
        }
        for (const field of fields) {
            onValueChange(`keyPersonnel.${personnelCount - 1}.${field}`, "")
        }
        setPersonnelCount((c) => c - 1)
    }

    return (
        <div className="bg-white text-sm space-y-8">
            {/* 제목 */}
            <h2 className="text-xl font-bold text-center mb-4 border-b-2 border-gray-800 pb-3">
                실증을 위한 규제특례 실증계획서
            </h2>

            {/* 메인 테이블 - 사업명, 신청기관, 기간 통합 */}
            <table className="w-full border-collapse text-sm mb-4">
                <colgroup>
                    <col style={{ width: "12%" }} />
                    <col style={{ width: "17%" }} />
                    <col style={{ width: "9%" }} />
                    <col style={{ width: "13%" }} />
                    <col style={{ width: "9%" }} />
                    <col style={{ width: "13%" }} />
                    <col style={{ width: "21%" }} />
                    <col style={{ width: "6%" }} />
                </colgroup>
                <tbody>
                    {/* 실증사업명 */}
                    <tr>
                        <td className="border border-gray-400 bg-gray-100 px-3 py-2 font-medium text-center whitespace-nowrap">실증사업명</td>
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
                        <td rowSpan={orgCount + 1} className="border border-gray-400 bg-gray-100 px-3 py-2 font-medium text-center align-middle whitespace-nowrap">
                            신청기관
                            <div className="mt-2">
                                <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    className="gap-1 h-6 text-xs px-2"
                                    onClick={addOrganization}
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
                    {Array.from({ length: orgCount }).map((_, index) => (
                        <tr key={index}>
                            <td className="border border-gray-400 px-1 py-1">
                                <Input
                                    value={getOrgValue(index, "organizationName")}
                                    onChange={(e) => setOrgValue(index, "organizationName", e.target.value)}
                                    className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                />
                            </td>
                            <td className="border border-gray-400 px-1 py-1">
                                <Input
                                    value={getOrgValue(index, "organizationType")}
                                    onChange={(e) => setOrgValue(index, "organizationType", e.target.value)}
                                    className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                />
                            </td>
                            <td className="border border-gray-400 px-1 py-1">
                                <Input
                                    value={getOrgValue(index, "responsiblePersonName")}
                                    onChange={(e) => setOrgValue(index, "responsiblePersonName", e.target.value)}
                                    className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                />
                            </td>
                            <td className="border border-gray-400 px-1 py-1">
                                <Input
                                    value={getOrgValue(index, "position")}
                                    onChange={(e) => setOrgValue(index, "position", e.target.value)}
                                    className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                />
                            </td>
                            <td className="border border-gray-400 px-1 py-1">
                                <Input
                                    value={getOrgValue(index, "phoneNumber")}
                                    onChange={(e) => setOrgValue(index, "phoneNumber", e.target.value)}
                                    className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                />
                            </td>
                            <td className="border border-gray-400 px-1 py-1">
                                <Input
                                    value={getOrgValue(index, "email")}
                                    onChange={(e) => setOrgValue(index, "email", e.target.value)}
                                    className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                />
                            </td>
                            <td className="border border-gray-400 px-1 py-1 text-center">
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="icon"
                                    className="h-6 w-6 text-muted-foreground hover:text-destructive"
                                    onClick={() => removeOrganization(index)}
                                    disabled={orgCount <= 1}
                                >
                                    <Trash2 className="h-3 w-3" />
                                </Button>
                            </td>
                        </tr>
                    ))}

                    {/* 실증기간 */}
                    <tr>
                        <td className="border border-gray-400 bg-gray-100 px-3 py-2 font-medium text-center whitespace-nowrap">기간</td>
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

            {/* 제출 문구 */}
            <p className="text-sm leading-relaxed mb-4 text-gray-700">
                과학기술정보통신부 소관의 실증을 위한 규제 특례 신청을 위하여 실증계획서를 다음과 같이 제출하오며,
                신청함에 있어 정보통신 진흥 및 융합 활성화 등에 관한 특별법 및 시행령, 시행규칙 등 제반사항을 준수하며
                위약시 어떠한 조치도 감수할 것을 확약합니다.
            </p>

            {/* 붙임 */}
            <div className="mb-6 text-sm">
                <p className="font-medium">붙임：</p>
                <p className="ml-4">1. 신청기관 현황자료 각 1부.</p>
                <p className="ml-4">2. 신청기관 인감증명서 각 1부.</p>
            </div>

            {/* 날짜 및 서명 */}
            <div className="flex flex-col items-end gap-4 mb-4">
                <Input
                    type="date"
                    value={getDateValue("submissionDate.submissionDate")}
                    onChange={(e) => onValueChange("submissionDate.submissionDate", e.target.value)}
                    className="w-36 h-8 text-sm"
                />
                <div className="text-sm font-medium">신청기관의 장</div>
                {Array.from({ length: sigCount }).map((_, index) => (
                    <div key={index} className="flex items-center gap-2">
                        <span>(기관명)</span>
                        <Input
                            value={getSigValue(index, "organizationName")}
                            onChange={(e) => setSigValue(index, "organizationName", e.target.value)}
                            className="w-28 h-8 text-sm"
                        />
                        <span>(성명)</span>
                        <Input
                            value={getSigValue(index, "name")}
                            onChange={(e) => setSigValue(index, "name", e.target.value)}
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
                    onClick={addSignature}
                >
                    <Plus className="h-3.5 w-3.5" />
                    서명란 추가
                </Button>
            </div>

            {/* 수신 */}
            <p className="mt-4 font-medium">과학기술정보통신부장관 귀하</p>

            <div className="border-t-2 border-gray-300 my-8" />

            {/* ======================================== */}
            {/* 1. 기술·서비스 내용 */}
            {/* ======================================== */}
            <section>
                <h2 className="text-lg font-bold mb-4">1. 기술·서비스 내용</h2>

                {/* 가. 기술·서비스 세부 내용 */}
                <div className="mb-6">
                    <h3 className="font-semibold mb-2 text-gray-800">가. 기술·서비스 세부 내용</h3>
                    <TiptapEditor
                        content={getValue("technologyService.detailedDescription")}
                        onChange={(content) => onValueChange("technologyService.detailedDescription", content)}
                        placeholder="실증을 위한 규제특례를 신청하는 기술·서비스에 대한 구체적인 내용을 작성하세요..."
                        className="min-h-[200px] border border-gray-300 hover:border-primary rounded transition-colors"
                    />
                </div>

                {/* 나. 기술·서비스 관련 시장 현황 및 전망 */}
                <div>
                    <h3 className="font-semibold mb-2 text-gray-800">나. 기술·서비스 관련 시장 현황 및 전망</h3>
                    <TiptapEditor
                        content={getValue("technologyService.marketStatusAndOutlook")}
                        onChange={(content) => onValueChange("technologyService.marketStatusAndOutlook", content)}
                        placeholder="국내외 관련 기술서비스 현황, 시장 규모 및 전망을 작성하세요..."
                        className="min-h-[200px] border border-gray-300 hover:border-primary rounded transition-colors"
                    />
                </div>
            </section>

            {/* ======================================== */}
            {/* 2. 규제특례 신청 내용(법률) */}
            {/* ======================================== */}
            <section>
                <h2 className="text-lg font-bold mb-4">2. 규제특례 신청 내용(법률)</h2>

                {/* 가. 규제 내용 */}
                <div className="mb-6">
                    <h3 className="font-semibold mb-2 text-gray-800">가. 규제 내용</h3>
                    <TiptapEditor
                        content={getValue("regulatoryExemption.regulationDetails")}
                        onChange={(content) => onValueChange("regulatoryExemption.regulationDetails", content)}
                        placeholder="규제 관련 법령 체계 및 해당 규제의 내용과 취지를 구체적으로 작성하세요..."
                        className="min-h-[200px] border border-gray-300 hover:border-primary rounded transition-colors"
                    />
                </div>

                {/* 나. 규제특례 필요성 및 내용 */}
                <div>
                    <h3 className="font-semibold mb-2 text-gray-800">나. 규제특례 필요성 및 내용</h3>
                    <TiptapEditor
                        content={getValue("regulatoryExemption.necessityAndRequest")}
                        onChange={(content) => onValueChange("regulatoryExemption.necessityAndRequest", content)}
                        placeholder="규제특례의 필요성, 신청 내용(면제, 완화 등)을 구체적으로 작성하세요..."
                        className="min-h-[200px] border border-gray-300 hover:border-primary rounded transition-colors"
                    />
                </div>
            </section>

            {/* ======================================== */}
            {/* 3. 세부 실증 계획 */}
            {/* ======================================== */}
            <section>
                <h2 className="text-lg font-bold mb-4">3. 세부 실증 계획</h2>

                {/* 가. 실증 목표 및 범위 */}
                <div className="mb-6">
                    <h3 className="font-semibold mb-2 text-gray-800">가. 실증 목표 및 범위</h3>
                    <TiptapEditor
                        content={getValue("testPlan.objectivesAndScope")}
                        onChange={(content) => onValueChange("testPlan.objectivesAndScope", content)}
                        placeholder="실증 목표, 실증 필요성, 실증 대상 범위를 작성하세요..."
                        className="min-h-[200px] border border-gray-300 hover:border-primary rounded transition-colors"
                    />
                </div>

                {/* 나. 단계별 추진 방법(세부 실증 시나리오) */}
                <div className="mb-6">
                    <h3 className="font-semibold mb-2 text-gray-800">나. 단계별 추진 방법(세부 실증 시나리오)</h3>
                    <TiptapEditor
                        content={getValue("testPlan.executionMethod")}
                        onChange={(content) => onValueChange("testPlan.executionMethod", content)}
                        placeholder="준비단계, 실행단계, 평가단계, 종료단계 등 단계별 추진 방법과 세부 실증 시나리오를 작성하세요..."
                        className="min-h-[200px] border border-gray-300 hover:border-primary rounded transition-colors"
                    />
                </div>

                {/* 다. 실증 기간 및 일정 계획 */}
                <div>
                    <h3 className="font-semibold mb-2 text-gray-800">다. 실증 기간 및 일정 계획</h3>
                    <TiptapEditor
                        content={getValue("testPlan.schedule")}
                        onChange={(content) => onValueChange("testPlan.schedule", content)}
                        placeholder="실증기간 동안의 단계별 작업 내용과 마일스톤을 기준으로 일정계획을 작성하세요..."
                        className="min-h-[150px] border border-gray-300 hover:border-primary rounded transition-colors"
                    />
                </div>
            </section>

            {/* ======================================== */}
            {/* 4. 실증 운영 계획 */}
            {/* ======================================== */}
            <section>
                <h2 className="text-lg font-bold mb-4">4. 실증 운영 계획</h2>
                <TiptapEditor
                    content={getValue("operationPlan.operationPlan")}
                    onChange={(content) => onValueChange("operationPlan.operationPlan", content)}
                    placeholder="실증 환경 구성, 이용자 확보 방법, 모니터링 및 통제 방법, 성과 측정 방법, 보고 계획 등을 작성하세요..."
                    className="min-h-[200px] border border-gray-300 hover:border-primary rounded transition-colors"
                />
            </section>

            {/* ======================================== */}
            {/* 5. 기대효과 */}
            {/* ======================================== */}
            <section>
                <h2 className="text-lg font-bold mb-4">5. 기대효과</h2>

                {/* 가. 정량적 기대효과 */}
                <div className="mb-6">
                    <h3 className="font-semibold mb-2 text-gray-800">가. 정량적 기대효과</h3>
                    <TiptapEditor
                        content={getValue("expectedEffects.quantitative")}
                        onChange={(content) => onValueChange("expectedEffects.quantitative", content)}
                        placeholder="사회적, 경제적 정량적 기대효과와 이용자 편익을 근거와 함께 작성하세요..."
                        className="min-h-[150px] border border-gray-300 hover:border-primary rounded transition-colors"
                    />
                </div>

                {/* 나. 정성적 기대효과 */}
                <div>
                    <h3 className="font-semibold mb-2 text-gray-800">나. 정성적 기대효과</h3>
                    <TiptapEditor
                        content={getValue("expectedEffects.qualitative")}
                        onChange={(content) => onValueChange("expectedEffects.qualitative", content)}
                        placeholder="사회적, 경제적 정성적 기대효과와 이용자 편익을 작성하세요..."
                        className="min-h-[150px] border border-gray-300 hover:border-primary rounded transition-colors"
                    />
                </div>
            </section>

            {/* ======================================== */}
            {/* 6. 실증 이후 계획 */}
            {/* ======================================== */}
            <section>
                <h2 className="text-lg font-bold mb-4">6. 실증 이후 계획</h2>

                {/* 가. 확산 계획 */}
                <div className="mb-6">
                    <h3 className="font-semibold mb-2 text-gray-800">가. 확산 계획</h3>
                    <TiptapEditor
                        content={getValue("postTestPlan.expansionPlan")}
                        onChange={(content) => onValueChange("postTestPlan.expansionPlan", content)}
                        placeholder="실증 종료 후 사업 확대/확산 계획, 투자 및 인력고용 계획, 기대효과 등을 작성하세요..."
                        className="min-h-[150px] border border-gray-300 hover:border-primary rounded transition-colors"
                    />
                </div>

                {/* 나. 실증 후 복구 계획 */}
                <div>
                    <h3 className="font-semibold mb-2 text-gray-800">나. 실증 후 복구 계획</h3>
                    <TiptapEditor
                        content={getValue("postTestPlan.restorationPlan")}
                        onChange={(content) => onValueChange("postTestPlan.restorationPlan", content)}
                        placeholder="실증 종료 후 원상복구가 필요한 경우 복구 계획을 작성하세요..."
                        className="min-h-[150px] border border-gray-300 hover:border-primary rounded transition-colors"
                    />
                </div>
            </section>

            {/* ======================================== */}
            {/* 7. 추진 체계 및 예산 */}
            {/* ======================================== */}
            <section>
                <h2 className="text-lg font-bold mb-4">7. 추진 체계 및 예산</h2>

                {/* 가. 추진 체계 */}
                <div className="mb-6">
                    <h3 className="font-semibold mb-2 text-gray-800">가. 추진 체계</h3>
                    <TiptapEditor
                        content={getValue("organizationAndBudget.organizationStructure")}
                        onChange={(content) => onValueChange("organizationAndBudget.organizationStructure", content)}
                        placeholder="실증관리조직, 이용자보호조직 등 조직 구성 방안과 조직별 책임/역할을 작성하세요..."
                        className="min-h-[150px] border border-gray-300 hover:border-primary rounded transition-colors"
                    />
                </div>

                {/* 나. 추진 예산 */}
                <div>
                    <h3 className="font-semibold mb-2 text-gray-800">나. 추진 예산</h3>
                    <TiptapEditor
                        content={getValue("organizationAndBudget.budget")}
                        onChange={(content) => onValueChange("organizationAndBudget.budget", content)}
                        placeholder="연차별 추진 운영예산, 이용자 보호를 위한 보험금 등을 세부적으로 작성하세요..."
                        className="min-h-[150px] border border-gray-300 hover:border-primary rounded transition-colors"
                    />
                </div>
            </section>

            {/* ======================================== */}
            {/* 붙임 1. 신청기관 현황자료 */}
            {/* ======================================== */}
            <section>
                <h2 className="text-lg font-bold mb-4">붙임 1. 신청기관 현황자료</h2>

                <table className="w-full border-collapse text-sm mb-6">
                    <tbody>
                        {/* 기관·단체명 */}
                        <tr>
                            <td className="border border-gray-400 bg-gray-100 px-3 py-2 font-medium w-28">기관·단체명</td>
                            <td colSpan={3} className="border border-gray-400 p-1">
                                <Input
                                    value={getValue("organizationProfile.organizationName")}
                                    onChange={(e) => onValueChange("organizationProfile.organizationName", e.target.value)}
                                    className="border-transparent hover:border-primary focus:border-primary transition-colors"
                                />
                            </td>
                        </tr>
                        {/* 일반현황 - 설립일 */}
                        <tr>
                            <td rowSpan={3} className="border border-gray-400 bg-gray-100 px-3 py-2 font-medium align-middle">일반현황</td>
                            <td className="border border-gray-400 bg-gray-100 px-2 py-1 w-20">설 립 일</td>
                            <td colSpan={2} className="border border-gray-400 p-1">
                                <Input
                                    type="date"
                                    value={getDateValue("organizationProfile.generalInfo.establishmentDate")}
                                    onChange={(e) => onValueChange("organizationProfile.generalInfo.establishmentDate", e.target.value)}
                                    className="border-transparent hover:border-primary focus:border-primary w-40 transition-colors"
                                />
                            </td>
                        </tr>
                        {/* 일반현황 - 대표자 */}
                        <tr>
                            <td className="border border-gray-400 bg-gray-100 px-2 py-1">대 표 자</td>
                            <td colSpan={2} className="border border-gray-400 p-1">
                                <Input
                                    value={getValue("organizationProfile.generalInfo.representativeName")}
                                    onChange={(e) => onValueChange("organizationProfile.generalInfo.representativeName", e.target.value)}
                                    className="border-transparent hover:border-primary focus:border-primary transition-colors"
                                />
                            </td>
                        </tr>
                        {/* 일반현황 - 주소 */}
                        <tr>
                            <td className="border border-gray-400 bg-gray-100 px-2 py-1">주 소</td>
                            <td colSpan={2} className="border border-gray-400 p-1">
                                <Input
                                    value={getValue("organizationProfile.generalInfo.address")}
                                    onChange={(e) => onValueChange("organizationProfile.generalInfo.address", e.target.value)}
                                    className="border-transparent hover:border-primary focus:border-primary transition-colors"
                                    placeholder="(우편번호 포함)"
                                />
                            </td>
                        </tr>
                        {/* 주요 사업 */}
                        <tr>
                            <td className="border border-gray-400 bg-gray-100 px-3 py-2 font-medium">주요 사업</td>
                            <td colSpan={3} className="border border-gray-400 p-0">
                                <TiptapEditor
                                    content={getValue("organizationProfile.mainBusiness")}
                                    onChange={(content) => onValueChange("organizationProfile.mainBusiness", content)}
                                    placeholder="주요 사업 내용"
                                    className="min-h-[80px] border-transparent hover:border-primary transition-colors"
                                />
                            </td>
                        </tr>
                        {/* 주요 인허가 사항 */}
                        <tr>
                            <td className="border border-gray-400 bg-gray-100 px-3 py-2 font-medium">주요 인허가<br />사항</td>
                            <td colSpan={3} className="border border-gray-400 p-0">
                                <TiptapEditor
                                    content={getValue("organizationProfile.licensesAndPermits")}
                                    onChange={(content) => onValueChange("organizationProfile.licensesAndPermits", content)}
                                    placeholder="주요 인허가 사항"
                                    className="min-h-[80px] border-transparent hover:border-primary transition-colors"
                                />
                            </td>
                        </tr>
                        {/* 보유기술 및 특허 */}
                        <tr>
                            <td className="border border-gray-400 bg-gray-100 px-3 py-2 font-medium">보유기술 및<br />특허</td>
                            <td colSpan={3} className="border border-gray-400 p-0">
                                <TiptapEditor
                                    content={getValue("organizationProfile.technologiesAndPatents")}
                                    onChange={(content) => onValueChange("organizationProfile.technologiesAndPatents", content)}
                                    placeholder="보유기술 및 특허"
                                    className="min-h-[80px] border-transparent hover:border-primary transition-colors"
                                />
                            </td>
                        </tr>
                    </tbody>
                </table>

                {/* 재무현황 */}
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
                        ].map((item) => (
                            <tr key={item.key}>
                                <td className="border border-gray-400 bg-gray-50 px-3 py-2 font-medium">{item.label}</td>
                                {["yearM2", "yearM1", "average"].map((col) => (
                                    <td key={col} className="border border-gray-400 px-1 py-1">
                                        <Input
                                            value={formatNumber(getValue(`financialStatus.${item.key}.${col}`))}
                                            onChange={(e) => onValueChange(`financialStatus.${item.key}.${col}`, parseNumber(e.target.value))}
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
                            onClick={addPersonnel}
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
                            {Array.from({ length: personnelCount }).map((_, index) => (
                                <tr key={index}>
                                    <td className="border border-gray-400 px-1 py-1">
                                        <Input
                                            value={getPersonnelValue(index, "name")}
                                            onChange={(e) => setPersonnelValue(index, "name", e.target.value)}
                                            className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                        />
                                    </td>
                                    <td className="border border-gray-400 px-1 py-1">
                                        <Input
                                            value={getPersonnelValue(index, "department")}
                                            onChange={(e) => setPersonnelValue(index, "department", e.target.value)}
                                            className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                        />
                                    </td>
                                    <td className="border border-gray-400 px-1 py-1">
                                        <Input
                                            value={getPersonnelValue(index, "position")}
                                            onChange={(e) => setPersonnelValue(index, "position", e.target.value)}
                                            className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                        />
                                    </td>
                                    <td className="border border-gray-400 px-1 py-1">
                                        <Input
                                            value={getPersonnelValue(index, "responsibilities")}
                                            onChange={(e) => setPersonnelValue(index, "responsibilities", e.target.value)}
                                            className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                        />
                                    </td>
                                    <td className="border border-gray-400 px-1 py-1">
                                        <Input
                                            value={getPersonnelValue(index, "qualificationsOrSkills")}
                                            onChange={(e) => setPersonnelValue(index, "qualificationsOrSkills", e.target.value)}
                                            className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none"
                                        />
                                    </td>
                                    <td className="border border-gray-400 px-1 py-1">
                                        <Input
                                            value={getPersonnelValue(index, "experienceYears")}
                                            onChange={(e) => setPersonnelValue(index, "experienceYears", e.target.value)}
                                            className="border-transparent hover:border-primary focus:border-primary h-7 text-sm shadow-none text-center"
                                        />
                                    </td>
                                    <td className="border border-gray-400 px-1 py-1 text-center">
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="icon"
                                            className="h-7 w-7 text-muted-foreground hover:text-destructive"
                                            onClick={() => removePersonnel(index)}
                                            disabled={personnelCount <= 1}
                                        >
                                            <Trash2 className="h-3.5 w-3.5" />
                                        </Button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {/* 붙임 안내 */}
                <div className="mt-6 text-sm text-gray-600">
                    <p className="font-medium">붙임：</p>
                    <p className="ml-4">1. 사업자등록증 또는 법인등기부 등본 사본</p>
                    <p className="ml-4">2. 과거 2년간 표준재무제표증명원</p>
                    <p className="ml-4">3. 기업신용등급평가확인서</p>
                </div>
            </section>
        </div>
    )
}
