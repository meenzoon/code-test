"""웹 검색 도구 — DuckDuckGo를 이용한 검색 (API 키 불필요)."""

from langchain_core.tools import tool


@tool
def search_web(query: str, max_results: int = 5) -> str:
    """DuckDuckGo로 웹을 검색하고 상위 결과를 마크다운 형식으로 반환한다."""
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                title = r.get("title", "")
                href = r.get("href", "")
                body = r.get("body", "")
                results.append(f"### {title}\n{href}\n{body}")

        return "\n\n".join(results) if results else "No results found."
    except ImportError:
        return "Error: duckduckgo-search package not installed. Run: pip install duckduckgo-search"
    except Exception as e:
        return f"Search error: {e}"


# 웹 검색 도구 목록
WEB_TOOLS = [search_web]
