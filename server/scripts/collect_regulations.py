"""규제제도 데이터 수집 및 Vector DB 저장 스크립트

R1. 규제제도 & 절차 RAG Tool용 데이터 수집

데이터 소스:
- 환경변수 R1_DATA_ID가 설정된 경우: Google Drive에서 다운로드
- 미설정 시: data/r1/r1_rag_ict_only.json (로컬 fallback)

실행:
    cd server
    uv run python scripts/collect_regulations.py
"""

import json
import re
import sys
import tempfile
from pathlib import Path

import gdown

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.core.config import settings
from app.core.constants import COLLECTION_REGULATIONS
from app.db.export import save_chunks_json
from app.db.vector import create_embeddings
from app.rag.config import load_embedding_config

# 로컬 데이터 파일 (fallback)
LOCAL_DATA_FILE = (
    Path(__file__).parent.parent / "data" / "r1_data" / "r1_rag_ict_only.json"
)
# chunks.json (기존 청크 데이터, 원본 없을 때 사용)
CHUNKS_FILE = Path(__file__).parent.parent / "data" / "r1_data" / "chunks.json"

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

# ASCII 박스 문자 패턴
ASCII_BOX_CHARS = re.compile(r"[┌┐└┘│─├┤┬┴┼╔╗╚╝║═╠╣╦╩╬▶▼◀▲→←↑↓]")
ASCII_BOX_LINE = re.compile(r"^[\s│┌┐└┘├┤┬┴┼─╔╗╚╝║═╠╣╦╩╬▶▼◀▲→←↑↓\|+\-=]+$")


def clean_ascii_art(content: str) -> str:
    """ASCII 박스 다이어그램 제거 및 텍스트 정제

    고정폭 기반 ASCII 아트는 반응형 UI에서 깨지므로 제거하고
    실제 텍스트 정보만 추출합니다.
    """
    lines = content.split("\n")
    cleaned_lines = []

    for line in lines:
        # 박스 문자로만 구성된 라인 제거
        if ASCII_BOX_LINE.match(line.strip()):
            continue

        # 박스 문자 제거 후 텍스트만 추출
        if ASCII_BOX_CHARS.search(line):
            # 박스 문자 제거
            cleaned = ASCII_BOX_CHARS.sub(" ", line)
            # 연속 공백 정리
            cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
            if cleaned:
                cleaned_lines.append(cleaned)
        else:
            cleaned_lines.append(line)

    # 연속 빈 줄 정리
    result = "\n".join(cleaned_lines)
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result.strip()


# 섹션 제목 추출 패턴 (우선순위 순)
SECTION_PATTERNS = [
    # 첨부/붙임 패턴: "첨부 2. 실증계획서", "붙임 1. 신청기관 현황자료"
    r"((?:첨부|붙임)\s*\d+\.\s*[가-힣A-Za-z\s·‧]+?)(?:\s{2,}|$|\n)",
    # 장절 복합 패턴: "제1장 개요 제1절 신속확인", "제2장 신속처리 운영 절차"
    r"(제\d+[장절]\s+[가-힣·]+(?:\s+제\d+[절]\s+[가-힣·]+)?)",
    # 절/조 단독 패턴: "제2절 실증단계"
    r"(제\d+[절조]\s+[가-힣·]+(?:\s+[가-힣·]+){0,2})",
    # 숫자 섹션 패턴: "1. 기술·서비스 내용", "3. 세부 실증 계획"
    r"(\d+\.\s*[가-힣·‧]+(?:\s+[가-힣·‧]+){0,4})",
    # 가나다 섹션 패턴: "가. 실증 목표", "나. 정성적 기대효과"
    r"([가-하]\.\s*[가-힣]+(?:\s+[가-힣]+){0,3})",
]


def extract_section_title(content: str, document_title: str) -> str:
    """content에서 세부 섹션 제목 추출

    긴 문서가 여러 청크로 분할될 때, 각 청크의 실제 섹션을 식별하기 위해
    content 본문에서 첫 번째 섹션 헤더를 추출합니다.

    Args:
        content: 청크 본문 (제목 포함)
        document_title: 문서 전체 제목

    Returns:
        추출된 섹션 제목 또는 원본 document_title
    """
    # 제목 부분 제거 (첫 번째 빈 줄까지)
    parts = content.split("\n\n", 1)
    body = parts[1] if len(parts) > 1 else content

    # 박스 기호 제거
    body = re.sub(r"[□■○●ㅇ]\s*", "", body)

    # 패턴 순서대로 매칭 시도
    for pattern in SECTION_PATTERNS:
        match = re.search(pattern, body[:200])  # 첫 200자 내에서만 검색
        if match:
            section = match.group(1).strip()
            # 너무 짧거나 긴 것 제외, document_title과 동일한 것 제외
            if 4 <= len(section) <= 40 and section != document_title:
                return section

    return document_title


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
    if LOCAL_DATA_FILE.exists():
        print(f"로컬 파일에서 데이터 로드: {LOCAL_DATA_FILE}")
        with open(LOCAL_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data, str(LOCAL_DATA_FILE)

    # chunks.json에서 원본 형식으로 변환 (두 번째 fallback)
    if CHUNKS_FILE.exists():
        print(f"chunks.json에서 데이터 복원: {CHUNKS_FILE}")
        with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
            chunks_data = json.load(f)

        # chunks.json → 원본 형식 변환
        data = []
        for chunk in chunks_data.get("chunks", []):
            meta = chunk.get("metadata", {})
            # chunk_id (고유 ID) 우선, 없으면 document_id fallback
            chunk_id = chunk.get("chunk_id", meta.get("document_id", ""))
            data.append(
                {
                    "id": chunk_id,
                    "title": meta.get("document_title", ""),
                    "content": chunk.get("content", ""),
                    "category": meta.get("category_label", "일반"),
                    "track": meta.get("track", "공통"),
                    "source": meta.get("source_file", ""),
                    "source_url": meta.get("source_url", ""),
                    "ministry": meta.get("ministry", "all"),
                }
            )
        return data, str(CHUNKS_FILE)

    raise FileNotFoundError(
        f"데이터 파일을 찾을 수 없습니다.\n"
        f"- R1_DATA_ID 환경변수를 설정하거나\n"
        f"- {LOCAL_DATA_FILE} 파일을 생성하세요."
    )


def create_documents(data: list[dict]) -> tuple[list[Document], list[str]]:
    """JSON 데이터를 Document 리스트로 변환

    중복 제목 처리:
    - 같은 document_title을 가진 청크들에 대해 content에서 섹션 제목 추출
    - 섹션 제목이 추출되면 section_title로 저장하여 구분 가능하게 함

    Returns:
        (documents, ids): 문서 리스트와 ID 리스트 튜플
    """
    documents = []
    doc_ids = []

    # 제목별 등장 횟수 추적 (중복 감지용)
    title_counts: dict[str, int] = {}
    for item in data:
        title = item.get("title", "")
        title_counts[title] = title_counts.get(title, 0) + 1

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

        # content 정제: ASCII 아트 제거
        chunk_content = clean_ascii_art(content)

        # 섹션 제목 추출 (중복 제목인 경우만 세부 섹션 추출 시도)
        if title_counts.get(title, 1) > 1:
            section_title = extract_section_title(content, title)
            # 추출 실패 시 원본 제목 유지 (인덱스 붙이지 않음)
        else:
            section_title = title

        # 인용 형식 생성 (section_title 사용)
        citation = f"{category} > {section_title}"

        doc = Document(
            page_content=chunk_content,
            metadata={
                "source_type": "regulation",
                "source_file": item.get("source", ""),
                "source_url": item.get("source_url", ""),
                "document_id": item.get("id", ""),
                "document_title": title,
                "section_title": section_title,
                "track": normalized_track,
                "category": category_code,
                "category_label": category,
                "ministry": item.get("ministry", "all"),
                "citation": citation,
            },
        )
        # ID 생성: 이미 reg_ prefix 있으면 그대로, 없으면 추가
        source_id = item.get("id", "")
        if source_id.startswith("reg_"):
            doc_id = source_id
        elif source_id:
            doc_id = f"reg_{source_id}"
        else:
            doc_id = f"reg_{idx}"
        documents.append(doc)
        doc_ids.append(doc_id)

    return documents, doc_ids


def collect_and_store_regulations(
    reset: bool = True,
    export_chunks: bool = False,
    embedding_config: str = "E0",
    collection_suffix: str = "",
):
    """규제제도 데이터 수집 및 Vector DB 저장

    Args:
        reset: True면 기존 컬렉션 삭제 후 새로 생성
        export_chunks: True면 청크 JSON도 함께 저장 (평가셋 작성용)
        embedding_config: 임베딩 설정 이름 (E0, E1, E2 등)
        collection_suffix: 컬렉션 이름에 붙일 접미사 (예: _E1)
    """
    print("=" * 60)
    print("규제제도 데이터 수집 시작 (R1 RAG Tool)")
    print("=" * 60)

    # JSON 데이터 로드 (URL 또는 로컬 파일)
    try:
        data, source_path = load_json_data()
    except FileNotFoundError as e:
        print(f"❌ {e}")
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

    # 임베딩 모델 초기화 (설정 파일 기반)
    try:
        emb_config = load_embedding_config(embedding_config, rag_type="r1")
        print(f"\n[임베딩 설정] {emb_config.name}: {emb_config.description}")
        print(f"  - 모델: {emb_config.model}")
        print(f"  - Provider: {emb_config.provider}")
        print(f"  - 차원: {emb_config.dimension}")
    except FileNotFoundError:
        print(f"\n[경고] 설정 '{embedding_config}'을 찾을 수 없습니다. 기본값(E0) 사용")
        emb_config = load_embedding_config("E0", rag_type="r1")

    embeddings = create_embeddings(emb_config)

    # Chroma DB 초기화
    persist_dir = Path(settings.CHROMA_PERSIST_DIR)
    persist_dir.mkdir(parents=True, exist_ok=True)

    # 컬렉션 이름 설정
    collection_name = COLLECTION_REGULATIONS + collection_suffix

    # 기존 컬렉션 삭제 (reset=True인 경우)
    if reset:
        import chromadb

        client = chromadb.PersistentClient(path=str(persist_dir))
        try:
            client.delete_collection(collection_name)
            print(f"\n[OK] 기존 {collection_name} 컬렉션 삭제")
        except Exception:
            pass

    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )

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

    # 수집 결과 저장
    result_file = persist_dir / "r1_collection_info.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "total_documents": len(documents),
                "source": source_path,
                "categories": categories,
                "tracks": tracks,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n수집 정보 저장: {result_file}")
    print("\n" + "=" * 60)
    print("수집 완료 요약:")
    print("=" * 60)
    print(f"  - 소스: {source_path}")
    print(f"  - 총 청크 수: {len(documents)}개")
    print(f"  - 저장 위치: {persist_dir}")
    print(f"  - 컬렉션명: {collection_name}")


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
        default="E1",
        help="임베딩 설정 (E0=OpenAI-small, E1=OpenAI-large, E2=Upstage)",
    )
    parser.add_argument(
        "--suffix",
        default="",
        help="컬렉션 이름 접미사 (예: _E1)",
    )
    args = parser.parse_args()

    collect_and_store_regulations(
        reset=True,
        export_chunks=args.export_chunks,
        embedding_config=args.embedding,
        collection_suffix=args.suffix,
    )
