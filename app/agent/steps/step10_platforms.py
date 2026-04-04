"""Step 10 — Competing Platform Check (ServiceNow, Salesforce, SAP)"""
from app.agent.state import ResearchState
from app.agent.tools.browser_tool import get_linkedin_people_count


PLATFORMS = ["ServiceNow", "Salesforce", "SAP"]


async def run(state: ResearchState, **kwargs) -> ResearchState:
    state.current_step = 10
    primary_url = state.linkedin_url_india or state.linkedin_url_company or state.linkedin_url_parent
    state.add_log(10, "Checking competing enterprise platforms on LinkedIn.")

    platform_results = []

    for platform in PLATFORMS:
        if primary_url:
            count = await get_linkedin_people_count(primary_url, keyword=platform)
            try:
                n = int(count)
                has_platform = "Yes" if n >= 3 else "No"
            except ValueError:
                has_platform = "Unconfirmed"
            platform_results.append(f"{platform} — {has_platform} ({count} profiles)")
            state.add_log(10, f"{platform}: {count} profiles")
        else:
            platform_results.append(f"{platform} — Unconfirmed (no LinkedIn)")

    state.col31_other_platforms = ", ".join(platform_results)
    return state
