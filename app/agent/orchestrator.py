"""
Orchestrator — runs 13 research steps in an async DAG (parallelized phases).

Execution Phases:
  Phase 1 (Sequential): Step 1 (Classify) + Step 6 (LinkedIn Discovery)
  Phase 2 (Parallel):   Steps 2, 3, 4, 5  (Revenue, Firmographics, Corporate, GCC)
  Phase 3 (Parallel):   Steps 7, 8, 9, 10, 11 (Headcounts, Pega, Platforms, Outsourcing)
  Phase 4 (Sequential): Step 12 (Categorize) + Step 13 (Notes)

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
from app.agent.tools.excel_tool import write_output_excel, upsert_to_master_excel


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


async def run_research(
    company_name: str,
    llm_model: Optional[str] = None,
    progress_callback: Optional[Callable] = None,
) -> ResearchState:
    """
    Run the full 13-step research pipeline in parallel phases.

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

    async def run_step(step_num: int, step_module, **kwargs) -> None:
        """Run a single step with error handling and WebSocket emission."""
        nonlocal state
        step_name = STEP_NAMES[step_num]
        await emit("step_start", step_num, {"message": f"Starting: {step_name}"})
        state.add_log(step_num, f"Starting step {step_num}: {step_name}")
        try:
            state = await step_module.run(state, llm_model=llm_model, **kwargs)
            # Incremental Excel upsert
            try:
                upsert_to_master_excel(state.to_excel_row())
            except Exception as e:
                state.add_error(step_num, f"Incremental Excel write failed: {e}")
            await emit("step_done", step_num, {"message": f"Completed: {step_name}"})
        except Exception as e:
            error_msg = f"Step {step_num} error: {str(e)}"
            state.add_error(step_num, error_msg)
            state.add_note(f"Step {step_num} ({step_name}) failed: {str(e)}")
            await emit("step_error", step_num, {"message": error_msg, "error": str(e)})

    await emit("start", 0, {"company": company_name})

    # ── Phase 1: Prerequisites (must run first, in order) ─────────────────────
    await emit("phase", 1, {"message": "Phase 1: Classification & LinkedIn Discovery"})
    await run_step(1, step1_classify)
    await run_step(6, step6_linkedin_discovery)

    # ── Phase 2: Parallel Research (all independent) ──────────────────────────
    await emit("phase", 2, {"message": "Phase 2: Running Revenue, Firmographics, Corporate & GCC in parallel…"})
    await asyncio.gather(
        run_step(2, step2_revenue),
        run_step(3, step3_firmographics),
        run_step(4, step4_corporate),
        run_step(5, step5_gcc),
    )

    # ── Phase 3: Parallel LinkedIn Headcounts & Signal Checks ─────────────────
    await emit("phase", 3, {"message": "Phase 3: Running headcounts, Pega verification & platform checks in parallel…"})
    await asyncio.gather(
        run_step(7, step7_employee_count),
        run_step(8, step8_headcount),
        run_step(9, step9_pega_usage),
        run_step(10, step10_platforms),
        run_step(11, step11_outsourcing),
    )

    # ── Phase 4: Synthesis (depends on all prior data) ────────────────────────
    await emit("phase", 4, {"message": "Phase 4: Final categorization & notes"})
    await run_step(12, step12_categorize)
    await run_step(13, step13_notes)

    # Final completion
    await emit("complete", 13, {"message": "Research complete!"})
    return state
