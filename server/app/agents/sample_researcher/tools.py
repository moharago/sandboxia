import httpx
from langchain_core.tools import tool

from app.core.config import settings


@tool
def web_search_tool(query: str) -> str:
    """Search the web for up-to-date information."""
    if not settings.TAVILY_API_KEY:
        return "검색 실패: TAVILY_API_KEY가 설정되지 않았습니다."

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": settings.TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": 3,
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        results_text = f"검색 결과 for '{query}':\n\n"
        for i, result in enumerate(data.get("results", [])[:3], 1):
            results_text += f"{i}. {result.get('title')}\n"
            results_text += f"   {result.get('content', '')[:150]}...\n\n"

        if data.get("answer"):
            results_text += f"요약: {data.get('answer')}\n"

        return results_text
    except Exception as exc:
        return f"검색 실패: {exc}"


__all__ = ["web_search_tool"]
