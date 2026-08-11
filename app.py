"""
app.py

AI Client Research & Outreach Agent - Streamlit entry point.

Workflow:
User Input -> Target Client Discovery (LangChain) -> Web Search (Tavily) ->
Company Information Extraction (LangChain) -> Lead Qualification (LangChain) ->
Lead Score -> Personalized Email Generation (LangChain) -> Human Review ->
Optional Email Sending (smtplib)
"""

import os
import io
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.models import UserProfile, Lead
from src.research import get_llm, get_tavily_client, plan_target_client_search, research_potential_clients
from src.lead_scoring import qualify_lead
from src.email_generator import generate_outreach_email
from src.email_sender import send_email, is_email_sending_configured
from utils.helpers import format_score_badge

load_dotenv()

st.set_page_config(page_title="AI Client Research & Outreach Agent", page_icon="🎯", layout="wide")

# ---------------------------------------------------------------------------
# Session state setup
# ---------------------------------------------------------------------------
if "leads" not in st.session_state:
    st.session_state.leads: list[Lead] = []
if "selected_lead_index" not in st.session_state:
    st.session_state.selected_lead_index = None

# ---------------------------------------------------------------------------
# Sidebar - user profile & API configuration
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("👤 Your Profile")
    user_name = st.text_input("Your Name", value=os.getenv("DEFAULT_USER_NAME", ""))
    user_company = st.text_input("Your Company/Brand", value=os.getenv("DEFAULT_USER_COMPANY", ""))
    user_service = st.text_area(
        "Service Offered",
        value=os.getenv("DEFAULT_USER_SERVICE", ""),
        help="Describe what you offer, e.g. 'I build fast, modern websites for small businesses.'",
    )
    user_website = st.text_input("Website/Portfolio", value=os.getenv("DEFAULT_USER_WEBSITE", ""))
    user_contact_email = st.text_input("Your Contact Email (for sign-off)", value=os.getenv("DEFAULT_USER_EMAIL", ""))

    st.divider()
    st.header("🎯 Targeting")
    target_industry = st.text_input("Target Industry/Niche", placeholder="e.g. local restaurants")
    target_location = st.text_input("Target Location (optional)", placeholder="e.g. Austin, TX")
    client_type = st.text_input("Type of Clients Wanted", placeholder="e.g. small businesses with outdated websites")
    num_leads = st.slider("Number of Potential Clients to Research", min_value=1, max_value=15, value=5)

    st.divider()
    st.header("🔑 API Configuration")
    st.caption("Keys are read from your .env file by default. You can override them here for this session only.")

    openai_key_input = st.text_input("OpenAI API Key", type="password", value="")
    tavily_key_input = st.text_input("Tavily API Key", type="password", value="")

    if openai_key_input:
        os.environ["OPENAI_API_KEY"] = openai_key_input
    if tavily_key_input:
        os.environ["TAVILY_API_KEY"] = tavily_key_input

    openai_ready = bool(os.getenv("OPENAI_API_KEY"))
    tavily_ready = bool(os.getenv("TAVILY_API_KEY"))

    st.write("✅ OpenAI key configured" if openai_ready else "⚠️ OpenAI key missing")
    st.write("✅ Tavily key configured" if tavily_ready else "⚠️ Tavily key missing")
    st.write("✅ Email sending configured" if is_email_sending_configured() else "ℹ️ Email sending not configured (optional)")

# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------
st.title("🎯 AI Client Research & Outreach Agent")
st.caption("Find relevant prospects, understand their business, and generate personalized outreach with AI.")

user_profile = UserProfile(
    name=user_name,
    company=user_company,
    service=user_service,
    website=user_website,
    contact_email=user_contact_email,
)

# ---------------------------------------------------------------------------
# Step 1 + 2 - Define target & run research
# ---------------------------------------------------------------------------
st.subheader("Step 1 — Define Your Target")
st.write(
    f"**Service:** {user_service or '_not set_'}  \n"
    f"**Target industry:** {target_industry or '_not set_'}  \n"
    f"**Target location:** {target_location or '_anywhere_'}  \n"
    f"**Client type:** {client_type or '_not set_'}"
)

st.subheader("Step 2 — Research Potential Clients")
find_clicked = st.button("🔎 Find Potential Clients", type="primary")

if find_clicked:
    if not user_service.strip():
        st.warning("Please describe your service in the sidebar before researching clients.")
    elif not openai_ready:
        st.error("OpenAI API key is not configured. Add it in the sidebar or in your .env file.")
    elif not tavily_ready:
        st.error("Tavily API key is not configured. Add it in the sidebar or in your .env file.")
    else:
        llm = get_llm()
        tavily_client = get_tavily_client()

        if llm is None:
            st.error("Could not initialize the LLM. Please check your OpenAI API key.")
        elif tavily_client is None:
            st.error("Could not initialize the web search client. Please check your Tavily API key.")
        else:
            with st.spinner("Planning research strategy..."):
                plan = plan_target_client_search(
                    llm, user_service, target_industry, target_location, client_type, num_leads
                )

            if plan is None:
                st.error("The AI couldn't build a research plan. Please try again or simplify your inputs.")
            else:
                st.info(f"**Research plan:** {plan.ideal_client_summary}")

                progress = st.progress(0, text="Searching the web for potential clients...")
                companies = []
                try:
                    companies = research_potential_clients(llm, tavily_client, plan, num_leads)
                except Exception as e:
                    st.error(f"Something went wrong during research: {e}")
                progress.progress(60, text="Qualifying leads...")

                leads: list[Lead] = []
                for i, company in enumerate(companies):
                    qualification = qualify_lead(llm, company, user_service)
                    if qualification is None:
                        # Skip leads the AI couldn't score rather than crashing.
                        continue
                    leads.append(Lead(company=company, qualification=qualification))

                progress.progress(100, text="Done!")
                progress.empty()

                if not leads:
                    st.warning(
                        "No leads could be found or qualified. Try a broader industry, "
                        "a different location, or check your API keys/quota."
                    )
                else:
                    leads.sort(key=lambda l: l.lead_score, reverse=True)
                    st.session_state.leads = leads
                    st.session_state.selected_lead_index = 0
                    st.success(f"Found and qualified {len(leads)} lead(s).")

# ---------------------------------------------------------------------------
# Step 3 - Lead dashboard
# ---------------------------------------------------------------------------
if st.session_state.leads:
    st.subheader("Step 3 — Lead Dashboard")

    table_rows = [
        {
            "Company": lead.company.company_name,
            "Industry": lead.company.industry,
            "Lead Score": lead.lead_score,
            "Website": lead.company.website,
            "Contact": lead.company.contact_email,
        }
        for lead in st.session_state.leads
    ]
    df = pd.DataFrame(table_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    company_names = [lead.company.company_name for lead in st.session_state.leads]
    selected_name = st.selectbox("Select a lead to view details", company_names)
    st.session_state.selected_lead_index = company_names.index(selected_name)

    selected_lead = st.session_state.leads[st.session_state.selected_lead_index]

    # -----------------------------------------------------------------
    # Step 4 - Lead details
    # -----------------------------------------------------------------
    st.subheader("Step 4 — Lead Details")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"### {selected_lead.company.company_name}")
        st.write(selected_lead.company.description)
        st.write(f"**Industry:** {selected_lead.company.industry}")
        st.write(f"**Location:** {selected_lead.company.location}")
        st.write(f"**Website:** {selected_lead.company.website}")
        st.write(f"**Contact:** {selected_lead.company.contact_email}")
        if selected_lead.company.source_urls:
            st.write("**Sources:**")
            for src in selected_lead.company.source_urls:
                st.write(f"- {src}")
    with col2:
        st.metric("Lead Score", f"{selected_lead.lead_score}/10")
        st.write(format_score_badge(selected_lead.lead_score))
        st.write("**Why this is a good lead:**")
        st.write(selected_lead.qualification.reason)

    # -----------------------------------------------------------------
    # Step 5 - AI outreach email
    # -----------------------------------------------------------------
    st.subheader("Step 5 — AI Outreach Email")

    if st.button("✉️ Generate Email"):
        if not openai_ready:
            st.error("OpenAI API key is not configured.")
        else:
            llm = get_llm()
            if llm is None:
                st.error("Could not initialize the LLM.")
            else:
                with st.spinner("Writing a personalized email..."):
                    email = generate_outreach_email(
                        llm, selected_lead.company, selected_lead.qualification, user_profile
                    )
                if email is None:
                    st.error("Couldn't generate an email for this lead. Please try again.")
                else:
                    selected_lead.email_subject = email.subject
                    selected_lead.email_body = email.body
                    st.success("Email generated below.")

    if selected_lead.email_subject and selected_lead.email_body:
        st.text_input("Subject", value=selected_lead.email_subject, key=f"subject_{st.session_state.selected_lead_index}")
        st.text_area(
            "Email Body",
            value=selected_lead.email_body,
            height=250,
            key=f"body_{st.session_state.selected_lead_index}",
        )

        email_text = f"Subject: {selected_lead.email_subject}\n\n{selected_lead.email_body}"
        col_a, col_b = st.columns(2)
        with col_a:
            st.download_button(
                "⬇️ Download Email (.txt)",
                data=email_text,
                file_name=f"{selected_lead.company.company_name.replace(' ', '_')}_email.txt",
                mime="text/plain",
            )
        with col_b:
            st.code(email_text, language=None)
            st.caption("Select the text above and copy it (Ctrl/Cmd+C).")

        # -----------------------------------------------------------------
        # Step 6 - Optional sending, with mandatory human confirmation
        # -----------------------------------------------------------------
        st.subheader("Step 6 — Send")

        if not is_email_sending_configured():
            st.info(
                "Email sending is optional and not configured. Set SMTP_SERVER, SMTP_PORT, "
                "SMTP_USERNAME, and SMTP_PASSWORD to enable it."
            )
        else:
            recipient = selected_lead.company.contact_email
            if recipient == "Contact email not found" or "@" not in recipient:
                st.warning("No verified contact email is available for this lead, so sending is disabled.")
            else:
                confirm_key = f"confirm_send_{st.session_state.selected_lead_index}"
                if st.checkbox(f"You are about to send this email to {recipient}. Continue?", key=confirm_key):
                    if st.button("🚀 Send Email Now"):
                        success, message = send_email(
                            recipient, selected_lead.email_subject, selected_lead.email_body
                        )
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
else:
    st.info("No leads yet. Fill in your profile and targeting in the sidebar, then click 'Find Potential Clients'.")

# ---------------------------------------------------------------------------
# Export all leads
# ---------------------------------------------------------------------------
if st.session_state.leads:
    st.divider()
    export_rows = [
        {
            "Company": lead.company.company_name,
            "Industry": lead.company.industry,
            "Location": lead.company.location,
            "Website": lead.company.website,
            "Contact": lead.company.contact_email,
            "Lead Score": lead.lead_score,
            "Reason": lead.qualification.reason,
            "Email Subject": lead.email_subject or "",
            "Email Body": lead.email_body or "",
        }
        for lead in st.session_state.leads
    ]
    export_df = pd.DataFrame(export_rows)
    csv_buffer = io.StringIO()
    export_df.to_csv(csv_buffer, index=False)
    st.download_button(
        "⬇️ Download All Leads (.csv)",
        data=csv_buffer.getvalue(),
        file_name="leads.csv",
        mime="text/csv",
    )
