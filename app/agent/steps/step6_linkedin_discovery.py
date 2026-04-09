"""Step 6 — LinkedIn Page Discovery & Verification"""
from app.agent.state import ResearchState
from app.agent.tools.llm_tool import llm_query
from app.agent.tools.search_tool import web_search


async def run(state: ResearchState, llm_model: str = None, **kwargs) -> ResearchState:
    state.current_step = 6
    company = state.company_name
    state.add_log(6, f"Finding LinkedIn pages for: {company}")

    entities = {
        "company": company,
        "india": state.col3_india_subsidiary if state.col3_india_subsidiary and state.col3_india_subsidiary != "None" else None,
        "parent": state.col2_parent_company if state.col2_parent_company and "None" not in state.col2_parent_company else None,
    }

    for entity_type, entity_name in entities.items():
        if not entity_name:
            continue
        results = await web_search(f"{entity_name} LinkedIn company page", site="linkedin.com", max_results=5)
        if not results:
            results = await web_search(f"{entity_name} LinkedIn", max_results=5)

        linkedin_url = ""
        for r in results:
            url = r["url"]
            if "linkedin.com" in url and "/company/" in url:
                linkedin_url = url.split("?")[0]  # strip query params
                break

        if linkedin_url:
            if entity_type == "company":
                state.linkedin_url_company = linkedin_url
            elif entity_type == "india":
                state.linkedin_url_india = linkedin_url
            elif entity_type == "parent":
                state.linkedin_url_parent = linkedin_url
            state.add_log(6, f"LinkedIn ({entity_type}): {linkedin_url}")
        else:
            state.add_log(6, f"LinkedIn not found for {entity_type}: {entity_name}")
            if entity_type == "india":
                state.use_parent_linkedin = True
                state.add_note(f"India subsidiary LinkedIn not found — using parent company LinkedIn for India steps.")

    # Cross-check industry and HQ against LinkedIn data
    primary_url = state.linkedin_url_india or state.linkedin_url_company
    if primary_url:
        from app.agent.tools.browser_tool import get_linkedin_company_info
        info = await get_linkedin_company_info(primary_url)
        li_industry = info.get("industry", "")
        li_hq = info.get("headquarters", "")

        if li_industry and state.col4_industry and li_industry.lower() not in state.col4_industry.lower():
            state.add_note(f"LinkedIn industry '{li_industry}' differs from Step 3 '{state.col4_industry}'.")
        if li_hq and state.col5_headquarters and li_hq.lower() not in state.col5_headquarters.lower():
            state.add_note(f"LinkedIn HQ '{li_hq}' differs from Step 3 '{state.col5_headquarters}'.")

    return state
