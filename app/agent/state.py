"""
Research State — shared data container for all 33 PRD columns + metadata.
Passed through every step of the pipeline and mutated in-place.
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class ResearchState:
    # ── Input ─────────────────────────────────────────────────────────────────
    company_name: str = ""

    # ── Column 1 ──────────────────────────────────────────────────────────────
    col1_company_name: str = ""

    # ── Column 2 ──────────────────────────────────────────────────────────────
    col2_parent_company: str = ""

    # ── Column 3 ──────────────────────────────────────────────────────────────
    col3_india_subsidiary: str = ""

    # ── Column 4 ──────────────────────────────────────────────────────────────
    col4_industry: str = ""

    # ── Column 5 ──────────────────────────────────────────────────────────────
    col5_headquarters: str = ""

    # ── Column 6 ──────────────────────────────────────────────────────────────
    col6_primary_revenue_source: str = ""

    # ── Column 7 ──────────────────────────────────────────────────────────────
    col7_software_or_not: str = ""  # "Software" or "Non-Software"

    # ── Column 8 ──────────────────────────────────────────────────────────────
    col8_annual_revenue: str = ""

    # ── Column 9 ──────────────────────────────────────────────────────────────
    col9_pega_customer_partner: str = ""  # "Customer" or "Partner"

    # ── Column 10 ─────────────────────────────────────────────────────────────
    col10_pega_usage_confirmed: str = ""  # "Yes" / "No" / "Unconfirmed"

    # ── Column 11 ─────────────────────────────────────────────────────────────
    col11_pega_evidence: str = ""

    # ── Column 12 ─────────────────────────────────────────────────────────────
    col12_subsidiaries: str = ""

    # ── Column 13 ─────────────────────────────────────────────────────────────
    col13_gcc_in_india: str = ""  # "Yes" or "No"

    # ── Column 14 ─────────────────────────────────────────────────────────────
    col14_number_of_gccs: str = ""

    # ── Column 15 ─────────────────────────────────────────────────────────────
    col15_gcc_locations: str = ""

    # ── Column 16 ─────────────────────────────────────────────────────────────
    col16_main_gcc: str = ""

    # ── Column 17 ─────────────────────────────────────────────────────────────
    col17_dev_model: str = ""  # "In-house" / "Outsourced" / "Mixed"

    # ── Column 18 ─────────────────────────────────────────────────────────────
    col18_service_company_signals: str = ""  # "Yes" / "No"

    # ── Column 19 ─────────────────────────────────────────────────────────────
    col19_service_companies: str = ""

    # ── Column 20 ─────────────────────────────────────────────────────────────
    col20_hiring_tech_roles: str = ""  # "Yes" / "No"

    # ── Column 21 ─────────────────────────────────────────────────────────────
    col21_tech_roles: str = ""

    # ── Column 22 ─────────────────────────────────────────────────────────────
    col22_total_employees: str = ""

    # ── Column 23 ─────────────────────────────────────────────────────────────
    col23_india_employees: str = ""

    # ── Column 24 ─────────────────────────────────────────────────────────────
    col24_engineering_global: str = ""

    # ── Column 25 ─────────────────────────────────────────────────────────────
    col25_engineering_india: str = ""

    # ── Column 26 ─────────────────────────────────────────────────────────────
    col26_it_global: str = ""

    # ── Column 27 ─────────────────────────────────────────────────────────────
    col27_it_india: str = ""

    # ── Column 28 ─────────────────────────────────────────────────────────────
    col28_sdet_qa_global: str = ""

    # ── Column 29 ─────────────────────────────────────────────────────────────
    col29_sdet_qa_india: str = ""

    # ── Column 30 ─────────────────────────────────────────────────────────────
    col30_engineering_pct: str = ""

    # ── Column 31 ─────────────────────────────────────────────────────────────
    col31_other_platforms: str = ""

    # ── Column 32 ─────────────────────────────────────────────────────────────
    col32_enterprise_type: str = ""  # "E1" / "E1.1" / "E2" / "E3"

    # ── Column 33 ─────────────────────────────────────────────────────────────
    col33_research_notes: str = ""

    # ── Pipeline Metadata ─────────────────────────────────────────────────────
    current_step: int = 0
    completed: bool = False
    stopped_early: bool = False  # True if Partner in Step 1
    step_logs: list = field(default_factory=list)
    step_errors: list = field(default_factory=list)
    step_models_used: dict = field(default_factory=dict)
    linkedin_url_company: str = ""
    linkedin_url_india: str = ""
    linkedin_url_parent: str = ""
    use_parent_linkedin: bool = False  # True if India subsidiary has no LinkedIn
    india_entity: str = ""  # Which entity to use for India-specific lookups
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    finished_at: str = ""

    def add_log(self, step: int, message: str):
        self.step_logs.append({"step": step, "message": message, "time": datetime.utcnow().isoformat()})

    def add_error(self, step: int, error: str):
        self.step_errors.append({"step": step, "error": error, "time": datetime.utcnow().isoformat()})

    def add_note(self, note: str):
        if self.col33_research_notes:
            self.col33_research_notes += f" | {note}"
        else:
            self.col33_research_notes = note

    def to_excel_row(self) -> dict:
        """Return all 33 columns as an ordered dict for Excel output."""
        return {
            "Company Name": self.col1_company_name,
            "Parent Company": self.col2_parent_company,
            "India Subsidiary": self.col3_india_subsidiary,
            "Industry": self.col4_industry,
            "Headquarters Location": self.col5_headquarters,
            "Primary Revenue Source": self.col6_primary_revenue_source,
            "Software or Non-Software": self.col7_software_or_not,
            "Annual Revenue (USD)": self.col8_annual_revenue,
            "Pega Customer / Partner": self.col9_pega_customer_partner,
            "Pega Usage Confirmed": self.col10_pega_usage_confirmed,
            "Pega Evidence": self.col11_pega_evidence,
            "Subsidiaries & Associated Companies": self.col12_subsidiaries,
            "GCCs in India": self.col13_gcc_in_india,
            "Number of GCCs": self.col14_number_of_gccs,
            "GCC Locations": self.col15_gcc_locations,
            "Main GCC in India": self.col16_main_gcc,
            "Software Development Model": self.col17_dev_model,
            "Signals of Service Companies": self.col18_service_company_signals,
            "Service Companies Identified": self.col19_service_companies,
            "Hiring for Tech Roles": self.col20_hiring_tech_roles,
            "Tech Roles Being Hired For": self.col21_tech_roles,
            "Total Employee Count (Org-wide)": self.col22_total_employees,
            "Employee Count (India)": self.col23_india_employees,
            "Engineering Count (Org-wide)": self.col24_engineering_global,
            "Engineering Count (India)": self.col25_engineering_india,
            "IT Count (Org-wide)": self.col26_it_global,
            "IT Count (India)": self.col27_it_india,
            "SDET & QA Count (Org-wide)": self.col28_sdet_qa_global,
            "SDET & QA Count (India)": self.col29_sdet_qa_india,
            "Engineering % of Total Headcount": self.col30_engineering_pct,
            "Other Enterprise Platforms": self.col31_other_platforms,
            "Enterprise Type": self.col32_enterprise_type,
            "Research Notes / Comments": self.col33_research_notes,
        }

    def to_dict(self) -> dict:
        """Serialize to JSON-safe dict for API responses."""
        return {
            "company_name": self.company_name,
            "current_step": self.current_step,
            "completed": self.completed,
            "stopped_early": self.stopped_early,
            "columns": self.to_excel_row(),
            "step_logs": self.step_logs,
            "step_errors": self.step_errors,
            "step_models_used": self.step_models_used,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }
