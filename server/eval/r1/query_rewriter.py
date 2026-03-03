"""Query Rewriting for R1 RAG

질문을 검색에 더 적합한 형태로 변환하여 Retrieval 성능 개선
"""

from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Query Rewriting 프롬프트
REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """당신은 규제샌드박스 관련 질문을 Vector DB 검색에 최적화된 형태로 변환하는 전문가입니다.

규칙:
1. 핵심 키워드를 명확히 포함
2. 동의어/유사어 추가 (예: 처리 기한 → 처리기한, 소요기간, 기간)
3. 트랙명 명시 (신속확인, 실증특례, 임시허가)
4. 불필요한 조사/어미 제거
5. 검색에 도움되는 관련 용어 추가

예시:
- "신속확인 처리 기한이 어떻게 되나요?" → "신속확인 처리기한 소요기간 30일 기한"
- "임시허가 지원 내용이 뭔가요?" → "임시허가 지원 내용 혜택 지원사항"
- "규제샌드박스 유효기간 연장" → "규제샌드박스 유효기간 연장 최대기간 2년 4년"
"""),
    ("human", "원본 질문: {question}\n\n검색 최적화된 쿼리:")
])


def create_query_rewriter(model: str = "gpt-4o-mini", temperature: float = 0):
    """Query Rewriter 생성"""
    llm = ChatOpenAI(model=model, temperature=temperature)
    chain = REWRITE_PROMPT | llm
    return chain


def rewrite_query(question: str, rewriter=None) -> str:
    """질문을 검색 최적화된 형태로 변환

    Args:
        question: 원본 질문
        rewriter: Query rewriter chain (없으면 새로 생성)

    Returns:
        변환된 쿼리
    """
    if rewriter is None:
        rewriter = create_query_rewriter()

    result = rewriter.invoke({"question": question})
    return result.content.strip()


def rewrite_queries_batch(questions: list[str], rewriter=None) -> list[str]:
    """여러 질문을 일괄 변환"""
    if rewriter is None:
        rewriter = create_query_rewriter()

    rewritten = []
    for q in questions:
        rewritten.append(rewrite_query(q, rewriter))
    return rewritten


# 테스트용
if __name__ == "__main__":
    test_questions = [
        "신속확인 처리 기한이 어떻게 되나요?",
        "임시허가 지원 내용이 뭔가요?",
        "규제샌드박스 유효기간이 얼마나 연장됐나요?",
    ]

    print("=== Query Rewriting 테스트 ===\n")
    rewriter = create_query_rewriter()

    for q in test_questions:
        rewritten = rewrite_query(q, rewriter)
        print(f"원본: {q}")
        print(f"변환: {rewritten}")
        print()
