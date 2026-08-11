"""
src/research.py

Handles the "research" side of the agent:
1. Use an LLM (via LangChain) to turn the user's target-client description
   into a small set of concrete web search queries (TargetClientPlan).
2. Run those queries against the Tavily search API.
3. Use an LLM (via LangChain, with structured output) to turn raw search
   results into clean CompanyInfo objects.

Every network / LLM call is wrapped in error handling so that one failed
company never crashes the whole app.
"""

import os
from typing import List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from src.models import TargetClientPlan, CompanyInfo
from utils.helpers import truncate_text, extract_email_from_text

try:
    from tavily import TavilyClient
except ImportError:  # pragma: no cover - handled gracefully at runtime
    TavilyClient = None


def get_llm(model: str = "gpt-4o-mini", temperature: float = 0.3) -> Optional[ChatOpenAI]:
    """
    Create a LangChain ChatOpenAI instance.

    Returns None (instead of raising) if no API key is configured, so callers
    can show a friendly Streamlit message instead of crashing.
    """
    if not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        return ChatOpenAI(model=model, temperature=temperature)
    except Exception:
        return None


def get_tavily_client() -> Optional["TavilyClient"]:
    """Create a Tavily search client, or None if not configured/available."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or TavilyClient is None:
        return None
    try:
        return TavilyClient(api_key=api_key)
    except Exception:
        return None


def plan_target_client_search(
    llm: ChatOpenAI,
    service_description: str,
    target_industry: str,
    target_location: str,
    client_type: str,
    num_leads: int,
) -> Optional[TargetClientPlan]:
    """
    Ask the LLM to turn the user's inputs into a short list of search queries.

    This is the first LangChain step in the workflow:
    User Input -> Target Client Discovery
    """
    structured_llm = llm.with_structured_output(TargetClientPlan)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a B2B lead-generation research assistant. Your job is to turn a "
                "freelancer/agency's service description into a small set of precise web "
                "search queries that will surface real companies who might need that service. "
                "Prefer specific, realistic search queries over vague ones. "
                "Generate at most 4 search queries, enough to realistically find "
                "{num_leads} distinct companies in total.",
            ),
            (
                "human",
                "My service: {service_description}\n"
                "Target industry/niche: {target_industry}\n"
                "Target location: {target_location}\n"
                "Type of client I want: {client_type}\n"
                "Number of leads needed: {num_leads}\n\n"
                "Generate a short ideal-client summary and a list of search queries.",
            ),
        ]
    )

    chain = prompt | structured_llm
    try:
        return chain.invoke(
            {
                "service_description": service_description,
                "target_industry": target_industry or "Not specified",
                "target_location": target_location or "Anywhere",
                "client_type": client_type or "Not specified",
                "num_leads": num_leads,
            }
        )
    except Exception:
        return None


def run_web_search(tavily_client: "TavilyClient", query: str, max_results: int = 5) -> List[dict]:
    """
    Run a single Tavily search query.

    Returns an empty list (never raises) if the search fails, is rate limited,
    or returns nothing - callers should treat an empty list as "no results".
    """
    if tavily_client is None:
        return []
    try:
        response = tavily_client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_answer=False,
        )
        return response.get("results", []) or []
    except Exception:
        return []


def extract_company_info(llm: ChatOpenAI, search_result: dict) -> Optional[CompanyInfo]:
    """
    Turn one raw Tavily search result (title/url/content) into a structured
    CompanyInfo object using the LLM with structured output.

    This is the "Company Information Extraction" step of the workflow.
    """
    title = search_result.get("title", "")
    url = search_result.get("url", "")
    content = truncate_text(search_result.get("content", ""))

    if not content and not title:
        return None

    structured_llm = llm.with_structured_output(CompanyInfo)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You extract factual company information from web search snippets. "
                "Only use information that is present in the provided text. "
                "If something is not mentioned, say 'Unknown' (or, for the contact email "
                "field specifically, say 'Contact email not found'). "
                "NEVER invent a company name, website, or email address that isn't in the text.",
            ),
            (
                "human",
                "Page title: {title}\n"
                "Page URL: {url}\n"
                "Page content snippet:\n{content}\n\n"
                "Extract structured company information from this.",
            ),
        ]
    )

    chain = prompt | structured_llm
    try:
        company = chain.invoke({"title": title, "url": url, "content": content})
    except Exception:
        return None

    if company is None:
        return None

    # Safety net: never trust a hallucinated email - re-verify it actually
    # appears in the source content, otherwise fall back to "not found".
    if company.contact_email and company.contact_email != "Contact email not found":
        if company.contact_email not in content:
            company.contact_email = extract_email_from_text(content)

    if not company.website or company.website.lower() == "not found":
        company.website = url or "Not found"

    if url and url not in company.source_urls:
        company.source_urls.append(url)

    return company


def research_potential_clients(
    llm: ChatOpenAI,
    tavily_client: Optional["TavilyClient"],
    plan: TargetClientPlan,
    num_leads: int,
) -> List[CompanyInfo]:
    """
    Run every search query in the plan, extract structured company info from
    each result, and return a de-duplicated list of up to `num_leads` companies.
    """
    companies: List[CompanyInfo] = []
    seen_names = set()

    if tavily_client is None:
        return companies

    for search_query in plan.search_queries:
        if len(companies) >= num_leads:
            break

        results = run_web_search(tavily_client, search_query.query)
        for result in results:
            if len(companies) >= num_leads:
                break

            company = extract_company_info(llm, result)
            if company is None:
                continue

            key = company.company_name.strip().lower()
            if not key or key in seen_names:
                continue

            seen_names.add(key)
            companies.append(company)

    return companies
