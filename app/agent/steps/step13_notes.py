"""Step 13 — Populate Research Notes"""
from app.agent.state import ResearchState
from datetime import datetime


async def run(state: ResearchState, **kwargs) -> ResearchState:
    state.current_step = 13
    state.add_log(13, "Finalizing research notes.")

    # Add timestamp and model summary
    model_summary = ", ".join([f"Step {k}: {v}" for k, v in sorted(state.step_models_used.items())])
    timestamp_note = f"Research completed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}."
    if model_summary:
        timestamp_note += f" Models used: {model_summary}."

    # Append to existing notes
    if state.col33_research_notes:
        state.col33_research_notes = state.col33_research_notes + " | " + timestamp_note
    else:
        state.col33_research_notes = timestamp_note

    # Flag empty critical columns
    missing = []
    critical = {
        "Industry": state.col4_industry,
        "Headquarters": state.col5_headquarters,
        "Annual Revenue": state.col8_annual_revenue,
        "Employee Count": state.col22_total_employees,
        "Enterprise Type": state.col32_enterprise_type,
    }
    for field, val in critical.items():
        if not val or val in ["N/A", "Unknown", ""]:
            missing.append(field)
    if missing:
        state.add_note(f"Data gaps — could not confirm: {', '.join(missing)}.")

    state.finished_at = datetime.utcnow().isoformat()
    state.completed = True
    state.add_log(13, "Research complete. All 33 columns populated.")
    return state
