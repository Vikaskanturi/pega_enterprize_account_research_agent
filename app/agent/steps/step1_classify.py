"""Step 1 — Input & Classification (Pega Partner vs. Customer)"""
from app.agent.state import ResearchState
from app.agent.tools.excel_tool import load_pega_accounts, classify_company


async def run(state: ResearchState, **kwargs) -> ResearchState:
    state.current_step = 1
    state.col1_company_name = state.company_name
    state.add_log(1, f"Classifying company: {state.company_name}")

    accounts = load_pega_accounts()
    if not accounts:
        state.add_log(1, "Reference Excel not found — treating as Customer and continuing.")
        state.add_note("Pega reference Excel not found; classification skipped.")
        state.col9_pega_customer_partner = "Customer"
        return state

    result = classify_company(state.company_name, accounts)
    state.add_log(1, f"Classification result: {result}")

    if result == "Partner":
        state.col9_pega_customer_partner = "Partner"
        state.stopped_early = True
        state.completed = True
        state.add_log(1, "STOP — company is a Pega Partner. Halting research.")
    elif result == "Customer":
        state.col9_pega_customer_partner = "Customer"
    else:
        # Not found in reference — assume Customer and note it
        state.col9_pega_customer_partner = "Customer"
        state.add_note(f"{state.company_name} not found in reference Excel — defaulted to Customer.")
        state.add_log(1, "Company not in reference data — defaulting to Customer.")

    return state
