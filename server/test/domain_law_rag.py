"""R3 RAG Tool 테스트 스크립트

실행:
    cd server
    uv run python test/domain_law_rag.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tools.shared.rag import search_domain_law


def test_search_domain_law():
    """search_domain_law 테스트"""
    print("=" * 60)
    print("search_domain_law 테스트")
    print("=" * 60)

    # # 테스트 1: 도메인 필터 없이 검색
    # print("=" * 60)
    # print("\n[테스트 1] 도메인 필터 없이 '원격 진료' 검색")
    # result = search_domain_law.invoke({"query": "원격 진료", "top_k": 3})
    # print(f"  총 결과: {result.total_count}개")
    # print(result.results)
    # # for i, r in enumerate(result.results, 1):
    # #     print(f"  {i}. [{r.citation}] (점수: {r.relevance_score})")
    # #     print(f"     도메인: {r.domain_label}")
    # #     print(f"     내용: {r.content[:100]}...")

    # # 테스트 2: 도메인 필터 지정
    # print("=" * 60)
    # print("\n[테스트 2] domain='finance'로 '전자금융거래' 검색")
    # result = search_domain_law.invoke({"query": "전자금융거래 보안", "domain": "finance", "top_k": 3})
    # print(f"  총 결과: {result.total_count}개, 필터: {result.domain_filter}")
    # print(result.results)
    # # for i, r in enumerate(result.results, 1):
    # #     print(f"  {i}. [{r.citation}] (점수: {r.relevance_score})")

    # # 테스트 3: 개인정보 관련
    # print("=" * 60)
    # print("\n[테스트 3] '개인정보 제3자 제공 동의' 검색")
    # result = search_domain_law.invoke({"query": "개인정보 제3자 제공 동의", "top_k": 3})
    # print(f"  총 결과: {result.total_count}개")
    # print(result.results)
    # # for i, r in enumerate(result.results, 1):
    # #     print(f"  {i}. [{r.citation}] - {r.law_name}")

    print("=" * 60)
    result = search_domain_law.invoke({"query": "의료법 제35조", "top_k": 3})
    print(result.results)


if __name__ == "__main__":
    test_search_domain_law()
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)
