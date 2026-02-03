"""승인 사례 데이터 수집 및 Vector DB 저장 스크립트

R2. 승인 사례 RAG Tool용 데이터 수집

데이터 소스:
- 환경변수 R2_DATA_ID가 설정된 경우: Google Drive에서 다운로드
- 미설정 시: data/r2/cases_structured.json (로컬 fallback)

실행:
    cd server
    uv run python scripts/collect_cases.py
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

import gdown

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.core.constants import COLLECTION_CASES

# 로컬 데이터 파일 (fallback)
LOCAL_DATA_FILE = Path(__file__).parent.parent / "data" / "r2" / "cases_structured.json"


def load_json_data() -> tuple[list[dict], str]:
    """JSON 데이터 로드 (Google Drive 폴더 또는 로컬 파일)

    Returns:
        (데이터 리스트, 소스 경로/URL)
    """
    # 환경변수에 Google Drive 폴더 ID가 설정된 경우 다운로드
    if settings.R2_DATA_ID:
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
                    f"Google Drive 폴더에서 JSON 파일을 찾을 수 없습니다.\n"
                    f"폴더 ID: {settings.R2_DATA_ID}"
                )

            print(f"  [OK] JSON 파일 발견: {json_file.name}")

            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 로컬에 JSON 파일 복사 (캐싱)
            LOCAL_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(json_file, LOCAL_DATA_FILE)
            print(f"  [OK] 로컬에 캐싱: {LOCAL_DATA_FILE}")

            return data, f"Google Drive Folder (ID: {settings.R2_DATA_ID})"

        finally:
            # 임시 디렉토리 삭제
            try:
                shutil.rmtree(tmp_dir)
            except Exception:
                pass

    # 로컬 파일 사용 (fallback)
    if not LOCAL_DATA_FILE.exists():
        raise FileNotFoundError(
            f"데이터 파일을 찾을 수 없습니다.\n"
            f"- R2_DATA_ID 환경변수를 설정하거나\n"
            f"- {LOCAL_DATA_FILE} 파일을 생성하세요."
        )

    print(f"로컬 파일에서 데이터 로드: {LOCAL_DATA_FILE}")
    with open(LOCAL_DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data, str(LOCAL_DATA_FILE)


def create_documents(data: list[dict]) -> list[Document]:
    """JSON 데이터를 Document 리스트로 변환

    각 케이스를 하나의 Document로 변환합니다.
    검색에 사용될 텍스트는 서비스명, 설명, 특례내용 등을 포함합니다.
    """
    documents = []

    for case in data:
        case_id = case.get("case_id", "")
        track = case.get("track", "")
        common = case.get("common_info", {})
        companies = case.get("companies", [])

        # 검색용 텍스트 구성
        service_name = common.get("service_name", "")
        service_description = common.get("service_description", "")
        special_provisions = common.get("special_provisions", "")
        current_regulation = common.get("current_regulation", "")
        expected_effect = common.get("expected_effect", "")
        pilot_scope = common.get("pilot_scope", "")

        # 기업 정보
        company_names = [c.get("company_name", "") for c in companies if c.get("company_name")]
        company_name = company_names[0] if company_names else ""

        # 지정번호
        designation_number = ""
        for c in companies:
            if c.get("designation_number"):
                designation_number = c.get("designation_number")
                break

        # 검색 콘텐츠 구성
        content_parts = [
            f"[{track}] {service_name}",
            f"기업: {', '.join(company_names)}" if company_names else "",
            f"서비스 설명: {service_description}" if service_description else "",
            f"특례 내용: {special_provisions}" if special_provisions else "",
            f"현행 규제: {current_regulation}" if current_regulation else "",
            f"기대 효과: {expected_effect}" if expected_effect else "",
            f"실증 범위: {pilot_scope}" if pilot_scope else "",
        ]
        content = "\n".join([p for p in content_parts if p])

        # 인용 형식
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
            },
        )
        documents.append(doc)

    return documents


def collect_and_store_cases(reset: bool = True):
    """승인 사례 데이터 수집 및 Vector DB 저장

    Args:
        reset: True면 기존 컬렉션 삭제 후 새로 생성
    """
    print("=" * 60)
    print("승인 사례 데이터 수집 시작 (R2 RAG Tool)")
    print("=" * 60)

    # JSON 데이터 로드 (URL 또는 로컬 파일)
    try:
        data, source_path = load_json_data()
    except FileNotFoundError as e:
        print(f"❌ {e}")
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

    # 임베딩 모델 초기화
    embeddings = OpenAIEmbeddings(model=settings.LLM_EMBEDDING_MODEL)

    # Chroma DB 초기화
    persist_dir = Path(settings.CHROMA_PERSIST_DIR)
    persist_dir.mkdir(parents=True, exist_ok=True)

    # 기존 컬렉션 삭제 (reset=True인 경우)
    if reset:
        import chromadb
        client = chromadb.PersistentClient(path=str(persist_dir))
        try:
            client.delete_collection(COLLECTION_CASES)
            print(f"\n[OK] 기존 {COLLECTION_CASES} 컬렉션 삭제")
        except Exception:
            pass

    vectorstore = Chroma(
        collection_name=COLLECTION_CASES,
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )

    # Document 생성
    documents = create_documents(data)
    print(f"\n{'=' * 60}")
    print(f"총 {len(documents)}개 문서 생성 완료")
    print("Vector DB에 저장 중...")

    # Vector DB에 저장
    vectorstore.add_documents(documents)

    print("[OK] 저장 완료!")

    # 수집 결과 저장
    result_file = persist_dir / "r2_collection_info.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "total_documents": len(documents),
                "source": source_path,
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
    print(f"  - 총 케이스 수: {len(documents)}개")
    print(f"  - 저장 위치: {persist_dir}")
    print(f"  - 컬렉션명: {COLLECTION_CASES}")


if __name__ == "__main__":
    collect_and_store_cases(reset=True)
