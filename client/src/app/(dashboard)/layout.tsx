import type { ReactNode } from "react"
import { DashboardLayout } from "@/components/layouts/DashboardLayout"

interface DashboardLayoutWrapperProps {
    children: ReactNode
}

export default function DashboardLayoutWrapper({ children }: DashboardLayoutWrapperProps) {
    return <DashboardLayout>{children}</DashboardLayout>
}
