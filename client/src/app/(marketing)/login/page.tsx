import { Suspense } from "react"
import { LoginForm, LoginFormFallback } from "@/components/features/login"

export default function LoginPage() {
    return (
        <div className="container mx-auto px-4 py-12">
            <div className="max-w-md mx-auto">
                <Suspense fallback={<LoginFormFallback />}>
                    <LoginForm />
                </Suspense>
            </div>
        </div>
    )
}
