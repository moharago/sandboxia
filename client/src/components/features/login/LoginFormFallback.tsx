import { Loader2 } from "lucide-react"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"

export function LoginFormFallback() {
    return (
        <Card>
            <CardHeader className="text-center">
                <CardTitle className="text-2xl">
                    <span className="text-gray-900">Sandbox</span>
                    <span className="text-teal-9">IA</span>
                </CardTitle>
                <CardDescription>규제 샌드박스 AI 컨설팅</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="flex items-center justify-center h-12">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
            </CardContent>
        </Card>
    )
}
