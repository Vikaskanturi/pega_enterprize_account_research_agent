"""
Orchestrator — runs all 13 research steps sequentially.
Broadcasts step progress via a queue for WebSocket streaming.
"""
import asyncio
from typing import Optional, Callable
from app.agent.state import ResearchState
from app.agent.steps import (
    step1_classify, step2_revenue, step3_firmographics,
    step4_corporate, step5_gcc, step6_linkedin_discovery,
    step7_employee_count, step8_headcount, step9_pega_usage,
    step10_platforms, step11_outsourcing, step12_categorize, step13_notes
)
from app.agent.tools.excel_tool import write_output_excel


STEP_NAMES = {
    1: "Input & Classification",
    2: "Revenue Classification",
    3: "Basic Firmographics",
    4: "Corporate Structure",
    5: "GCC Check (India)",
    6: "LinkedIn Discovery",
    7: "Employee Count",
    8: "Engineering / IT / QA Headcount",
    9: "Pega Usage Verification",
    10: "Competing Platforms",
    11: "Service Company Check",
    12: "Final Categorization",
    13: "Research Notes & Completion",
}

STEPS = [
    step1_classify,
    step2_revenue,
    step3_firmographics,
    step4_corporate,
    step5_gcc,
    step6_linkedin_discovery,
    step7_employee_count,
    step8_headcount,
    step9_pega_usage,
    step10_platforms,
    step11_outsourcing,
    step12_categorize,
    step13_notes,
]


async def run_research(
    company_name: str,
    llm_model: Optional[str] = None,
    progress_callback: Optional[Callable] = None,
) -> ResearchState:
    """
    Run the full 13-step research pipeline for a company.

    Args:
        company_name: The company to research
        llm_model: Override model for all LLM steps
        progress_callback: Async callable(event_dict) for real-time progress

    Returns:
        Completed ResearchState with all 33 columns populated
    """
    state = ResearchState(company_name=company_name)

    async def emit(event_type: str, step: int, data: dict = None):
        if progress_callback:
            event = {
                "type": event_type,
                "step": step,
                "step_name": STEP_NAMES.get(step, ""),
                "total_steps": 13,
                "state": state.to_dict(),
                **(data or {}),
            }
            await progress_callback(event)

    await emit("start", 0, {"company": company_name})

    for i, step_module in enumerate(STEPS, 1):
        step_name = STEP_NAMES[i]
        await emit("step_start", i, {"message": f"Starting: {step_name}"})
        state.add_log(i, f"Starting step {i}: {step_name}")

        try:
            state = await step_module.run(state, llm_model=llm_model)
            
            # ── NEW: Save Excel after EVERY step for partial downloads ─────
            try:
                write_output_excel([state.to_excel_row()])
                await emit("excel_ready", i, {"output_path": "output/research_results.xlsx"})
            except Exception as e:
                state.add_error(i, f"Incremental Excel write failed: {e}")

            await emit("step_done", i, {"message": f"Completed: {step_name}"})

            # Early exit: company is a Pega Partner
            if state.stopped_early:
                await emit("stopped_early", i, {"message": "Company is a Pega Partner — halting research."})
                break

        except Exception as e:
            error_msg = f"Step {i} error: {str(e)}"
            state.add_error(i, error_msg)
            state.add_note(f"Step {i} ({step_name}) failed: {str(e)}")
            await emit("step_error", i, {"message": error_msg, "error": str(e)})
            # Continue to next step (graceful degradation)
            continue

    # Final completion emit
    await emit("complete", 13, {"message": "Research complete!"})
    return state
