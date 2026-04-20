"""Web tools — search the web via DuckDuckGo (no API key required)."""

from langchain_core.tools import tool


@tool
def search_web(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo and return a summary of top results."""
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


WEB_TOOLS = [search_web]
