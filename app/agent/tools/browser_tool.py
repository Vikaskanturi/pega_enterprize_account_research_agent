"""
Browser tool — async Playwright wrapper for live web scraping.
Used for LinkedIn page visits, website analysis, and verification.
"""
import os
import re
import asyncio
import json
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page


_browser: Optional[Browser] = None
_playwright = None


async def get_browser() -> Browser:
    """Get or create the shared Playwright browser instance."""
    global _browser, _playwright
    if _browser is None or not _browser.is_connected():
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"],
        )
    return _browser


async def close_browser():
    """Shutdown the browser gracefully."""
    global _browser, _playwright
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None


async def _new_page(browser: Browser) -> Page:
    """Create a new stealth page with optional LinkedIn cookies."""
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
        locale="en-US",
    )

    cookies_file = os.getenv("LINKEDIN_COOKIES_FILE", "data/linkedin_cookies.json")
    if os.path.exists(cookies_file):
        with open(cookies_file) as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)

    page = await context.new_page()
    # Anti-bot: hide webdriver
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)
    return page


async def fetch_page_text(url: str, wait_for: str = "domcontentloaded", timeout: int = 30000) -> str:
    """Navigate to a URL and return page content as clean Markdown for better LLM context."""
    browser = await get_browser()
    page = await _new_page(browser)
    try:
        await page.goto(url, wait_until=wait_for, timeout=timeout)
        await asyncio.sleep(2)
        # Get raw HTML for semantic conversion
        html = await page.evaluate("() => document.body.innerHTML")
        if not html:
            return ""
        # Convert HTML → clean Markdown (much better semantic structure for LLMs)
        try:
            from markdownify import markdownify as md
            text = md(html, heading_style="ATX", strip=["script", "style", "img", "video"])
            # Collapse excessive whitespace
            import re
            text = re.sub(r"\n{3,}", "\n\n", text)
            return text[:8000]  # Larger limit since Markdown is more compact
        except ImportError:
            # Graceful fallback if markdownify somehow not available
            text = await page.evaluate("() => document.body.innerText")
            return text[:4000] if text else ""
    except Exception as e:
        return f"ERROR fetching {url}: {e}"
    finally:
        await page.close()



async def get_linkedin_company_info(linkedin_url: str) -> dict:
    """
    Visit a LinkedIn company page and extract:
    - employee count (About section)
    - industry
    - headquarters
    """
    text = await fetch_page_text(linkedin_url)
    result = {
        "raw_text": text[:3000],
        "employee_count": _extract_employee_count(text),
        "industry": _extract_linkedin_field(text, "Industry"),
        "headquarters": _extract_linkedin_field(text, "Headquarters"),
    }
    return result


async def get_linkedin_people_count(linkedin_url: str, keyword: str = "", location: str = "") -> str:
    """
    Navigate to a LinkedIn People section and extract headcount for a given keyword.
    Returns count as string or 'N/A'.
    """
    people_url = linkedin_url.rstrip("/") + "/people/"
    params = []
    if keyword:
        params.append(f"keywords={keyword}")
    if location:
        params.append(f"geoUrn=102713980")  # India geo URN for LinkedIn
    if params:
        people_url += "?" + "&".join(params)

    text = await fetch_page_text(people_url)
    count = _extract_employee_count(text)
    return count


async def check_linkedin_jobs(linkedin_url: str, keywords: list[str]) -> dict:
    """Check LinkedIn Jobs section for specific role keywords."""
    jobs_url = linkedin_url.rstrip("/") + "/jobs/"
    text = await fetch_page_text(jobs_url)
    found_roles = []
    for kw in keywords:
        if kw.lower() in text.lower():
            found_roles.append(kw)
    return {
        "raw_text": text[:2000],
        "found_roles": found_roles,
        "hiring": len(found_roles) > 0,
    }


async def visit_company_website(company_name: str) -> str:
    """Search for company website and return homepage text."""
    from app.agent.tools.search_tool import web_search
    results = await web_search(f"{company_name} official website")
    if not results:
        return ""
    url = results[0]["url"]
    return await fetch_page_text(url)


# ── Text extraction helpers ───────────────────────────────────────────────────

def _extract_employee_count(text: str) -> str:
    """Extract employee count from LinkedIn page text."""
    patterns = [
        r"([\d,]+)\s+employees on LinkedIn",
        r"([\d,]+)\s+followers",
        r"(\d[\d,]*)\s*–\s*(\d[\d,]*)\s*employees",
        r"About\s+([\d,]+)\s+results",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).replace(",", "")
    return "N/A"


def _extract_linkedin_field(text: str, field: str) -> str:
    """Extract a labelled field from LinkedIn page text."""
    pattern = rf"{field}\s*\n?\s*(.+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()[:100]
    return ""
