"use client"

import { useState, useCallback } from "react"
import { DynamicFormCard } from "./DynamicFormCard"
import type { FormType } from "@/stores/wizard-store"

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

interface FormSectionListProps {
    formType: FormType
}

export function FormSectionList({ formType }: FormSectionListProps) {
    const [formValues, setFormValues] = useState<Record<string, string>>({})
    const [savedMessage, setSavedMessage] = useState<string | null>(null)

    const formData = formDataMap[formType]
    const cardKeys = Object.keys(formData)

    const handleValueChange = useCallback((key: string, value: string) => {
        setFormValues((prev) => ({
            ...prev,
            [key]: value,
        }))
    }, [])

    const handleSave = useCallback((cardKey: string) => {
        // 임시저장 로직 (실제로는 API 호출 또는 localStorage 저장)
        console.log(`Saving card ${cardKey}:`, formValues)
        setSavedMessage(`${cardKey} 임시저장 완료`)
        setTimeout(() => setSavedMessage(null), 2000)
    }, [formValues])

    return (
        <div className="space-y-4">
            {savedMessage && (
                <div className="fixed top-4 right-4 bg-grass-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 animate-in fade-in slide-in-from-top-2">
                    {savedMessage}
                </div>
            )}

            {cardKeys.map((cardKey) => (
                <DynamicFormCard
                    key={cardKey}
                    cardKey={cardKey}
                    cardName={getCardName(formType, cardKey)}
                    formSchema={formData[cardKey]}
                    values={formValues}
                    onValueChange={handleValueChange}
                    onSave={() => handleSave(cardKey)}
                />
            ))}
        </div>
    )
}
