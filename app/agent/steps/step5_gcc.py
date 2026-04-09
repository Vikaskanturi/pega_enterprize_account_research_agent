"""Step 5 — GCC (Global Capability Centre) Check in India"""
from typing import Optional
from pydantic import BaseModel, Field
from app.agent.state import ResearchState
from app.agent.tools.llm_tool import llm_structured_query
from app.agent.tools.search_tool import agentic_search, web_search, format_results_as_text


class GCCResult(BaseModel):
    has_gcc: str = Field(default="No", description="'Yes' if company has GCC(s) in India, 'No' otherwise")
    gcc_count: str = Field(default="N/A", description="Number of GCCs, or 'N/A'")
    gcc_locations: str = Field(default="N/A", description="Comma-separated cities, e.g. 'Bangalore, Hyderabad', or 'N/A'")
    main_gcc: str = Field(default="N/A", description="City with highest headcount GCC, or 'N/A'")
    evidence: str = Field(default="", description="1 sentence explaining the source/confidence level")


async def run(state: ResearchState, llm_model: str = None, **kwargs) -> ResearchState:
    state.current_step = 5
    company = state.company_name
    state.add_log(5, f"Checking for GCCs in India for: {company}")

    # LLM-chosen primary strategy for GCC research
    gcc_search = await agentic_search(
        task_description="Find Global Capability Centre (GCC) presence in India — count, locations, and names of GCC centers",
        company_name=company,
        llm_model=llm_model,
        context=f"Industry: {state.col4_industry or 'Unknown'}, HQ: {state.col5_headquarters or 'Unknown'}",
    )
    state.add_log(5, f"GCC search strategy: {gcc_search['strategy']} — {gcc_search['reasoning']}")

    # Supplement with a direct web search for broader coverage
    supp_results = await web_search(f"{company} operations centers India GCC capability", max_results=4)
    all_text = gcc_search["raw_results"] + "\n\n" + format_results_as_text(supp_results)

    prompt = f"""Determine if {company} has any Global Capability Centres (GCCs) in India.

A GCC is a large captive offshore delivery center (typically 200+ employees), distinct from a small satellite office.

Research Data:
{all_text}

Extract the GCC presence JSON fields for company: {company}"""

    result: GCCResult = await llm_structured_query(
        prompt=prompt,
        pydantic_model=GCCResult,
        model=llm_model,
    )
    state.step_models_used[5] = llm_model or "default"

    state.col13_gcc_in_india = result.has_gcc
    state.col14_number_of_gccs = result.gcc_count
    state.col15_gcc_locations = result.gcc_locations
    state.col16_main_gcc = result.main_gcc
    if result.evidence:
        state.add_log(5, result.evidence)

    # Normalize N/A for No GCCs
    if state.col13_gcc_in_india == "No":
        state.col14_number_of_gccs = "N/A"
        state.col15_gcc_locations = "N/A"
        state.col16_main_gcc = "N/A"

    state.add_log(5, f"GCC: {state.col13_gcc_in_india} | Locations: {state.col15_gcc_locations}")
    return state
