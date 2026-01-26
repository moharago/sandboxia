"use client"

import { useState } from "react"
import { ChevronDown, ChevronUp, Save } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils/cn"

interface FormField {
    key: string
    label: string
    formType: string
    contents?: FormField[] | RadioOption[]
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

            default:
                return null
        }
    }

    const renderSection = (section: FormSection) => {
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
                        // textarea는 전체 너비
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
