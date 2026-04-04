"""Step 8 — Engineering, IT, QA & SDET Headcount"""
from app.agent.state import ResearchState
from app.agent.tools.browser_tool import get_linkedin_people_count


FUNCTIONS = {
    "engineering": ["Engineering", "Software Engineering"],
    "it": ["Information Technology", "IT"],
    "sdet_qa": ["Quality Assurance", "QA", "SDET"],
}


async def run(state: ResearchState, **kwargs) -> ResearchState:
    state.current_step = 8
    primary_url = state.linkedin_url_company or state.linkedin_url_parent
    india_url = state.linkedin_url_india or (primary_url if state.use_parent_linkedin else None)

    state.add_log(8, "Collecting functional headcounts (Engineering, IT, QA/SDET).")

    async def get_count(url, keyword, location=""):
        if not url:
            return "N/A"
        return await get_linkedin_people_count(url, keyword=keyword, location=location)

    # Engineering
    state.col24_engineering_global = await get_count(primary_url, "Engineering")
    state.col25_engineering_india = await get_count(india_url, "Engineering", location="India")

    # IT
    state.col26_it_global = await get_count(primary_url, "Information Technology")
    state.col27_it_india = await get_count(india_url, "Information Technology", location="India")

    # SDET & QA
    state.col28_sdet_qa_global = await get_count(primary_url, "Quality Assurance")
    state.col29_sdet_qa_india = await get_count(india_url, "Quality Assurance", location="India")

    state.add_log(8, f"Engineering global: {state.col24_engineering_global} | India: {state.col25_engineering_india}")
    state.add_log(8, f"IT global: {state.col26_it_global} | India: {state.col27_it_india}")
    state.add_log(8, f"QA/SDET global: {state.col28_sdet_qa_global} | India: {state.col29_sdet_qa_india}")

    # Calculate Engineering % of total headcount
    try:
        eng = int(state.col24_engineering_global.replace(",", ""))
        total = int(state.col22_total_employees.replace(",", ""))
        if total > 0:
            pct = round((eng / total) * 100, 1)
            state.col30_engineering_pct = f"{pct}%"
        else:
            state.col30_engineering_pct = "N/A"
    except (ValueError, AttributeError):
        state.col30_engineering_pct = "N/A"
        state.add_note("Engineering % could not be calculated — numeric values unavailable.")

    state.add_log(8, f"Engineering %: {state.col30_engineering_pct}")
    return state
