"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card"

export default function SignupPage() {
    return (
        <div className="container mx-auto px-4 py-12">
            <div className="max-w-md mx-auto">
                <Card>
                    <CardHeader className="text-center">
                        <CardTitle className="text-2xl">회원가입</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <form className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="company">회사명</Label>
                                <Input id="company" placeholder="회사명을 입력하세요" />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="name">담당자명</Label>
                                <Input id="name" placeholder="이름을 입력하세요" />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="email">이메일</Label>
                                <Input id="email" type="email" placeholder="example@company.com" />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="password">비밀번호</Label>
                                <Input id="password" type="password" placeholder="8자 이상 입력하세요" />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="passwordConfirm">비밀번호 확인</Label>
                                <Input id="passwordConfirm" type="password" placeholder="비밀번호를 다시 입력하세요" />
                            </div>
                            <Button type="submit" className="w-full" variant="gradient">
                                가입하기
                            </Button>
                        </form>
                    </CardContent>
                    <CardFooter className="justify-center">
                        <p className="text-sm text-muted-foreground">
                            이미 계정이 있으신가요?{" "}
                            <Link href="/login" className="text-primary hover:underline">
                                로그인
                            </Link>
                        </p>
                    </CardFooter>
                </Card>
            </div>
        </div>
    )
}
