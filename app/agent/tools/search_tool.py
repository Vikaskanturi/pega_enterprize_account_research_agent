"""
Search tool — DuckDuckGo-based web search with optional SerpAPI fallback.
Returns structured results with title, URL, and snippet.
"""
import os
import asyncio
import httpx
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
async def web_search(query: str, max_results: int = 5, site: Optional[str] = None) -> list[dict]:
    """
    Perform a web search and return a list of results.

    Args:
        query: Search query string
        max_results: Number of results to return
        site: Optional site filter (e.g. 'linkedin.com')

    Returns:
        List of dicts with keys: title, url, snippet
    """
    if site:
        query = f"site:{site} {query}"

    tavily_key = os.getenv("TAVILY_API_KEY", "")
    serpapi_key = os.getenv("SERPAPI_KEY", "")

    if tavily_key:
        try:
            return await _tavily_search(query, max_results, tavily_key)
        except Exception as e:
            print(f"Tavily failed: {e}. Falling back to other engines.")

    if serpapi_key:
        try:
            return await _serpapi_search(query, max_results, serpapi_key)
        except Exception as e:
            print(f"SerpAPI failed: {e}. Falling back to DuckDuckGo.")
            return await _duckduckgo_search(query, max_results)
    else:
        return await _duckduckgo_search(query, max_results)


async def _duckduckgo_search(query: str, max_results: int) -> list[dict]:
    import urllib.parse as uparse
    from bs4 import BeautifulSoup as bs

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url = f"https://html.duckduckgo.com/html/?q={uparse.quote(query)}"

    try:
        async with httpx.AsyncClient(headers=headers, timeout=15, follow_redirects=True) as client:
            resp = await client.get(url)
            soup = bs(resp.text, "html.parser")
            results = []
            for d in soup.find_all("div", class_="result"):
                h2 = d.find("h2", class_="result__title")
                title_elem = h2.find("a") if h2 else None
                snippet_elem = d.find("a", class_="result__snippet")
                url_elem = d.find("a", class_="result__url")

                if title_elem and url_elem:
                    try:
                        raw_url = url_elem["href"]
                        if "uddg=" in raw_url:
                            found_url = uparse.unquote(raw_url.split("uddg=")[1].split("&")[0])
                        else:
                            found_url = raw_url
                        results.append({
                            "title": title_elem.text.strip(),
                            "url": found_url,
                            "snippet": snippet_elem.text.strip() if snippet_elem else "",
                        })
                    except Exception:
                        pass
                if len(results) >= max_results:
                    break
            return results
    except Exception as e:
        print(f"DuckDuckGo async search error: {e}")
        return []


async def _tavily_search(query: str, max_results: int, api_key: str) -> list[dict]:
    import asyncio
    from tavily import AsyncTavilyClient
    try:
        # Using AsyncTavilyClient if available, otherwise synchronous in a thread
        client = AsyncTavilyClient(api_key=api_key)
        data = await client.search(query=query, max_results=max_results, search_depth="basic")
    except ImportError:
        # Fallback to sync client if older version of tavily installed
        def sync_tavily():
            from tavily import TavilyClient
            return TavilyClient(api_key=api_key).search(query=query, max_results=max_results, search_depth="basic")
        data = await asyncio.to_thread(sync_tavily)

    results = data.get("results", [])
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
        for r in results[:max_results]
    ]



async def _serpapi_search(query: str, max_results: int, api_key: str) -> list[dict]:
    import httpx
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            "https://serpapi.com/search",
            params={"q": query, "api_key": api_key, "num": max_results, "engine": "google"},
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("organic_results", [])
        return [
            {"title": r.get("title", ""), "url": r.get("link", ""), "snippet": r.get("snippet", "")}
            for r in results[:max_results]
        ]


def format_results_as_text(results: list[dict]) -> str:
    """Format search results into a readable text block for LLM consumption."""
    if not results:
        return "No results found."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r['title']}")
        lines.append(f"    URL: {r['url']}")
        lines.append(f"    {r['snippet']}")
        lines.append("")
    return "\n".join(lines)


# ── Tool registry exposed to the LLM ─────────────────────────────────────────
TOOL_CATALOG = """
AVAILABLE RESEARCH TOOLS:
─────────────────────────────────────────────────────────────────────────────
1. web_search(query)
   Best for: Broad public information, news articles, company websites, press
   releases, annual reports, revenue figures, firmographic data.
   Example use: Revenue, HQ location, industry classification, GCC presence.

2. linkedin_search(query)
   Best for: Employee profiles, headcount signals, job titles, Pega usage
   evidence via engineer titles (CSSA, LSA, etc.), hiring activity.
   Example use: Engineer counts, QA roles, Pega certifications.

3. browser_visit(url)
   Best for: Visiting a specific URL to read full page content (company
   website deep-dives, LinkedIn company pages, annual reports).
   Example use: Reading the LinkedIn /about page for employee count.

4. llm_knowledge(topic)
   Best for: Well-known Fortune 500 companies or globally recognized brands
   where basic public facts (HQ, revenue range, industry) are unambiguous
   and widely documented. Use ONLY when other tools return empty results.
   Example use: Basic firmographics for TCS, Infosys, IBM, Google.

5. tavily_extract(url)
   Best for: Extracting clean, structured content directly from a single URL without loading a heavy browser. Highly efficient for reading specific articles.

6. tavily_research(query)
   Best for: Deep, comprehensive AI research on complex queries. Scours multiple sources automatically and returns an aggregated research report.

7. tavily_crawl(url)
   Best for: Finding sub-pages recursively on a specific domain (e.g. finding docs or sub-links).

8. tavily_map(url)
   Best for: Generating a site map of all URLs available under a specific domain.
─────────────────────────────────────────────────────────────────────────────
"""


async def agentic_search(
    task_description: str,
    company_name: str,
    llm_model: str = None,
    context: str = "",
) -> dict:
    """
    Let the LLM decide which search tool(s) to use, then execute the chosen strategy.

    Args:
        task_description: What information needs to be gathered (e.g. "Find revenue and HQ")
        company_name: Name of the company being researched
        llm_model: LLM model identifier to use for the decision
        context: Optional prior context (e.g. LinkedIn URL, industry hint)

    Returns:
        dict with keys:
          - strategy: the tool name chosen ("web_search", "linkedin_search", "browser_visit", "llm_knowledge")
          - reasoning: why the LLM chose this tool
          - raw_results: text content gathered by the chosen tool
    """
    from app.agent.tools.llm_tool import llm_query

    decision_prompt = f"""You are a research planning AI. Your job is to select the BEST tool to gather the information requested.

COMPANY: {company_name}
TASK: {task_description}
{f'PRIOR CONTEXT: {context}' if context else ''}

{TOOL_CATALOG}

Based on the task above, decide which tool is most appropriate.
If the task requires multiple tools (e.g. web_search for broad context AND linkedin_search for headcount), list them in priority order.

Respond in this EXACT format:
TOOL: <web_search | linkedin_search | browser_visit | llm_knowledge | tavily_extract | tavily_research | tavily_crawl | tavily_map>
QUERY: <the exact query or URL to use with the tool>
SECONDARY_TOOL: <optional second tool name, or NONE>
SECONDARY_QUERY: <optional second query, or NONE>
REASONING: <1 sentence explaining the choice>"""

    decision = await llm_query(
        decision_prompt,
        system="You are a search strategy planner for B2B enterprise research. Always pick the most targeted, efficient tool.",
        model=llm_model,
        temperature=0.0,
    )

    # Parse decision
    tool = "web_search"
    query = f"{company_name} {task_description}"
    secondary_tool = None
    secondary_query = None
    reasoning = ""

    for line in decision.strip().split("\n"):
        if line.startswith("TOOL:"):
            tool = line.split(":", 1)[1].strip().lower()
        elif line.startswith("QUERY:"):
            query = line.split(":", 1)[1].strip()
        elif line.startswith("SECONDARY_TOOL:"):
            val = line.split(":", 1)[1].strip().lower()
            secondary_tool = val if val != "none" else None
        elif line.startswith("SECONDARY_QUERY:"):
            val = line.split(":", 1)[1].strip()
            secondary_query = val if val.lower() != "none" else None
        elif line.startswith("REASONING:"):
            reasoning = line.split(":", 1)[1].strip()

    # Execute the primary tool
    raw_results = await _execute_tool(tool, query, company_name)

    # Execute secondary tool if requested and primary returned nothing useful
    if secondary_tool and secondary_query and (not raw_results or "No results" in raw_results):
        secondary_results = await _execute_tool(secondary_tool, secondary_query, company_name)
        if secondary_results:
            raw_results = raw_results + "\n\n--- Secondary Tool Results ---\n" + secondary_results

    return {
        "strategy": tool,
        "query": query,
        "reasoning": reasoning,
        "raw_results": raw_results,
    }


async def _execute_tool(tool: str, query: str, company_name: str) -> str:
    """Execute a named tool and return raw result text."""
    if tool == "web_search":
        results = await web_search(query, max_results=5)
        return format_results_as_text(results)

    elif tool == "linkedin_search":
        results = await web_search(query, site="linkedin.com", max_results=5)
        if not results:
            results = await web_search(f"{company_name} LinkedIn", max_results=5)
        return format_results_as_text(results)

    elif tool == "browser_visit":
        from app.agent.tools.browser_tool import fetch_page_text
        try:
            text = await fetch_page_text(query)  # query is used as URL here
            return text[:3000]
        except Exception as e:
            return f"Browser visit failed: {e}"

    elif tool == "llm_knowledge":
        # For LLM knowledge, we return a signal so the calling step knows to rely on llm intrinsic facts
        return f"[LLM_KNOWLEDGE_MODE]: Use your baseline knowledge about {company_name} to answer: {query}"

    elif tool.startswith("tavily_"):
        import os, asyncio
        tavily_key = os.getenv("TAVILY_API_KEY", "")
        if not tavily_key:
            return "Error: Tavily API Key not configured. Fallback to web_search."
        
        try:
            from tavily import AsyncTavilyClient
            client = AsyncTavilyClient(api_key=tavily_key)
            
            if tool == "tavily_extract":
                data = await client.extract(urls=[query])
                results = data.get("results", [])
                return results[0].get("raw_content", "")[:3000] if results else "No content extracted."
                
            elif tool == "tavily_research":
                # 'research' usually implies advanced deep search
                data = await client.search(query=query, search_depth="advanced", max_results=5)
                results = data.get("results", [])
                return "\n".join([f"[{i+1}] {r.get('title')}: {r.get('content')}" for i, r in enumerate(results)])
                
            elif tool == "tavily_crawl":
                data = await (getattr(client, 'crawl', client.search))(query)
                return str(data)[:3000]
                
            elif tool == "tavily_map":
                # We attempt to use .map if supported, else fallback gracefully
                data = await (getattr(client, 'map', client.search))(query)
                return str(data)[:3000]
                
        except Exception as e:
            return f"{tool} failed: {e}"

    else:
        # Fallback to web search
        results = await web_search(query, max_results=5)
        return format_results_as_text(results)

