/**
 * Step 4 (신청서 초안) 폼 스키마 타입 정의
 */

export interface FieldOption {
    id: string
    label: string
    value: string
}

export interface FormField {
    key: string
    label: string
    formType: string
    dataType: string
    required: boolean
    options?: FieldOption[]
}

export interface TableColumn {
    key: string
    label: string
}

export interface TableRow {
    key: string
    label: string
    dataType: string
}

export interface FormSection {
    key: string
    label: string
    fields?: FormField[]
    isArray?: boolean
    isTable?: boolean
    columns?: TableColumn[]
    rows?: TableRow[]
}

export interface FormSchema {
    formId: string
    formName: string
    version: string
    sections: FormSection[]
}
