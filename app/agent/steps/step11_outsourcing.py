"""Step 11 — Service Company & Outsourcing Check"""
from pydantic import BaseModel, Field
from app.agent.state import ResearchState
from app.agent.tools.llm_tool import llm_structured_query
from app.agent.tools.search_tool import web_search, format_results_as_text
from app.agent.tools.browser_tool import get_linkedin_people_count, check_linkedin_jobs


SERVICE_COMPANIES = ["Accenture", "TCS", "Infosys", "Wipro", "Cognizant", "HCL", "Capgemini", "IBM"]
TECH_ROLES = ["Pega Developer", "Software Developer", "QA Engineer", "Test Engineer", "SDET", "Software Engineer"]


class OutsourcingResult(BaseModel):
    dev_model: str = Field(default="Mixed", description="'In-house', 'Outsourced', or 'Mixed'")
    service_signals: str = Field(default="No", description="'Yes' or 'No'")
    service_companies: str = Field(default="None", description="Comma-separated list of detected service companies, or 'None'")
    hiring_tech: str = Field(default="No", description="'Yes' or 'No' — is the company actively hiring for tech roles?")
    tech_roles_found: str = Field(default="N/A", description="Comma-separated list of tech roles found, or 'N/A'")


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

    prompt = f"""Determine the software development model for {company}.

Service company signals found: {', '.join(service_signals) if service_signals else 'None'}
LinkedIn tech job postings: {jobs_info.get('found_roles', [])}
Hiring for tech roles: {jobs_info.get('hiring', False)}

Search Evidence:
{all_search_text[:1500]}

Development model definitions:
- "In-house": Primarily internal engineering team, minimal outsourcing
- "Outsourced": Majority of development/testing done by service companies
- "Mixed": Combination of in-house and outsourced

Extract the development model JSON fields for company: {company}"""

    result: OutsourcingResult = await llm_structured_query(
        prompt=prompt,
        pydantic_model=OutsourcingResult,
        model=llm_model,
    )
    state.step_models_used[11] = llm_model or "default"

    state.col17_dev_model = result.dev_model
    state.col18_service_company_signals = result.service_signals
    state.col19_service_companies = result.service_companies
    state.col20_hiring_tech_roles = result.hiring_tech
    state.col21_tech_roles = result.tech_roles_found

    state.add_log(11, f"Dev model: {state.col17_dev_model} | Service companies: {state.col19_service_companies}")
    return state
