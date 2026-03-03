"""승인 사례 데이터 수집 및 Vector DB 저장 스크립트

R2. 승인 사례 RAG Tool용 데이터 수집

데이터 소스: 환경변수 R2_DATA_ID로 지정된 Google Drive 폴더에서 다운로드

실행:
    cd server

    # 기본 실행 (E1 임베딩 + Qdrant + H3 Hybrid)
    uv run python scripts/collect_cases.py

    # 전략 변경
    uv run python scripts/collect_cases.py --strategy hybrid

    # Chroma 사용 (기존 방식)
    uv run python scripts/collect_cases.py --vectordb chroma --embedding E0
"""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

VALID_STRATEGIES = ("structured", "hybrid", "fulltext")

import gdown

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.documents import Document

from app.core.config import settings
from app.core.constants import COLLECTION_CASES
from app.db.export import save_chunks_json
from app.db.vector import HybridSearchConfig, create_embeddings, create_vector_store
from app.rag.config import load_embedding_config, load_hybrid_config

# 다운로드된 JSON 캐싱 경로
LOCAL_CACHE_FILE = Path(__file__).parent.parent / "data" / "r2_data" / "cases_structured.json"


def load_json_data() -> tuple[list[dict], str]:
    """Google Drive 폴더에서 JSON 데이터 다운로드

    Returns:
        (데이터 리스트, 소스 경로/URL)
    """
    if not settings.R2_DATA_ID:
        raise RuntimeError(
            "R2_DATA_ID 환경변수가 설정되지 않았습니다.\n"
            ".env 파일에 R2_DATA_ID=<Google Drive 폴더 ID>를 추가하세요."
        )

    folder_url = f"{settings.GOOGLE_DRIVE_URL}{settings.R2_DATA_ID}"
    print("Google Drive 폴더에서 데이터 다운로드 중...")
    print(f"  Folder ID: {settings.R2_DATA_ID}")

    # 임시 디렉토리에 폴더 다운로드
    tmp_dir = tempfile.mkdtemp()
    try:
        gdown.download_folder(folder_url, output=tmp_dir, quiet=False)

        # 다운로드된 폴더에서 JSON 파일 찾기
        tmp_path = Path(tmp_dir)
        json_file = None

        for item in tmp_path.iterdir():
            if item.name == "cases_structured.json":
                json_file = item
                break

        if not json_file:
            # 모든 JSON 파일 검색
            json_files = list(tmp_path.rglob("*.json"))
            if json_files:
                json_file = json_files[0]

        if not json_file:
            raise FileNotFoundError(
                f"Google Drive 폴더에서 JSON 파일을 찾을 수 없습니다.\n" f"폴더 ID: {settings.R2_DATA_ID}"
            )

        print(f"  [OK] JSON 파일 발견: {json_file.name}")

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 로컬에 JSON 파일 복사 (캐싱)
        LOCAL_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(json_file, LOCAL_CACHE_FILE)
        print(f"  [OK] 로컬에 캐싱: {LOCAL_CACHE_FILE}")

        return data, f"Google Drive Folder (ID: {settings.R2_DATA_ID})"

    finally:
        # 임시 디렉토리 삭제
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass


def _build_structured_content(case: dict) -> str:
    """structured 전략: 유효 필드만 조합 (baseline)"""
    track = case.get("track", "")
    common = case.get("common_info", {})
    companies = case.get("companies", [])

    service_name = common.get("service_name", "")
    service_description = common.get("service_description", "")
    special_provisions = common.get("special_provisions", "")
    pilot_scope = common.get("pilot_scope", "")
    conditions = common.get("conditions", [])

    company_names = [c.get("company_name", "") for c in companies if c.get("company_name")]

    # conditions 리스트 → 텍스트
    conditions_text = ""
    if conditions:
        conditions_text = "조건: " + " / ".join(conditions)

    content_parts = [
        f"[{track}] {service_name}",
        f"기업: {', '.join(company_names)}" if company_names else "",
        f"서비스 설명: {service_description}" if service_description else "",
        f"특례 내용: {special_provisions}" if special_provisions else "",
        f"실증 범위: {pilot_scope}" if pilot_scope else "",
        conditions_text,
    ]
    return "\n".join([p for p in content_parts if p])


def create_documents(
    data: list[dict], strategy: str = "structured"
) -> tuple[list[Document], list[str]]:
    """JSON 데이터를 Document 리스트로 변환

    Args:
        data: 케이스 데이터 리스트
        strategy: 데이터 전략 (structured / hybrid / fulltext)

    Returns:
        (documents, ids): 문서 리스트와 ID 리스트 튜플
    """
    documents = []
    doc_ids = []

    for case in data:
        case_id = case.get("case_id", "")
        track = case.get("track", "")
        common = case.get("common_info", {})
        companies = case.get("companies", [])

        company_names = [c.get("company_name", "") for c in companies if c.get("company_name")]
        company_name = company_names[0] if company_names else ""

        # 지정번호
        designation_number = ""
        for c in companies:
            if c.get("designation_number"):
                designation_number = c.get("designation_number")
                break

        # 전략별 content 구성
        if strategy == "fulltext":
            content = case.get("full_text", "")
        else:
            content = _build_structured_content(case)
            if strategy == "hybrid" and len(content) < 100:
                full_text = case.get("full_text", "")
                if full_text:
                    content = full_text

        # 빈 content 스킵 (임베딩 불가)
        if not content or not content.strip():
            print(f"  [WARN] 빈 content 스킵: {case_id} (strategy={strategy})")
            continue

        service_name = common.get("service_name", "")
        citation = f"{track} - {service_name} ({company_name})"

        doc = Document(
            page_content=content,
            metadata={
                "source_type": "case",
                "case_id": case_id,
                "track": track,
                "service_name": service_name,
                "company_name": company_name,
                "designation_number": designation_number,
                "source_url": case.get("source_url", ""),
                "citation": citation,
                "strategy": strategy,
            },
        )
        doc_id = f"case_{case_id}" if case_id else f"case_{len(documents)}"
        documents.append(doc)
        doc_ids.append(doc_id)

    return documents, doc_ids


def collect_and_store_cases(
    reset: bool = True,
    strategy: str = "structured",
    export_chunks: bool = False,
    embedding_config: str | None = None,
    vectordb_type: str = "qdrant",
    hybrid_config_name: str | None = None,
):
    """승인 사례 데이터 수집 및 Vector DB 저장

    Args:
        reset: True면 기존 컬렉션 삭제 후 새로 생성
        strategy: 데이터 전략 (structured / hybrid / fulltext)
        export_chunks: True면 청크 JSON도 함께 저장 (평가셋 작성용)
        embedding_config: 임베딩 설정 이름 (E0, E1 등). None이면 RAG 기본값(E1) 사용
        vectordb_type: Vector DB 타입 (qdrant 또는 chroma)
        hybrid_config_name: Hybrid Search 설정 이름 (H0~H7). None이면 RAG 기본값(H3) 사용
    """
    print("=" * 60)
    print(f"승인 사례 데이터 수집 시작 (R2 RAG Tool) [전략: {strategy}]")
    print("=" * 60)

    # JSON 데이터 로드 (URL 또는 로컬 파일)
    try:
        data, source_path = load_json_data()
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return

    print(f"\n[데이터 소스] {source_path}")
    print(f"  [OK] 로드된 케이스: {len(data)}개")

    # 통계 출력
    tracks = {}
    for item in data:
        track = item.get("track", "unknown")
        tracks[track] = tracks.get(track, 0) + 1

    print("\n[트랙 분포]")
    for k, v in sorted(tracks.items()):
        print(f"  - {k}: {v}개")

    # 임베딩 모델 초기화 (기본값: E1)
    if embedding_config:
        try:
            emb_config = load_embedding_config(embedding_config, rag_type="r3")
        except FileNotFoundError:
            print(f"\n[경고] 설정 '{embedding_config}'을 찾을 수 없습니다. 기본값(E1) 사용")
            emb_config = load_embedding_config("E1", rag_type="r3")
    else:
        emb_config = load_embedding_config("E1", rag_type="r3")

    print(f"\n[임베딩 설정] {emb_config.name}: {emb_config.description}")
    print(f"  - 모델: {emb_config.model}")
    print(f"  - Provider: {emb_config.provider}")
    print(f"  - 차원: {emb_config.dimension}")

    embeddings = create_embeddings(emb_config)

    # Hybrid Search 설정 (기본값: H3)
    hybrid_config = None
    if vectordb_type == "qdrant":
        h_cfg_name = hybrid_config_name or "H3"
        try:
            h_cfg = load_hybrid_config(h_cfg_name, rag_type="r3")
        except FileNotFoundError:
            print(f"\n[경고] Hybrid 설정 '{h_cfg_name}'을 찾을 수 없습니다. H3 사용")
            h_cfg = load_hybrid_config("H3", rag_type="r3")
        hybrid_config = HybridSearchConfig(
            enabled=True,
            alpha=h_cfg.alpha,
            sparse_model=h_cfg.sparse_model,
        )
        print(f"\n[Hybrid 설정] {h_cfg.name}: {h_cfg.description}")
        print(f"  - Sparse 모델: {hybrid_config.sparse_model}")
        print(f"  - Alpha: {hybrid_config.alpha} (Dense {hybrid_config.alpha*100:.0f}%)")

    # 기존 컬렉션 삭제 (reset=True인 경우)
    if reset:
        if vectordb_type == "qdrant":
            from qdrant_client import QdrantClient

            try:
                client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
                client.delete_collection(COLLECTION_CASES)
                print(f"\n[OK] 기존 Qdrant 컬렉션 '{COLLECTION_CASES}' 삭제")
            except Exception:
                pass
        else:
            import chromadb

            persist_dir = Path(settings.CHROMA_PERSIST_DIR)
            persist_dir.mkdir(parents=True, exist_ok=True)
            try:
                client = chromadb.PersistentClient(path=str(persist_dir))
                client.delete_collection(COLLECTION_CASES)
                print(f"\n[OK] 기존 Chroma 컬렉션 '{COLLECTION_CASES}' 삭제")
            except Exception:
                pass

    # VectorStore 생성
    vectorstore = create_vector_store(
        collection_name=COLLECTION_CASES,
        embeddings=embeddings,
        vectordb_type=vectordb_type,
        hybrid_config=hybrid_config,
    )
    print(f"\n[Vector DB] {vectordb_type.upper()}")

    # Document 생성
    documents, document_ids = create_documents(data, strategy=strategy)
    print(f"\n{'=' * 60}")
    print(f"총 {len(documents)}개 문서 생성 완료")
    print("Vector DB에 저장 중...")

    # Vector DB에 저장 (ID 포함)
    vectorstore.add_documents(documents, ids=document_ids)

    print("[OK] Vector DB 저장 완료!")

    # 청크 JSON 저장 (평가용, 플래그가 True일 때만)
    if export_chunks:
        chunks_json_path = Path(__file__).parent.parent / "data" / "r2_data" / "chunks.json"
        saved_count = save_chunks_json(documents, document_ids, chunks_json_path)
        print(f"[OK] 청크 JSON 저장 완료: {chunks_json_path} ({saved_count}개)")

    print("\n" + "=" * 60)
    print("수집 완료 요약:")
    print("=" * 60)
    print(f"  - 전략: {strategy}")
    print(f"  - 소스: {source_path}")
    print(f"  - 총 케이스 수: {len(documents)}개")
    print(f"  - Vector DB: {vectordb_type.upper()}")
    print(f"  - 임베딩: {emb_config.name} ({emb_config.model})")
    if hybrid_config:
        print(f"  - Hybrid: alpha={hybrid_config.alpha}, sparse={hybrid_config.sparse_model}")
    print(f"  - 컬렉션명: {COLLECTION_CASES}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="R2 승인 사례 수집 및 Vector DB 저장")
    parser.add_argument(
        "--strategy",
        choices=VALID_STRATEGIES,
        default="structured",
        help="데이터 전략: structured(기본) / hybrid / fulltext",
    )
    parser.add_argument(
        "--export-chunks",
        action="store_true",
        help="청크 JSON도 함께 저장 (평가셋 작성용)",
    )
    parser.add_argument(
        "--embedding",
        default=None,
        help="임베딩 설정 (E0=OpenAI-small, E1=OpenAI-large). 미지정 시 E1 사용",
    )
    parser.add_argument(
        "--vectordb",
        type=str,
        choices=["chroma", "qdrant"],
        default="qdrant",
        help="사용할 Vector DB (기본: qdrant)",
    )
    parser.add_argument(
        "--hybrid",
        type=str,
        default=None,
        help="Hybrid Search 설정 (H0~H7). 미지정 시 H3 사용. Qdrant 전용",
    )
    args = parser.parse_args()
    collect_and_store_cases(
        reset=True,
        strategy=args.strategy,
        export_chunks=args.export_chunks,
        embedding_config=args.embedding,
        vectordb_type=args.vectordb,
        hybrid_config_name=args.hybrid,
    )
