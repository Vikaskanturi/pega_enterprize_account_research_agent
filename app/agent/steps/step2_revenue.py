"""Step 2 — Website Research & Revenue Classification"""
from app.agent.state import ResearchState
from app.agent.tools.llm_tool import llm_query
from app.agent.tools.search_tool import web_search, format_results_as_text
from app.agent.tools.browser_tool import fetch_page_text


async def run(state: ResearchState, llm_model: str = None, **kwargs) -> ResearchState:
    state.current_step = 2
    company = state.company_name
    state.add_log(2, f"Researching revenue classification for: {company}")

    # Try to visit official website
    results = await web_search(f"{company} official website", max_results=3)
    website_text = ""
    if results:
        url = results[0]["url"]
        state.add_log(2, f"Visiting website: {url}")
        website_text = await fetch_page_text(url)
        website_text = website_text[:3000]

    # Supplement with LLM knowledge
    prompt = f"""You are analyzing {company} for B2B sales research.

Website content (may be partial):
{website_text[:1500] if website_text else 'Not available'}

Search results:
{format_results_as_text(results)}

Answer these questions precisely:
1. What does {company} do? (2-3 sentences)
2. What is their PRIMARY source of revenue? (1 sentence, e.g. "Insurance premiums", "Enterprise software licensing")
3. Is their core business SOFTWARE or NON-SOFTWARE?
   - Software = company's main product IS software (like Autodesk, Salesforce)
   - Non-Software = software is just a tool for their real business (like a bank, insurer, manufacturer)

Respond in this exact format:
PRIMARY_REVENUE_SOURCE: <brief description>
CLASSIFICATION: <Software | Non-Software>
REASONING: <1-2 sentences>"""

    response = await llm_query(prompt, model=llm_model)
    state.step_models_used[2] = llm_model or "default"

    # Parse response
    lines = response.strip().split("\n")
    for line in lines:
        if line.startswith("PRIMARY_REVENUE_SOURCE:"):
            state.col6_primary_revenue_source = line.split(":", 1)[1].strip()
        elif line.startswith("CLASSIFICATION:"):
            val = line.split(":", 1)[1].strip()
            if "non-software" in val.lower():
                state.col7_software_or_not = "Non-Software"
            else:
                state.col7_software_or_not = "Software"
        elif line.startswith("REASONING:"):
            state.add_log(2, f"Reasoning: {line.split(':', 1)[1].strip()}")

    state.add_log(2, f"Revenue source: {state.col6_primary_revenue_source}, Type: {state.col7_software_or_not}")
    return state
