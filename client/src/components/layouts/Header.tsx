"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { Menu, X, User, LogOut, Settings } from "lucide-react"
import * as DropdownMenu from "@radix-ui/react-dropdown-menu"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils/cn"
import { createClient } from "@/lib/supabase/client"
import { useUserStore } from "@/stores/user-store"
import { useUIStore } from "@/stores/ui-store"

interface NavItem {
    label: string
    href: string
}

const navItems: NavItem[] = []

export function Header() {
    const pathname = usePathname()
    const router = useRouter()
    const supabase = createClient()
    const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false)
    const user = useUserStore((state) => state.user)
    const setUser = useUserStore((state) => state.setUser)
    const { devMode, isAuthenticated: devAuthenticated } = useUIStore()

    // 세션 체크 및 user-store 동기화
    React.useEffect(() => {
        const syncUser = async () => {
            // devMode + 임시 로그인 상태면 건너뛰기
            if (devMode && devAuthenticated) return

            const { data: { session } } = await supabase.auth.getSession()

            if (session && !user) {
                // 세션은 있는데 user-store가 비어있으면 API 호출
                try {
                    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
                    const response = await fetch(`${apiBaseUrl}/api/users/me`, {
                        headers: {
                            'Authorization': `Bearer ${session.access_token}`
                        }
                    })
                    if (response.ok) {
                        const userData = await response.json()
                        setUser({
                            email: userData.email || session.user.email,
                            name: userData.name || session.user.user_metadata?.full_name || session.user.user_metadata?.name || session.user.email?.split('@')[0],
                            company: userData.company,
                            phone: userData.phone
                        })
                    }
                } catch {
                    // 서버 연결 실패 시 기본 정보로 설정
                    setUser({
                        email: session.user.email || '',
                        name: session.user.user_metadata?.full_name || session.user.user_metadata?.name || session.user.email?.split('@')[0] || '',
                        company: null,
                        phone: null
                    })
                }
            }
        }

        syncUser()

        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
            // devMode + 임시 로그인 상태면 user 초기화하지 않음
            if (!session && !(devMode && devAuthenticated)) {
                setUser(null)
            }
        })

        return () => subscription.unsubscribe()
    }, [supabase.auth, setUser, devMode, devAuthenticated, user])

    const handleLogout = async () => {
        await supabase.auth.signOut()
        setUser(null)
        router.push('/')
    }

    const isAuthenticated = user !== null
    const userName = user?.name || '사용자'

    return (
        <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="container mx-auto flex h-16 items-center justify-between px-4">
                <div className="flex items-center gap-8">
                    <Link href="/" className="flex items-center gap-2">
                        <span className="text-xl font-bold">
                            <span className="text-gray-900">Sandbox</span>
                            <span className="text-teal-9">IA</span>
                        </span>
                    </Link>

                    <nav className="hidden md:flex items-center gap-6">
                        {navItems.map((item) => (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    "text-sm font-medium transition-colors hover:text-primary",
                                    pathname === item.href ? "text-primary" : "text-muted-foreground"
                                )}
                            >
                                {item.label}
                            </Link>
                        ))}
                    </nav>
                </div>

                <div className="hidden md:flex items-center gap-4">
                    {isAuthenticated ? (
                        <>
                            <Link href="/dashboard">
                                <Button variant="ghost" size="sm">
                                    대시보드
                                </Button>
                            </Link>
                            <DropdownMenu.Root>
                                <DropdownMenu.Trigger asChild>
                                    <Button variant="outline" size="sm" className="gap-2">
                                        <User className="h-4 w-4" />
                                        {userName}
                                    </Button>
                                </DropdownMenu.Trigger>
                                <DropdownMenu.Portal>
                                    <DropdownMenu.Content
                                        className="min-w-[115px] rounded-md border border-neutral-200 bg-popover p-1 shadow-md z-100"
                                        align="end"
                                        sideOffset={4}
                                    >
                                        <DropdownMenu.Item asChild>
                                            <Link
                                                href="/my-account"
                                                className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent"
                                            >
                                                <Settings className="h-4 w-4" />
                                                마이페이지
                                            </Link>
                                        </DropdownMenu.Item>
                                        <DropdownMenu.Separator className="my-1 h-px bg-border" />
                                        <DropdownMenu.Item
                                            className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-destructive outline-none hover:bg-accent"
                                            onClick={handleLogout}
                                        >
                                            <LogOut className="h-4 w-4" />
                                            로그아웃
                                        </DropdownMenu.Item>
                                    </DropdownMenu.Content>
                                </DropdownMenu.Portal>
                            </DropdownMenu.Root>
                        </>
                    ) : (
                        <Link href="/login">
                            <Button variant="gradient" size="sm">
                                로그인
                            </Button>
                        </Link>
                    )}
                </div>

                <button className="md:hidden p-2" onClick={() => setMobileMenuOpen(!mobileMenuOpen)} aria-label="메뉴 토글">
                    {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
                </button>
            </div>

            {mobileMenuOpen && (
                <div className="md:hidden border-t border-border">
                    <nav className="container mx-auto px-4 py-4 flex flex-col gap-2">
                        {navItems.map((item) => (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    "py-2 text-sm font-medium transition-colors",
                                    pathname === item.href ? "text-primary" : "text-muted-foreground"
                                )}
                                onClick={() => setMobileMenuOpen(false)}
                            >
                                {item.label}
                            </Link>
                        ))}
                        <div className="flex flex-col gap-2 pt-4 border-t border-border mt-2">
                            {isAuthenticated ? (
                                <>
                                    <Link href="/dashboard">
                                        <Button variant="outline" className="w-full">
                                            대시보드
                                        </Button>
                                    </Link>
                                    <Button variant="destructive" className="w-full" onClick={handleLogout}>
                                        로그아웃
                                    </Button>
                                </>
                            ) : (
                                <Link href="/login">
                                    <Button variant="gradient" className="w-full">
                                        로그인
                                    </Button>
                                </Link>
                            )}
                        </div>
                    </nav>
                </div>
            )}
        </header>
    )
}
