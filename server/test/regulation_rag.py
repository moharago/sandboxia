"""R1. 규제제도 & 절차 RAG Tool 테스트

실행:
    cd server
    uv run python test/regulation_rag.py
"""

import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tools.shared.rag.regulation_rag import (
    search_regulation,
    get_track_definition,
    get_application_requirements,
    get_review_criteria,
    compare_tracks,
    list_available_tracks,
)


def test_search_regulation():
    """기본 검색 테스트"""
    print("\n" + "=" * 60)
    print("1. 기본 검색 테스트: '신속확인 신청 절차'")
    print("=" * 60)

    result = search_regulation.invoke({"query": "신속확인 신청 절차"})

    print(f"총 결과 수: {result.total_count}")
    print(f"검색 쿼리: {result.query}")
    print()

    for i, r in enumerate(result.results[:3], 1):
        print(f"[{i}] {r.document_title} > {r.section_title}")
        print(f"    - 트랙: {r.track}")
        print(f"    - 카테고리: {r.category_label}")
        print(f"    - 관련도: {r.relevance_score}")
        print(f"    - 인용: {r.citation}")
        print(f"    - 내용 미리보기: {r.content[:100]}...")
        print()


def test_search_with_track_filter():
    """트랙 필터 검색 테스트"""
    print("\n" + "=" * 60)
    print("2. 트랙 필터 검색 테스트: '제출 서류' (실증특례)")
    print("=" * 60)

    result = search_regulation.invoke({
        "query": "제출 서류",
        "track": "실증특례",
    })

    print(f"총 결과 수: {result.total_count}")
    print(f"트랙 필터: {result.track_filter}")
    print()

    for i, r in enumerate(result.results[:3], 1):
        print(f"[{i}] {r.document_title} > {r.section_title}")
        print(f"    - 트랙: {r.track}")
        print(f"    - 내용 미리보기: {r.content[:100]}...")
        print()


def test_search_with_category_filter():
    """카테고리 필터 검색 테스트"""
    print("\n" + "=" * 60)
    print("3. 카테고리 필터 검색 테스트: '심사' (criteria)")
    print("=" * 60)

    result = search_regulation.invoke({
        "query": "심사 기준",
        "category": "criteria",
    })

    print(f"총 결과 수: {result.total_count}")
    print(f"카테고리 필터: {result.category_filter}")
    print()

    for i, r in enumerate(result.results[:3], 1):
        print(f"[{i}] {r.document_title} > {r.section_title}")
        print(f"    - 카테고리: {r.category_label}")
        print(f"    - 내용 미리보기: {r.content[:100]}...")
        print()


def test_get_track_definition():
    """트랙 정의 조회 테스트"""
    print("\n" + "=" * 60)
    print("4. 트랙 정의 조회 테스트: '임시허가'")
    print("=" * 60)

    results = get_track_definition.invoke({"track": "임시허가"})

    print(f"총 결과 수: {len(results)}")
    print()

    for i, r in enumerate(results[:3], 1):
        print(f"[{i}] {r.document_title} > {r.section_title}")
        print(f"    - 트랙: {r.track}")
        print(f"    - 내용 미리보기: {r.content[:100]}...")
        print()


def test_get_application_requirements():
    """신청 요건 조회 테스트"""
    print("\n" + "=" * 60)
    print("5. 신청 요건 조회 테스트: 실증특례")
    print("=" * 60)

    results = get_application_requirements.invoke({"track": "실증특례"})

    print(f"총 결과 수: {len(results)}")
    print()

    for i, r in enumerate(results[:3], 1):
        print(f"[{i}] {r.document_title} > {r.section_title}")
        print(f"    - 내용 미리보기: {r.content[:150]}...")
        print()


def test_get_review_criteria():
    """심사 기준 조회 테스트"""
    print("\n" + "=" * 60)
    print("6. 심사 기준 조회 테스트")
    print("=" * 60)

    results = get_review_criteria.invoke({})

    print(f"총 결과 수: {len(results)}")
    print()

    for i, r in enumerate(results[:3], 1):
        print(f"[{i}] {r.document_title} > {r.section_title}")
        print(f"    - 내용 미리보기: {r.content[:150]}...")
        print()


def test_compare_tracks():
    """트랙 비교 테스트"""
    print("\n" + "=" * 60)
    print("7. 트랙 비교 조회 테스트")
    print("=" * 60)

    results = compare_tracks.invoke({})

    print(f"총 결과 수: {len(results)}")
    print()

    for i, r in enumerate(results[:3], 1):
        print(f"[{i}] {r.document_title} > {r.section_title}")
        print(f"    - 내용 미리보기: {r.content[:150]}...")
        print()


def test_list_available_tracks():
    """사용 가능한 트랙 목록 테스트"""
    print("\n" + "=" * 60)
    print("8. 사용 가능한 트랙/카테고리 목록")
    print("=" * 60)

    result = list_available_tracks.invoke({})

    print("\n[트랙]")
    for track, desc in result["tracks"].items():
        print(f"  - {track}: {desc}")

    print("\n[카테고리]")
    for cat, label in result["categories"].items():
        print(f"  - {cat}: {label}")

    print("\n[부처]")
    for ministry, sandbox in result["ministries"].items():
        print(f"  - {ministry}: {sandbox}")


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("R1. 규제제도 & 절차 RAG Tool 테스트")
    print("=" * 60)

    try:
        test_search_regulation()
        test_search_with_track_filter()
        test_search_with_category_filter()
        test_get_track_definition()
        test_get_application_requirements()
        test_get_review_criteria()
        test_compare_tracks()
        test_list_available_tracks()

        print("\n" + "=" * 60)
        print("✅ 모든 테스트 완료!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
