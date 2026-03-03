"""규제제도 데이터 수집 및 Vector DB 저장 스크립트

R1. 규제제도 & 절차 RAG Tool용 데이터 수집

데이터 소스:
- 환경변수 R1_DATA_ID가 설정된 경우: Google Drive에서 다운로드
- 미설정 시: data/r1/r1_rag_ict_only.json (로컬 fallback)

실행:
    cd server

    # 기본 실행 (E1 임베딩 + Qdrant + H3 Hybrid)
    uv run python scripts/collect_regulations.py

    # Chroma 사용 (기존 방식)
    uv run python scripts/collect_regulations.py --vectordb chroma --embedding E0
"""

import json
import sys
import tempfile
from pathlib import Path

import gdown

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.documents import Document

from app.core.config import settings
from app.core.constants import COLLECTION_REGULATIONS
from app.db.export import save_chunks_json
from app.db.vector import HybridSearchConfig, create_embeddings, create_vector_store
from app.rag.config import load_embedding_config, load_hybrid_config

# 로컬 데이터 파일 (fallback)
LOCAL_DATA_FILE = (
    Path(__file__).parent.parent / "data" / "r1_data" / "r1_rag_ict_only.json"
)

# 카테고리 영문 코드 매핑
CATEGORY_CODE_MAPPING = {
    "제도정의": "definition",
    "트랙정의": "track_definition",
    "절차": "procedure",
    "제출요건": "requirement",
    "심사기준": "criteria",
    "트랙비교": "comparison",
    "부처별차이": "ministry",
    "제도변경": "changes",
    "법적근거": "legal_basis",
    "일반": "general",
}

# 트랙 정규화 매핑
TRACK_MAPPING = {
    "공통": "all",
    "신속확인": "신속확인",
    "실증특례": "실증특례",
    "임시허가": "임시허가",
}


def load_json_data() -> tuple[list[dict], str]:
    """JSON 데이터 로드 (Google Drive 폴더 또는 로컬 파일)

    Returns:
        (데이터 리스트, 소스 경로/URL)
    """
    # 환경변수에 Google Drive 폴더 ID가 설정된 경우 다운로드
    if settings.R1_DATA_ID:
        folder_url = f"{settings.GOOGLE_DRIVE_URL}{settings.R1_DATA_ID}"
        print("Google Drive 폴더에서 데이터 다운로드 중...")
        print(f"  Folder ID: {settings.R1_DATA_ID}")

        # 임시 디렉토리에 폴더 다운로드
        tmp_dir = tempfile.mkdtemp()
        gdown.download_folder(folder_url, output=tmp_dir, quiet=False)

        # 다운로드된 폴더에서 JSON 파일 찾기
        json_files = list(Path(tmp_dir).rglob("*.json"))
        if not json_files:
            raise FileNotFoundError(
                f"Google Drive 폴더에서 JSON 파일을 찾을 수 없습니다.\n"
                f"폴더 ID: {settings.R1_DATA_ID}"
            )

        # 첫 번째 JSON 파일 사용 (또는 특정 파일명 매칭)
        json_file = json_files[0]
        print(f"  [OK] JSON 파일 발견: {json_file.name}")

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 임시 디렉토리 삭제
        import shutil

        shutil.rmtree(tmp_dir)

        return data, f"Google Drive Folder (ID: {settings.R1_DATA_ID})"

    # 로컬 파일 사용 (fallback)
    if not LOCAL_DATA_FILE.exists():
        raise FileNotFoundError(
            f"데이터 파일을 찾을 수 없습니다.\n"
            f"- R1_DATA_ID 환경변수를 설정하거나\n"
            f"- {LOCAL_DATA_FILE} 파일을 생성하세요."
        )

    print(f"로컬 파일에서 데이터 로드: {LOCAL_DATA_FILE}")
    with open(LOCAL_DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data, str(LOCAL_DATA_FILE)


def create_documents(data: list[dict]) -> tuple[list[Document], list[str]]:
    """JSON 데이터를 Document 리스트로 변환

    Returns:
        (documents, ids): 문서 리스트와 ID 리스트 튜플
    """
    documents = []
    doc_ids = []

    for idx, item in enumerate(data):
        # 카테고리 코드 변환
        category = item.get("category", "general")
        category_code = CATEGORY_CODE_MAPPING.get(category, "general")

        # 트랙 정규화
        track = item.get("track", "공통")
        normalized_track = TRACK_MAPPING.get(track, "all")

        # 청크 내용 구성
        title = item.get("title", "")
        content = item.get("content", "")
        chunk_content = f"[{title}]\n\n{content}"

        # 인용 형식 생성
        citation = f"{category} > {title}"

        doc = Document(
            page_content=chunk_content,
            metadata={
                "source_type": "regulation",
                "source_file": item.get("source", ""),
                "source_url": item.get("source_url", ""),
                "document_id": item.get("id", ""),
                "document_title": title,
                "section_title": title,
                "track": normalized_track,
                "category": category_code,
                "category_label": category,
                "ministry": item.get("ministry", "all"),
                "citation": citation,
            },
        )
        # ID 생성: reg_{document_id} 또는 reg_{index}
        source_id = item.get("id", "")
        doc_id = f"reg_{source_id}" if source_id else f"reg_{idx}"
        documents.append(doc)
        doc_ids.append(doc_id)

    return documents, doc_ids


def collect_and_store_regulations(
    reset: bool = True,
    export_chunks: bool = False,
    embedding_config: str | None = None,
    vectordb_type: str = "qdrant",
    hybrid_config_name: str | None = None,
):
    """규제제도 데이터 수집 및 Vector DB 저장

    Args:
        reset: True면 기존 컬렉션 삭제 후 새로 생성
        export_chunks: True면 청크 JSON도 함께 저장 (평가셋 작성용)
        embedding_config: 임베딩 설정 이름 (E0, E1 등). None이면 RAG 기본값(E1) 사용
        vectordb_type: Vector DB 타입 (qdrant 또는 chroma)
        hybrid_config_name: Hybrid Search 설정 이름 (H0~H7). None이면 RAG 기본값(H3) 사용
    """
    print("=" * 60)
    print("규제제도 데이터 수집 시작 (R1 RAG Tool)")
    print("=" * 60)

    # JSON 데이터 로드 (URL 또는 로컬 파일)
    try:
        data, source_path = load_json_data()
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return

    print(f"\n[데이터 소스] {source_path}")
    print(f"  [OK] 로드된 청크: {len(data)}개")

    # 통계 출력
    categories = {}
    tracks = {}
    for item in data:
        cat = item.get("category", "unknown")
        track = item.get("track", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
        tracks[track] = tracks.get(track, 0) + 1

    print("\n[카테고리 분포]")
    for k, v in sorted(categories.items()):
        print(f"  - {k}: {v}개")

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
                client.delete_collection(COLLECTION_REGULATIONS)
                print(f"\n[OK] 기존 Qdrant 컬렉션 '{COLLECTION_REGULATIONS}' 삭제")
            except Exception:
                pass
        else:
            import chromadb

            persist_dir = Path(settings.CHROMA_PERSIST_DIR)
            persist_dir.mkdir(parents=True, exist_ok=True)
            try:
                client = chromadb.PersistentClient(path=str(persist_dir))
                client.delete_collection(COLLECTION_REGULATIONS)
                print(f"\n[OK] 기존 Chroma 컬렉션 '{COLLECTION_REGULATIONS}' 삭제")
            except Exception:
                pass

    # VectorStore 생성
    vectorstore = create_vector_store(
        collection_name=COLLECTION_REGULATIONS,
        embeddings=embeddings,
        vectordb_type=vectordb_type,
        hybrid_config=hybrid_config,
    )
    print(f"\n[Vector DB] {vectordb_type.upper()}")

    # Document 생성
    documents, document_ids = create_documents(data)
    print(f"\n{'=' * 60}")
    print(f"총 {len(documents)}개 문서 생성 완료")
    print("Vector DB에 저장 중...")

    # Vector DB에 저장 (ID 포함)
    vectorstore.add_documents(documents, ids=document_ids)

    print("[OK] Vector DB 저장 완료!")

    # 청크 JSON 저장 (평가용, 플래그가 True일 때만)
    if export_chunks:
        chunks_json_path = Path(__file__).parent.parent / "data" / "r1_data" / "chunks.json"
        saved_count = save_chunks_json(documents, document_ids, chunks_json_path)
        print(f"[OK] 청크 JSON 저장 완료: {chunks_json_path} ({saved_count}개)")

    print("\n" + "=" * 60)
    print("수집 완료 요약:")
    print("=" * 60)
    print(f"  - 소스: {source_path}")
    print(f"  - 총 청크 수: {len(documents)}개")
    print(f"  - Vector DB: {vectordb_type.upper()}")
    print(f"  - 임베딩: {emb_config.name} ({emb_config.model})")
    if hybrid_config:
        print(f"  - Hybrid: alpha={hybrid_config.alpha}, sparse={hybrid_config.sparse_model}")
    print(f"  - 컬렉션명: {COLLECTION_REGULATIONS}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="규제제도 데이터 수집 및 Vector DB 저장")
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

    collect_and_store_regulations(
        reset=True,
        export_chunks=args.export_chunks,
        embedding_config=args.embedding,
        vectordb_type=args.vectordb,
        hybrid_config_name=args.hybrid,
    )
