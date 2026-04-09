"""Step 4 — Corporate Structure (Parent Company & Subsidiaries)"""
from pydantic import BaseModel, Field
from app.agent.state import ResearchState
from app.agent.tools.llm_tool import llm_structured_query
from app.agent.tools.search_tool import web_search, format_results_as_text


class CorporateResult(BaseModel):
    parent_company: str = Field(default="None — is the parent company", description="Parent company name, or 'None — is the parent company'")
    india_subsidiary: str = Field(default="None", description="Name of India subsidiary, or 'None'")
    subsidiaries: str = Field(default="None", description="Comma-separated list of known subsidiaries, or 'None'")
    india_entity: str = Field(default="", description="The India subsidiary name if it exists, else the company name itself")


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

Extract the corporate structure JSON fields for company: {company}"""

    result: CorporateResult = await llm_structured_query(
        prompt=prompt,
        pydantic_model=CorporateResult,
        model=llm_model,
    )
    state.step_models_used[4] = llm_model or "default"

    state.col2_parent_company = result.parent_company
    state.col3_india_subsidiary = result.india_subsidiary
    state.col12_subsidiaries = result.subsidiaries
    state.india_entity = result.india_entity if result.india_entity else company

    state.add_log(4, f"Parent: {state.col2_parent_company} | India Sub: {state.col3_india_subsidiary}")
    return state
