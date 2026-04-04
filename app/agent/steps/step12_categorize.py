"""Step 12 — Final Categorization (E1 / E1.1 / E2 / E3)"""
from app.agent.state import ResearchState
from app.agent.tools.llm_tool import llm_query


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
- E1 (Fully Outsourced): Completely outsourced development, minimal internal engineering, no/little tech hiring. High service company presence.
- E1.1 (Transitioning In-House): Currently outsources but actively building internal team. Service company signals PLUS meaningful engineering headcount AND active tech hiring.
- E2 (Non-Software Enterprise): Primary business is NOT software (insurance, banking, manufacturing, etc.). Software is a supporting tool, not the core product.
- E3 (Software-First Enterprise): Primary business IS software. Strong internal engineering culture. Prefers build-over-buy but may use enterprise platforms.

Based on this data, assign exactly one category. Be precise and decisive.

Respond in EXACT format:
ENTERPRISE_TYPE: <E1 | E1.1 | E2 | E3>
REASONING: <2-3 sentences explaining the classification with specific evidence>"""

    response = await llm_query(
        prompt,
        model=llm_model or "claude-sonnet",  # Use strongest model for final categorization
        temperature=0.05,  # Near-deterministic
    )
    state.step_models_used[12] = llm_model or "claude-sonnet"

    for line in response.strip().split("\n"):
        if line.startswith("ENTERPRISE_TYPE:"):
            val = line.split(":", 1)[1].strip()
            # Validate
            if val in ["E1", "E1.1", "E2", "E3"]:
                state.col32_enterprise_type = val
            else:
                state.col32_enterprise_type = "E2"  # safe default
                state.add_note(f"Enterprise type parse failed (got '{val}') — defaulted to E2.")
        elif line.startswith("REASONING:"):
            reasoning = line.split(":", 1)[1].strip()
            state.add_log(12, f"Categorization reasoning: {reasoning}")
            state.add_note(f"E-type reasoning: {reasoning}")

    state.add_log(12, f"Final enterprise type: {state.col32_enterprise_type}")
    return state
