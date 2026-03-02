# Portfolio: SandboxIA

## AI 에이전트 엔지니어 포트폴리오

---

## 1. 프로젝트 개요

### 프로젝트명
**SandboxIA** - 규제 샌드박스 컨설팅 AI 에이전트 시스템

### 한 줄 요약
> 6개 전문 AI 에이전트가 협업하여 규제 샌드박스 신청의 대상성 판단, 트랙 추천, 신청서 자동 생성까지 엔드-투-엔드로 지원하는 멀티에이전트 시스템

### 문제 정의
규제 샌드박스 컨설턴트는 다음과 같은 구조적 비효율에 시달림:
- **비정형 데이터**: 기업 서비스 설명이 HWP, PDF, 자유 텍스트 등 다양한 형식으로 제공
- **파편화된 사례**: 수백 건의 승인/반려 사례가 여러 출처에 분산
- **반복 작업**: 매 건마다 유사한 형식의 신청서를 새로 작성
- **촉박한 기한**: 회신 기한 30일 → 15일 단축

### 솔루션
**LangGraph 기반 멀티에이전트 아키텍처**와 **3-도메인 Hybrid RAG 시스템**을 결합하여:
1. 비정형 입력을 표준화된 구조(Canonical Structure)로 변환
2. RAG 기반 근거 검색으로 대상성 판단 및 트랙 추천
3. 템플릿 기반 신청서 자동 생성
4. 실시간 진행 상태 스트리밍으로 사용자 경험 최적화

---

## 2. 시스템 아키텍처

### 전체 구조

```
┌────────────────────────────────────────────────────────────────────┐
│                    Client (Next.js 16 + React 19)                  │
│         ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│         │ TanStack    │  │ Zustand     │  │ SSE         │          │
│         │ Query 5     │  │ Persistence │  │ Streaming   │          │
│         └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────┬──────────────────────────────────┘
                                  │ REST API + Server-Sent Events
┌─────────────────────────────────▼──────────────────────────────────┐
│                   Server (FastAPI + LangGraph)                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Supervisor Agent                          │  │
│  │              (에이전트 오케스트레이션 & 라우팅)                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│           │             │             │             │              │
│      ┌────▼────┐   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐         │
│      │Service  │   │Eligib-  │   │Track    │   │Applic-  │         │
│      │Struct-  │   │ility    │   │Recomm-  │   │ation    │         │
│      │urer     │   │Evaluator│   │ender    │   │Drafter  │         │
│      └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘         │
│           │             │             │             │              │
│  ┌────────▼─────────────▼─────────────▼─────────────▼───────┐      │
│  │                Shared RAG Tools (R1, R2, R3)             │      │
│  └─────────────────────────────┬────────────────────────────┘      │
└────────────────────────────────┼───────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────┐
│                      RAG Infrastructure                            │
│    ┌──────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│    │ Embedding    │  │ Vector DB   │  │ Hybrid Search           │  │
│    │ KURE (Local) │  │ Qdrant      │  │ Dense 0.7 + BM25 0.3    │  │
│    └──────────────┘  └─────────────┘  └─────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

### 에이전트 파이프라인

```
[사용자 입력]
      │
      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  1. Service     │    │  2. Eligibility │    │  3. Track       │    │  4. Application │
│     Structurer  │───▶│     Evaluator   │───▶│     Recommender │───▶│     Drafter     │
│                 │    │                 │    │                 │    │                 │
│  HWP 파싱 →     │    │  병렬 RAG 검색   │    │  트랙별 점수    │    │  템플릿 기반    │
│  Canonical 변환 │    │  → 대상성 판정   │    │  → 최적 추천    │    │  → 초안 생성    │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            ┌─────────────┐      ┌─────────────┐
            │ 5. Strategy │      │ 6. Risk     │
            │    Advisor  │      │    Checker  │
            │             │      │             │
            │ 승인 패턴   │      │ QA 체크     │
            │ 전략 생성   │      │ 리스크 탐지 │
            └─────────────┘      └─────────────┘
```

---

## 3. 핵심 기술 역량

### 3.1 LangGraph 멀티에이전트 설계

#### Supervisor Pattern
- 6개 독립 에이전트의 실행 순서 및 상태 관리
- 조건부 라우팅으로 동적 워크플로우 구성
- 재귀 제한(recursion_limit=15)으로 무한 루프 방지

#### TypedDict 상태 관리
```python
class EligibilityState(TypedDict):
    # 입력
    project_id: str
    canonical: CanonicalStructure

    # 중간 RAG 결과
    screening_result: ScreeningResult
    regulation_results: list[RegulationChunk]
    case_results: list[CaseChunk]
    law_results: list[LawChunk]

    # 최종 출력
    eligibility_label: Literal["required", "not_required", "unclear"]
    confidence_score: float
    judgment_summary: list[JudgmentItem]
```

#### LangGraph 워크플로우 정의
```python
# Eligibility Evaluator 파이프라인
graph = StateGraph(EligibilityState)

graph.add_node("screen", screen_node)
graph.add_node("search_all_rag", parallel_rag_node)  # R1+R2+R3 병렬 검색
graph.add_node("compose_decision", compose_decision_node)
graph.add_node("generate_evidence", generate_evidence_node)

graph.add_edge(START, "screen")
graph.add_edge("screen", "search_all_rag")
graph.add_edge("search_all_rag", "compose_decision")
graph.add_edge("compose_decision", "generate_evidence")
graph.add_edge("generate_evidence", END)
```

---

### 3.2 3-도메인 Hybrid RAG 시스템

#### RAG 도메인 분리 설계

| RAG | 데이터 | 주요 활용 |
|-----|--------|----------|
| **R1** 규제제도 & 절차 | 트랙 정의, 절차, 요건, 심사 기준 | 대상성 판단, 트랙 추천, 신청서 작성 |
| **R2** 승인 사례 | 승인/반려 사례, 조건, 실증 범위 | 유사 사례 검색, 전략 조언 |
| **R3** 도메인별 법령 | 분야별 법령, 인허가 체계 | 규제 쟁점 분석, 법적 근거 |

#### Hybrid Search 구현

```python
class HybridSearchConfig:
    """Dense + Sparse 검색 설정"""
    enabled: bool = True
    alpha: float = 0.7           # Dense 가중치 70%
    sparse_model: str = "bm25"   # Sparse 가중치 30%


class QdrantHybridStore:
    def __init__(self, collection_name: str, config: HybridSearchConfig):
        self.client = QdrantClient()
        self.embedding = KUREEmbedding()  # 로컬 한국어 임베딩
        self.sparse_encoder = BM25Encoder()
        self.config = config

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter: dict | None = None
    ) -> list[Document]:
        # Dense vector (KURE 임베딩)
        dense_vector = self.embedding.embed(query)

        # Sparse vector (BM25)
        sparse_vector = self.sparse_encoder.encode(query)

        # Hybrid 검색 실행
        return self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(
                    query=dense_vector,
                    using="dense",
                    limit=top_k * 2,
                ),
                models.Prefetch(
                    query=sparse_vector,
                    using="sparse",
                    limit=top_k * 2,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k,
            query_filter=filter,
        )
```

#### 메타데이터 필터링

```python
@tool
def search_regulation(
    query: str,
    track: str | None = None,      # 신속확인/실증특례/임시허가
    category: str | None = None,   # overview/procedure/requirement
    ministry: str | None = None,   # 산업부/과기부/금융위
    top_k: int = 5
) -> RegulationSearchOutput:
    """규제 제도 검색 with 필터링"""

    # 입력 정규화
    track = normalize_track(track)
    category = normalize_category(category)
    ministry = normalize_ministry(ministry)

    # 필터 구성
    filter_conditions = _build_filter(track, category, ministry)

    # Hybrid 검색 실행
    results = vector_store.search(
        query=query,
        top_k=top_k,
        filter=filter_conditions
    )

    # 관련성 임계값 필터
    return [r for r in results if r.score >= RELEVANCE_THRESHOLD]
```

---

### 3.3 실시간 에이전트 상태 스트리밍

#### SSE (Server-Sent Events) 구현

**서버 측 (FastAPI)**
```python
@router.get("/agents/progress/subscribe/{project_id}")
async def subscribe_progress(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    async def event_generator():
        async for event in agent_progress_stream(project_id):
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

**클라이언트 측 (React Hook)**
```typescript
interface AgentProgressEvent {
  event_type: "agent_start" | "node_start" | "node_end" | "agent_end" | "error";
  node_id?: string;
  progress: number;  // 0-100
  completed_nodes: string[];
  message?: string;
}

export function useAgentProgress(options: UseAgentProgressOptions) {
  const [progress, setProgress] = useState<AgentProgressEvent | null>(null);

  const subscribe = useCallback(async () => {
    const response = await fetch(
      `${API_BASE}/agents/progress/subscribe/${options.projectId}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const data = decoder.decode(value);
      const event = parseSSEEvent(data);

      setProgress(event);
      options.onNodeComplete?.(event.node_id);
    }
  }, [options.projectId]);

  return { progress, subscribe };
}
```

---

### 3.4 클라이언트 상태 관리

#### Zustand + LocalStorage 영속성

```typescript
interface WizardState {
  currentStep: ProjectStep;          // 1-6
  completedSteps: ProjectStep[];
  serviceData: ServiceData | null;
  marketAnalysis: MarketAnalysis | null;
  trackSelection: Track | null;
  draftData: DraftData | null;
  selectedFormType: FormType;
}

export const useWizardStore = create<WizardState>()(
  persist(
    (set, get) => ({
      currentStep: 1,
      completedSteps: [],

      setCurrentStep: (step) => set({ currentStep: step }),

      completeStep: (step) => set((state) => ({
        completedSteps: [...new Set([...state.completedSteps, step])]
      })),

      reset: () => set({
        currentStep: 1,
        completedSteps: [],
        serviceData: null,
        // ...
      }),
    }),
    {
      name: "wizard-storage",
      storage: createJSONStorage(() => localStorage),
    }
  )
);
```

---

## 4. 기술 스택

### Backend (Python)
| 기술 | 버전 | 용도 |
|------|------|------|
| FastAPI | 0.128.* | 웹 프레임워크 |
| LangGraph | 1.0.5 | 에이전트 워크플로우 |
| LangChain | 1.2.* | LLM 프레임워크 |
| OpenAI | 2.14.0 | GPT-4o 모델 |
| Qdrant | - | 벡터 DB (Hybrid Search) |
| KURE | - | 로컬 한국어 임베딩 |
| Pydantic | 2.12.* | 데이터 검증 |
| Supabase | 2.0.0 | DB/Auth/Storage |
| RAGAS | 0.2.0 | RAG 평가 |

### Frontend (Node.js)
| 기술 | 버전 | 용도 |
|------|------|------|
| Next.js | 16.1.1 | 풀스택 프레임워크 |
| React | 19.2.3 | UI 라이브러리 |
| TypeScript | 5 | 타입 안정성 |
| TailwindCSS | 4 | 유틸리티 CSS |
| TanStack Query | 5 | 서버 상태 관리 |
| Zustand | 5.0.10 | 클라이언트 상태 |
| React Hook Form | 7 | 폼 관리 |
| Zod | 3.24.1 | 스키마 검증 |

### Infrastructure
| 기술 | 용도 |
|------|------|
| Supabase | PostgreSQL + Auth + Storage |
| Qdrant | 벡터 DB (Docker) |
| OpenAI API | LLM |
| Google Drive API | 데이터 다운로드 |
| LibreOffice | PDF 변환 |

### Deployment
| 기술 | 용도 |
|------|------|
| **AWS EC2** | Backend 서버 호스팅 (Ubuntu 22.04) |
| **Docker Compose** | 컨테이너 오케스트레이션 (FastAPI + ChromaDB) |
| **Vercel** | Frontend 배포 (Next.js SSR + Edge CDN) |
| **GitHub Container Registry** | Docker 이미지 저장소 |
| **Caddy** | Reverse Proxy + Auto HTTPS |

---

## 5. 배포 아키텍처

### Production Environment

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           Production Architecture                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────┐       ┌─────────────────────────────────┐  │
│   │         Vercel              │       │        AWS EC2 (Ubuntu)         │  │
│   │       (Frontend)            │       │          (Backend)              │  │
│   │                             │       │                                 │  │
│   │  ┌───────────────────────┐  │       │  ┌───────────────────────────┐  │  │
│   │  │    Next.js 16         │  │       │  │     Docker Compose        │  │  │
│   │  │    App Router         │  │       │  │                           │  │  │
│   │  │                       │  │       │  │  ┌─────────┐ ┌─────────┐  │  │  │
│   │  │  • Static Generation  │  │ HTTPS │  │  │ FastAPI │ │ChromaDB │  │  │  │
│   │  │  • SSR                │◀─┼───────┼─▶│  │  :8000  │ │  :8001  │  │  │  │
│   │  │  • Edge Functions     │  │       │  │  │         │ │         │  │  │  │
│   │  └───────────────────────┘  │       │  │  └────┬────┘ └────┬────┘  │  │  │
│   │                             │       │  │       │           │       │  │  │
│   │  Features:                  │       │  │       └─────┬─────┘       │  │  │
│   │  • Edge CDN (Global)        │       │  │     sandbox-network       │  │  │
│   │  • Auto HTTPS               │       │  └───────────────────────────┘  │  │
│   │  • Preview Deployments      │       │                                 │  │
│   │  • Analytics                │       │  Reverse Proxy: Caddy           │  │
│   └─────────────────────────────┘       │  Auto SSL: Let's Encrypt        │  │
│                                         └─────────────────────────────────┘  │
│                                                                              │
│   ┌───────────────────────────────────────────────────────────────────────┐  │
│   │                          External Services                            │  │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐   │  │
│   │   │  Supabase   │  │ OpenAI API  │  │    GHCR     │  │  GitHub    │   │  │
│   │   │  (DB/Auth/  │  │ (LLM/Embed) │  │  (Images)   │  │  Actions   │   │  │
│   │   │  Storage)   │  │             │  │             │  │  (CI/CD)   │   │  │
│   │   └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘   │  │
│   └───────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Docker Compose 구성

```yaml
services:
  api:
    image: ghcr.io/kernelacademy-aicamp/server-api:latest
    container_name: sandbox-api
    ports:
      - "8000:8000"
    depends_on:
      - chroma
    networks:
      - sandbox-network

  chroma:
    image: chromadb/chroma:1.4.1
    container_name: sandbox-chroma
    ports:
      - "8001:8000"
    volumes:
      - ./data/chroma:/data
    networks:
      - sandbox-network

networks:
  sandbox-network:
    driver: bridge
```

### CI/CD 파이프라인

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   GitHub     │     │   GitHub     │     │    GHCR /    │     │  AWS EC2 /   │
│   Push       │────▶│   Actions    │────▶│   Vercel     │────▶│   Vercel     │
│              │     │   (Build)    │     │   (Deploy)   │     │   (Live)     │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘

Frontend (client/):
  main push → Vercel auto-deploy → Edge CDN

Backend (server/):
  main push → Docker build → GHCR push → EC2 pull & restart
```

### 배포 명령어

**Frontend (Vercel):**
```bash
# CLI 배포
vercel --prod

# 또는 GitHub 연동으로 자동 배포 (main 브랜치 push 시)
```

**Backend (AWS EC2):**
```bash
# EC2 접속
ssh -i key.pem ubuntu@ec2-ip

# Docker Compose 실행
cd server
docker-compose pull
docker-compose up -d

# 로그 확인
docker-compose logs -f api
```

---

## 6. 데이터 흐름

### 엔드-투-엔드 처리 흐름

```
1. 클라이언트 입력 (HWP 파일 + 상담 정보)
   │
   ▼
2. POST /api/v1/agents/structure
   │  └─▶ Service Structurer Agent
   │       ├─ HWP 파싱 (hwp_parser)
   │       └─ Canonical Structure 생성
   │
   ▼
3. POST /api/v1/agents/eligibility
   │  └─▶ Eligibility Evaluator Agent
   │       ├─ Rule Screening (키워드 탐지)
   │       ├─ Parallel RAG Search
   │       │   ├─ R1: 규제제도 검색
   │       │   ├─ R2: 승인사례 검색
   │       │   └─ R3: 도메인법령 검색
   │       └─ Decision Composition (LLM 통합 판정)
   │
   ▼
4. POST /api/v1/agents/track
   │  └─▶ Track Recommender Agent
   │       ├─ 트랙별 적합도 스코어링
   │       ├─ 트랙 정의/요건 RAG (R1)
   │       └─ 유사 사례 기반 추천 (R2)
   │
   ▼
5. POST /api/v1/agents/draft
   │  └─▶ Application Drafter Agent
   │       ├─ 템플릿 선택 (docxtpl)
   │       ├─ 섹션별 데이터 매핑
   │       ├─ 문장 생성 (LLM)
   │       └─ DOCX/PDF 렌더링 (LibreOffice)
   │
   ▼
6. SSE /api/v1/agents/progress/subscribe/{projectId}
   │  └─▶ 실시간 진행 상태 스트리밍
   │       ├─ agent_start
   │       ├─ node_start / node_end (각 노드별)
   │       └─ agent_end / error
   │
   ▼
7. 클라이언트 UI 업데이트 (Zustand + TanStack Query)
```

---

## 7. RAG 평가 체계

### RAGAS 기반 평가 메트릭

| 메트릭 | 설명 |
|--------|------|
| **Context Precision** | 검색된 문서 중 관련 문서 비율 |
| **Context Recall** | 관련 문서 중 검색된 비율 |
| **NDCG** | 순위 기반 검색 품질 |
| **Answer Relevancy** | 답변의 질문 관련성 |
| **Faithfulness** | 답변의 컨텍스트 근거 정확도 |

### 평가 설정 (YAML)

```yaml
# eval/r3/configs/chunking.yaml
C0_baseline:
  chunk_unit: article
  prefix: none
  min_tokens: 50
  max_tokens: 512

C1_paragraph:
  chunk_unit: paragraph
  prefix: article_only
  min_tokens: 30
  max_tokens: 256

C2_multi_granularity:
  multi_granularity: [article, paragraph]
  prefix: law_and_article
```

```yaml
# eval/r3/configs/hybrid.yaml
H0_dense_only:
  enabled: false

H1_hybrid_07_03:
  enabled: true
  alpha: 0.7
  sparse_model: bm25

H2_hybrid_05_05:
  enabled: true
  alpha: 0.5
  sparse_model: bm25
```

### 평가 명령어

```bash
# 기본 평가 (Retrieval 메트릭)
uv run python eval/r3/run_evaluation.py --top_k 5 --config C1_paragraph

# LLM-as-Judge 평가
uv run python eval/r3/run_llm_evaluation.py --limit 10 --config H1_hybrid_07_03
```

---

## 8. 프로젝트 특징 및 차별점

### 8.1 실제 도메인 적용
- 추상적 데모가 아닌 **실제 규제 법령/제도 데이터** 활용
- 산업융합촉진법, ICT 규제샌드박스 등 실제 제도 반영

### 8.2 멀티에이전트 협업
- 단일 LLM 호출이 아닌 **6개 전문 에이전트 파이프라인**
- 각 에이전트의 역할과 책임 명확히 분리
- 상태 기반 데이터 흐름 관리

### 8.3 Advanced RAG
- **3-도메인 분리**: 제도/사례/법령 각각 최적화된 검색
- **Hybrid Search**: Dense (KURE) 70% + Sparse (BM25) 30%
- **메타데이터 필터링**: 트랙/카테고리/부처별 정밀 검색
- **로컬 임베딩**: KURE 모델로 비용 절감 + 한국어 특화

### 8.4 실시간 UX
- SSE 기반 **에이전트 진행 상태 실시간 스트리밍**
- Zustand 영속성으로 **세션 복구** 지원
- 노드별 진행률 표시로 **투명한 처리 과정**

### 8.5 평가 체계
- RAGAS 기반 **Retrieval 품질 지속 측정**
- 청킹/임베딩/Hybrid 설정별 **A/B 테스트** 지원
- LLM-as-Judge로 **생성 품질 평가**

---

## 9. 기술적 도전과 해결

### Challenge 1: 비정형 HWP 문서 파싱
**문제**: 단순상담/신속확인/임시허가/실증특례 양식이 모두 다름

**해결**:
- 문서 타입 자동 감지 로직 구현
- 양식별 섹션 매핑 규칙 정의
- Canonical Structure로 통일된 출력 보장

### Challenge 2: 병렬 RAG 검색 최적화
**문제**: R1, R2, R3 순차 검색 시 지연 발생

**해결**:
- `asyncio.gather()`로 3개 RAG 병렬 실행
- 검색 결과 통합 후 LLM에 전달
- 약 60% 응답 시간 단축

### Challenge 3: 한국어 임베딩 품질
**문제**: 영어 기반 임베딩 모델의 한국어 성능 한계

**해결**:
- KURE 로컬 모델 도입 (한국어 특화)
- BM25와 Hybrid 검색으로 키워드 매칭 보완
- 도메인별 평가셋으로 성능 검증

---

## 10. 향후 개선 계획

1. **Strategy Advisor / Risk Checker 에이전트 고도화**
   - 승인 패턴 추출 및 전략 생성
   - 심사관 관점 QA 체크리스트

2. **RAG 성능 최적화**
   - Re-ranking 모델 도입
   - Query Expansion/Decomposition

3. **사용자 피드백 루프**
   - 컨설턴트 수정 이력 학습
   - 개인화된 문체/표현 반영

---

## 11. 연락처

- **GitHub**: [Repository Link]
- **Email**: [Contact Email]
- **LinkedIn**: [Profile Link]

---

*이 프로젝트는 AI 에이전트 엔지니어링의 실제 적용 사례로, 멀티에이전트 설계, Advanced RAG, 실시간 스트리밍 등 현대 AI 시스템의 핵심 기술을 종합적으로 다룹니다.*
