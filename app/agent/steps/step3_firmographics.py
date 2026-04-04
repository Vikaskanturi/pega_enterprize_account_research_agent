"""Step 3 — Basic Firmographics"""
from app.agent.state import ResearchState
from app.agent.tools.llm_tool import llm_query
from app.agent.tools.search_tool import web_search, format_results_as_text


async def run(state: ResearchState, llm_model: str = None, **kwargs) -> ResearchState:
    state.current_step = 3
    company = state.company_name
    state.add_log(3, f"Gathering firmographics for: {company}")

    results = await web_search(f"{company} industry headquarters annual revenue employees", max_results=5)
    search_text = format_results_as_text(results)

    prompt = f"""Extract firmographic details for {company} from the search results below.

Search Results:
{search_text}

Respond in this exact format (use 'Unknown' if data not found):
INDUSTRY: <industry sector, e.g. "Financial Services", "Healthcare Technology">
HEADQUARTERS: <City, Country>
ANNUAL_REVENUE: <USD figure with units, e.g. "$2.3 billion" or "$450 million">"""

    response = await llm_query(prompt, model=llm_model)
    state.step_models_used[3] = llm_model or "default"

    for line in response.strip().split("\n"):
        if line.startswith("INDUSTRY:"):
            state.col4_industry = line.split(":", 1)[1].strip()
        elif line.startswith("HEADQUARTERS:"):
            state.col5_headquarters = line.split(":", 1)[1].strip()
        elif line.startswith("ANNUAL_REVENUE:"):
            state.col8_annual_revenue = line.split(":", 1)[1].strip()

    state.add_log(3, f"Industry: {state.col4_industry} | HQ: {state.col5_headquarters} | Revenue: {state.col8_annual_revenue}")
    return state
