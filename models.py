"""
src/models.py

Pydantic models used across the application.

Using structured Pydantic models (instead of raw free-form LLM text) means
the rest of the app can rely on predictable fields instead of trying to
parse unstructured strings out of an LLM response. This is the core of how
we make the LangChain calls in this project robust.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """Information about the person/business using the tool (used to write emails)."""

    name: str = Field(default="", description="The user's own name")
    company: str = Field(default="", description="The user's business/brand name")
    service: str = Field(default="", description="Description of the service the user offers")
    website: str = Field(default="", description="The user's website or portfolio link")
    contact_email: str = Field(default="", description="The user's contact email for sign-off")


class SearchQuery(BaseModel):
    """A single web-search query the agent decided to run, and why."""

    query: str = Field(description="The exact search query text")
    reason: str = Field(description="Why this query helps find relevant target clients")


class TargetClientPlan(BaseModel):
    """The LLM's understanding of what kind of clients to look for, and how to search for them."""

    ideal_client_summary: str = Field(
        description="A short summary of what an ideal client/prospect looks like for this user"
    )
    search_queries: List[SearchQuery] = Field(
        description="A list of distinct web search queries to find such companies"
    )


class CompanyInfo(BaseModel):
    """Structured, extracted information about a single researched company."""

    company_name: str = Field(description="Name of the company or brand")
    website: str = Field(default="Not found", description="Company website URL")
    industry: str = Field(default="Unknown", description="Industry or business category")
    location: str = Field(default="Unknown", description="City/country of operation if known")
    description: str = Field(description="Short factual description of what the company does")
    contact_email: str = Field(
        default="Contact email not found",
        description="A publicly listed contact email, ONLY if explicitly found in the source text. "
        "Never invent or guess an email address.",
    )
    source_urls: List[str] = Field(default_factory=list, description="URLs used as research sources")


class LeadQualification(BaseModel):
    """The LLM's qualification/scoring output for a single lead."""

    lead_score: int = Field(ge=1, le=10, description="Lead quality score from 1 (poor) to 10 (excellent)")
    reason: str = Field(description="Concise explanation of why this company is (or isn't) a good lead")


class Lead(BaseModel):
    """A fully processed lead: research + qualification + (optionally) an email."""

    company: CompanyInfo
    qualification: LeadQualification
    email_subject: Optional[str] = None
    email_body: Optional[str] = None

    @property
    def lead_score(self) -> int:
        return self.qualification.lead_score


class OutreachEmail(BaseModel):
    """Structured output for a generated cold email."""

    subject: str = Field(description="A short, specific, non-spammy subject line")
    body: str = Field(description="The full email body, including greeting and sign-off")
