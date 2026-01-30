"use client"

import * as React from "react"
import { useDropzone, Accept, FileRejection } from "react-dropzone"
import { Upload, X, File } from "lucide-react"
import { cn } from "@/lib/utils/cn"
import { Button } from "./button"

export interface FileUploadProps {
    value?: File | null
    onChange?: (file: File | null) => void
    accept?: Accept
    maxSize?: number
    disabled?: boolean
    className?: string
}

export function FileUpload({
    value,
    onChange,
    accept = {
        "application/pdf": [".pdf"],
        "application/msword": [".doc"],
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
        "application/x-hwp": [".hwp"],
    },
    maxSize = 10 * 1024 * 1024, // 10MB
    disabled = false,
    className,
}: FileUploadProps) {
    const [error, setError] = React.useState<string | null>(null)

    const onDrop = React.useCallback(
        (acceptedFiles: File[], rejectedFiles: FileRejection[]) => {
            setError(null)

            if (rejectedFiles.length > 0) {
                const rejection = rejectedFiles[0]
                const errorCode = rejection.errors[0]?.code
                if (errorCode === "file-too-large") {
                    setError(`파일 크기는 ${Math.round(maxSize / 1024 / 1024)}MB 이하여야 합니다`)
                } else if (errorCode === "file-invalid-type") {
                    setError("지원하지 않는 파일 형식입니다")
                } else {
                    setError("파일 업로드에 실패했습니다")
                }
                return
            }

            if (acceptedFiles.length > 0) {
                onChange?.(acceptedFiles[0])
            }
        },
        [onChange, maxSize]
    )

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept,
        maxSize,
        maxFiles: 1,
        disabled,
    })

    const handleRemove = (e: React.MouseEvent) => {
        e.stopPropagation()
        onChange?.(null)
        setError(null)
    }

    const formatFileSize = (bytes: number) => {
        if (bytes < 1024) return `${bytes}B`
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
        return `${(bytes / 1024 / 1024).toFixed(1)}MB`
    }

    const hasFile = !!value
    const rootProps = hasFile ? {} : getRootProps()
    const inputProps = hasFile ? {} : getInputProps()

    return (
        <div className={className}>
            <div
                {...rootProps}
                className={cn(
                    "flex items-center justify-between rounded-lg p-4 transition-colors",
                    hasFile ? "border border-border bg-muted/30" : "border-2 border-dashed cursor-pointer",
                    !hasFile && isDragActive && "border-primary bg-primary/5",
                    !hasFile && !isDragActive && "border-border hover:border-primary/50",
                    disabled && "cursor-not-allowed opacity-50",
                    error && "border-destructive"
                )}
            >
                {!hasFile && <input {...inputProps} />}
                <div className="flex items-center gap-4 min-w-0">
                    {hasFile ? (
                        <File className="h-6 w-6 shrink-0 text-muted-foreground" />
                    ) : (
                        <Upload className="h-6 w-6 shrink-0 text-muted-foreground" />
                    )}
                    <div className="min-w-0 text-left">
                        {hasFile ? (
                            <>
                                <p className="text-sm font-medium truncate">{value.name}</p>
                                <p className="text-xs text-muted-foreground">{formatFileSize(value.size)}</p>
                            </>
                        ) : (
                            <div className="text-muted-foreground">
                                <p className="text-sm">{isDragActive ? "파일을 놓으세요" : "파일을 드래그하거나 클릭하여 업로드"}</p>
                                <p className="text-xs">PDF, DOCX, HWP</p>
                            </div>
                        )}
                    </div>
                </div>
                {hasFile ? (
                    <Button type="button" variant="ghost" size="sm" onClick={handleRemove} disabled={disabled} className="shrink-0">
                        <X className="h-4 w-4" />
                    </Button>
                ) : (
                    <Button type="button" variant="outline" size="sm" disabled={disabled}>
                        파일 선택
                    </Button>
                )}
            </div>
            {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
        </div>
    )
}
