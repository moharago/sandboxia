import { LoginForm } from "@/components/features/login/LoginForm"
import { LoginFormFallback } from "@/components/features/login/LoginFormFallback"
import { Suspense } from "react"

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
