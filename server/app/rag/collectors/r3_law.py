"""법령 데이터 수집 모듈 (R3 RAG)

법령 API에서 데이터를 수집하고 Vector DB에 저장합니다.
"""

import json
from pathlib import Path

from langchain_chroma import Chroma

from app.core.config import settings
from app.core.constants import COLLECTION_LAWS
from app.db.export import save_chunks_json
from app.db.vector import create_embeddings
from app.rag.chunkers.r3_law import LawChunker
from app.rag.config import ChunkingConfig, EmbeddingConfig
from app.services.law_api import law_api_client

# =============================================================================
# 수집 대상 법령
# =============================================================================

TARGET_LAWS = [
    ("의료법", "healthcare"),
    ("전자금융거래법", "finance"),
    ("데이터 산업진흥 및 이용촉진에 관한 기본법", "data"),
    ("신용정보의 이용 및 보호에 관한 법률", "finance"),
    ("개인정보 보호법", "privacy"),
    ("전기통신사업법", "telecom"),
    ("정보통신 진흥 및 융합 활성화 등에 관한 특별법", "telecom"),
    ("산업융합 촉진법", "regulation"),
    ("금융혁신지원 특별법", "regulation"),
    ("규제자유특구 및 지역특화발전특구에 관한 규제특례법", "regulation"),
    ("행정규제기본법", "regulation"),
]

DOMAIN_LABELS = {
    "healthcare": "의료/헬스케어",
    "finance": "금융",
    "data": "데이터",
    "privacy": "개인정보",
    "telecom": "통신/ICT",
    "regulation": "규제/제도",
}


# =============================================================================
# 메인 수집 함수
# =============================================================================


async def collect_and_store_laws(
    config: ChunkingConfig,
    export_chunks: bool = False,
    collection_suffix: str = "",
    reset: bool = False,
    embedding_config: EmbeddingConfig | None = None,
):
    """법령 데이터 수집 및 Vector DB 저장

    Args:
        config: 청킹 설정
        export_chunks: 청크 JSON 내보내기 여부
        collection_suffix: 컬렉션 이름에 붙일 접미사
        reset: 기존 컬렉션 삭제 후 새로 생성 여부
        embedding_config: 임베딩 설정 (None이면 .env의 LLM_EMBEDDING_MODEL 사용)
    """

    print("=" * 60)
    print("법령 데이터 수집 시작")
    print(f"청킹 설정: {config.name} - {config.description}")
    print("=" * 60)

    print("\n[청킹 설정]")
    print(f"  - 청킹 단위: {config.chunk_unit.value}")
    print(f"  - 멀티 그래뉼러리티: {[g.value for g in config.multi_granularity] or '없음'}")
    print(f"  - prefix: {config.prefix.value}")
    print(f"  - hybrid: {config.hybrid}")
    if config.hybrid:
        print(f"  - min/max tokens: {config.min_tokens} / {config.max_tokens}")
    print(f"  - overlap: {config.overlap}")
    print(f"  - top_k: {config.top_k}")

    # 임베딩 모델 결정
    if embedding_config:
        # E* 프리셋 지정 시: 프리셋 설정 사용 (평가용)
        print(f"\n[임베딩 설정] {embedding_config.name} - {embedding_config.description}")
        print(f"  - 모델: {embedding_config.model}")
        print(f"  - 제공자: {embedding_config.provider}")
        print(f"  - 차원: {embedding_config.dimension}")
        embeddings = create_embeddings(embedding_config)
    else:
        # 기본값: .env의 LLM_EMBEDDING_MODEL 사용 (운영용)
        from langchain_openai import OpenAIEmbeddings

        print(f"\n[임베딩 설정] .env 기본값: {settings.LLM_EMBEDDING_MODEL}")
        embeddings = OpenAIEmbeddings(
            model=settings.LLM_EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )

    chunker = LawChunker(config)

    persist_dir = Path(settings.CHROMA_PERSIST_DIR)
    persist_dir.mkdir(parents=True, exist_ok=True)

    collection_name = COLLECTION_LAWS + collection_suffix

    # 기존 컬렉션 삭제 (reset 옵션)
    if reset:
        import chromadb

        print(f"\n[컬렉션 초기화] '{collection_name}' 삭제 중...")
        client = chromadb.PersistentClient(path=str(persist_dir))
        try:
            client.delete_collection(name=collection_name)
            print("  ✓ 기존 컬렉션 삭제 완료")
        except ValueError:
            print("  - 기존 컬렉션 없음 (새로 생성)")

    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )

    documents = []
    document_ids = []
    seen_ids: set[str] = set()
    collected_laws = []

    for law_name, domain in TARGET_LAWS:
        print(f"\n[{law_name}] 검색 중...")

        law_summary = await law_api_client.search_law_by_name(law_name)
        if not law_summary:
            print(f"  ⚠️  '{law_name}' 법령을 찾을 수 없습니다.")
            continue

        print(f"  [OK] 발견: {law_summary.name} (MST: {law_summary.mst})")
        print(f"    - 소관부처: {law_summary.ministry}")
        print(f"    - 시행일자: {law_summary.enforcement_date}")

        law_detail = await law_api_client.get_law_detail(law_summary.mst)
        if not law_detail:
            print("  ⚠️  본문 조회 실패")
            continue

        print(f"  [OK] 조문 수: {len(law_detail.articles)}개")

        law_doc_count = 0
        for article in law_detail.articles:
            article_docs, article_ids = chunker.create_chunks(
                article=article,
                law_name=law_detail.name,
                domain=domain,
                domain_label=DOMAIN_LABELS.get(domain, domain),
                ministry=law_detail.ministry,
                enforcement_date=law_detail.enforcement_date,
                mst=law_summary.mst,
            )
            documents.extend(article_docs)
            document_ids.extend(article_ids)
            law_doc_count += len(article_docs)

        print(f"  [OK] 생성된 청크: {law_doc_count}개")

        collected_laws.append(
            {
                "name": law_detail.name,
                "mst": law_summary.mst,
                "domain": domain,
                "article_count": len(law_detail.articles),
                "chunk_count": law_doc_count,
            }
        )

    if not documents:
        print("\n⚠️  수집된 문서가 없습니다.")
        return

    # 중복 ID 해결
    unique_ids = []
    duplicate_count = 0
    for doc_id in document_ids:
        if doc_id in seen_ids:
            duplicate_count += 1
            suffix = 1
            new_id = f"{doc_id}_{suffix}"
            while new_id in seen_ids:
                suffix += 1
                new_id = f"{doc_id}_{suffix}"
            doc_id = new_id
        seen_ids.add(doc_id)
        unique_ids.append(doc_id)

    if duplicate_count > 0:
        print(f"\n⚠️  중복 ID {duplicate_count}개 발견 → suffix 추가로 해결")

    print(f"\n{'=' * 60}")
    print(f"총 {len(documents)}개 문서 생성 완료")
    print("Vector DB에 저장 중...")

    # 배치 크기 제한 (ChromaDB max batch size: 5461)
    batch_size = 5000
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i : i + batch_size]
        batch_ids = unique_ids[i : i + batch_size]
        vectorstore.add_documents(batch_docs, ids=batch_ids)
        print(f"  - 배치 {i // batch_size + 1}: {len(batch_docs)}개 저장 완료")

    print("[OK] Vector DB 저장 완료!")
    print(f"  - 컬렉션: {collection_name}")

    if export_chunks:
        chunks_dir = Path(__file__).parent.parent.parent.parent / "data" / "r3_data"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        chunks_json_path = chunks_dir / f"chunks_{config.name}.json"
        saved_count = save_chunks_json(documents, unique_ids, chunks_json_path)
        print(f"[OK] 청크 JSON 저장 완료: {chunks_json_path} ({saved_count}개)")

    result_file = persist_dir / "r3_collection_info.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "config": {
                    "name": config.name,
                    "description": config.description,
                    "chunk_unit": config.chunk_unit.value,
                    "multi_granularity": [g.value for g in config.multi_granularity],
                    "prefix": config.prefix.value,
                    "hybrid": config.hybrid,
                    "min_tokens": config.min_tokens,
                    "max_tokens": config.max_tokens,
                    "overlap": config.overlap,
                    "top_k": config.top_k,
                },
                "total_documents": len(documents),
                "laws": collected_laws,
                "domains": list(DOMAIN_LABELS.keys()),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n수집 정보 저장: {result_file}")
    print("\n" + "=" * 60)
    print("수집 완료 요약:")
    print("=" * 60)
    for law in collected_laws:
        print(f"  - {law['name']}: {law['article_count']}개 조문 → {law['chunk_count']}개 청크 ({law['domain']})")
    print(f"\n총 청크 수: {len(documents)}개")
    print(f"저장 위치: {persist_dir}")
