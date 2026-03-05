"use client"

import { useEditor, EditorContent } from "@tiptap/react"
import StarterKit from "@tiptap/starter-kit"
import Placeholder from "@tiptap/extension-placeholder"
import { useEffect, useRef, useState } from "react"
import { Undo, Redo } from "lucide-react"
import { cn } from "@/lib/utils/cn"

interface TiptapEditorProps {
    content: string
    onChange: (content: string) => void
    placeholder?: string
    className?: string
    editable?: boolean
}

export function TiptapEditor({
    content,
    onChange,
    placeholder = "내용을 입력하세요...",
    className,
    editable = true,
}: TiptapEditorProps) {
    const editor = useEditor({
        extensions: [
            StarterKit.configure({
                heading: false,
                codeBlock: false,
                blockquote: false,
                horizontalRule: false,
                bold: false,
                italic: false,
                bulletList: false,
                orderedList: false,
            }),
            Placeholder.configure({
                placeholder,
                emptyEditorClass: "is-editor-empty",
            }),
        ],
        content: content || "",
        editable,
        immediatelyRender: false,
        onUpdate: ({ editor }) => {
            const text = editor.getText()
            onChange(text)
        },
        editorProps: {
            attributes: {
                class: "prose prose-sm max-w-none focus:outline-none min-h-[120px] px-3 py-2",
            },
        },
    })

    // Undo/Redo 가능 상태 추적
    const [canUndo, setCanUndo] = useState(false)
    const [canRedo, setCanRedo] = useState(false)
    const isExternalUpdate = useRef(false)

    // 외부에서 content가 변경되면 에디터 업데이트
    useEffect(() => {
        if (editor && content !== editor.getText()) {
            isExternalUpdate.current = true
            editor.commands.setContent(content || "", { emitUpdate: false })
            // 외부 업데이트 후에는 undo/redo 비활성화
            setCanUndo(false)
            setCanRedo(false)
            setTimeout(() => {
                isExternalUpdate.current = false
            }, 100)
        }
    }, [content, editor])

    // 에디터 상태 변화 감지
    useEffect(() => {
        if (!editor) return

        const updateUndoRedo = () => {
            // 외부 업데이트 중이 아닐 때만 상태 갱신
            if (!isExternalUpdate.current) {
                setCanUndo(editor.can().undo())
                setCanRedo(editor.can().redo())
            }
        }

        editor.on("transaction", updateUndoRedo)
        return () => {
            editor.off("transaction", updateUndoRedo)
        }
    }, [editor])

    // 에디터가 없으면 로딩 표시
    if (!editor) {
        return (
            <div className={cn("border border-input rounded-md bg-background min-h-[120px]", className)}>
                <div className="px-3 py-2 text-muted-foreground text-sm">로딩 중...</div>
            </div>
        )
    }

    return (
        <div className={cn("border border-input rounded-md bg-background overflow-hidden", className)}>
            {/* Undo/Redo 툴바 */}
            <div className="flex items-center justify-start gap-1 px-2 py-1 border-b border-input bg-muted/30">
                <button
                    type="button"
                    onClick={() => editor.chain().focus().undo().run()}
                    disabled={!canUndo}
                    title="실행 취소 (Ctrl+Z)"
                    className={cn(
                        "p-1.5 rounded hover:bg-accent transition-colors",
                        !canUndo && "opacity-50 cursor-not-allowed"
                    )}
                >
                    <Undo className="h-4 w-4" />
                </button>
                <button
                    type="button"
                    onClick={() => editor.chain().focus().redo().run()}
                    disabled={!canRedo}
                    title="다시 실행 (Ctrl+Y)"
                    className={cn(
                        "p-1.5 rounded hover:bg-accent transition-colors",
                        !canRedo && "opacity-50 cursor-not-allowed"
                    )}
                >
                    <Redo className="h-4 w-4" />
                </button>
            </div>
            <EditorContent editor={editor} />
        </div>
    )
}
