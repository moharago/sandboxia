import { AlertCircle } from "lucide-react"
import { Button } from "./button"

interface NoResultsViewProps {
    title?: string
    description?: string
    buttonLabel?: string
    onNavigate: () => void
}

export function NoResultsView({ title = "분석 결과가 없습니다", description, buttonLabel = "현재 단계로 이동하기", onNavigate }: NoResultsViewProps) {
    return (
        <div className="py-6">
            <div className="container">
                <div className="flex items-center justify-center min-h-[400px]">
                    <div className="text-center space-y-4">
                        <AlertCircle className="h-12 w-12 mx-auto text-amber-500" />
                        <h2 className="text-lg font-semibold">{title}</h2>
                        {description && <p className="text-muted-foreground">{description}</p>}
                        <Button onClick={onNavigate}>{buttonLabel}</Button>
                    </div>
                </div>
            </div>
        </div>
    )
}
