"""Step 9 — Pega Usage Verification (LinkedIn + Google)"""
from pydantic import BaseModel, Field
from app.agent.state import ResearchState
from app.agent.tools.llm_tool import llm_structured_query
from app.agent.tools.browser_tool import get_linkedin_people_count
from app.agent.tools.search_tool import agentic_search, format_results_as_text


PEGA_KEYWORDS = ["Pega", "CSSA", "LSA", "PRPC", "Pega QA", "Lead System Architect", "Digital Process Automation", "Pega Strategic Partner", "Pega Partner"]


class PegaUsageResult(BaseModel):
    pega_usage: str = Field(default="Unconfirmed", description="'Yes', 'No', or 'Unconfirmed'")
    evidence: str = Field(default="No evidence found.", description="1-2 sentence explanation with source name and date if known")


async def run(state: ResearchState, llm_model: str = None, **kwargs) -> ResearchState:
    state.current_step = 9
    company = state.company_name
    primary_url = state.linkedin_url_india or state.linkedin_url_company or state.linkedin_url_parent
    state.add_log(9, "Verifying Pega usage via LinkedIn and Google.")

    pega_linkedin_count = 0
    evidence_parts = []

    # 9a — LinkedIn keyword search
    if primary_url:
        pega_count = await get_linkedin_people_count(primary_url, keyword="Pega")
        try:
            pega_linkedin_count = int(pega_count)
            evidence_parts.append(f"{pega_count} LinkedIn profiles matching 'Pega'")
        except ValueError:
            evidence_parts.append(f"LinkedIn 'Pega' search: {pega_count}")

    # 9b — Agentic search: LLM picks best strategy for Pega verification
    pega_search = await agentic_search(
        task_description="Find evidence of Pega software usage, implementation, partnership, or Pega certification among employees",
        company_name=company,
        llm_model=llm_model,
        context=f"Pega type: {state.col9_pega_customer_partner}, LinkedIn: {primary_url or 'N/A'}",
    )
    state.add_log(9, f"Pega search strategy: {pega_search['strategy']} — {pega_search['reasoning']}")
    google_text = pega_search["raw_results"]

    prompt = f"""Determine if {company} uses Pega (the enterprise software platform by Pegasystems).

LinkedIn Evidence: {'; '.join(evidence_parts) if evidence_parts else 'No LinkedIn data available'}

Web Research Results:
{google_text}

Assessment criteria:
- "Yes": 5+ LinkedIn profiles with current Pega roles, OR company is explicitly listed as a Pega Partner/Global Strategic Partner, OR strong recent Google evidence of implementation/partnership.
- "Unconfirmed": Some signals exist but sources are old (>3 years) or low-confidence
- "No": No credible evidence found

Extract the Pega usage JSON fields for company: {company}"""

    result: PegaUsageResult = await llm_structured_query(
        prompt=prompt,
        pydantic_model=PegaUsageResult,
        model=llm_model,
    )
    state.step_models_used[9] = llm_model or "default"

    state.col10_pega_usage_confirmed = result.pega_usage
    state.col11_pega_evidence = result.evidence

    state.add_log(9, f"Pega Usage: {state.col10_pega_usage_confirmed} | {state.col11_pega_evidence}")
    return state
