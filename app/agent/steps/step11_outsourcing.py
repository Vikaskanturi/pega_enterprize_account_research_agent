"""Step 11 — Service Company & Outsourcing Check"""
from app.agent.state import ResearchState
from app.agent.tools.llm_tool import llm_query
from app.agent.tools.search_tool import web_search, format_results_as_text
from app.agent.tools.browser_tool import get_linkedin_people_count, check_linkedin_jobs


SERVICE_COMPANIES = ["Accenture", "TCS", "Infosys", "Wipro", "Cognizant", "HCL", "Capgemini", "IBM"]
TECH_ROLES = ["Pega Developer", "Software Developer", "QA Engineer", "Test Engineer", "SDET", "Software Engineer"]


async def run(state: ResearchState, llm_model: str = None, **kwargs) -> ResearchState:
    state.current_step = 11
    company = state.company_name
    primary_url = state.linkedin_url_company or state.linkedin_url_parent
    state.add_log(11, "Checking for outsourcing and service company signals.")

    service_signals = []
    all_search_text = ""

    for sc in SERVICE_COMPANIES:
        results = await web_search(f"{company} {sc}", max_results=2)
        text = format_results_as_text(results)
        if any(sc.lower() in r["snippet"].lower() for r in results):
            service_signals.append(sc)
        all_search_text += f"\n{sc}: {text[:300]}"

    # LinkedIn check for service employees
    if primary_url:
        for sc in SERVICE_COMPANIES[:4]:  # Check top 4 to avoid rate limits
            sc_count = await get_linkedin_people_count(primary_url, keyword=sc)
            try:
                if int(sc_count) >= 2 and sc not in service_signals:
                    service_signals.append(sc)
            except ValueError:
                pass

    # Jobs section check
    jobs_info = {}
    if primary_url:
        jobs_info = await check_linkedin_jobs(primary_url, TECH_ROLES)

    # LLM synthesis
    prompt = f"""Determine the software development model for {company}.

Service company signals found: {', '.join(service_signals) if service_signals else 'None'}
LinkedIn tech job postings: {jobs_info.get('found_roles', [])}
Hiring for tech roles: {jobs_info.get('hiring', False)}

Search Evidence:
{all_search_text[:1500]}

Classify the development model:
- "In-house": Primarily internal engineering team, minimal outsourcing
- "Outsourced": Majority of development/testing done by service companies
- "Mixed": Combination of in-house and outsourced

Respond in EXACT format:
DEV_MODEL: <In-house | Outsourced | Mixed>
SERVICE_SIGNALS: <Yes | No>
SERVICE_COMPANIES: <comma-separated list or "None">
HIRING_TECH: <Yes | No>
TECH_ROLES_FOUND: <comma-separated list or "N/A">"""

    response = await llm_query(prompt, model=llm_model)
    state.step_models_used[11] = llm_model or "default"

    for line in response.strip().split("\n"):
        if line.startswith("DEV_MODEL:"):
            state.col17_dev_model = line.split(":", 1)[1].strip()
        elif line.startswith("SERVICE_SIGNALS:"):
            state.col18_service_company_signals = line.split(":", 1)[1].strip()
        elif line.startswith("SERVICE_COMPANIES:"):
            state.col19_service_companies = line.split(":", 1)[1].strip()
        elif line.startswith("HIRING_TECH:"):
            state.col20_hiring_tech_roles = line.split(":", 1)[1].strip()
        elif line.startswith("TECH_ROLES_FOUND:"):
            state.col21_tech_roles = line.split(":", 1)[1].strip()

    state.add_log(11, f"Dev model: {state.col17_dev_model} | Service companies: {state.col19_service_companies}")
    return state
