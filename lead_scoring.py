"""
src/lead_scoring.py

Uses LangChain (structured output) to qualify a researched company as a lead,
producing a 1-10 score and a short justification.
"""

from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from src.models import CompanyInfo, LeadQualification


def qualify_lead(
    llm: ChatOpenAI,
    company: CompanyInfo,
    service_description: str,
) -> Optional[LeadQualification]:
    """
    Ask the LLM how good a fit `company` is for someone offering
    `service_description`, and return a structured LeadQualification.
    """
    structured_llm = llm.with_structured_output(LeadQualification)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a lead-qualification assistant for a freelancer/agency. "
                "Given a company's public information and the service being offered, "
                "score how good a potential client this company is, from 1 (very poor fit) "
                "to 10 (excellent fit). Base your reasoning only on the information given. "
                "Be honest and realistic - most leads should score in the 3-7 range unless "
                "there is a clear, specific reason they'd need this service.",
            ),
            (
                "human",
                "Service being offered: {service_description}\n\n"
                "Company name: {company_name}\n"
                "Industry: {industry}\n"
                "Description: {description}\n\n"
                "Score this lead and explain why in 1-2 sentences.",
            ),
        ]
    )

    chain = prompt | structured_llm
    try:
        return chain.invoke(
            {
                "service_description": service_description,
                "company_name": company.company_name,
                "industry": company.industry,
                "description": company.description,
            }
        )
    except Exception:
        return None
