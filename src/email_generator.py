"""
src/email_generator.py

Generates a personalized cold outreach email for a qualified lead using
LangChain with structured output (OutreachEmail).
"""

from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from src.models import CompanyInfo, LeadQualification, UserProfile, OutreachEmail


def generate_outreach_email(
    llm: ChatOpenAI,
    company: CompanyInfo,
    qualification: LeadQualification,
    user: UserProfile,
) -> Optional[OutreachEmail]:
    """
    Generate a personalized, non-spammy cold email for a single lead.
    """
    structured_llm = llm.with_structured_output(OutreachEmail)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You write short, professional, personalized cold outreach emails. "
                "Rules you must follow strictly:\n"
                "- Reference something SPECIFIC and TRUE about the company, based only on "
                "the description given. Do not invent facts, statistics, or claims.\n"
                "- Do not pretend to have personally researched the company beyond what "
                "is provided.\n"
                "- Do not invent a contact person's name - use a generic greeting like "
                "'Hi there' or the company name if no contact name is available.\n"
                "- Avoid generic filler like 'I hope this email finds you well'.\n"
                "- Keep the body under 150 words.\n"
                "- End with a clear, low-pressure call to action.\n"
                "- Sign off using the sender's real name/company provided below.",
            ),
            (
                "human",
                "SENDER INFO:\n"
                "Name: {sender_name}\n"
                "Company: {sender_company}\n"
                "Service offered: {sender_service}\n"
                "Website/portfolio: {sender_website}\n\n"
                "LEAD INFO:\n"
                "Company: {company_name}\n"
                "Industry: {industry}\n"
                "Description: {description}\n"
                "Why this is a good lead: {reason}\n\n"
                "Write a personalized subject line and email body.",
            ),
        ]
    )

    chain = prompt | structured_llm
    try:
        return chain.invoke(
            {
                "sender_name": user.name or "A freelancer",
                "sender_company": user.company or "",
                "sender_service": user.service or "professional services",
                "sender_website": user.website or "",
                "company_name": company.company_name,
                "industry": company.industry,
                "description": company.description,
                "reason": qualification.reason,
            }
        )
    except Exception:
        return None
