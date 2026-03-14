from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Annotated
from typing_extensions import TypedDict
from operator import add

# ── NexusAI State ─────────────────────────────────────────────────
class NexusState(TypedDict):
    # Input
    company_name: str
    session_id: str
    
    # Scout Agent output
    profile: Optional[Dict[str, Any]]
    raw_sources: Optional[Dict[str, Any]]
    icp_score: Optional[float]
    signals: Optional[List[str]]
    confidence_scores: Optional[Dict[str, float]]
    
    # Finder Agent output
    contact: Optional[Dict[str, Any]]
    
    # Writer Agent output
    email_variant_a: Optional[str]
    email_variant_b: Optional[str]
    subject_a: Optional[str]
    subject_b: Optional[str]
    score_a: Optional[Dict[str, float]]
    score_b: Optional[Dict[str, float]]
    winner_variant: Optional[str]
    winner_reasoning: Optional[str]
    best_email: Optional[str]
    best_subject: Optional[str]
    html_card: Optional[str]
    
    # Closer Agent output
    send_result: Optional[Dict[str, Any]]
    
    # Control flow
    error: Optional[str]
    logs: Optional[List[str]]

# ── Original State (kept for backward compatibility) ──────────────
class SocialMediaLinks(BaseModel):
    blog: str = ""
    facebook: str = ""
    twitter: str = ""
    youtube: str = ""
    # Can add other platform
    
class Report(BaseModel):
    title: str = ""
    content: str = ""
    is_markdown: bool = False

# Define the base data needed about the lead
class LeadData(BaseModel):
    id: str = Field(..., description="The unique identifier for the lead being processed")
    name: str = Field(..., description="The full name of the lead")
    address: str = Field(..., description="The address of the lead")
    email: str = Field(..., description="The email address of the lead")
    phone: str = Field(..., description="The phone number of the lead")
    profile: str = Field(..., description="The lead profile summary from LinkedIn data")

class CompanyData(BaseModel):
    name: str = ""
    profile: str = ""
    website: str = ""
    social_media_links: SocialMediaLinks = SocialMediaLinks()
    
class GraphInputState(TypedDict):
    leads_ids: List[str]

class GraphState(TypedDict):
    leads_ids: List[str]
    leads_data: List[dict]
    current_lead: LeadData
    lead_score: str = ""
    company_data: CompanyData
    reports: Annotated[list[Report], add]
    reports_folder_link: str
    custom_outreach_report_link: str
    personalized_email: str
    interview_script: str
    number_leads: int
