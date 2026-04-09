"""Pydantic request/response schemas for the API."""
from pydantic import BaseModel, Field
from typing import Optional


class ResearchRequest(BaseModel):
    company_name: str = Field(..., min_length=1, description="Company name to research")
    llm_model: Optional[str] = Field(None, description="LLM model override (e.g. 'gemini-2.0-flash', 'gpt-4o')")


class ResearchStatus(BaseModel):
    job_id: str
    company_name: str
    status: str  # "queued" | "running" | "complete" | "error"
    progress_pct: float
    current_step: int
    total_steps: int = 13
    message: str = ""


class ApiKeysConfig(BaseModel):
    gemini: Optional[str] = None
    openai: Optional[str] = None
    anthropic: Optional[str] = None
    groq: Optional[str] = None
    huggingface: Optional[str] = None
    serpapi: Optional[str] = None
    tavily: Optional[str] = None


class ColumnData(BaseModel):
    """All 33 research columns."""
    company_name: str = ""
    parent_company: str = ""
    india_subsidiary: str = ""
    industry: str = ""
    headquarters: str = ""
    primary_revenue_source: str = ""
    software_or_not: str = ""
    annual_revenue: str = ""
    pega_customer_partner: str = ""
    pega_usage_confirmed: str = ""
    pega_evidence: str = ""
    subsidiaries: str = ""
    gcc_in_india: str = ""
    number_of_gccs: str = ""
    gcc_locations: str = ""
    main_gcc: str = ""
    dev_model: str = ""
    service_company_signals: str = ""
    service_companies: str = ""
    hiring_tech_roles: str = ""
    tech_roles: str = ""
    total_employees: str = ""
    india_employees: str = ""
    engineering_global: str = ""
    engineering_india: str = ""
    it_global: str = ""
    it_india: str = ""
    sdet_qa_global: str = ""
    sdet_qa_india: str = ""
    engineering_pct: str = ""
    other_platforms: str = ""
    enterprise_type: str = ""
    research_notes: str = ""


class ResearchResult(BaseModel):
    job_id: str
    company_name: str
    completed: bool
    stopped_early: bool
    columns: dict
    step_logs: list
    step_errors: list
    step_models_used: dict
    started_at: str
    finished_at: str
