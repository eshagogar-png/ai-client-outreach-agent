# 🎯 AI Client Research & Outreach Agent

An AI-powered Streamlit app that helps freelancers, agencies, and small businesses **discover potential clients, understand their business, and generate personalized cold outreach emails** — with a human always reviewing before anything is sent.

---

## Project Overview

Finding the right clients to reach out to, and writing a genuinely personalized (not spammy) first email, is one of the most time-consuming parts of freelance/agency business development. This project automates the *research* and *drafting* work using an LLM agent built with LangChain, while keeping a human firmly in control of what actually gets sent.

You describe your service and the type of client you're after. The agent searches the web, extracts structured company information, scores each company as a lead (1–10), and drafts a personalized email for you to review, edit, and optionally send.

---

## Features

- 🔍 AI-powered prospect research using live web search
- 🧠 LLM-based lead qualification with a 1–10 lead score
- ✍️ Personalized, non-generic cold email generation
- 🌐 Structured extraction of company info (industry, description, contact, sources)
- 🙋 Human-in-the-loop review before any email is sent
- 📤 Optional SMTP/Gmail sending — fully optional, app works without it
- 📊 Clean Streamlit dashboard with export to CSV
- 🛡️ Graceful error handling everywhere — one bad lead never crashes the app

---

## Architecture

```
User
 ↓
Streamlit (UI, session state, human review)
 ↓
LangChain (structured prompts + Pydantic models)
 ↓
Web Search (Tavily API)
 ↓
LLM (OpenAI, via LangChain structured output)
 ↓
Lead Qualification (1-10 score + reasoning)
 ↓
Personalized Email (subject + body)
 ↓
Human Review (edit, copy, download)
 ↓
Optional Email Sending (smtplib, with explicit confirmation)
```

---

## Technologies Used

| Technology | Why it's used |
|---|---|
| **Streamlit** | Fast, simple way to build the interactive UI — no separate frontend needed |
| **LangChain** | Structures the multi-step LLM workflow (planning → extraction → scoring → writing) and enforces structured (Pydantic) outputs instead of fragile free-text parsing |
| **OpenAI API** (via `langchain-openai`) | The underlying LLM that powers reasoning, extraction, scoring, and writing |
| **Tavily API** | Simple, LLM-friendly web search API used for prospect research |
| **Pydantic** | Defines strict data models (`CompanyInfo`, `LeadQualification`, `OutreachEmail`, etc.) so the app never depends on parsing raw LLM text |
| **pandas** | Powers the lead dashboard table and CSV export |
| **python-dotenv** | Loads API keys/config from a local `.env` file |
| **smtplib** (standard library) | Sends emails via SMTP/Gmail — no extra email service required |

---

## Project Structure

```
ai-client-outreach-agent/
│
├── app.py                  # Streamlit UI and main workflow
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
│
├── src/
│   ├── __init__.py
│   ├── models.py            # Pydantic models (CompanyInfo, Lead, etc.)
│   ├── research.py          # LangChain planning + Tavily search + extraction
│   ├── lead_scoring.py      # LangChain lead qualification
│   ├── email_generator.py   # LangChain personalized email generation
│   └── email_sender.py      # Optional SMTP email sending
│
└── utils/
    ├── __init__.py
    └── helpers.py            # Small shared utility functions
```

---

## Installation

```bash
git clone <repository-url>
cd ai-client-outreach-agent
pip install -r requirements.txt
```

Then create your `.env` file from the example:

```bash
cp .env.example .env
```

Open `.env` and fill in your API keys (see below).

---

## API Keys

| Key | Where to get it |
|---|---|
| `OPENAI_API_KEY` | Create an account and generate a key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `TAVILY_API_KEY` | Sign up for a free key at [tavily.com](https://tavily.com) |
| `SMTP_*` (optional) | For Gmail: enable 2FA on your Google account, then generate an **App Password** at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) and use that as `SMTP_PASSWORD` |

Never commit your `.env` file — it's already excluded via `.gitignore`.

---

## Running Locally

```bash
streamlit run app.py
```

Then open the local URL Streamlit prints (usually `http://localhost:8501`).

You can also paste your API keys directly into the sidebar for a single session instead of using `.env`.

---

## Streamlit Deployment

1. Push this repository to GitHub (your `.env` will **not** be included, since it's git-ignored).
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your GitHub repo.
3. Set the main file path to `app.py`.
4. In your app's **Settings → Secrets**, add your keys in TOML format instead of a `.env` file:

```toml
OPENAI_API_KEY = "your_openai_api_key_here"
TAVILY_API_KEY = "your_tavily_api_key_here"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = "587"
SMTP_USERNAME = "your_email@gmail.com"
SMTP_PASSWORD = "your_app_password_here"
```

Streamlit automatically exposes these as environment variables (`os.getenv(...)`), so no code changes are needed.

---

## Example Use Case

> "A freelance web developer wants to find small businesses whose websites could be improved."

1. In the sidebar, they describe their service: *"I redesign slow, outdated websites into fast, modern, mobile-friendly sites for small businesses."*
2. They set the target industry to *"local restaurants"* and location to *"Austin, TX"*.
3. They click **🔎 Find Potential Clients**. The agent plans search queries like `"Austin TX restaurants official website"`, runs them via Tavily, and extracts structured info about each business found.
4. Each business is scored — a restaurant with an obviously outdated or missing website scores higher than one with a modern site.
5. The developer reviews the top leads, clicks **Generate Email** for the best one, edits the draft slightly, and — only after confirming the recipient address — sends it.

---

## Limitations

- **Search API limitations**: Tavily's free tier has rate limits, and search results may not always be a perfect fit for your niche.
- **LLM hallucinations**: While structured outputs and prompt constraints reduce this significantly, always review AI-generated content before sending it.
- **Incomplete public contact info**: Many companies don't publish a direct email address; the app will honestly show "Contact email not found" rather than guessing.
- **Email deliverability**: This app does not handle bounce tracking, spam-score checking, or deliverability optimization.
- **Rate limits**: Both OpenAI and Tavily enforce API rate limits — researching many leads at once may take time or occasionally fail for a subset of results.

---

## Future Improvements

- CRM integration (e.g. sync qualified leads to HubSpot/Airtable)
- LinkedIn-based research for better contact discovery
- Email open/click analytics
- Automated, human-approved follow-up sequences
- Persistent lead history across sessions (database integration)
- Multi-language outreach email generation

---

## How LangChain Is Used

LangChain is used to structure four distinct LLM steps as composable **prompt → structured-output chains**:

1. **Target Client Discovery** (`plan_target_client_search`) — turns the user's service/niche description into a list of concrete search queries (`TargetClientPlan`).
2. **Company Information Extraction** (`extract_company_info`) — turns a raw web search result into a clean `CompanyInfo` object.
3. **Lead Qualification** (`qualify_lead`) — scores a company 1–10 as a `LeadQualification` object.
4. **Email Generation** (`generate_outreach_email`) — writes a subject + body as an `OutreachEmail` object.

Each step uses `ChatPromptTemplate` combined with `llm.with_structured_output(PydanticModel)`, so the LLM's response is parsed directly into a typed Python object instead of being parsed from free text. This is the core LangChain pattern used throughout the project, and it's what makes the app reliable enough to demo or explain in an interview.

## How the AI Agent Works

The "agent" here is a **deterministic multi-step pipeline** (not a fully autonomous tool-calling agent), which keeps it simple, debuggable, and explainable:

```
Plan searches → Search the web → Extract structured info →
Qualify each lead → Generate a personalized email → Wait for human review
```

Each step's output feeds directly into the next step's input. This linear structure means every intermediate result (search plan, extracted company, lead score, email draft) is visible and inspectable in the Streamlit UI, and any single step failing (e.g. one bad search result) is caught and skipped without breaking the rest of the pipeline.
