'use client';

import { User, Building2, Mail, Phone, Shield, Bell } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { ToggleSwitch } from '@/components/ui/toggle-switch';

export default function MyAccountPage() {
  return (
    <div className="p-6">
      <div className="max-w-2xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold mb-2">마이페이지</h1>
          <p className="text-muted-foreground">계정 정보를 관리하세요</p>
        </div>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <User className="h-5 w-5 text-muted-foreground" />
              <CardTitle>기본 정보</CardTitle>
            </div>
            <CardDescription>계정의 기본 정보를 수정합니다</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">이름</Label>
                <Input id="name" defaultValue="홍길동" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">이메일</Label>
                <Input id="email" type="email" defaultValue="hong@company.com" />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="phone">연락처</Label>
                <Input id="phone" type="tel" defaultValue="010-1234-5678" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="position">직책</Label>
                <Input id="position" defaultValue="대표이사" />
              </div>
            </div>
            <Button>정보 저장</Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-muted-foreground" />
              <CardTitle>회사 정보</CardTitle>
            </div>
            <CardDescription>소속 회사 정보를 수정합니다</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="company">회사명</Label>
              <Input id="company" defaultValue="스마트모빌리티" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="businessNumber">사업자등록번호</Label>
                <Input id="businessNumber" defaultValue="123-45-67890" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="industry">업종</Label>
                <Input id="industry" defaultValue="모빌리티" />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="address">주소</Label>
              <Input id="address" defaultValue="서울시 강남구 테헤란로 123" />
            </div>
            <Button>정보 저장</Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Bell className="h-5 w-5 text-muted-foreground" />
              <CardTitle>알림 설정</CardTitle>
            </div>
            <CardDescription>알림 수신 설정을 관리합니다</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ToggleSwitch
              id="emailNotification"
              label="이메일 알림"
              description="케이스 진행 상황을 이메일로 받습니다"
              defaultChecked
            />
            <ToggleSwitch
              id="smsNotification"
              label="SMS 알림"
              description="중요 알림을 SMS로 받습니다"
            />
            <ToggleSwitch
              id="marketingNotification"
              label="마케팅 정보 수신"
              description="SandboxIA의 새로운 소식을 받습니다"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-muted-foreground" />
              <CardTitle>보안 설정</CardTitle>
            </div>
            <CardDescription>비밀번호를 변경합니다</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="currentPassword">현재 비밀번호</Label>
              <Input id="currentPassword" type="password" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="newPassword">새 비밀번호</Label>
              <Input id="newPassword" type="password" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">비밀번호 확인</Label>
              <Input id="confirmPassword" type="password" />
            </div>
            <Button>비밀번호 변경</Button>
          </CardContent>
        </Card>

        <Card className="border-destructive/20">
          <CardHeader>
            <CardTitle className="text-destructive">계정 삭제</CardTitle>
            <CardDescription>
              계정을 삭제하면 모든 데이터가 영구적으로 삭제됩니다
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="destructive">계정 삭제</Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
