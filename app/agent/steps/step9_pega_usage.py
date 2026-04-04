"""Step 9 — Pega Usage Verification (LinkedIn + Google)"""
from app.agent.state import ResearchState
from app.agent.tools.llm_tool import llm_query
from app.agent.tools.browser_tool import get_linkedin_people_count
from app.agent.tools.search_tool import web_search, format_results_as_text


PEGA_KEYWORDS = ["Pega", "CSSA", "LSA", "PRPC", "Pega QA", "Lead System Architect", "Digital Process Automation"]


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

    # 9b — Google confirmation
    google_results = await web_search(f"{company} Pega implementation case study", max_results=5)
    google_text = format_results_as_text(google_results)

    prompt = f"""Determine if {company} uses Pega (the enterprise software platform by Pegasystems).

LinkedIn Evidence: {'; '.join(evidence_parts) if evidence_parts else 'No LinkedIn data available'}

Google Search Results:
{google_text}

Assessment criteria:
- "Yes": 5+ LinkedIn profiles with current Pega roles, OR strong recent Google evidence (news, case study, job postings)
- "Unconfirmed": Some signals exist but sources are old (>3 years) or low-confidence
- "No": No credible evidence found

Respond in this EXACT format:
PEGA_USAGE: <Yes | No | Unconfirmed>
EVIDENCE: <1-2 sentence explanation, including source name and date if known>"""

    response = await llm_query(prompt, model=llm_model)
    state.step_models_used[9] = llm_model or "default"

    for line in response.strip().split("\n"):
        if line.startswith("PEGA_USAGE:"):
            state.col10_pega_usage_confirmed = line.split(":", 1)[1].strip()
        elif line.startswith("EVIDENCE:"):
            state.col11_pega_evidence = line.split(":", 1)[1].strip()

    state.add_log(9, f"Pega Usage: {state.col10_pega_usage_confirmed} | {state.col11_pega_evidence}")
    return state
