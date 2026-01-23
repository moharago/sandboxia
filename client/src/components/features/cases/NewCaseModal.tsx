"use client";

import { useUIStore } from "@/stores";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Modal,
  ModalContent,
  ModalDescription,
  ModalFooter,
  ModalHeader,
  ModalTitle,
} from "@/components/ui/modal";
import { useState } from "react";

export function NewCaseModal() {
  const { isNewCaseModalOpen, closeNewCaseModal } = useUIStore();
  const [formData, setFormData] = useState({
    companyName: "",
    serviceName: "",
    description: "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Logic to handle submission (e.g., API call) would go here
    console.log("Submitting new case:", formData);
    closeNewCaseModal();
    // Reset form
    setFormData({ companyName: "", serviceName: "", description: "" });
  };

  return (
    <Modal open={isNewCaseModalOpen} onOpenChange={(open: boolean) => !open && closeNewCaseModal()}>
      <ModalContent className="sm:max-w-[500px]">
        <ModalHeader>
          <ModalTitle>새 케이스 생성</ModalTitle>
          <ModalDescription>
            새로운 샌드박스 신청 케이스를 생성합니다. 기본 정보를 입력해주세요.
          </ModalDescription>
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
                setFormData({ ...formData, companyName: e.target.value })
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
                setFormData({ ...formData, serviceName: e.target.value })
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
                setFormData({ ...formData, description: e.target.value })
              }
              rows={4}
            />
          </div>
          <ModalFooter>
            <Button
              type="button"
              variant="outline"
              onClick={closeNewCaseModal}
            >
              취소
            </Button>
            <Button type="submit">생성하기</Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  );
}
