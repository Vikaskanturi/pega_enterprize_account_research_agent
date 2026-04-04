"""Step 4 — Corporate Structure (Parent Company & Subsidiaries)"""
from app.agent.state import ResearchState
from app.agent.tools.llm_tool import llm_query
from app.agent.tools.search_tool import web_search, format_results_as_text


async def run(state: ResearchState, llm_model: str = None, **kwargs) -> ResearchState:
    state.current_step = 4
    company = state.company_name
    state.add_log(4, f"Researching corporate structure for: {company}")

    results = await web_search(f"{company} subsidiaries and parent company", max_results=6)
    india_results = await web_search(f"{company} India subsidiary", max_results=4)

    all_text = format_results_as_text(results) + "\n\n" + format_results_as_text(india_results)

    prompt = f"""Research the corporate structure for {company}.

Search Results:
{all_text}

Respond in this EXACT format:
PARENT_COMPANY: <parent company name, or "None — is the parent company">
INDIA_SUBSIDIARY: <India subsidiary name, or "None">
SUBSIDIARIES: <comma-separated list of known subsidiaries with their country, e.g. "XYZ India (India), ABC GmbH (Germany)">
INDIA_ENTITY: <the name of the India subsidiary if exists, else the company name itself>"""

    response = await llm_query(prompt, model=llm_model)
    state.step_models_used[4] = llm_model or "default"

    for line in response.strip().split("\n"):
        if line.startswith("PARENT_COMPANY:"):
            state.col2_parent_company = line.split(":", 1)[1].strip()
        elif line.startswith("INDIA_SUBSIDIARY:"):
            state.col3_india_subsidiary = line.split(":", 1)[1].strip()
        elif line.startswith("SUBSIDIARIES:"):
            state.col12_subsidiaries = line.split(":", 1)[1].strip()
        elif line.startswith("INDIA_ENTITY:"):
            state.india_entity = line.split(":", 1)[1].strip()

    if not state.india_entity:
        state.india_entity = company

    state.add_log(4, f"Parent: {state.col2_parent_company} | India Sub: {state.col3_india_subsidiary}")
    return state
