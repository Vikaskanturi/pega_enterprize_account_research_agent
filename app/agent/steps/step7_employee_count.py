"""Step 7 — Total Employee Count (Org-wide and India)"""
from app.agent.state import ResearchState
from app.agent.tools.browser_tool import get_linkedin_company_info, get_linkedin_people_count


async def run(state: ResearchState, **kwargs) -> ResearchState:
    state.current_step = 7
    state.add_log(7, "Collecting employee counts from LinkedIn.")

    # Org-wide count from primary company LinkedIn
    primary_url = state.linkedin_url_company or state.linkedin_url_parent
    if primary_url:
        info = await get_linkedin_company_info(primary_url)
        state.col22_total_employees = info.get("employee_count", "N/A")
        state.add_log(7, f"Org-wide employees: {state.col22_total_employees}")
    else:
        state.col22_total_employees = "N/A"
        state.add_note("LinkedIn URL not found — employee count unavailable.")

    # India count — use India subsidiary LinkedIn or parent with India filter
    india_url = state.linkedin_url_india
    if not india_url and state.use_parent_linkedin:
        india_url = state.linkedin_url_parent or state.linkedin_url_company

    if india_url:
        india_count = await get_linkedin_people_count(india_url, location="India")
        state.col23_india_employees = india_count
        state.add_log(7, f"India employees: {state.col23_india_employees}")
    else:
        state.col23_india_employees = "N/A"

    return state
