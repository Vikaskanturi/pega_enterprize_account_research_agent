"""Step 2 — Website Research & Revenue Classification"""
from typing import Optional
from pydantic import BaseModel, Field
from app.agent.state import ResearchState
from app.agent.tools.llm_tool import llm_structured_query
from app.agent.tools.search_tool import agentic_search


class RevenueResult(BaseModel):
    primary_revenue_source: str = Field(default="Unknown", description="Primary source of revenue, e.g. 'IT consulting services'")
    classification: str = Field(default="Unknown", description="'Software' if core business is software/IT, 'Non-Software' otherwise")
    reasoning: str = Field(default="", description="1-2 sentence explanation")


async def run(state: ResearchState, llm_model: str = None, **kwargs) -> ResearchState:
    state.current_step = 2
    company = state.company_name
    state.add_log(2, f"Researching revenue classification for: {company}")

    # Let the LLM decide the best search strategy for finding revenue/business model
    search_result = await agentic_search(
        task_description="Find primary revenue source, business model, and whether core business is software or non-software",
        company_name=company,
        llm_model=llm_model,
    )
    state.add_log(2, f"Search strategy chosen: {search_result['strategy']} — {search_result['reasoning']}")
    search_text = search_result["raw_results"]

    prompt = f"""You are analyzing {company} for B2B sales research.

Research data gathered:
{search_text[:3000]}

Note: If basic facts are missing but the company is a well-known Fortune 500 or global enterprise, use your internal baseline knowledge.

Determine:
1. What is their PRIMARY source of revenue? (e.g. "Insurance premiums", "IT consulting services", "Enterprise software licensing")
2. Is their core business SOFTWARE or NON-SOFTWARE?
   - Software = company's main product/service is software, technology delivery, or IT consulting (like TCS, Accenture, Salesforce)
   - Non-Software = software is just a supporting internal tool (like a bank, insurer, manufacturer)

Extract the following JSON fields for company: {company}"""

    result: RevenueResult = await llm_structured_query(
        prompt=prompt,
        pydantic_model=RevenueResult,
        model=llm_model,
    )
    state.step_models_used[2] = llm_model or "default"

    state.col6_primary_revenue_source = result.primary_revenue_source
    state.col7_software_or_not = result.classification
    if result.reasoning:
        state.add_log(2, f"Reasoning: {result.reasoning}")

    state.add_log(2, f"Revenue source: {state.col6_primary_revenue_source}, Type: {state.col7_software_or_not}")
    return state
