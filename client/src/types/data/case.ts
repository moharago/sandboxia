export type CaseStatus = "consult" | "draft" | "waiting" | "done" | "direct";
export type CaseStage = 1 | 2 | 3 | 4;

export interface Case {
  id: string;
  company: string;
  service: string;
  status: CaseStatus;
  stage: CaseStage;
  progress: number;
  description?: string;
  createdAt: string;
  updatedAt: string;
  sandboxType?: SandboxType;
}

export const CASE_STATUS_LABELS: Record<CaseStatus, string> = {
  consult: "기업상담",
  draft: "신청서작성",
  waiting: "결과대기",
  done: "완료",
  direct: "바로출시",
};

export const CASE_STAGE_LABELS: Record<CaseStage, string> = {
  1: "기업 정보 입력",
  2: "시장출시 진단",
  3: "트랙 선택",
  4: "신청서 작성",
};

export type SandboxType = "demonstration" | "temporary" | "rapid";

export const SANDBOX_TYPE_LABELS: Record<SandboxType, string> = {
  demonstration: "실증특례",
  temporary: "임시허가",
  rapid: "신속확인",
};
