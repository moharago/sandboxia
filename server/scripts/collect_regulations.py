"""규제제도 데이터 수집 및 Vector DB 저장 스크립트

R1. 규제제도 & 절차 RAG Tool용 데이터 수집

대상 데이터:
- 규제샌드박스 개요
- 트랙 정의 (신속확인/실증특례/임시허가)
- 신청 절차
- 제출 서류 요건
- 심사 기준
- 부처별 차이점
- 2026년 제도 개선 사항

청킹 전략:
- H2(##) 기준으로 섹션 분리
- 각 섹션을 독립적인 청크로 저장
- 메타데이터로 트랙, 카테고리, 출처 등 포함

실행:
    cd server
    uv run python scripts/collect_regulations.py
"""

import json
import re
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings

# 데이터 디렉토리
DATA_DIR = Path(__file__).parent.parent / "data" / "r1"

# 카테고리 매핑
CATEGORY_MAPPING = {
    "01_sandbox_overview.md": {
        "category": "overview",
        "category_label": "제도 개요",
        "track": "all",
    },
    "02_ministry_differences.md": {
        "category": "ministry",
        "category_label": "부처별 차이",
        "track": "all",
    },
    "03_2026_changes.md": {
        "category": "changes",
        "category_label": "제도 개선",
        "track": "all",
    },
    "tracks/01_rapid_confirmation.md": {
        "category": "definition",
        "category_label": "트랙 정의",
        "track": "신속확인",
    },
    "tracks/02_demonstration_exception.md": {
        "category": "definition",
        "category_label": "트랙 정의",
        "track": "실증특례",
    },
    "tracks/03_temporary_permit.md": {
        "category": "definition",
        "category_label": "트랙 정의",
        "track": "임시허가",
    },
    "tracks/04_track_comparison.md": {
        "category": "comparison",
        "category_label": "트랙 비교",
        "track": "all",
    },
    "procedures/01_application_procedure.md": {
        "category": "procedure",
        "category_label": "신청 절차",
        "track": "all",
    },
    "requirements/01_submission_documents.md": {
        "category": "requirement",
        "category_label": "제출 서류",
        "track": "all",
    },
    "criteria/01_review_criteria.md": {
        "category": "criteria",
        "category_label": "심사 기준",
        "track": "all",
    },
}


def extract_sections(content: str, file_path: str) -> list[dict]:
    """마크다운 파일에서 H2(##) 섹션 추출

    Args:
        content: 마크다운 파일 내용
        file_path: 파일 경로 (메타데이터용)

    Returns:
        섹션 리스트 [{title, content, level}, ...]
    """
    sections = []

    # H1 제목 추출
    h1_match = re.search(r"^# (.+)$", content, re.MULTILINE)
    document_title = h1_match.group(1) if h1_match else Path(file_path).stem

    # H2 기준으로 분할
    h2_pattern = r"^## (.+)$"
    h2_matches = list(re.finditer(h2_pattern, content, re.MULTILINE))

    if not h2_matches:
        # H2가 없으면 전체를 하나의 청크로
        sections.append({
            "title": document_title,
            "section_title": "",
            "content": content.strip(),
            "level": 1,
        })
        return sections

    # 첫 H2 이전 내용 (있다면)
    first_h2_start = h2_matches[0].start()
    intro_content = content[:first_h2_start].strip()

    # H1 제목 라인 제거
    if h1_match:
        intro_content = intro_content.replace(h1_match.group(0), "").strip()

    # 구분선(---) 제거
    intro_content = re.sub(r"^---+\s*$", "", intro_content, flags=re.MULTILINE).strip()

    if intro_content and len(intro_content) > 50:
        sections.append({
            "title": document_title,
            "section_title": "개요",
            "content": intro_content,
            "level": 1,
        })

    # H2 섹션들 처리
    for i, match in enumerate(h2_matches):
        section_title = match.group(1)
        start = match.end()

        # 다음 H2까지 또는 파일 끝까지
        if i + 1 < len(h2_matches):
            end = h2_matches[i + 1].start()
        else:
            end = len(content)

        section_content = content[start:end].strip()

        # 구분선 제거
        section_content = re.sub(r"^---+\s*$", "", section_content, flags=re.MULTILINE).strip()

        if section_content and len(section_content) > 30:
            sections.append({
                "title": document_title,
                "section_title": section_title,
                "content": section_content,
                "level": 2,
            })

    return sections


def detect_track_from_content(content: str, default_track: str) -> str:
    """내용에서 특정 트랙 감지"""
    if default_track != "all":
        return default_track

    # 내용에서 트랙 키워드 감지
    track_keywords = {
        "신속확인": ["신속확인", "규제 신속확인", "30일 이내", "규제 유무 확인"],
        "실증특례": ["실증특례", "실증을 위한", "시험·검증", "실증 테스트"],
        "임시허가": ["임시허가", "임시 허가", "시장 출시", "안전성 검증 완료"],
    }

    detected_tracks = []
    content_lower = content.lower()

    for track, keywords in track_keywords.items():
        for keyword in keywords:
            if keyword in content:
                detected_tracks.append(track)
                break

    if len(detected_tracks) == 1:
        return detected_tracks[0]

    return "all"


def detect_ministry_from_content(content: str) -> str:
    """내용에서 부처 감지"""
    ministry_keywords = {
        "산업통상자원부": ["산업통상자원부", "산업부", "산업융합"],
        "과학기술정보통신부": ["과학기술정보통신부", "과기부", "ICT", "정보통신"],
        "금융위원회": ["금융위원회", "금융위", "혁신금융", "금융규제"],
        "중소벤처기업부": ["중소벤처기업부", "중기부", "규제자유특구"],
        "국토교통부": ["국토교통부", "국토부", "스마트도시", "모빌리티"],
        "환경부": ["환경부", "순환경제"],
    }

    detected = []
    for ministry, keywords in ministry_keywords.items():
        for keyword in keywords:
            if keyword in content:
                detected.append(ministry)
                break

    if len(detected) == 1:
        return detected[0]

    return "all"


def create_documents(file_path: Path, file_info: dict) -> list[Document]:
    """마크다운 파일을 Document 리스트로 변환"""
    documents = []

    # 파일 읽기
    content = file_path.read_text(encoding="utf-8")

    # 섹션 추출
    relative_path = str(file_path.relative_to(DATA_DIR))
    sections = extract_sections(content, relative_path)

    for section in sections:
        # 트랙 감지
        track = detect_track_from_content(section["content"], file_info["track"])

        # 부처 감지
        ministry = detect_ministry_from_content(section["content"])

        # 인용 형식 생성
        citation = f"{section['title']}"
        if section["section_title"]:
            citation += f" > {section['section_title']}"

        # 청크 내용 구성
        chunk_content = f"[{section['title']}]"
        if section["section_title"]:
            chunk_content += f" {section['section_title']}"
        chunk_content += f"\n\n{section['content']}"

        doc = Document(
            page_content=chunk_content,
            metadata={
                "source_type": "regulation",
                "source_file": relative_path,
                "document_title": section["title"],
                "section_title": section["section_title"],
                "track": track,
                "category": file_info["category"],
                "category_label": file_info["category_label"],
                "ministry": ministry,
                "citation": citation,
            },
        )
        documents.append(doc)

    return documents


def collect_and_store_regulations():
    """규제제도 데이터 수집 및 Vector DB 저장"""

    print("=" * 60)
    print("규제제도 데이터 수집 시작 (R1 RAG Tool)")
    print("=" * 60)

    # 임베딩 모델 초기화
    embeddings = OpenAIEmbeddings(
        model=settings.LLM_EMBEDDING_MODEL,
        openai_api_key=settings.OPENAI_API_KEY,
    )

    # Chroma DB 초기화
    persist_dir = Path(settings.CHROMA_PERSIST_DIR)
    persist_dir.mkdir(parents=True, exist_ok=True)

    vectorstore = Chroma(
        collection_name="r1_data",
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )

    documents = []
    collected_files = []

    for relative_path, file_info in CATEGORY_MAPPING.items():
        file_path = DATA_DIR / relative_path

        if not file_path.exists():
            print(f"  ⚠️  파일 없음: {relative_path}")
            continue

        print(f"\n[{relative_path}] 처리 중...")

        file_docs = create_documents(file_path, file_info)
        documents.extend(file_docs)

        print(f"  ✓ 생성된 청크: {len(file_docs)}개")
        print(f"    - 카테고리: {file_info['category_label']}")
        print(f"    - 트랙: {file_info['track']}")

        collected_files.append({
            "file": relative_path,
            "category": file_info["category"],
            "track": file_info["track"],
            "chunk_count": len(file_docs),
        })

    if not documents:
        print("\n⚠️  수집된 문서가 없습니다.")
        return

    print(f"\n{'=' * 60}")
    print(f"총 {len(documents)}개 문서 생성 완료")
    print("Vector DB에 저장 중...")

    # Vector DB에 저장
    vectorstore.add_documents(documents)

    print("✓ 저장 완료!")

    # 수집 결과 저장
    result_file = persist_dir / "r1_collection_info.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "total_documents": len(documents),
                "files": collected_files,
                "categories": list(set(f["category"] for f in collected_files)),
                "tracks": ["신속확인", "실증특례", "임시허가", "all"],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n수집 정보 저장: {result_file}")
    print("\n" + "=" * 60)
    print("수집 완료 요약:")
    print("=" * 60)
    for f in collected_files:
        print(f"  - {f['file']}: {f['chunk_count']}개 청크 ({f['category']})")
    print(f"\n총 청크 수: {len(documents)}개")
    print(f"저장 위치: {persist_dir}")
    print(f"컬렉션명: r1_data")


if __name__ == "__main__":
    collect_and_store_regulations()
