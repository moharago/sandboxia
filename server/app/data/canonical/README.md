# Canonical Schema

규제 샌드박스 신청서의 표준화된 데이터 구조 정의입니다.

## 파일 구조

```
canonical/
├── schema.json     # canonical 필드 정의 (JSON Schema)
├── mapping.json    # canonical → draft 매핑 규칙
└── README.md       # 이 파일
```

## 데이터 흐름

```
HWP 파일
    ↓ hwp_parser.py
parsed_data (extracted_fields)
    ↓ merge_parsed_documents()
merged_hwp_data
    ↓ service_structurer (LLM)
canonical ←────────────── schema.json 참조
    ↓ application_drafter
draft ←────────────────── mapping.json 참조
    ↓
클라이언트 폼 표시
```

## schema.json

canonical 구조의 모든 필드를 JSON Schema 형식으로 정의합니다.

### 주요 섹션

| 섹션 | 설명 | 소스 |
|------|------|------|
| `company` | 회사/신청인 기본 정보 | HWP 신청서 |
| `service` | 신규 기술·서비스 정보 | HWP 신청서 |
| `technology` | 기술/혁신 정보 | HWP 신청서 |
| `regulatory` | 규제 관련 정보 | HWP 신청서 |
| `financial` | 재무현황 | HWP 붙임 테이블 |
| `hr` | 인력현황 | HWP 붙임 테이블 |
| `project_plan` | 사업/실증 계획 | HWP 사업계획서 |
| `applicants` | 신청기관 및 서명 | HWP 신청서 |
| `section_texts` | 섹션별 원문 텍스트 | HWP 각 섹션 |
| `form_selections` | 체크박스/라디오 선택값 | HWP 파서 |
| `metadata` | 메타데이터 | 시스템 생성 |

### 키 이름 규칙

- **canonical**: snake_case (예: `company_name`, `business_number`)
- **draft**: camelCase (예: `companyName`, `businessRegistrationNumber`)

## mapping.json

canonical 필드가 draft의 어떤 필드로 매핑되는지 정의합니다.

### 매핑 유형

1. **직접 매핑**: canonical 값을 그대로 복사
   ```
   canonical.company.company_name → draft.applicant.companyName
   ```

2. **키 변환**: snake_case → camelCase
   ```
   canonical.hr.keyPersonnel[].qualifications → draft.keyPersonnel[].qualificationsOrSkills
   ```

3. **구조 변환**: 데이터 구조 변경
   ```
   canonical.financial.yearM2.totalAssets → draft.financialStatus.totalAssets.yearM2
   (연도 기준 → 항목 기준으로 전치)
   ```

4. **AI 생성**: 원본에 없는 필드
   ```
   신속확인 → 실증특례: justification 필드 AI 생성
   ```

## 사용법

### prompts.py에서 참조

```python
# schema.json의 구조를 프롬프트에 반영
OUTPUT_SCHEMA = """
{
  "company": { "company_name", "representative", ... },
  ...
}
"""
```

### nodes.py에서 매핑

```python
# mapping.json의 규칙을 코드로 구현
def _merge_passthrough_data(draft: dict, canonical: dict) -> dict:
    company = canonical.get("company", {})
    # canonical.company.company_name → draft.applicant.companyName
    if company.get("company_name"):
        draft["applicant"]["companyName"] = company["company_name"]
```

## 새 필드 추가 시

1. `schema.json`에 필드 정의 추가
2. `mapping.json`에 매핑 규칙 추가
3. `hwp_patterns.py`에 파싱 패턴 추가 (필요시)
4. `prompts.py`에 프롬프트 업데이트
5. `nodes.py`에 매핑 코드 추가

## 문제 발생 시 체크리스트

데이터가 빈칸으로 나오면:

1. [ ] `schema.json`에 필드가 정의되어 있는가?
2. [ ] `hwp_patterns.py`에 파싱 패턴이 있는가?
3. [ ] `hwp_parser.py`의 `merge_parsed_documents()`에서 매핑되는가?
4. [ ] `prompts.py`의 출력 스키마에 포함되어 있는가?
5. [ ] `nodes.py`에서 올바른 경로로 읽는가?
6. [ ] 키 이름이 일치하는가? (snake_case vs camelCase)
