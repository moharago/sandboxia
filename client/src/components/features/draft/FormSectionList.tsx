"use client"

import { useState, useCallback, useEffect, useRef, useMemo } from "react"
import { DynamicFormCard } from "./DynamicFormCard"
import type { FormType } from "@/stores/wizard-store"
import { getTodayIso, formatDateIso } from "@/lib/utils/date"
import { useDraftCardUpdateMutation } from "@/hooks/mutations/use-draft-mutation"

// 새로운 스키마 타입 정의
interface FieldOption {
    id: string
    label: string
    value: string
}

interface FormField {
    key: string
    label: string
    formType: string
    dataType: string
    required: boolean
    options?: FieldOption[]
}

interface TableColumn {
    key: string
    label: string
}

interface TableRow {
    key: string
    label: string
    dataType: string
}

interface FormSection {
    key: string
    label: string
    fields?: FormField[]
    isArray?: boolean
    isTable?: boolean
    columns?: TableColumn[]
    rows?: TableRow[]
}

interface FormSchema {
    formId: string
    formName: string
    version: string
    sections: FormSection[]
}

type FormData = Record<string, FormSchema>

// 폼 데이터 import
import counselingData from "@/data/form/counseling.json"
import temporaryData from "@/data/form/temporary.json"
import demonstrationData from "@/data/form/demonstration.json"
import fastcheckData from "@/data/form/fastcheck.json"
import formMetaData from "@/data/formData.json"

const formDataMap: Record<FormType, FormData> = {
    counseling: counselingData as FormData,
    temporary: temporaryData as FormData,
    demonstration: demonstrationData as FormData,
    fastcheck: fastcheckData as FormData,
}

// 카드 ID -> 한글 이름 매핑
const getCardName = (formType: FormType, cardKey: string): string => {
    const formMeta = formMetaData.find((f) => f.type === formType)
    const application = formMeta?.application.find((a) => a.id === cardKey)
    return application?.name || cardKey
}

/**
 * 오늘 날짜를 기본값으로 설정해야 하는 필드 목록
 */
const DATE_FIELDS_WITH_TODAY_DEFAULT = [
    "application.applicationDate", // 신청일자
    "submissionDate.submissionDate", // 제출일자
]

/**
 * 다른 필드 값을 복사해서 기본값으로 설정할 필드 매핑
 * { 대상필드: 원본필드 }
 */
const FIELD_COPY_DEFAULTS: Record<string, string> = {
    "application.applicantSignature": "applicant.representativeName", // 신청인 성명 ← 대표자명
}

/**
 * 종료일 필드인지 확인
 */
const END_DATE_FIELDS = ["endDate", "period.endDate", "projectInfo.period.endDate"]

function isEndDateField(fieldKey: string): boolean {
    return END_DATE_FIELDS.some((f) => fieldKey.endsWith(f))
}

/**
 * 문자열이 날짜 형식인지 확인하고 ISO 형식으로 변환
 * "2025년 11월 24일" → "2025-11-24"
 * "2026. 02. 06." → "2026-02-06"
 * @param fieldKey 필드 키 (종료일 여부 판단용)
 */
function tryConvertDateToIso(value: string, fieldKey = ""): string {
    // 날짜 패턴 감지: 년/월/일 포함 또는 YYYY.MM.DD 형식
    const isDateLike =
        /\d{4}\s*년/.test(value) || // 2025년
        /^\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.?$/.test(value.trim()) // 2026. 02. 06.

    if (isDateLike) {
        const isEndDate = isEndDateField(fieldKey)
        const converted = formatDateIso(value, isEndDate)
        return converted || value // 변환 실패 시 원본 반환
    }
    return value
}

/**
 * 배열이 문자열만 포함하는지 확인 (체크박스 그룹용)
 */
function isStringArray(arr: unknown[]): arr is string[] {
    return arr.length > 0 && arr.every((item) => typeof item === "string")
}

/**
 * 중첩된 객체를 flat한 key 구조로 변환
 * { applicant: { companyName: "ABC" } } → { "applicant.companyName": "ABC" }
 *
 * 배열 처리:
 * - 문자열 배열 (체크박스 그룹): ["a", "b"] → "a,b" (쉼표 구분 문자열)
 * - 객체 배열 (동적 행): [{...}, {...}] → { "key.0.field": "...", "key.1.field": "..." }
 */
function flattenObject(obj: Record<string, unknown>, prefix = ""): Record<string, string> {
    const result: Record<string, string> = {}

    for (const [key, value] of Object.entries(obj)) {
        const newKey = prefix ? `${prefix}.${key}` : key

        if (value === null || value === undefined) {
            // null/undefined는 빈 문자열로
            result[newKey] = ""
        } else if (Array.isArray(value)) {
            // 문자열 배열은 체크박스 그룹으로 간주 → 쉼표 구분 문자열로 변환
            if (isStringArray(value)) {
                result[newKey] = value.join(",")
            } else if (value.length === 0) {
                // 빈 배열은 빈 문자열
                result[newKey] = ""
            } else {
                // 객체 배열은 인덱스 기반으로 재귀 처리 (DynamicFormCard와 동일한 dot notation 사용)
                for (let i = 0; i < value.length; i++) {
                    const item = value[i]
                    const arrayKey = `${newKey}.${i}`

                    if (item === null || item === undefined) {
                        result[arrayKey] = ""
                    } else if (typeof item === "object") {
                        // 배열 내 객체는 재귀 처리
                        Object.assign(result, flattenObject(item as Record<string, unknown>, arrayKey))
                    } else {
                        // 기타 primitive는 문자열로 변환
                        const strItem = String(item)
                        result[arrayKey] = tryConvertDateToIso(strItem, arrayKey)
                    }
                }
            }
        } else if (typeof value === "object") {
            // 중첩 객체는 재귀 처리
            Object.assign(result, flattenObject(value as Record<string, unknown>, newKey))
        } else if (typeof value === "boolean") {
            // boolean은 문자열로 변환
            result[newKey] = value ? "true" : ""
        } else {
            // 나머지는 문자열로 변환 (날짜 형식이면 ISO로 변환)
            const strValue = String(value)
            result[newKey] = tryConvertDateToIso(strValue, newKey)
        }
    }

    return result
}

interface FormSectionListProps {
    formType: FormType
    initialValues?: Record<string, unknown>
    projectId: string
}

export function FormSectionList({ formType, initialValues, projectId }: FormSectionListProps) {
    const [formValues, setFormValues] = useState<Record<string, Record<string, string>>>({})
    const prevInitialValuesRef = useRef<Record<string, unknown> | undefined>(undefined)

    // initialValues를 카드별 flat 구조로 변환
    const flattenedInitialValues = useMemo(() => {
        if (!initialValues) return {}

        const result: Record<string, Record<string, string>> = {}
        const todayDate = getTodayIso()

        for (const [cardKey, cardData] of Object.entries(initialValues)) {
            if (cardData && typeof cardData === "object") {
                // cardData.data가 있으면 그 안의 데이터를 flatten
                const data = (cardData as Record<string, unknown>).data as Record<string, unknown> | undefined
                if (data && typeof data === "object") {
                    const flatData = flattenObject(data)

                    // 특정 날짜 필드에 오늘 날짜 기본값 적용
                    for (const fieldKey of DATE_FIELDS_WITH_TODAY_DEFAULT) {
                        if (fieldKey in flatData && !flatData[fieldKey]) {
                            flatData[fieldKey] = todayDate
                        }
                    }

                    // 다른 필드 값을 복사해서 기본값 적용 (예: 신청인 성명 ← 대표자명)
                    for (const [targetField, sourceField] of Object.entries(FIELD_COPY_DEFAULTS)) {
                        if (targetField in flatData && !flatData[targetField] && flatData[sourceField]) {
                            flatData[targetField] = flatData[sourceField]
                        }
                    }

                    result[cardKey] = flatData
                }
            }
        }

        return result
    }, [initialValues])

    // initialValues가 변경되면 formValues 업데이트 (새로운 AI 초안 생성 시 반영)
    // deep equality 비교로 실제 데이터 변경 시에만 덮어쓰기 (사용자 입력 보호)
    useEffect(() => {
        if (!initialValues) return

        const prevJson = JSON.stringify(prevInitialValuesRef.current)
        const currentJson = JSON.stringify(initialValues)

        // Fast Refresh 등으로 formValues가 초기화된 경우도 처리
        const isFormValuesEmpty = Object.keys(formValues).length === 0
        const hasFlattenedData = Object.keys(flattenedInitialValues).length > 0

        if (prevJson !== currentJson || (isFormValuesEmpty && hasFlattenedData)) {
            prevInitialValuesRef.current = initialValues
            setFormValues(flattenedInitialValues)
        }
    }, [initialValues, flattenedInitialValues, formValues])
    const [savedMessage, setSavedMessage] = useState<string | null>(null)
    const [saveError, setSaveError] = useState<string | null>(null)

    // 카드 저장 mutation
    const cardUpdateMutation = useDraftCardUpdateMutation({
        onSuccess: (data) => {
            setSavedMessage(`${getCardName(formType, data.card_key)} 저장 완료`)
            setTimeout(() => setSavedMessage(null), 2000)
        },
        onError: (error) => {
            setSaveError(error.message)
            setTimeout(() => setSaveError(null), 3000)
        },
    })

    const formData = formDataMap[formType]
    const cardKeys = Object.keys(formData)

    const handleValueChange = useCallback((cardKey: string, fieldKey: string, value: string) => {
        setFormValues((prev) => ({
            ...prev,
            [cardKey]: {
                ...(prev[cardKey] || {}),
                [fieldKey]: value,
            },
        }))
    }, [])

    const handleSave = useCallback((cardKey: string) => {
        const cardData = formValues[cardKey] || {}
        cardUpdateMutation.mutate({
            project_id: projectId,
            card_key: cardKey,
            card_data: cardData,
        })
    }, [formValues, projectId, cardUpdateMutation])

    return (
        <div className="space-y-4">
            {savedMessage && (
                <div className="fixed top-4 right-4 bg-grass-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 animate-in fade-in slide-in-from-top-2">
                    {savedMessage}
                </div>
            )}

            {saveError && (
                <div className="fixed top-4 right-4 bg-rose-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 animate-in fade-in slide-in-from-top-2">
                    저장 실패: {saveError}
                </div>
            )}

            {cardKeys.map((cardKey) => (
                <DynamicFormCard
                    key={cardKey}
                    cardKey={cardKey}
                    cardName={getCardName(formType, cardKey)}
                    formSchema={formData[cardKey]}
                    values={formValues[cardKey] || {}}
                    onValueChange={(fieldKey, value) => handleValueChange(cardKey, fieldKey, value)}
                    onSave={() => handleSave(cardKey)}
                    isSaving={cardUpdateMutation.isPending}
                />
            ))}
        </div>
    )
}
