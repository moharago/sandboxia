"use client"

import { useState } from "react"
import { ChevronDown, ChevronUp, Save, Plus, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils/cn"

interface TableRow {
    key: string
    label: string
}

interface FormField {
    key: string
    label: string
    formType: string
    contents?: FormField[] | RadioOption[]
    headers?: string[]
    rows?: TableRow[]
}

interface RadioOption {
    id: string
    name: string
    value: string
}

interface FormSection {
    key: string
    label: string
    formType?: string
    contents: FormField[]
}

interface DynamicFormCardProps {
    cardKey: string
    cardName: string
    sections: FormSection[]
    values: Record<string, string>
    onValueChange: (key: string, value: string) => void
    onSave: () => void
}

export function DynamicFormCard({ cardKey, cardName, sections, values, onValueChange, onSave }: DynamicFormCardProps) {
    const [isOpen, setIsOpen] = useState(true)
    const [listRowCounts, setListRowCounts] = useState<Record<string, number>>({})

    const getRowCount = (fieldKey: string) => {
        return listRowCounts[fieldKey] ?? 1
    }

    const addRow = (fieldKey: string) => {
        setListRowCounts((prev) => ({
            ...prev,
            [fieldKey]: (prev[fieldKey] ?? 1) + 1,
        }))
    }

    const removeRow = (fieldKey: string, rowIndex: number) => {
        const currentCount = listRowCounts[fieldKey] ?? 1
        if (currentCount <= 1) return

        // 삭제할 행 이후의 데이터를 한 칸씩 앞으로 이동
        const newValues: Record<string, string> = {}
        for (let i = rowIndex; i < currentCount - 1; i++) {
            // 다음 행의 데이터를 현재 행으로 복사
            Object.keys(values).forEach((key) => {
                if (key.startsWith(`${fieldKey}.${i + 1}.`)) {
                    const newKey = key.replace(`${fieldKey}.${i + 1}.`, `${fieldKey}.${i}.`)
                    newValues[newKey] = values[key]
                }
            })
        }

        // 마지막 행의 데이터 삭제
        Object.keys(values).forEach((key) => {
            if (key.startsWith(`${fieldKey}.${currentCount - 1}.`)) {
                onValueChange(key, "")
            }
        })

        // 이동된 데이터 업데이트
        Object.entries(newValues).forEach(([key, val]) => {
            onValueChange(key, val)
        })

        setListRowCounts((prev) => ({
            ...prev,
            [fieldKey]: currentCount - 1,
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
                        </Label>
                        <Input id={fieldKey} value={value} onChange={(e) => onValueChange(fieldKey, e.target.value)} className="h-9" />
                    </div>
                )

            case "textarea":
                return (
                    <div key={fieldKey} className="space-y-1.5">
                        <Label htmlFor={fieldKey} className="text-sm">
                            {field.label}
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
                        </Label>
                        <Input id={fieldKey} type="date" value={value} onChange={(e) => onValueChange(fieldKey, e.target.value)} className="h-9" />
                    </div>
                )

            case "radio":
                return (
                    <div key={fieldKey} className="space-y-2">
                        <Label className="text-sm">{field.label}</Label>
                        <div className="space-y-1.5">
                            {(field.contents as RadioOption[])?.map((option) => (
                                <label key={option.id} className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="radio"
                                        name={fieldKey}
                                        value={option.value}
                                        checked={value === option.value}
                                        onChange={(e) => onValueChange(fieldKey, e.target.value)}
                                        className="h-4 w-4 text-primary accent-primary"
                                    />
                                    <span className="text-sm">{option.name}</span>
                                </label>
                            ))}
                        </div>
                    </div>
                )

            case "checkbox":
                // 단독 체크박스 (contents가 없는 경우)
                if (!field.contents || !Array.isArray(field.contents)) {
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

                // 체크박스 그룹 (contents가 있는 경우)
                return (
                    <div key={fieldKey} className="space-y-2">
                        <Label className="text-sm">{field.label}</Label>
                        <div className="space-y-1.5">
                            {(field.contents as RadioOption[]).map((option) => {
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
                                        <span className="text-sm">{option.name}</span>
                                    </label>
                                )
                            })}
                        </div>
                    </div>
                )

            case "table":
                const headers = field.headers || []
                const tableRows = field.rows || []
                const columnKeys = ["yearM2", "yearM1", "average"]

                return (
                    <div key={fieldKey} className="space-y-2">
                        <Label className="text-sm font-medium">{field.label}</Label>
                        <div className="overflow-x-auto border border-border rounded-lg">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="bg-muted/50">
                                        <th className="px-3 py-2 text-left font-medium border-b border-border"></th>
                                        {headers.map((header, idx) => (
                                            <th key={idx} className="px-3 py-2 text-center font-medium border-b border-border">
                                                {header}
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
                                            {columnKeys.map((colKey) => {
                                                const cellKey = `${fieldKey}.${row.key}.${colKey}`
                                                const cellValue = values[cellKey] ?? ""
                                                return (
                                                    <td key={colKey} className="px-2 py-1.5 border-b border-border">
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

            case "addList":
                const listContents = (field.contents as FormField[]) || []
                const rowCount = getRowCount(fieldKey)

                return (
                    <div key={fieldKey} className="space-y-2">
                        <div className="flex items-center justify-between">
                            <Label className="text-sm font-medium">{field.label}</Label>
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                className="gap-1 h-7 text-xs"
                                onClick={() => addRow(fieldKey)}
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
                                        {listContents.map((col) => (
                                            <th key={col.key} className="px-2 py-2 text-center font-medium border-b border-border whitespace-nowrap">
                                                {col.label}
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
                                            {listContents.map((col) => {
                                                const cellKey = `${fieldKey}.${rowIdx}.${col.key}`
                                                const cellValue = values[cellKey] ?? ""
                                                return (
                                                    <td key={col.key} className="px-1.5 py-1.5 border-b border-border">
                                                        <Input
                                                            value={cellValue}
                                                            onChange={(e) => onValueChange(cellKey, e.target.value)}
                                                            className="h-8"
                                                            placeholder={col.label}
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
                                                    onClick={() => removeRow(fieldKey, rowIdx)}
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

            default:
                return null
        }
    }

    const renderSection = (section: FormSection) => {
        // section 자체가 addList인 경우
        if (section.formType === "addList") {
            return renderField(section as unknown as FormField, "")
        }

        // contents가 없는 경우 section 자체를 단일 필드로 렌더링
        if (!section.contents || section.contents.length === 0) {
            if (section.formType) {
                return renderField(section as unknown as FormField, "")
            }
            return null
        }

        return (
            <div key={section.key} className="space-y-4">
                <h4 className="font-bold border-b border-gray-300 pb-2">{section.label}</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {section.contents.map((field) => {
                        // textarea, radio, checkbox, table, addList는 전체 너비
                        if (field.formType === "textarea" || field.formType === "radio" || field.formType === "checkbox" || field.formType === "table" || field.formType === "addList") {
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
            <CardHeader className="cursor-pointer" onClick={() => setIsOpen(!isOpen)}>
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{cardName}</CardTitle>
                    <Button variant="ghost" size="icon-sm">
                        {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </Button>
                </div>
            </CardHeader>

            <div className={cn("overflow-hidden transition-all duration-300", isOpen ? "opacity-100" : "max-h-0 opacity-0")}>
                <CardContent className="space-y-6">
                    {sections.map(renderSection)}

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
