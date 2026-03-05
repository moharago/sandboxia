# Application Drafter Agent

신청서 초안 생성 에이전트. Canonical 구조를 입력받아 트랙별 신청서 폼을 생성합니다.

## 핵심 원칙: 문서 기반 생성

**"원본에 없는 내용은 만들지 않는다"**

신청서는 법적 문서이므로, AI가 임의로 내용을 생성하면 안 됩니다.
단, 일부 필드는 사용자 편의를 위해 AI 추론을 허용하되, 반드시 마킹합니다.

---

## 필드별 생성 원칙

### 1. 데이터 레이어 구분

| 레이어 | 설명 | 예시 |
|--------|------|------|
| `canonical` (application_input) | 원본 문서에서 추출한 데이터 | HWP 파싱 결과 |
| `draft` (application_draft) | 초안 생성 결과 | 폼에 채워질 값 |

### 2. 필드 유형별 처리

#### A. 서술형 설명 필드
- **canonical**: 원본 그대로 저장
- **draft**: AI가 다듬기 OK (문장 정리, 형식 맞춤)
- **예시**: `detailedDescription`, `regulationDetails`, `technologyServiceDetails`

#### B. 메타데이터 필드 (행정 정보)
- **canonical**: 원본에서 추출 or null (추론 금지)
- **draft**: canonical 값 그대로 사용 (생성 금지)
- **예시**: `expected_agency` (소관 부처), `expected_permit` (예상 허가)
- **이유**: 행정 주체 식별 정보는 문서에 명시된 값만 사용해야 함

#### C. 원본에 없는 필드 (트랙 변환 시)
- **canonical**: null
- **draft**: AI 추론 생성 허용
- **마킹**: `"generated_by": "ai"` 필수
- **톤 제한**: "확인 필요", "검토 요청" 수준 (확정 표현 금지)
- **예시**: `additional_questions` (임시허가 → 신속확인 변환 시)

### 3. 필드 유형 전체 목록

#### 메타데이터 (생성 금지) - 문서에 없으면 null

| 필드 | 설명 | 이유 |
|------|------|------|
| `expected_agency` / `expectedGoverningAgency` | 소관 부처 | 행정 주체 식별 |
| `expected_permit` / `expectedPermitOrApproval` | 예상 허가등 | 법적 근거 |
| `companyName` | 회사명 | 법인 식별 |
| `representativeName` | 대표자명 | 법인 대표 |
| `businessRegistrationNumber` | 사업자등록번호 | 법적 식별자 |
| `address` | 주소 | 사실 정보 |
| `phoneNumber` | 전화번호 | 사실 정보 |
| `email` | 이메일 | 사실 정보 |
| `applicationDate` | 신청일자 | 법적 날짜 |
| `receiptNumber` | 접수번호 | 행정 식별자 |
| `receiptDate` | 접수일시 | 행정 날짜 |
| `applicantSignature` | 신청인 서명 | 법적 서명 |
| `submissionDate` | 제출일자 | 법적 날짜 |

#### 숫자/사실 정보 (생성 금지) - 문서에 없으면 null

| 필드 | 설명 | 이유 |
|------|------|------|
| `totalAssets` | 총자산 | 재무 사실 |
| `equity` | 자기자본 | 재무 사실 |
| `totalRevenue` | 총매출액 | 재무 사실 |
| `netIncome` | 당기순이익 | 재무 사실 |
| `debtRatio` | 부채비율 | 재무 사실 |
| `currentAssets` / `currentLiabilities` | 유동자산/부채 | 재무 사실 |
| `fixedLiabilities` | 고정부채 | 재무 사실 |
| `totalEmployees` | 총 직원 수 | 사실 정보 |
| `durationMonths` | 사업 기간 (개월) | 계획 숫자 |
| `startDate` / `endDate` | 사업 시작/종료일 | 계획 날짜 |

#### 서술형 필드 (AI 다듬기 OK)

| 필드 | 설명 |
|------|------|
| `detailedDescription` | 기술·서비스 세부 내용 |
| `technologyServiceDetails` | 기술·서비스 세부내용 (신속확인) |
| `regulationDetails` | 규제 내용 |
| `legalIssues` | 법·제도 이슈 사항 (신속확인) |
| `necessityAndRequest` | 규제특례 필요성 및 내용 |
| `marketStatusAndOutlook` | 시장 현황 및 전망 |
| `objectivesAndScope` | 사업 목표 및 범위 |
| `businessContent` | 사업 내용 |
| `schedule` | 기간 및 일정 계획 |
| `operationPlan` | 운영 계획 |
| `quantitativeEffect` | 정량적 기대효과 |
| `qualitativeEffect` | 정성적 기대효과 |
| `expansionPlan` | 확대·확산 계획 |
| `restorationPlan` | 실증 후 복구 계획 |
| `organizationStructure` | 추진 체계 |
| `budget` | 추진 예산 |
| `safetyVerification` | 안전성 검증 자료 |
| `userProtectionPlan` | 이용자 보호 방안 |
| `riskAndResponse` | 위험 및 대응 방안 |
| `stakeholderConflictResolution` | 이해관계 충돌 해소 방안 |
| `justification` | 해당여부에 대한 근거 |

#### AI 추론 생성 (마킹 필수)

| 필드 | 조건 | 마킹 |
|------|------|------|
| `additionalQuestions` | 임시허가/실증특례 → 신속확인 변환 시 | `generated_by: "ai"` |
| `temporaryPermitReason` | 신속확인 → 임시허가 변환 시 | `generated_by: "ai"` |
| `regulatoryExemptionReason` | 신속확인 → 실증특례 변환 시 | `generated_by: "ai"` |

---

## 트랙 변환 매트릭스 (9가지 케이스)

### 변환 유형 요약

| 입력 ↓ / 출력 → | 신속확인 | 임시허가 | 실증특례 |
|-----------------|----------|----------|----------|
| **신속확인** | 동일 트랙 | 크로스 변환 | 크로스 변환 |
| **임시허가** | 크로스 변환 | 동일 트랙 | 유사 트랙 |
| **실증특례** | 크로스 변환 | 유사 트랙 | 동일 트랙 |

---

### 1. 동일 트랙 (신속확인/임시허가/실증특례 모두 동일)

| 필드 유형 | 처리 |
|-----------|------|
| 메타데이터/숫자 | 원본 그대로 사용 |
| 서술형 필드 | 원본 기반 + AI 다듬기 (말투, 형식 정리) |

---

### 2. 유사 트랙 (임시허가 ↔ 실증특례)

임시허가와 실증특례는 폼 구조가 거의 동일하여 1:1 매핑됩니다.

#### 임시허가 → 실증특례
| 내용 | 원본 필드 | 대상 필드 | 처리 |
|------|-----------|-----------|------|
| 기술·서비스 세부내용 | `detailedDescription` | `detailedDescription` | 원본 사용 |
| 규제 내용 | `regulationDetails` | `regulationDetails` | 원본 사용 |
| 규제특례 필요성 및 내용 | `necessityAndRequest` | `necessityAndRequest` | 원본 사용 |
| 소관 부처 | `expected_agency` | `expected_agency` | 원본 사용 |
| 예상 허가등 | `expected_permit` | `expected_permit` | 원본 사용 |
| 임시허가 사유 → 실증특례 사유 | `temporaryPermitReason` | `regulatoryExemptionReason` | 매핑 변환 |

#### 실증특례 → 임시허가
| 내용 | 원본 필드 | 대상 필드 | 처리 |
|------|-----------|-----------|------|
| 기술·서비스 세부내용 | `detailedDescription` | `detailedDescription` | 원본 사용 |
| 규제 내용 | `regulationDetails` | `regulationDetails` | 원본 사용 |
| 규제특례 필요성 및 내용 | `necessityAndRequest` | `necessityAndRequest` | 원본 사용 |
| 소관 부처 | `expected_agency` | `expected_agency` | 원본 사용 |
| 예상 허가등 | `expected_permit` | `expected_permit` | 원본 사용 |
| 실증특례 사유 → 임시허가 사유 | `regulatoryExemptionReason` | `temporaryPermitReason` | 매핑 변환 |

---

### 3. 크로스 변환 (신속확인 ↔ 임시허가/실증특례)

폼 구조가 다르므로 필드 매핑이 필요합니다.

#### 신속확인 → 임시허가

| 내용 | 원본 필드 | 대상 필드 | 처리 |
|------|-----------|-----------|------|
| 기술·서비스 세부내용 | `technologyServiceDetails` | `detailedDescription` | 원본 사용 |
| 법·제도 이슈 → 규제 내용 | `legalIssues` | `regulationDetails` | 원본 사용 |
| 기타 질의 → 규제특례 필요성 | `additionalQuestions` | `necessityAndRequest` | 참고용 (AI 다듬기) |
| 소관 부처 | `expectedGoverningAgency` | `expected_agency` | 원본 사용 |
| 예상 허가등 | `expectedPermitOrApproval` | `expected_permit` | 원본 사용 |
| 임시허가 사유 | (없음) | `temporaryPermitReason` | AI 추론 + 마킹 |

#### 신속확인 → 실증특례

| 내용 | 원본 필드 | 대상 필드 | 처리 |
|------|-----------|-----------|------|
| 기술·서비스 세부내용 | `technologyServiceDetails` | `detailedDescription` | 원본 사용 |
| 법·제도 이슈 → 규제 내용 | `legalIssues` | `regulationDetails` | 원본 사용 |
| 기타 질의 → 규제특례 필요성 | `additionalQuestions` | `necessityAndRequest` | 참고용 (AI 다듬기) |
| 소관 부처 | `expectedGoverningAgency` | `expected_agency` | 원본 사용 |
| 예상 허가등 | `expectedPermitOrApproval` | `expected_permit` | 원본 사용 |
| 실증특례 사유 | (없음) | `regulatoryExemptionReason` | AI 추론 + 마킹 |

#### 임시허가 → 신속확인

| 내용 | 원본 필드 | 대상 필드 | 처리 |
|------|-----------|-----------|------|
| 기술·서비스 세부내용 | `detailedDescription` | `technologyServiceDetails` | 원본 사용 |
| 규제 내용 → 법·제도 이슈 | `regulationDetails` | `legalIssues` | 원본 사용 |
| 소관 부처 | `expected_agency` | `expectedGoverningAgency` | 원본 사용 |
| 예상 허가등 | `expected_permit` | `expectedPermitOrApproval` | 원본 사용 |
| 규제특례 필요성 | `necessityAndRequest` | (참고용) | AI 다듬기 |
| 기타 질의 사항 | (없음) | `additionalQuestions` | **AI 추론 + 마킹** |

#### 실증특례 → 신속확인

| 내용 | 원본 필드 | 대상 필드 | 처리 |
|------|-----------|-----------|------|
| 기술·서비스 세부내용 | `detailedDescription` | `technologyServiceDetails` | 원본 사용 |
| 규제 내용 → 법·제도 이슈 | `regulationDetails` | `legalIssues` | 원본 사용 |
| 소관 부처 | `expected_agency` | `expectedGoverningAgency` | 원본 사용 |
| 예상 허가등 | `expected_permit` | `expectedPermitOrApproval` | 원본 사용 |
| 규제특례 필요성 | `necessityAndRequest` | (참고용) | AI 다듬기 |
| 기타 질의 사항 | (없음) | `additionalQuestions` | **AI 추론 + 마킹** |

---

## AI 생성 마킹 규칙

```python
# AI가 추론 생성한 필드는 반드시 마킹
{
    "additionalQuestions": {
        "value": "본 서비스의 규제 적용 범위에 대해 확인을 요청드립니다...",
        "generated_by": "ai",
        "confidence": "low",
        "tone": "inquiry"  # 확인/검토 요청 톤
    }
}
```

### 톤 가이드라인

| 허용 | 금지 |
|------|------|
| "~에 대해 확인을 요청합니다" | "~입니다" (단정) |
| "~여부를 검토해주시기 바랍니다" | "~해야 합니다" (의무) |
| "~가능성이 있어 문의드립니다" | "~없습니다" (부정 단언) |

---

## 코드 참조

- 패턴 정의: `app/services/parsers/hwp_patterns.py`
- 필드 매핑: `app/agents/application_drafter/nodes.py` (`_apply_section_texts`)
- 프롬프트: `app/agents/application_drafter/prompts.py`
