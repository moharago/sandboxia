# 비즈니스 로직 정의

LLM/Agent와 무관한 순수 비즈니스 로직 정리.

---

## 공통 로직 (Common)

> 여러 기능에서 재사용되는 공통 로직

### 1. 인증/인가 (Authentication/Authorization)

| 기능 | 설명 | 위치 |
|------|------|------|
| 로그인 | 이메일/비밀번호 인증, JWT 토큰 발급 | `services/auth.py` |
| 로그아웃 | 토큰 무효화 | `services/auth.py` |
| 토큰 갱신 | Refresh token으로 Access token 재발급 | `services/auth.py` |
| 권한 검증 | 역할 기반 접근 제어 (RBAC) | `api/deps.py` |

**사용자 역할:**
- `consultant`: 컨설턴트 (기본)
- `admin`: 관리자

### 2. 파일 관리 (File Management)

| 기능 | 설명 | 위치 |
|------|------|------|
| 파일 업로드 | HWP/PDF/DOCX 업로드, 확장자/크기 검증 | `services/file.py` |
| 파일 저장 | 로컬/S3 저장, 경로 생성 | `services/file.py` |
| 파일 조회 | 파일 메타데이터 조회 | `services/file.py` |
| 파일 삭제 | 파일 및 메타데이터 삭제 | `services/file.py` |

**파일 제한:**
- 최대 크기: 10MB
- 허용 확장자: `.hwp`, `.pdf`, `.docx`

### 3. 에러 처리 (Error Handling)

| 에러 타입 | HTTP 코드 | 설명 |
|-----------|-----------|------|
| `ValidationError` | 400 | 입력값 검증 실패 |
| `AuthenticationError` | 401 | 인증 실패 |
| `AuthorizationError` | 403 | 권한 부족 |
| `NotFoundError` | 404 | 리소스 없음 |
| `FileProcessingError` | 422 | 파일 처리 실패 |
| `AgentExecutionError` | 500 | 에이전트 실행 실패 |

### 4. 로깅 (Logging)

| 레벨 | 용도 |
|------|------|
| `DEBUG` | 개발 디버깅 |
| `INFO` | 일반 작업 로그 (API 호출, 에이전트 실행) |
| `WARNING` | 경고 (재시도, 폴백) |
| `ERROR` | 에러 (예외 발생) |

---

## 도메인 로직

### 1. 상담 관리 (Consultation)

> 상담 신청 CRUD 및 상태 관리

| 기능 | 설명 | 위치 |
|------|------|------|
| 상담 생성 | HWP 업로드 → C1 파싱 → 상담 레코드 생성 | `services/consultation.py` |
| 상담 조회 | 상담 상세 정보 조회 | `services/consultation.py` |
| 상담 목록 | 필터/정렬/페이징 | `services/consultation.py` |
| 상담 수정 | CanonicalStructure 수정 (C2 Patch 사용) | `services/consultation.py` |
| 상담 삭제 | 소프트 삭제 (is_deleted 플래그) | `services/consultation.py` |

**상담 상태 (Status):**
```
draft → structuring → evaluating → recommending → drafting → reviewing → completed
  │                                                                          │
  └──────────────────────────── cancelled ←──────────────────────────────────┘
```

| 상태 | 설명 |
|------|------|
| `draft` | 초안 (HWP 업로드 완료) |
| `structuring` | 1번 에이전트 실행 중 |
| `evaluating` | 2번 에이전트 실행 중 |
| `recommending` | 3번 에이전트 실행 중 |
| `drafting` | 4번 에이전트 실행 중 |
| `reviewing` | 5-6번 에이전트 실행 중 |
| `completed` | 완료 |
| `cancelled` | 취소 |

### 2. HWP 파싱 (HWP Parser) - C1 서비스

> HWP 상담신청서 → CanonicalStructure 변환

| 기능 | 설명 | 위치 |
|------|------|------|
| HWP 텍스트 추출 | pyhwpx로 HWP 파일 텍스트 추출 | `services/hwp_parser.py` |
| 타이틀 기반 파싱 | 타이틀-값 쌍 추출 | `services/hwp_parser.py` |
| 필드 매핑 | 추출 값 → CanonicalStructure 매핑 | `services/hwp_parser.py` |
| 파싱 검증 | 필수 필드 누락 체크 | `services/hwp_parser.py` |

**파싱 흐름:**
```
HWP 파일
    │
    ▼
pyhwpx 텍스트 추출
    │
    ▼
타이틀-값 쌍 파싱
    │
    ▼
DEFAULT_TITLE_MAPPINGS로 필드 매핑
    │
    ▼
CanonicalStructure 생성
    │
    ▼
검증 (필수 필드 체크)
    │
    ▼
저장 및 반환
```

### 3. 데이터 패치 (Patch) - C2 유틸리티

> 사용자 수정 반영 및 변경 이력 관리

| 기능 | 설명 | 위치 |
|------|------|------|
| 패치 적용 | diff → 원본 데이터에 적용 | `tools/shared/utils/patch.py` |
| 패치 병합 | 여러 패치 충돌 해결 후 병합 | `tools/shared/utils/patch.py` |
| 이력 조회 | 변경 이력 타임라인 조회 | `tools/shared/utils/patch.py` |
| 롤백 | 특정 시점으로 되돌리기 | `tools/shared/utils/patch.py` |

### 4. 문서 생성 (Document Generation)

> 신청서 초안을 DOCX/PDF로 렌더링

| 기능 | 설명 | 위치 |
|------|------|------|
| 템플릿 선택 | 트랙/부처별 템플릿 매칭 | `services/document.py` |
| DOCX 렌더링 | python-docx로 DOCX 생성 | `services/document.py` |
| PDF 변환 | DOCX → PDF 변환 | `services/document.py` |
| 다운로드 URL 생성 | 임시 다운로드 링크 생성 | `services/document.py` |

### 5. 에이전트 실행 관리 (Agent Execution)

> 에이전트 실행 상태 추적 및 결과 저장

| 기능 | 설명 | 위치 |
|------|------|------|
| 실행 시작 | 에이전트 실행 요청, 상태 `running` | `services/agent_runner.py` |
| 진행 상태 조회 | 현재 단계, 진행률 | `services/agent_runner.py` |
| 결과 저장 | 에이전트 출력 저장 | `services/agent_runner.py` |
| 실행 취소 | 실행 중인 에이전트 취소 | `services/agent_runner.py` |
| 재실행 | 실패한 에이전트 재실행 | `services/agent_runner.py` |

**실행 상태:**
| 상태 | 설명 |
|------|------|
| `pending` | 대기 중 |
| `running` | 실행 중 |
| `completed` | 완료 |
| `failed` | 실패 |
| `cancelled` | 취소됨 |

---

## API 엔드포인트 정리

### 인증 API

```
POST   /api/v1/auth/login          # 로그인
POST   /api/v1/auth/logout         # 로그아웃
POST   /api/v1/auth/refresh        # 토큰 갱신
GET    /api/v1/auth/me             # 현재 사용자 정보
```

### 상담 API

```
POST   /api/v1/consultations                    # 상담 생성 (HWP 업로드)
GET    /api/v1/consultations                    # 상담 목록
GET    /api/v1/consultations/{id}               # 상담 상세
PATCH  /api/v1/consultations/{id}               # 상담 수정 (C2 Patch)
DELETE /api/v1/consultations/{id}               # 상담 삭제
GET    /api/v1/consultations/{id}/history       # 변경 이력
```

### 에이전트 API

```
POST   /api/v1/consultations/{id}/agents/structure     # 1. 구조화 실행
POST   /api/v1/consultations/{id}/agents/eligibility   # 2. 대상성 판단
POST   /api/v1/consultations/{id}/agents/track         # 3. 트랙 추천
POST   /api/v1/consultations/{id}/agents/draft         # 4. 신청서 초안
POST   /api/v1/consultations/{id}/agents/strategy      # 5. 전략 추천
POST   /api/v1/consultations/{id}/agents/risk          # 6. 리스크 체크
POST   /api/v1/consultations/{id}/agents/full          # 전체 파이프라인

GET    /api/v1/agents/status/{task_id}                 # 실행 상태 조회
DELETE /api/v1/agents/status/{task_id}                 # 실행 취소
```

### 문서 API

```
GET    /api/v1/consultations/{id}/documents            # 생성된 문서 목록
POST   /api/v1/consultations/{id}/documents/export     # 문서 내보내기 (DOCX/PDF)
GET    /api/v1/documents/{id}/download                 # 문서 다운로드
```

### 파일 API

```
POST   /api/v1/files/upload        # 파일 업로드
GET    /api/v1/files/{id}          # 파일 메타데이터
DELETE /api/v1/files/{id}          # 파일 삭제
```

---

## 데이터 모델 (DB Schema)

### User (사용자)

```python
class User:
    id: str (UUID)
    email: str (unique)
    password_hash: str
    name: str
    role: str  # consultant, admin
    created_at: datetime
    updated_at: datetime
```

### Consultation (상담)

```python
class Consultation:
    id: str (UUID)
    user_id: str (FK → User)
    status: str  # draft, structuring, ...
    canonical: JSON  # CanonicalStructure
    source_file_id: str (FK → File)
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
```

### AgentResult (에이전트 결과)

```python
class AgentResult:
    id: str (UUID)
    consultation_id: str (FK → Consultation)
    agent_type: str  # structure, eligibility, track, draft, strategy, risk
    status: str  # pending, running, completed, failed
    input_data: JSON
    output_data: JSON
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None
```

### PatchHistory (변경 이력)

```python
class PatchHistory:
    id: str (UUID)
    consultation_id: str (FK → Consultation)
    field_path: str
    old_value: JSON
    new_value: JSON
    changed_by: str (FK → User)
    reason: str | None
    created_at: datetime
```

### File (파일)

```python
class File:
    id: str (UUID)
    filename: str
    original_filename: str
    content_type: str
    size: int
    storage_path: str
    uploaded_by: str (FK → User)
    created_at: datetime
```

### Document (생성 문서)

```python
class Document:
    id: str (UUID)
    consultation_id: str (FK → Consultation)
    document_type: str  # draft, final
    format: str  # docx, pdf
    file_id: str (FK → File)
    created_at: datetime
```

---

## 서비스 구현 우선순위

### Phase 1: MVP (필수)

1. **인증** - 로그인/로그아웃
2. **파일 업로드** - HWP 업로드
3. **HWP 파싱** - C1 서비스
4. **상담 CRUD** - 기본 CRUD
5. **에이전트 실행** - 단일 에이전트 실행

### Phase 2: 기본 기능

1. **패치 시스템** - C2 유틸리티
2. **변경 이력** - 히스토리 조회
3. **문서 생성** - DOCX 렌더링
4. **전체 파이프라인** - 에이전트 순차 실행

### Phase 3: 고도화

1. **토큰 갱신** - Refresh token
2. **PDF 변환** - DOCX → PDF
3. **역할 기반 권한** - RBAC
4. **실행 취소/재실행** - 에이전트 제어
