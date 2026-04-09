"""Step 3 — Basic Firmographics"""
from pydantic import BaseModel, Field
from app.agent.state import ResearchState
from app.agent.tools.llm_tool import llm_structured_query
from app.agent.tools.search_tool import agentic_search


class FirmographicsResult(BaseModel):
    industry: str = Field(default="Unknown", description="Industry sector, e.g. 'IT Services & Consulting'")
    headquarters: str = Field(default="Unknown", description="City, Country format, e.g. 'Mumbai, India'")
    annual_revenue: str = Field(default="Unknown", description="USD figure with units, e.g. '$29 billion'")


async def run(state: ResearchState, llm_model: str = None, **kwargs) -> ResearchState:
    state.current_step = 3
    company = state.company_name
    state.add_log(3, f"Gathering firmographics for: {company}")

    search_result = await agentic_search(
        task_description="Find industry sector, headquarters city/country, and annual revenue",
        company_name=company,
        llm_model=llm_model,
    )
    state.add_log(3, f"Search strategy: {search_result['strategy']} — {search_result['reasoning']}")
    search_text = search_result["raw_results"]

    prompt = f"""Extract firmographic details for {company} from the research data below.

Research Data:
{search_text}

Note: If basic facts (industry, HQ location, annual revenue) are missing but the company is a globally renowned Fortune 500 or large enterprise, use your internal baseline knowledge to answer accurately.

Extract the following firmographic JSON fields for company: {company}"""

    result: FirmographicsResult = await llm_structured_query(
        prompt=prompt,
        pydantic_model=FirmographicsResult,
        model=llm_model,
    )
    state.step_models_used[3] = llm_model or "default"

    state.col4_industry = result.industry
    state.col5_headquarters = result.headquarters
    state.col8_annual_revenue = result.annual_revenue

    state.add_log(3, f"Industry: {state.col4_industry} | HQ: {state.col5_headquarters} | Revenue: {state.col8_annual_revenue}")
    return state
