# DB 스키마 ↔ 화면 매핑 가이드

> SandboxIA 규제 샌드박스 컨설팅 플랫폼

---

## 📋 테이블 구조 요약

| 테이블                | 용도             | 주요 화면                         |
| --------------------- | ---------------- | --------------------------------- |
| `users`               | 사용자 정보      | 로그인, 추가정보 입력, 마이페이지 |
| `projects`            | 프로젝트 정보    | 대시보드, Step 1~4 전체           |
| `project_files`       | 업로드 파일      | Step 1 파일 업로드                |
| `eligibility_results` | Step 2 판단 결과 | Step 2, 오른쪽 패널               |
| `track_results`       | Step 3 추천 결과 | Step 3                            |

---

## 1️⃣ users 테이블

### 📱 화면: 로그인 → 추가 정보 입력 → 마이페이지

| 컬럼      | 화면 요소         | 설명                                 |
| --------- | ----------------- | ------------------------------------ |
| `id`      | auth.users와 연동 | Google 로그인 시 자동 생성           |
| `email`   | 이메일 (읽기전용) | Google 계정 이메일                   |
| `name`    | 성명 입력 필드    | 추가 정보 입력 화면에서 입력         |
| `company` | 회사명 입력 필드  | 추가 정보 입력 화면에서 입력         |
| `phone`   | 연락처 입력 필드  | 추가 정보 입력 화면에서 입력         |
| `status`  | -                 | PENDING → ACTIVE (추가 정보 입력 후) |

### 흐름

```
Google 로그인 → auth.users 생성 → users 자동 생성 (트리거)
                                    ↓
                              status = 'PENDING'
                                    ↓
                            추가 정보 입력 완료
                                    ↓
                              status = 'ACTIVE'

```

---

## 2️⃣ projects 테이블

### 📱 화면: 대시보드 (프로젝트 목록)

| 컬럼           | 화면 요소               | 설명                                                                         |
| -------------- | ----------------------- | ---------------------------------------------------------------------------- |
| `company_name` | 프로젝트 고객사(회사명) | 커넥트ICT, 드론에어 등                                                       |
| `service_name` | 프로젝트 서비스명       | 5G 기반 원격 의료 통신 등                                                    |
| `status`       | 상태 배지               | 기업상담/신청서작성/결과대기/완료                                            |
| `track`        | 트랙 배지               | 실증특례/임시허가/신속확인                                                   |
| `current_step` | 진행률 단계             | step에 따른 진행률 단계 (1=서비스분석, 2=시장진단, 3=트랙선택, 4=신청서생성) |
| `created_at`   | 날짜                    | 26.01.27 등                                                                  |

### status 값 매핑

| 값  | 화면 표시  |
| --- | ---------- |
| 1   | 기업상담   |
| 2   | 신청서작성 |
| 3   | 결과대기   |
| 4   | 완료       |

---

### 📱 화면: Step 1 (기업 정보 입력)

| 컬럼                  | 화면 요소            | 설명                                |
| --------------------- | -------------------- | ----------------------------------- |
| `company_name`        | 회사명 입력 필드     | 커넥트ICT                           |
| `service_name`        | 서비스명 입력 필드   | 5G 기반 원격 의료 통신              |
| `service_description` | 서비스 설명 textarea | 서비스 상세 설명                    |
| `additional_notes`    | 추가 메모 textarea   | 추가 기록할 내용                    |
| `track` (초기)        | 신청 유형 라디오버튼 | 상담신청/신속확인/임시허가/실증특례 |

---

### 📱 JSONB 컬럼들 (Step 1 저장 → Step 2~4 사용)

| 컬럼                | 용도                        | 수정 여부                |
| ------------------- | --------------------------- | ------------------------ |
| `canonical`         | 에이전트 분석용 (Step 2, 3) | AI만 사용                |
| `application_input` | 원본 보존 (diff용)          | ❌ 수정 안 함            |
| `application_draft` | Step 4 폼 필드들            | ✅ AI 초안 → 사용자 수정 |

```json
// 1️⃣ application_input (사용자 원본) ❌ 수정 안 함
{
  "fastcheck-1": {
    "data": {
      "applicant": { "companyName": "드론에어" },
      "technologyService": {
        "mainContent": "드론으로 배달합니다"
      }
    }
  }
}

// 2️⃣ canonical (에이전트 분석용) - 통일 구조
{
  "companyInfo": { "companyName": "드론에어" },
  "serviceInfo": {
    "serviceDescription": "드론으로 배달합니다"
  }
}

// 3️⃣ application_draft (AI 초안) ✅ 수정 가능
{
  "fastcheck-1": {
    "data": {
      "applicant": { "companyName": "드론에어" },
      "technologyService": {
        "mainContent": "도심 라스트마일 배송 효율 제고를 위한 소형 무인비행장치(드론) 기반 배송 서비스"
      }
    }
  }
}
```

**차이점:**

- `application_input` vs `application_draft` → **구조 동일, 값만 AI가 다듬음**
- `canonical` → **구조가 다름** (양식 상관없이 통일)'

---

### 데이터 흐름

```
Step 1: 신청서 업로드
    ↓
application_input ← 원본 저장 (양식별 JSON)
canonical ← 통일 구조로 변환 (에이전트용)
    ↓
Step 2: canonical 읽고 → 대상성 판단
Step 3: canonical 읽고 → 트랙 추천
    ↓
Step 4: application_input 바탕으로 AI 초안 생성
    ↓
application_draft ← 초안 저장 → 사용자 수정 → UPDATE
```

---

## 3️⃣ project_files 테이블

### 📱 화면: Step 1 파일 업로드

| 컬럼             | 화면 요소            | 설명                    |
| ---------------- | -------------------- | ----------------------- |
| `file_name`      | 업로드된 파일명 표시 | 신청서.pdf              |
| `storage_bucket` | -                    | Supabase Storage 버킷명 |
| `storage_path`   | 다운로드 링크        | Storage 내 파일 경로    |
| `file_type`      | 파일 아이콘          | pdf/hwp/docx            |
| `extracted_text` | -                    | AI 분석용 추출 텍스트   |

---

## extracted_text vs 위 3개 컬럼

| 컬럼                | 타입      | 내용                                  |
| ------------------- | --------- | ------------------------------------- |
| `extracted_text`    | **TEXT**  | 파일에서 뽑은 원문 텍스트 (구조 없음) |
| `application_input` | **JSONB** | 원문을 JSON으로 파싱한 것             |
| `canonical`         | **JSONB** | JSON을 통일 구조로 변환               |
| `application_draft` | **JSONB** | AI가 값을 다듬은 JSON                 |

---

## 데이터 흐름

```
[PDF 파일]
     ↓ 텍스트 추출
[extracted_text] ← 원문 그대로
     ↓ LLM 파싱
[application_input] ← JSON 구조화
     ↓ 구조 통일
[canonical] ← 에이전트용
```

---

## 예시

```json
// 📄 extracted_text (TEXT) - 파일에서 뽑은 원문 그대로
"회사명(성명): 드론에어
사업자등록번호: 123-45-67890
주소: 서울시 강남구
대표자명: 홍길동
전화번호: 02-1234-5678
전자우편: contact@droneair.kr

명칭: 드론 배송 서비스
유형: 서비스
주요내용: 드론으로 배달합니다

예상되는 소관기관: 국토교통부
예상되는 허가등: 항공안전법"

// 📦 application_input (JSONB) - 위 텍스트를 JSON으로 파싱
{
  "fastcheck-1": {
    "data": {
      "applicant": {
        "companyName": "드론에어",
        "businessRegistrationNumber": "123-45-67890"
      },
      "technologyService": {
        "mainContent": "드론으로 배달합니다"
      }
    }
  }
}
```

---

## 왜 둘 다 필요?

| 상황                              | 사용                |
| --------------------------------- | ------------------- |
| LLM 파싱 실패해서 다시 해야 할 때 | `extracted_text`    |
| 화면에 값 보여줄 때               | `application_input` |
| 원본 텍스트 검색할 때             | `extracted_text`    |

→ `extracted_text`는 **백업/재파싱용**, `application_input`은 **화면용**

---

- 컬럼 네 개 다 필요한지?
  **MVP에서 필수 아님**
  ***
  ## 정리
  | 컬럼                | MVP 필수?   | 없으면?                            |
  | ------------------- | ----------- | ---------------------------------- |
  | `extracted_text`    | ❌          | 재파싱 못함 (한 번에 성공하면 OK)  |
  | `application_input` | ❌          | diff/원본 비교 못함                |
  | `canonical`         | ❌          | 에이전트가 통으로 JSON 받아서 분석 |
  | `application_draft` | ✅ **필수** | Step 4 화면에 뿌릴 데이터 없음     |
  ***
  ## 최소 구성 (MVP)
  `application_draft만 있으면 돌아감`
  - 에이전트: `application_draft` 통으로 받아서 분석
  - Step 4: `application_draft` 화면에 표시 + 수정
  ***
  ## 왜 4개로 설계했냐면
  | 기능                          | 필요한 컬럼                               |
  | ----------------------------- | ----------------------------------------- |
  | diff 비교 ("AI가 뭘 바꿨지?") | `application_input` + `application_draft` |
  | 에이전트 안정성/토큰 절약     | `canonical`                               |
  | 파싱 실패 시 재시도           | `extracted_text`                          |
  ***
  ## 결론
  | 선택                  | 컬럼                  |
  | --------------------- | --------------------- |
  | **MVP 빠르게**        | `application_draft`만 |
  | **포트폴리오 퀄리티** | 4개 다 유지           |

---

## 4️⃣ eligibility_results 테이블

### 📱 화면: Step 2 (시장출시 진단)

| 컬럼                  | 화면 요소               | 설명                                 |
| --------------------- | ----------------------- | ------------------------------------ |
| `eligibility_label`   | AI 추천 배지            | 바로 시장 출시 / 규제 샌드박스 신청  |
| `confidence_score`    | 신뢰도 94%              | 우측 상단 배지                       |
| `result_summary`      | AI 분석 결과 텍스트     | 본 서비스는 현행 규제 체계 내에서... |
| `direct_launch_risks` | -                       | 바로 출시 시 리스크 (JSONB)          |
| `evidence_data`       | 판단 근거 + 오른쪽 패널 | 법령/사례/규제 기준 (JSONB)          |

### eligibility_label 값 매핑

<<<<<<< HEAD
| 값                     | 화면 표시               |
| ---------------------- | ----------------------- |
| `sandbox_required`     | 규제 샌드박스 신청 필요 |
| `sandbox_not_required` | 바로 시장 출시 가능     |
| `unclear`              | 불명확 - 추가 검토 필요 |
=======
| 값 | 화면 표시 |
| --- | --- |
| `required` | 규제 샌드박스 신청 필요 |
| `not_required` | 바로 시장 출시 가능 |
| `unclear` | 불명확 - 추가 검토 필요 |
>>>>>>> 2ff0b2e9e06dc275d4d9c9b7899c553da97e2c7d

---

### 📦 evidence_data JSONB 구조

```json
{
  "judgment_summary": [...],   // Step 2 판단 근거 (왼쪽)
  "approval_cases": [...],     // 오른쪽 승인사례 탭
  "regulations": [...]         // 오른쪽 법령·제도 탭
}

```

### judgment_summary (Step 2 판단 근거)

| 필드      | 화면 요소   | 예시                                 |
| --------- | ----------- | ------------------------------------ |
| `type`    | 배지 색상   | 법령 기준 / 사례 기준 / 규제 기준    |
| `title`   | 근거 제목   | 규제 저촉 사항 없음                  |
| `summary` | 설명 텍스트 | 대형 시설 내 자율주행 청소 로봇은... |
| `source`  | 근거 출처   | 「도로교통법」 제2조 (정의)...       |

### approval_cases (오른쪽 패널 - 승인사례 탭)

| 필드         | 화면 요소     | 예시                                     |
| ------------ | ------------- | ---------------------------------------- |
| `track`      | 트랙 배지     | 실증특례 / 임시허가                      |
| `date`       | 날짜          | 2023-06-15                               |
| `similarity` | 유사도        | 92% 유사                                 |
| `title`      | 사례 제목     | 자율주행 배달로봇 실증특례               |
| `company`    | 회사명        | 뉴빌리티                                 |
| `summary`    | 요약          | 보도 위 자율주행 배달로봇 운행을 위한... |
| `detail_url` | 상세보기 링크 | https://...                              |

### regulations (오른쪽 패널 - 법령·제도 탭)

| 필드         | 화면 요소     | 예시                                 |
| ------------ | ------------- | ------------------------------------ |
| `category`   | 카테고리 배지 | 실증특례 / 임시허가 / 절차 / 참고    |
| `title`      | 법령명        | 정보통신융합법 제36조                |
| `summary`    | 요약          | 신규 정보통신융합등 기술·서비스의... |
| `source_url` | 원문보기 링크 | https://...                          |

---

## 5️⃣ track_results 테이블

### 📱 화면: Step 3 (트랙 선택)

| 컬럼                | 화면 요소           | 설명                                     |
| ------------------- | ------------------- | ---------------------------------------- |
| `recommended_track` | AI 추천 배지        | 1번 카드에 'AI 추천' 배지                |
| `confidence_score`  | 신뢰도 89%          | 우측 상단 배지                           |
| `result_summary`    | AI 분석 결과 텍스트 | 서비스 특성과 규제 현황을 분석한 결과... |
| `track_comparison`  | 트랙별 카드 3개     | 실증특례/임시허가/신속확인 비교          |

---

### 📦 track_comparison JSONB 구조

```json
{
  "demo": {
    "fit_score": 90,
    "rank": 1,
    "status": "AI 추천",
    "reasons": [...],
    "evidence": [...]
  },
  "temp_permit": {
    "fit_score": 75,
    "rank": 2,
    "status": "조건부 가능",
    "reasons": [...],
    "evidence": [...]
  },
  "quick_check": {
    "fit_score": 30,
    "rank": 3,
    "status": "비추천",
    "reasons": [...],
    "evidence": [...]
  }
}

**아래 구조로 예정**
{
    "demo": {
      "fit_score": 90,
      "rank": 1,
      "status": "AI 추천",
      "reasons": [
        { "type": "positive", "text": "유사 사례가 승인받은 선례가 있습니다." },
        { "type": "negative", "text": "안전성 검증 데이터가 부족합니다." },
        { "type": "neutral", "text": "실증 기간 내 데이터 확보 필요합니다." }
      ],
      "evidence": [
        { "source_type": "사례", "source": "실증특례 제2023-ICT융합-0147호" },
        { "source_type": "법령", "source": "「정보통신융합법」 제38조의2" },
        { "source_type": "법령", "source": "「정보통신융합법」 제38조의2 제4항" }
      ]
    }
  }

```

### 각 트랙 객체

| 필드         | 화면 요소              | 설명                                  |
| ------------ | ---------------------- | ------------------------------------- |
| `fit_score`  | 순위 결정용            | 화면에 직접 표시 X                    |
| `rank`       | 카드 순서              | 1, 2, 3                               |
| `status`     | 상태 배지              | AI 추천 / 조건부 가능 / 비추천        |
| `reasons[]`  | 체크/X 아이콘 + 텍스트 | ✓ 유사 사례가 승인받은 선례...        |
| `evidence[]` | 근거 텍스트            | 근거: 「정보통신융합법」 제38조의2... |

---

### 🔄 projects.track vs track_results.recommended_track

| 컬럼                              | 내용                      | 변경 여부      |
| --------------------------------- | ------------------------- | -------------- |
| `track_results.recommended_track` | AI가 추천한 트랙          | ❌ 고정        |
| `projects.track`                  | 사용자가 최종 선택한 트랙 | ✅ UPDATE 가능 |

```
AI 추천: 실증특례 (demo)
    ↓
track_results.recommended_track = "demo"
projects.track = "demo" (일단 추천값으로 저장)
    ↓
사용자가 임시허가 선택
    ↓
projects.track = "temp_permit" (UPDATE)
track_results.recommended_track = "demo" (그대로)

```

---

## 6️⃣ Step 4: 신청서 작성

### 📱 화면: 왼쪽 폼 영역

| 데이터 소스                  | 화면 요소    | 설명                  |
| ---------------------------- | ------------ | --------------------- |
| `projects.application_draft` | 전체 폼 필드 | AI 초안 → 사용자 수정 |

### 양식별 구조

| 트랙     | 양식 갯수 | 키                           |
| -------- | --------- | ---------------------------- |
| 신속확인 | 2개       | `fastcheck-1`, `fastcheck-2` |
| 실증특례 | 4개       | `demonstration-1` ~ `4`      |
| 임시허가 | 4개       | `temporary-1` ~ `4`          |

---

### 📱 화면: 오른쪽 패널

| 탭        | 데이터 소스                                        | 설명                            |
| --------- | -------------------------------------------------- | ------------------------------- |
| 승인사례  | `eligibility_results.evidence_data.approval_cases` | Step 2에서 저장한 데이터 재사용 |
| 법령·제도 | `eligibility_results.evidence_data.regulations`    | Step 2에서 저장한 데이터 재사용 |

> 💡 RAG 재호출 없음! Step 2에서 한 번 저장하면 Step 4에서 DB 조회만 함

---

## 🔄 전체 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: 기업 정보 입력                                            │
├─────────────────────────────────────────────────────────────────┤
│ → projects 생성 (company_name, service_name, track 등)           │
│ → project_files 생성 (파일 업로드)                                │
│ → canonical 저장 (에이전트 분석용 통일 구조)                        │
│ → application_input 저장 (원본 보존)                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: 시장출시 진단                                            │
├─────────────────────────────────────────────────────────────────┤
│ ← canonical 읽기                                                 │
│ → RAG 검색 (법령/사례)                                           │
│ → eligibility_results 저장 (판단 결과 + evidence_data)            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: 트랙 선택                                                │
├─────────────────────────────────────────────────────────────────┤
│ ← canonical 읽기                                                 │
│ → track_results 저장 (추천 결과 + track_comparison)               │
│ → projects.track 저장 (사용자 최종 선택)                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: 신청서 작성                                              │
├─────────────────────────────────────────────────────────────────┤
│ ← application_input 읽기 (AI 초안 생성용)                         │
│ ← evidence_data 읽기 (오른쪽 패널 - RAG 재호출 X)                  │
│ → application_draft 저장 (AI 초안 + 사용자 수정본)                 │
└─────────────────────────────────────────────────────────────────┘

```

---

## 📊 테이블 관계도

```
users (1)
  │
  └──< projects (N)
          │
          ├──< project_files (N)
          │
          ├──< eligibility_results (1)
          │
          └──< track_results (1)

```

---

## ✅ 최종 테이블 목록 (5개)

| #   | 테이블                | 설명                      |
| --- | --------------------- | ------------------------- |
| 1   | `users`               | 컨설턴트 유저 정보        |
| 2   | `projects`            | 컨설팅 프로젝트           |
| 3   | `project_files`       | 업로드 파일 메타정보      |
| 4   | `eligibility_results` | Step 2 시장출시 진단 결과 |
| 5   | `track_results`       | Step 3 트랙 추천 결과     |

> 💡 regulations, approval_cases 테이블은 제외됨
> → RAG 결과를 evidence_data JSONB에 직접 저장하므로 별도 테이블 불필요

## ERD

erDiagram
users {
uuid id PK
text email
text name
text company
text phone
text status
timestamp created_at
}

    projects {
        uuid id PK
        uuid user_id FK
        text company_name
        text service_name
        text service_description
        text industry
        text additional_notes
        int status
        int current_step
        text track
        jsonb canonical
        jsonb application_input
        jsonb application_draft
        timestamp created_at
        timestamp updated_at
    }

    project_files {
        uuid id PK
        uuid project_id FK
        text file_name
        text storage_bucket
        text storage_path
        text file_type
        text extracted_text
        timestamp created_at
    }

    eligibility_results {
        uuid id PK
        uuid project_id FK
        text eligibility_label
        float8 confidence_score
        text result_summary
        jsonb direct_launch_risks
        jsonb evidence_data
        timestamp created_at
    }

    track_results {
        uuid id PK
        uuid project_id FK
        text recommended_track
        float8 confidence_score
        text result_summary
        jsonb track_comparison
        text model_name
        timestamp created_at
    }

    users ||--o{ projects : owns
    projects ||--o{ project_files : has
    projects ||--o{ eligibility_results : generates
    projects ||--o{ track_results : generates
