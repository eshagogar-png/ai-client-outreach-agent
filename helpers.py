"""
utils/helpers.py

Small, reusable helper functions used across the app.
"""

import os
import re


def is_configured(*env_vars: str) -> bool:
    """Return True if all given environment variable names are set and non-empty."""
    return all(os.getenv(var) for var in env_vars)


def truncate_text(text: str, max_chars: int = 1500) -> str:
    """Trim long text (e.g. scraped web content) down to a safe size before sending to an LLM."""
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def extract_email_from_text(text: str) -> str:
    """
    Try to find a real email address inside a block of text (e.g. search snippets).
    Returns 'Contact email not found' if none exists.

    We NEVER invent an email address - we only return one if it is literally
    present in the source text.
    """
    if not text:
        return "Contact email not found"
    match = EMAIL_REGEX.search(text)
    if match:
        return match.group(0)
    return "Contact email not found"


def safe_filename(name: str) -> str:
    """Convert a company name into a safe filename fragment."""
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip())
    return cleaned.strip("_").lower() or "lead"


def format_score_badge(score: int) -> str:
    """Return a small text badge describing a lead score, used in the UI."""
    if score >= 8:
        return "🟢 Strong lead"
    if score >= 5:
        return "🟡 Moderate lead"
    return "🔴 Weak lead"
