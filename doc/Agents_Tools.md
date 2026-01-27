# Agents & Tools 명세서

## 서비스 핵심 플로우

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  1. 기업 정보     │    │  2. 시장 출시     │    │  3. 트랙 선택      │    │  4. 신청서 작성   │
│     입력         │───▶│     진단         │───▶│                 │───▶│                 │
│                 │    │                 │    │                 │    │                 │
│ Service         │    │ Eligibility     │    │ Track           │    │ Application     │
│ Structurer      │    │ Evaluator       │    │ Recommender     │    │ Drafter         │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 공용 RAG Tools (기 구현)

| Tool                           | 데이터                             | 주 사용 에이전트 |
| ------------------------------ | ---------------------------------- | ---------------- |
| **R1. 규제제도 & 절차 RAG**    | 트랙 정의, 절차, 요건, 심사 포인트 | 2, 3, 4          |
| **R2. 승인 사례 RAG**          | 승인/반려 사례, 조건, 실증 범위    | 2, 3, 4          |
| **R3. 도메인별 규제·법령 RAG** | 분야별 법령/인허가 체계            | 2, 3, 4          |

---

## 1) 기업 서비스 구조화 에이전트 (Service Structurer Agent)

### 역할

- 컨설턴트가 입력한 고객사 기본 정보와 업로드된 문서를 파싱하여 동일한 구조(Canonical Structure)로 변환
- 단순상담, 신속확인, 임시허가, 실증특례 양식이 모두 다르므로 이후 에이전트들이 사용할 수 있는 통일된 구조로 구조화

### 입력 데이터

- 컨설턴트 입력: 회사명, 서비스 이름, 서비스 설명, 추가 메모
- 업로드 문서: 단순상담 신청서 또는 신속확인/임시허가/실증특례 신청서 (HWP/PDF)

### Tools

#### A. 문서 파싱 Tool (Document Parser)

| 항목     | 내용                                                                              |
| -------- | --------------------------------------------------------------------------------- |
| **입력** | 업로드된 문서 파일 (HWP/PDF), 문서 타입 힌트 (optional)                           |
| **출력** | 원문 텍스트, 섹션/필드 구조, 표 데이터, 문서 타입 추정 결과                       |
| **참고** | pyhwpx 라이브러리 활용, 문서 타입 자동 감지 (단순상담/신속확인/임시허가/실증특례) |

#### B. 양식 스키마 매칭 Tool (Form Schema Matcher)

| 항목     | 내용                                                                                                              |
| -------- | ----------------------------------------------------------------------------------------------------------------- |
| **입력** | 문서 타입, 파싱된 문서 구조                                                                                       |
| **출력** | 매칭된 양식 스키마 (JSON), 필드 매핑 결과                                                                         |
| **참고** | `client/src/data/form/` 하위 양식 파일 참조 (counseling.json, fastcheck.json, temporary.json, demonstration.json) |

#### C. 자동 채움 Tool (Auto-Fill Extractor)

| 항목     | 내용                                                          |
| -------- | ------------------------------------------------------------- |
| **입력** | 파싱된 문서 데이터, 양식 스키마, 컨설턴트 입력 정보           |
| **출력** | 필드별 추출값, 값의 근거 위치 (페이지/섹션), 추출 신뢰도 점수 |
| **참고** | LLM 기반 필드 매핑, 컨설턴트 입력 정보 우선 적용              |

#### D. Canonical 구조 변환 Tool (Canonical Converter)

| 항목     | 내용                                                                     |
| -------- | ------------------------------------------------------------------------ |
| **입력** | 자동 채움 결과, 양식 스키마, 원본 문서 타입                              |
| **출력** | `CanonicalStructure` - 통일된 표준 구조 (아래 스키마 참조)               |
| **참고** | 모든 양식 타입을 동일한 구조로 변환, 이후 2~4번 에이전트의 입력으로 사용 |

**Canonical Structure 스키마:**

```json
{
  "company_info": {
    "company_name": "string",
    "representative": "string",
    "business_number": "string",
    "address": "string",
    "contact": "string"
  },
  "service_info": {
    "service_name": "string",
    "service_description": "string",
    "service_category": "string",
    "target_users": "string",
    "business_model": "string"
  },
  "technology_info": {
    "core_technology": "string",
    "innovation_points": ["string"],
    "related_patents": ["string"]
  },
  "regulatory_info": {
    "related_regulations": ["string"],
    "regulatory_issues": "string",
    "requested_track": "string | null"
  },
  "additional_info": {
    "consultant_memo": "string",
    "attachments": ["string"]
  },
  "metadata": {
    "original_document_type": "counseling | fastcheck | temporary | demonstration",
    "extraction_confidence": "number",
    "created_at": "datetime",
    "session_id": "string"
  }
}
```

#### E. 불확실/누락 탐지 Tool (Uncertainty Detector)

| 항목     | 내용                                                                     |
| -------- | ------------------------------------------------------------------------ |
| **입력** | Canonical Structure, 추출 신뢰도 데이터                                  |
| **출력** | 누락 필드 목록, 불확실 필드 목록 (낮은 신뢰도), 추가 질문 생성, 우선순위 |
| **참고** | 필수 필드 누락 시 경고, 신뢰도 낮은 필드에 대한 확인 질문 생성           |

### DB 연동 (Supabase)

| 테이블                 | 저장 데이터                                                             | 비고                 |
| ---------------------- | ----------------------------------------------------------------------- | -------------------- |
| `consulting_sessions`  | session_id, consultant_id, company_name, created_at, status             | 세션 생성 시 저장    |
| `canonical_structures` | session_id, canonical_data (JSONB), original_doc_type, confidence_score | Canonical 구조 저장  |
| `uploaded_documents`   | session_id, file_name, file_path, file_type, parsed_content             | 원본 문서 메타데이터 |

---

## 2) 샌드박스 대상성 판단 에이전트 (Eligibility Evaluator Agent)

### 역할

- 구조화된 데이터를 기반으로 샌드박스 신청 대상인지, 바로 출시 가능한지 판단
- RAG Tools (R1, R2, R3) 활용하여 근거 기반 판단

### 입력 데이터

- `CanonicalStructure` (1번 에이전트 출력)

### 출력 데이터

- 샌드박스 대상 여부 (eligible / not_eligible / uncertain)
- 판단 근거 (법령, 사례, 규제 기준별)
- 바로 출시 시 예상 리스크 (샌드박스 대상인 경우)

### Tools

#### A. 대상성 Rule 스크리너 Tool (Eligibility Rule Screener)

| 항목     | 내용                                                                    |
| -------- | ----------------------------------------------------------------------- |
| **입력** | Canonical Structure                                                     |
| **출력** | 규제 해당 여부 시그널, 키워드/조건 매칭 결과, 1차 라벨 (높음/중간/낮음) |
| **참고** | 규칙 기반 1차 필터링, 신속확인/임시허가/실증특례 대상 조건 확인         |

#### B. 유사 사례 검색 Tool (Similar Case Retriever)

| 항목     | 내용                                                                     |
| -------- | ------------------------------------------------------------------------ |
| **입력** | Canonical Structure, Rule 스크리너 결과                                  |
| **출력** | 상위 N개 유사 사례 (요약, 메타데이터), 유사 이유, 유사도 점수            |
| **참고** | **R2 (승인 사례 RAG)** 활용, 서비스 분야/기술/규제 이슈 기준 유사도 계산 |

#### C. 규제 법령 검색 Tool (Regulation Retriever)

| 항목     | 내용                                                |
| -------- | --------------------------------------------------- |
| **입력** | Canonical Structure의 서비스 분야, 관련 규제 키워드 |
| **출력** | 관련 법령/규제 목록, 조항 스니펫, 인허가 요건       |
| **참고** | **R3 (도메인별 규제·법령 RAG)** 활용                |

#### D. 근거 정리 & 판정 통합 Tool (Decision Composer)

| 항목     | 내용                                                                                |
| -------- | ----------------------------------------------------------------------------------- |
| **입력** | Rule 스크리너 결과, 유사 사례 검색 결과, 규제 법령 검색 결과                        |
| **출력** | 최종 판정 (eligible/not_eligible/uncertain), 근거 bullet 리스트, 확신도/리스크 표시 |
| **참고** | 결정 로직 고정 (튜닝 용이), 법령/사례/규제 기준별 근거 분류                         |

**Decision Composer 출력 스키마:**

```json
{
  "eligibility": "eligible | not_eligible | uncertain",
  "confidence": "number (0-100)",
  "reasoning": {
    "법령_기준": [
      {
        "content": "string",
        "source": "string (법령명, 조항)",
        "source_url": "string | null"
      }
    ],
    "사례_기준": [
      {
        "content": "string",
        "source": "string (승인 사례 제목)",
        "case_id": "string",
        "source_url": "string | null"
      }
    ],
    "규제_기준": [
      {
        "content": "string",
        "source": "string"
      }
    ]
  },
  "direct_launch_risks": [
    {
      "risk": "string",
      "severity": "high | medium | low",
      "related_regulation": "string"
    }
  ]
}
```

#### E. 리스크 분석 Tool (Risk Analyzer)

| 항목     | 내용                                                     |
| -------- | -------------------------------------------------------- |
| **입력** | 판정 결과, Canonical Structure                           |
| **출력** | 바로 출시 시 예상 리스크, 리스크 심각도, 관련 규제/법령  |
| **참고** | 샌드박스 대상으로 판정된 경우에만 실행, 경고 메시지 생성 |

### DB 연동 (Supabase)

| 테이블                | 저장 데이터                                                                       | 비고                        |
| --------------------- | --------------------------------------------------------------------------------- | --------------------------- |
| `eligibility_results` | session_id, eligibility, confidence, reasoning (JSONB), risks (JSONB), created_at | 판정 결과 저장              |
| `rag_search_logs`     | session_id, agent_type, rag_tool (R1/R2/R3), query, results (JSONB)               | RAG 검색 로그 (근거 추적용) |

---

## 3) 샌드박스 트랙 추천 에이전트 (Track Recommender Agent)

### 역할

- 샌드박스 대상으로 판정된 경우, 적합한 트랙(신속확인/임시허가/실증특례) 추천
- 각 트랙별 적합/부적합 이유와 근거 제공

### 입력 데이터

- `CanonicalStructure` (1번 에이전트 출력)
- 대상성 판단 결과 (2번 에이전트 출력)

### 출력 데이터

- 트랙별 추천 순위 (1순위, 2순위, 3순위)
- 각 트랙별 적합/부적합 이유 (positive/negative/neutral)
- 이유별 근거 (법령, 사례, 규제 기준)

### Tools

#### A. 트랙 적합도 스코어링 Tool (Track Scorer)

| 항목     | 내용                                                                   |
| -------- | ---------------------------------------------------------------------- |
| **입력** | Canonical Structure, 대상성 판단 요약                                  |
| **출력** | 신속확인/임시허가/실증특례 각 점수 (0-100), 점수 근거 (조건 충족 여부) |
| **참고** | 각 트랙의 법적 요건 기준 점수 산정                                     |

**트랙별 핵심 판단 기준:**

- **신속확인**: 허가 필요 여부가 불명확한 경우, 기존 규제 적용 가능 여부 확인
- **임시허가**: 안전성 검증 완료, 기존 법령으로 허가 불가, 시장 출시 필요
- **실증특례**: 실증 테스트 필요, 안전성 미검증, 제한된 범위 실험

#### B. 트랙 정의/요건 RAG Tool (Track Definition Retriever)

| 항목     | 내용                                                 |
| -------- | ---------------------------------------------------- |
| **입력** | 후보 트랙 (1~2개), Canonical Structure 핵심 포인트   |
| **출력** | 해당 트랙의 정의/요건 스니펫, 출처, 적용 논리 연결점 |
| **참고** | **R1 (규제제도 & 절차 RAG)** 활용                    |

#### C. 유사 트랙 승인 사례 검색 Tool (Track Case Retriever)

| 항목     | 내용                                                  |
| -------- | ----------------------------------------------------- |
| **입력** | 각 트랙, Canonical Structure (서비스 분야, 규제 이슈) |
| **출력** | 트랙별 유사 승인 사례, 해당 트랙 선택 이유 분석       |
| **참고** | **R2 (승인 사례 RAG)** 활용, 트랙별 필터링            |

#### D. 추천 사유 생성 Tool (Recommendation Explainer)

| 항목     | 내용                                                                                          |
| -------- | --------------------------------------------------------------------------------------------- |
| **입력** | 트랙 점수, 트랙 정의/요건, 유사 사례                                                          |
| **출력** | 추천 순위 (1/2/3순위), 트랙별 적합/부적합 이유, 이유별 타입 (positive/negative/neutral), 근거 |
| **참고** | 컨설턴트 설명용 문장 템플릿 포함                                                              |

**Recommendation Explainer 출력 스키마:**

```json
{
  "recommendations": [
    {
      "rank": 1,
      "track": "실증특례 | 임시허가 | 신속확인",
      "score": "number (0-100)",
      "reasons": [
        {
          "content": "string",
          "type": "positive | negative | neutral",
          "source_type": "법령 | 사례 | 규제",
          "source": "string (구체적 법령명/사례 제목)",
          "source_url": "string | null"
        }
      ],
      "summary": "string (5-7줄 요약)"
    }
  ],
  "original_requested_track": "string | null",
  "track_changed": "boolean",
  "track_change_reason": "string | null"
}
```

### DB 연동 (Supabase)

| 테이블                  | 저장 데이터                                                            | 비고                    |
| ----------------------- | ---------------------------------------------------------------------- | ----------------------- |
| `track_recommendations` | session_id, recommendations (JSONB), selected_track, created_at        | 추천 결과 저장          |
| `track_selections`      | session_id, selected_track, selection_reason, selected_by, selected_at | 컨설턴트 최종 선택 저장 |

---

## 4) 신청서 초안 생성 에이전트 (Application Drafter Agent)

### 역할

- 컨설턴트가 선택한 트랙의 신청서 폼을 AI 초안으로 채움
- 구조화된 데이터, 판단/추천 근거, RAG 검색 결과를 활용
- 공식적인 어투로 작성
- 우측 패널에 참고 자료 (승인사례, 법령/제도) 제공

### 입력 데이터

- `CanonicalStructure` (1번 에이전트 출력)
- 대상성 판단 결과 (2번 에이전트 출력)
- 트랙 추천 결과 및 컨설턴트 선택 트랙 (3번 에이전트 출력)

### 출력 데이터

- 선택된 트랙의 신청서 초안 (섹션별)
- 참고 자료: 승인사례, 법령/제도 정보

### Tools

#### A. 양식 선택 Tool (Template Selector)

| 항목     | 내용                                                                                        |
| -------- | ------------------------------------------------------------------------------------------- |
| **입력** | 선택된 트랙, 서비스 분야 (optional)                                                         |
| **출력** | 사용할 템플릿 ID, 섹션 목록, 필수 필드 스키마                                               |
| **참고** | `client/src/data/form/` 하위 양식 참조 (fastcheck.json, temporary.json, demonstration.json) |

#### B. 섹션별 데이터 매핑 Tool (Section Data Mapper)

| 항목     | 내용                                                      |
| -------- | --------------------------------------------------------- |
| **입력** | Canonical Structure, 대상성/트랙 판단 결과, 템플릿 스키마 |
| **출력** | 섹션별 채워넣을 데이터 JSON, 데이터 출처 메타데이터       |
| **참고** | 출처 메타데이터 포함 (이후 참고자료 패널 활용)            |

#### C. 섹션 문장 생성 Tool (Section Writer)

| 항목     | 내용                                        |
| -------- | ------------------------------------------- |
| **입력** | 섹션별 데이터, 섹션 타입 (텍스트/표/리스트) |
| **출력** | 섹션별 초안 문단, 표/리스트 포함            |
| **참고** | 공공 문서 공식 어투 사용, 톤/형식 맞춤      |

**문장 생성 가이드라인:**

- 경어체 사용 (~합니다, ~입니다)
- 객관적이고 명확한 표현
- 전문 용어 적절히 사용
- 근거 기반 서술

#### D. 승인사례 참고자료 생성 Tool (Case Reference Generator)

| 항목     | 내용                                                              |
| -------- | ----------------------------------------------------------------- |
| **입력** | Canonical Structure, 선택된 트랙, 섹션별 데이터                   |
| **출력** | 관련 승인사례 목록 (일자, 제목, 서비스명, 회사명, 유사 이유, URL) |
| **참고** | **R2 (승인 사례 RAG)** 활용, 신청서 작성에 참고할 사례 선별       |

**승인사례 출력 스키마:**

```json
{
  "cases": [
    {
      "case_id": "string",
      "date": "string (YYYY-MM-DD)",
      "title": "string",
      "service_name": "string",
      "company_name": "string",
      "track": "실증특례 | 임시허가 | 신속확인",
      "similarity_reason": "string (현재 신청서와 유사한 이유)",
      "relevance_score": "number (0-100)",
      "url": "string"
    }
  ]
}
```

#### E. 법령/제도 참고자료 생성 Tool (Regulation Reference Generator)

| 항목     | 내용                                                               |
| -------- | ------------------------------------------------------------------ |
| **입력** | Canonical Structure, 선택된 트랙, 대상성 판단 근거                 |
| **출력** | 관련 법령/제도 목록 (출처명, 조항, 관련성 설명, URL)               |
| **참고** | **R1 (규제제도 & 절차 RAG)**, **R3 (도메인별 규제·법령 RAG)** 활용 |

**법령/제도 출력 스키마:**

```json
{
  "regulations": [
    {
      "source_name": "string (법령명)",
      "article": "string (제X조)",
      "location": "string (출처 위치)",
      "relevance": "string (현재 신청서 작성과의 관련성)",
      "url": "string"
    }
  ]
}
```

#### F. 일관성/형식 검수 Tool (Consistency Checker)

| 항목     | 내용                                                               |
| -------- | ------------------------------------------------------------------ |
| **입력** | 전체 초안                                                          |
| **출력** | 용어 통일 제안, 중복 제거 포인트, 누락 섹션 경고, 품질 개선 포인트 |
| **참고** | 자동 수정보다 경고/제안 형태로 제공                                |

### DB 연동 (Supabase)

| 테이블                | 저장 데이터                                                            | 비고                         |
| --------------------- | ---------------------------------------------------------------------- | ---------------------------- |
| `application_drafts`  | session_id, track, draft_data (JSONB), version, created_at, updated_at | 신청서 초안 저장 (버전 관리) |
| `draft_sections`      | draft_id, section_id, content, source_metadata (JSONB)                 | 섹션별 초안 및 출처 정보     |
| `reference_materials` | session_id, type (case/regulation), data (JSONB)                       | 참고자료 캐싱                |

---

## DB 스키마 요약 (Supabase)

### 전체 테이블 목록

| 테이블명                | 용도                     | 주요 컬럼                                                        |
| ----------------------- | ------------------------ | ---------------------------------------------------------------- |
| `consulting_sessions`   | 상담 세션 관리           | session_id (PK), consultant_id, company_name, status, created_at |
| `canonical_structures`  | 구조화된 기업 정보       | session_id (FK), canonical_data (JSONB), original_doc_type       |
| `uploaded_documents`    | 업로드 문서 메타데이터   | session_id (FK), file_name, file_path, file_type                 |
| `eligibility_results`   | 대상성 판단 결과         | session_id (FK), eligibility, confidence, reasoning (JSONB)      |
| `track_recommendations` | 트랙 추천 결과           | session_id (FK), recommendations (JSONB)                         |
| `track_selections`      | 컨설턴트 트랙 선택       | session_id (FK), selected_track, selected_at                     |
| `application_drafts`    | 신청서 초안              | session_id (FK), track, draft_data (JSONB), version              |
| `draft_sections`        | 초안 섹션별 데이터       | draft_id (FK), section_id, content, source_metadata (JSONB)      |
| `reference_materials`   | 참고자료 (승인사례/법령) | session_id (FK), type, data (JSONB)                              |
| `rag_search_logs`       | RAG 검색 로그            | session_id (FK), agent_type, rag_tool, query, results (JSONB)    |

### 세션 상태 (status) 값

| 상태             | 설명                               |
| ---------------- | ---------------------------------- |
| `draft`          | 정보 입력 중                       |
| `structured`     | 구조화 완료 (1단계 완료)           |
| `evaluated`      | 대상성 판단 완료 (2단계 완료)      |
| `track_selected` | 트랙 선택 완료 (3단계 완료)        |
| `drafted`        | 신청서 초안 작성 완료 (4단계 완료) |
| `completed`      | 최종 완료                          |

---

## 에이전트 간 데이터 흐름

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                              Consulting Session                                   │
│                                 (session_id)                                      │
├───────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  [1. Service Structurer]                                                          │
│       │                                                                           │
│       ├── Input: 컨설턴트 입력 + 업로드 문서                                            │
│       │                                                                           │
│       └── Output: CanonicalStructure ──────────────────────────┐                  │
│                                                                │                  │
│  [2. Eligibility Evaluator]                                    │                  │
│       │                                                        │                  │
│       ├── Input: CanonicalStructure ◄──────────────────────────┤                  │
│       │                                                        │                  │
│       └── Output: EligibilityResult ──────────────────────────┐│                  │
│                                                               ││                  │
│  [3. Track Recommender]                                       ││                  │
│       │                                                       ││                  │
│       ├── Input: CanonicalStructure ◄─────────────────────────┼┘                  │
│       │          EligibilityResult ◄──────────────────────────┘                   │
│       │                                                                           │
│       └── Output: TrackRecommendation ─────────────────────────┐                  │
│                   + 컨설턴트 선택 (TrackSelection)                │                  │
│                                                                │                  │
│  [4. Application Drafter]                                      │                  │
│       │                                                        │                  │
│       ├── Input: CanonicalStructure                            │                  │
│       │          EligibilityResult                             │                  │
│       │          TrackSelection ◄──────────────────────────────┘                  │
│       │                                                                           │
│       └── Output: ApplicationDraft + ReferencesMaterials                          │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 참고: 양식 파일 경로

| 양식 타입 | 파일 경로                                 |
| --------- | ----------------------------------------- |
| 단순상담  | `client/src/data/form/counseling.json`    |
| 신속확인  | `client/src/data/form/fastcheck.json`     |
| 임시허가  | `client/src/data/form/temporary.json`     |
| 실증특례  | `client/src/data/form/demonstration.json` |

---

---

## 5) 전략 추천 에이전트 (고도화)

이건 “유사 사례 → 승인 포인트 패턴 → 이번 건 적용” 파이프라인이 핵심.

### A. 유사 사례 군집/선정 tool

- 입력: (1) 구조화 결과 + (3) 트랙 후보
- 출력: 유사 사례 Top N + “왜 유사한지”(비교 축)

### B. 승인 포인트 패턴 추출 tool

- 입력: 유사 사례 N개(원문 요약/핵심 문장)
- 출력: 반복되는 승인 포인트(실증 범위, 안전/책임, 소비자 고지 등) + 빈도/중요도

### C. 이번 건 적용 전략 생성 tool

- 입력: (1) 구조화 결과 + B의 패턴
- 출력: 이번 건에 맞는 “강조해야 할 포인트”, “피해야 할 서술”, “구체 문장 가이드”

### D. 근거 스니펫 & 인용 후보 tool

- 입력: C 결과 + 사례 원문
- 출력: 참고할 표현(짧은 문장 단위), 출처/사례 ID, 적용 위치 추천
- 포인트: 컨설턴트가 “복붙 가능한” 형태로 주면 체감 가치 큼

### E. (옵션) 유사 사례 없음 대응 tool

- 입력: 검색 결과 없음 신호
- 출력: “근접 분야 사례”로 대체 탐색 전략 + 일반 승인 프레임(보수적 가이드)

---

## 6) 체크리스트 & 리스크 알림 에이전트 (고도화)

이건 “심사관 관점의 QA”라서, **체크 항목 생성 / 검출 / 개선안**을 분리하는 게 좋아.

### A. 기준 체크리스트 생성 tool

- 입력: 트랙/부처/양식 + (1) 구조화 결과
- 출력: 필수 항목 체크리스트(항목ID, 기준, 합격 조건, 증빙 예시)

### B. 초안 대비 누락/약점 탐지 tool

- 입력: 신청서 초안 + A 체크리스트
- 출력: 누락 항목, 약한 항목(근거 부족/모호/과장), 위험도(상/중/하) + 근거 위치

### C. 리스크 시나리오 생성 tool

- 입력: B 결과
- 출력: 예상 반려/보완 요청 포인트(질문 형태), “왜 위험한지” 설명

### D. 개선 문장/대체 표현 생성 tool

- 입력: (초안의 문제 문장 + B/C 결과) + (5) 전략 추천 결과(있으면)
- 출력: 수정 제안 문장(전/후), 추가로 넣을 근거 항목, 표현 톤 가이드

### E. 최종 검수 리포트 생성 tool

- 입력: A~D 결과
- 출력: 컨설턴트 제출용 리포트(요약, 우선순위, 바로 고칠 것 TOP5)
