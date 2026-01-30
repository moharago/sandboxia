"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Modal, ModalContent, ModalDescription, ModalFooter, ModalHeader, ModalTitle } from "@/components/ui/modal"
import { Textarea } from "@/components/ui/textarea"
import { useCreateProjectMutation } from "@/hooks/mutations/use-create-project-mutation"
import { useAuthStore } from "@/stores/auth-store"
import { useUIStore } from "@/stores/ui-store"
import { useRouter } from "next/navigation"
import { useState } from "react"

export function NewCaseModal() {
    const router = useRouter()
    const user = useAuthStore((state) => state.user)
    const { isNewCaseModalOpen, closeNewCaseModal } = useUIStore()
    const [formData, setFormData] = useState({
        companyName: "",
        serviceName: "",
        description: "",
    })

    const { mutate: createProject, isPending } = useCreateProjectMutation({
        onSuccess: (data) => {
            closeNewCaseModal()
            setFormData({ companyName: "", serviceName: "", description: "" })
            router.push(`/projects/${data.id}/structure`)
        },
        onError: (error) => {
            alert(`프로젝트 생성 실패: ${error.message}`)
        },
    })

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()

        if (!user) {
            alert("로그인이 필요합니다.")
            return
        }

        createProject({
            user_id: user.id,
            company_name: formData.companyName,
            service_name: formData.serviceName || undefined,
            service_description: formData.description || undefined,
        })
    }

    return (
        <Modal open={isNewCaseModalOpen} onOpenChange={(open: boolean) => !open && closeNewCaseModal()}>
            <ModalContent className="sm:max-w-[500px]">
                <ModalHeader>
                    <ModalTitle>새 프로젝트 생성</ModalTitle>
                    <ModalDescription>새로운 샌드박스 신청 프로젝트를 생성합니다. 기본 정보를 입력해주세요.</ModalDescription>
                </ModalHeader>
                <form onSubmit={handleSubmit} className="space-y-4 py-4">
                    <div className="space-y-2">
                        <label htmlFor="companyName" className="text-sm font-medium">
                            기업명
                        </label>
                        <Input
                            id="companyName"
                            placeholder="기업명을 입력하세요"
                            value={formData.companyName}
                            onChange={(e) =>
                                setFormData({
                                    ...formData,
                                    companyName: e.target.value,
                                })
                            }
                            required
                        />
                    </div>
                    <div className="space-y-2">
                        <label htmlFor="serviceName" className="text-sm font-medium">
                            서비스명
                        </label>
                        <Input
                            id="serviceName"
                            placeholder="서비스명을 입력하세요"
                            value={formData.serviceName}
                            onChange={(e) =>
                                setFormData({
                                    ...formData,
                                    serviceName: e.target.value,
                                })
                            }
                            required
                        />
                    </div>
                    <div className="space-y-2">
                        <label htmlFor="description" className="text-sm font-medium">
                            설명
                        </label>
                        <Textarea
                            id="description"
                            placeholder="서비스에 대한 간단한 설명을 입력하세요"
                            value={formData.description}
                            onChange={(e) =>
                                setFormData({
                                    ...formData,
                                    description: e.target.value,
                                })
                            }
                            rows={4}
                        />
                    </div>
                    <ModalFooter>
                        <Button type="button" variant="outline" onClick={closeNewCaseModal} disabled={isPending}>
                            취소
                        </Button>
                        <Button type="submit" disabled={isPending}>
                            {isPending ? "생성 중..." : "생성하기"}
                        </Button>
                    </ModalFooter>
                </form>
            </ModalContent>
        </Modal>
    )
}
