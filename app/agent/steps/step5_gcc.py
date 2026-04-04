"""Step 5 — GCC (Global Capability Centre) Check in India"""
from app.agent.state import ResearchState
from app.agent.tools.llm_tool import llm_query
from app.agent.tools.search_tool import web_search, format_results_as_text


async def run(state: ResearchState, llm_model: str = None, **kwargs) -> ResearchState:
    state.current_step = 5
    company = state.company_name
    state.add_log(5, f"Checking for GCCs in India for: {company}")

    gcc_results = await web_search(f"{company} GCC in India Global Capability Centre", max_results=4)
    ops_results = await web_search(f"{company} operations centers India", max_results=4)
    cap_results = await web_search(f"{company} capability centre India", max_results=3)

    all_text = (
        format_results_as_text(gcc_results)
        + "\n\n" + format_results_as_text(ops_results)
        + "\n\n" + format_results_as_text(cap_results)
    )

    prompt = f"""Determine if {company} has any Global Capability Centres (GCCs) in India.

A GCC is a large captive offshore delivery center (typically 200+ employees), distinct from a small satellite office.

Search Results:
{all_text}

Respond in this EXACT format:
HAS_GCC: <Yes | No>
GCC_COUNT: <number or N/A>
GCC_LOCATIONS: <comma-separated list of cities, or N/A>
MAIN_GCC: <city/location with highest headcount, or N/A>
EVIDENCE: <1 sentence explaining the source/confidence>"""

    response = await llm_query(prompt, model=llm_model)
    state.step_models_used[5] = llm_model or "default"

    for line in response.strip().split("\n"):
        if line.startswith("HAS_GCC:"):
            state.col13_gcc_in_india = line.split(":", 1)[1].strip()
        elif line.startswith("GCC_COUNT:"):
            state.col14_number_of_gccs = line.split(":", 1)[1].strip()
        elif line.startswith("GCC_LOCATIONS:"):
            state.col15_gcc_locations = line.split(":", 1)[1].strip()
        elif line.startswith("MAIN_GCC:"):
            state.col16_main_gcc = line.split(":", 1)[1].strip()
        elif line.startswith("EVIDENCE:"):
            state.add_log(5, line.split(":", 1)[1].strip())

    # Normalize N/A for No GCCs
    if state.col13_gcc_in_india == "No":
        state.col14_number_of_gccs = "N/A"
        state.col15_gcc_locations = "N/A"
        state.col16_main_gcc = "N/A"

    state.add_log(5, f"GCC: {state.col13_gcc_in_india} | Locations: {state.col15_gcc_locations}")
    return state
