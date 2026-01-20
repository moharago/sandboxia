"""R3 RAG Tool 테스트 스크립트

실행:
    cd server
    uv run python test/domain_law_rag.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tools.shared.rag import search_domain_law, get_law_article, list_available_laws


def test_search_domain_law():
    """search_domain_law 테스트"""
    print("=" * 60)
    print("1. search_domain_law 테스트")
    print("=" * 60)

    # 테스트 1: 도메인 필터 없이 검색
    print("\n[테스트 1] 도메인 필터 없이 '원격 진료' 검색")
    result = search_domain_law.invoke({"query": "원격 진료", "top_k": 3})
    print(f"  총 결과: {result.total_count}개")
    for i, r in enumerate(result.results, 1):
        print(f"  {i}. [{r.citation}] (점수: {r.relevance_score})")
        print(f"     도메인: {r.domain_label}")
        print(f"     내용: {r.content[:100]}...")

    # 테스트 2: 도메인 필터 지정
    print("\n[테스트 2] domain='finance'로 '전자금융거래' 검색")
    result = search_domain_law.invoke({"query": "전자금융거래 보안", "domain": "finance", "top_k": 3})
    print(f"  총 결과: {result.total_count}개, 필터: {result.domain_filter}")
    for i, r in enumerate(result.results, 1):
        print(f"  {i}. [{r.citation}] (점수: {r.relevance_score})")

    # 테스트 3: 개인정보 관련
    print("\n[테스트 3] '개인정보 제3자 제공 동의' 검색")
    result = search_domain_law.invoke({"query": "개인정보 제3자 제공 동의", "top_k": 3})
    print(f"  총 결과: {result.total_count}개")
    for i, r in enumerate(result.results, 1):
        print(f"  {i}. [{r.citation}] - {r.law_name}")


def test_get_law_article():
    """get_law_article 테스트"""
    print("\n" + "=" * 60)
    print("2. get_law_article 테스트")
    print("=" * 60)

    # 의료법 제34조 조회
    print("\n[테스트] 의료법 제34조 조회")
    results = get_law_article.invoke({"law_name": "의료법", "article_no": "34"})
    if results:
        print(f"  총 {len(results)}개 항 발견")
        for r in results:
            print(f"  - {r.citation}: {r.content[:80]}...")
    else:
        print("  결과 없음")


def test_list_available_laws():
    """list_available_laws 테스트"""
    print("\n" + "=" * 60)
    print("3. list_available_laws 테스트")
    print("=" * 60)

    result = list_available_laws.invoke({})
    print("\n사용 가능한 법령:")
    for domain, laws in result.items():
        print(f"  [{domain}]")
        for law in laws:
            print(f"    - {law}")


if __name__ == "__main__":
    test_search_domain_law()
    test_get_law_article()
    test_list_available_laws()
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)
