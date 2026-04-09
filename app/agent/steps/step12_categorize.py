"""Step 12 — Final Categorization (E1 / E1.1 / E2 / E3)"""
from pydantic import BaseModel, Field
from app.agent.state import ResearchState
from app.agent.tools.llm_tool import llm_structured_query


class CategorizationResult(BaseModel):
    enterprise_type: str = Field(default="E2", description="One of: E1, E1.1, E2, E3")
    reasoning: str = Field(default="", description="2-3 sentences explaining the classification with specific evidence")


async def run(state: ResearchState, llm_model: str = None, **kwargs) -> ResearchState:
    state.current_step = 12
    state.add_log(12, "Running final enterprise type categorization.")

    prompt = f"""You are a senior B2B sales analyst. Based on all research collected, assign the correct Enterprise Type.

COMPANY: {state.company_name}

RESEARCH SUMMARY:
- Primary Revenue: {state.col6_primary_revenue_source}
- Software or Non-Software: {state.col7_software_or_not}
- Industry: {state.col4_industry}
- Annual Revenue: {state.col8_annual_revenue}
- Total Employees (global): {state.col22_total_employees}
- Engineering headcount (global): {state.col24_engineering_global}
- Engineering % of total: {state.col30_engineering_pct}
- Software Development Model: {state.col17_dev_model}
- Service company signals: {state.col18_service_company_signals} ({state.col19_service_companies})
- Hiring for tech roles: {state.col20_hiring_tech_roles} ({state.col21_tech_roles})
- Pega Usage Confirmed: {state.col10_pega_usage_confirmed}
- GCC in India: {state.col13_gcc_in_india}

ENTERPRISE TYPE DEFINITIONS:
- E1 (Fully Outsourced): Completely outsourced development, minimal internal engineering, no/little tech hiring.
- E1.1 (Transitioning In-House): Currently outsources but actively building internal team.
- E2 (Non-Software Enterprise): Primary business is NOT software (e.g. legacy insurance, banking, manufacturing). Software is a support function.
- E3 (Software-First or IT Services Enterprise): Primary business IS software OR technology services. Includes SaaS, Tech Giants, and large IT Services/Systems Integrators (TCS, Infosys, Accenture) with massive engineering cultures.

Extract the enterprise type JSON fields for company: {state.company_name}"""

    result: CategorizationResult = await llm_structured_query(
        prompt=prompt,
        pydantic_model=CategorizationResult,
        model=llm_model,
        temperature=0.0,
    )
    state.step_models_used[12] = llm_model or "default"

    if result.enterprise_type in ["E1", "E1.1", "E2", "E3"]:
        state.col32_enterprise_type = result.enterprise_type
    else:
        state.col32_enterprise_type = "E2"
        state.add_note(f"Enterprise type parse returned '{result.enterprise_type}' — defaulted to E2.")

    if result.reasoning:
        state.add_log(12, f"Categorization reasoning: {result.reasoning}")
        state.add_note(f"E-type reasoning: {result.reasoning}")

    state.add_log(12, f"Final enterprise type: {state.col32_enterprise_type}")
    return state
