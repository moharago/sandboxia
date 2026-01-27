"use client"

import { useState, useEffect, useMemo } from "react"
import { ChevronDown, ChevronUp, Save, Plus, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils/cn"

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

interface DynamicFormCardProps {
    cardKey: string
    cardName: string
    formSchema: FormSchema
    values: Record<string, string>
    onValueChange: (key: string, value: string) => void
    onSave: () => void
}

export function DynamicFormCard({ cardKey, cardName, formSchema, values, onValueChange, onSave }: DynamicFormCardProps) {
    const [isOpen, setIsOpen] = useState(true)
    const [listRowCounts, setListRowCounts] = useState<Record<string, number>>({})

    // values에서 isArray 섹션의 행 수를 계산
    const computedRowCounts = useMemo(() => {
        const counts: Record<string, number> = {}
        const arraySections = formSchema.sections.filter((s) => s.isArray)

        arraySections.forEach((section) => {
            let maxIndex = 0
            Object.keys(values).forEach((key) => {
                // sectionKey.{index}.fieldKey 패턴 매칭
                const match = key.match(new RegExp(`^${section.key}\\.(\\d+)\\.`))
                if (match) {
                    const index = parseInt(match[1], 10)
                    if (index >= maxIndex) {
                        maxIndex = index + 1
                    }
                }
            })
            counts[section.key] = Math.max(maxIndex, 1)
        })

        return counts
    }, [values, formSchema.sections])

    // values 변경 시 listRowCounts 동기화
    useEffect(() => {
        setListRowCounts((prev) => {
            const updated = { ...prev }
            Object.entries(computedRowCounts).forEach(([key, count]) => {
                // 기존 값보다 computed 값이 크면 업데이트
                if (!updated[key] || updated[key] < count) {
                    updated[key] = count
                }
            })
            return updated
        })
    }, [computedRowCounts])

    const getRowCount = (sectionKey: string) => {
        return listRowCounts[sectionKey] ?? computedRowCounts[sectionKey] ?? 1
    }

    const addRow = (sectionKey: string) => {
        setListRowCounts((prev) => ({
            ...prev,
            [sectionKey]: (prev[sectionKey] ?? 1) + 1,
        }))
    }

    const removeRow = (sectionKey: string, rowIndex: number) => {
        const currentCount = listRowCounts[sectionKey] ?? 1
        if (currentCount <= 1) return

        // 삭제할 행 이후의 데이터를 한 칸씩 앞으로 이동
        const newValues: Record<string, string> = {}
        for (let i = rowIndex; i < currentCount - 1; i++) {
            Object.keys(values).forEach((key) => {
                if (key.startsWith(`${sectionKey}.${i + 1}.`)) {
                    const newKey = key.replace(`${sectionKey}.${i + 1}.`, `${sectionKey}.${i}.`)
                    newValues[newKey] = values[key]
                }
            })
        }

        // 마지막 행의 데이터 삭제
        Object.keys(values).forEach((key) => {
            if (key.startsWith(`${sectionKey}.${currentCount - 1}.`)) {
                onValueChange(key, "")
            }
        })

        // 이동된 데이터 업데이트
        Object.entries(newValues).forEach(([key, val]) => {
            onValueChange(key, val)
        })

        setListRowCounts((prev) => ({
            ...prev,
            [sectionKey]: currentCount - 1,
        }))
    }

    const renderField = (field: FormField, parentKey = "") => {
        const fieldKey = parentKey ? `${parentKey}.${field.key}` : field.key
        const value = values[fieldKey] ?? ""

        switch (field.formType) {
            case "text":
                return (
                    <div key={fieldKey} className="space-y-1.5">
                        <Label htmlFor={fieldKey} className="text-sm">
                            {field.label}
                            {field.required && <span className="text-destructive ml-1">*</span>}
                        </Label>
                        <Input id={fieldKey} value={value} onChange={(e) => onValueChange(fieldKey, e.target.value)} className="h-9" />
                    </div>
                )

            case "textarea":
                return (
                    <div key={fieldKey} className="space-y-1.5">
                        <Label htmlFor={fieldKey} className="text-sm">
                            {field.label}
                            {field.required && <span className="text-destructive ml-1">*</span>}
                        </Label>
                        <Textarea
                            id={fieldKey}
                            value={value}
                            onChange={(e) => onValueChange(fieldKey, e.target.value)}
                            rows={4}
                            className="resize-none"
                        />
                    </div>
                )

            case "date":
                return (
                    <div key={fieldKey} className="space-y-1.5">
                        <Label htmlFor={fieldKey} className="text-sm">
                            {field.label}
                            {field.required && <span className="text-destructive ml-1">*</span>}
                        </Label>
                        <Input id={fieldKey} type="date" value={value} onChange={(e) => onValueChange(fieldKey, e.target.value)} className="h-9" />
                    </div>
                )

            case "radio":
                return (
                    <div key={fieldKey} className="space-y-2">
                        <Label className="text-sm">
                            {field.label}
                            {field.required && <span className="text-destructive ml-1">*</span>}
                        </Label>
                        <div className="space-y-1.5">
                            {field.options?.map((option) => (
                                <label key={option.id} className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="radio"
                                        name={fieldKey}
                                        value={option.value}
                                        checked={value === option.value}
                                        onChange={(e) => onValueChange(fieldKey, e.target.value)}
                                        className="h-4 w-4 text-primary accent-primary"
                                    />
                                    <span className="text-sm">{option.label}</span>
                                </label>
                            ))}
                        </div>
                    </div>
                )

            case "checkbox": {
                // options가 있으면 체크박스 그룹, 없으면 단독 체크박스
                if (field.options && field.options.length > 0) {
                    // 체크박스 그룹
                    return (
                        <div key={fieldKey} className="space-y-2">
                            <Label className="text-sm">
                                {field.label}
                                {field.required && <span className="text-destructive ml-1">*</span>}
                            </Label>
                            <div className="space-y-1.5">
                                {field.options.map((option) => {
                                    const checkedValues = value ? value.split(",") : []
                                    const isChecked = checkedValues.includes(option.value)

                                    return (
                                        <label key={option.id} className="flex items-start gap-2 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={isChecked}
                                                onChange={(e) => {
                                                    const newValues = e.target.checked
                                                        ? [...checkedValues, option.value]
                                                        : checkedValues.filter((v) => v !== option.value)
                                                    onValueChange(fieldKey, newValues.join(","))
                                                }}
                                                className="h-4 w-4 mt-0.5 text-primary accent-primary"
                                            />
                                            <span className="text-sm">{option.label}</span>
                                        </label>
                                    )
                                })}
                            </div>
                        </div>
                    )
                }

                // 단독 체크박스 (boolean)
                return (
                    <div key={fieldKey} className="space-y-2">
                        <label className="flex items-start gap-2 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={value === "true"}
                                onChange={(e) => onValueChange(fieldKey, e.target.checked ? "true" : "")}
                                className="h-4 w-4 mt-0.5 text-primary accent-primary"
                            />
                            <span className="text-sm">{field.label}</span>
                        </label>
                    </div>
                )
            }

            default:
                return null
        }
    }

    const renderTableSection = (section: FormSection) => {
        const columns = section.columns || []
        const tableRows = section.rows || []

        return (
            <div key={section.key} className="space-y-2">
                <Label className="text-sm font-medium">{section.label}</Label>
                <div className="overflow-x-auto border border-border rounded-lg">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="bg-muted/50">
                                <th className="px-3 py-2 text-left font-medium border-b border-border"></th>
                                {columns.map((col) => (
                                    <th key={col.key} className="px-3 py-2 text-center font-medium border-b border-border">
                                        {col.label}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {tableRows.map((row, rowIdx) => (
                                <tr key={row.key} className={rowIdx % 2 === 0 ? "bg-background" : "bg-muted/30"}>
                                    <td className="px-3 py-2 font-medium border-b border-border whitespace-nowrap">
                                        {row.label}
                                    </td>
                                    {columns.map((col) => {
                                        const cellKey = `${section.key}.${row.key}.${col.key}`
                                        const cellValue = values[cellKey] ?? ""
                                        return (
                                            <td key={col.key} className="px-2 py-1.5 border-b border-border">
                                                <Input
                                                    value={cellValue}
                                                    onChange={(e) => onValueChange(cellKey, e.target.value)}
                                                    className="h-8 text-center"
                                                />
                                            </td>
                                        )
                                    })}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        )
    }

    const renderArraySection = (section: FormSection) => {
        const fields = section.fields || []
        const rowCount = getRowCount(section.key)

        return (
            <div key={section.key} className="space-y-2">
                <div className="flex items-center justify-between">
                    <Label className="text-sm font-medium">{section.label}</Label>
                    <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="gap-1 h-7 text-xs"
                        onClick={() => addRow(section.key)}
                    >
                        <Plus className="h-3.5 w-3.5" />
                        행 추가
                    </Button>
                </div>
                <div className="overflow-x-auto border border-border rounded-lg">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="bg-muted/50">
                                <th className="px-2 py-2 text-center font-medium border-b border-border w-10">No.</th>
                                {fields.map((field) => (
                                    <th key={field.key} className="px-2 py-2 text-center font-medium border-b border-border whitespace-nowrap">
                                        {field.label}
                                        {field.required && <span className="text-destructive ml-1">*</span>}
                                    </th>
                                ))}
                                <th className="px-2 py-2 text-center font-medium border-b border-border w-12"></th>
                            </tr>
                        </thead>
                        <tbody>
                            {Array.from({ length: rowCount }).map((_, rowIdx) => (
                                <tr key={rowIdx} className={rowIdx % 2 === 0 ? "bg-background" : "bg-muted/30"}>
                                    <td className="px-2 py-1.5 text-center border-b border-border text-muted-foreground">
                                        {rowIdx + 1}
                                    </td>
                                    {fields.map((field) => {
                                        const cellKey = `${section.key}.${rowIdx}.${field.key}`
                                        const cellValue = values[cellKey] ?? ""
                                        return (
                                            <td key={field.key} className="px-1.5 py-1.5 border-b border-border">
                                                <Input
                                                    value={cellValue}
                                                    onChange={(e) => onValueChange(cellKey, e.target.value)}
                                                    className="h-8"
                                                    placeholder={field.label}
                                                />
                                            </td>
                                        )
                                    })}
                                    <td className="px-1.5 py-1.5 border-b border-border text-center">
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="icon-sm"
                                            className="h-7 w-7 text-muted-foreground hover:bg-white hover:border hover:border-destructive hover:text-destructive"
                                            onClick={() => removeRow(section.key, rowIdx)}
                                            disabled={rowCount <= 1}
                                        >
                                            <Trash2 className="h-3.5 w-3.5" />
                                        </Button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        )
    }

    const renderSection = (section: FormSection) => {
        // isTable인 경우
        if (section.isTable) {
            return renderTableSection(section)
        }

        // isArray인 경우 (동적 행 추가)
        if (section.isArray) {
            return renderArraySection(section)
        }

        // 일반 섹션 (fields 포함)
        if (!section.fields || section.fields.length === 0) {
            return null
        }

        return (
            <div key={section.key} className="space-y-4">
                <h4 className="font-bold border-b border-gray-300 pb-2">{section.label}</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {section.fields.map((field) => {
                        // textarea, radio, checkbox는 전체 너비
                        if (field.formType === "textarea" || field.formType === "radio" || field.formType === "checkbox") {
                            return (
                                <div key={field.key} className="col-span-full">
                                    {renderField(field, section.key)}
                                </div>
                            )
                        }
                        return renderField(field, section.key)
                    })}
                </div>
            </div>
        )
    }

    return (
        <Card>
            <CardHeader
                className="cursor-pointer"
                onClick={() => setIsOpen(!isOpen)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault()
                        setIsOpen(!isOpen)
                    }
                }}
                aria-expanded={isOpen}
            >
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{cardName}</CardTitle>
                    <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={isOpen ? "섹션 접기" : "섹션 펼치기"}
                        tabIndex={-1}
                    >
                        {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </Button>
                </div>
            </CardHeader>

            <div className={cn("overflow-hidden transition-all duration-300", isOpen ? "opacity-100" : "max-h-0 opacity-0")}>
                <CardContent className="space-y-6">
                    {formSchema.sections.map(renderSection)}

                    <div className="flex justify-end">
                        <Button
                            variant="outline"
                            size="sm"
                            className="gap-2"
                            onClick={(e) => {
                                e.stopPropagation()
                                onSave()
                            }}
                        >
                            <Save className="h-4 w-4" />
                            임시저장
                        </Button>
                    </div>
                </CardContent>
            </div>
        </Card>
    )
}
