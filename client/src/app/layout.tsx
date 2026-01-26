import type { ReactNode } from "react"
import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import { QueryProvider } from "@/components/QueryProvider"
import { DevModeToggle } from "@/components/DevModeToggle"
import "./globals.css"

const geistSans = Geist({
    variable: "--font-geist-sans",
    subsets: ["latin"],
})

const geistMono = Geist_Mono({
    variable: "--font-geist-mono",
    subsets: ["latin"],
})

export const metadata: Metadata = {
    title: "SandboxIA",
    description: "규제 샌드박스 컨설팅 지원 시스템",
}

interface RootLayoutProps {
    children: ReactNode
}

export default function RootLayout({ children }: RootLayoutProps) {
    return (
        <html lang="ko" suppressHydrationWarning>
            <body className={`${geistSans.variable} ${geistMono.variable} antialiased`} suppressHydrationWarning>
                <QueryProvider>
                    {children}
                    <DevModeToggle />
                </QueryProvider>
            </body>
        </html>
    )
}
