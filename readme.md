# MetaBot 🤖 — AI Data Governance Agent for OpenMetadata

> An intelligent AI-powered assistant that brings natural language interaction, PII detection, lineage exploration, and governance automation to OpenMetadata.

## 🏆 Hackathon Track
**Paradox #T-01: MCP Ecosystem & AI Agents**

MetaBot transforms OpenMetadata from a passive catalog into an active, conversational intelligence layer. Data engineers and governance teams can interact with their entire data estate through natural language — discovering assets, detecting PII, exploring lineage, and monitoring data quality without writing a single query.

---

## ✨ Features

### 💬 AI Chat Agent
- Powered by Claude via Anthropic API with streaming responses
- Context-aware: pulls live OpenMetadata stats into every conversation
- Smart quick actions for common governance workflows
- Works offline with intelligent fallback responses

### 🔒 PII Scanner
- Automatically detects 10+ PII categories (email, phone, SSN, credit card, DOB, address, name, IP, passport, national ID)
- Pattern matching against column names across all tables
- Risk scoring (HIGH / MEDIUM / LOW) per table
- Expandable detail view per table
- JSON report export

### 📊 Observability Dashboard
- Real-time platform stats (tables, dashboards, pipelines, topics)
- Data quality test pass/fail rates with visual bars
- Failing test detail with entity context
- PII risk summary at a glance

### 🔍 Asset Search
- Full-text search across tables, dashboards, pipelines, and topics
- Filter by entity type
- Owner, tags, and description preview
- Click-to-chat for deep dives

### 🔗 Lineage Explorer
- Visual upstream/downstream lineage graph
- Support for tables, dashboards, pipelines
- Node/edge count statistics
- Configurable depth (3 levels up/downstream)

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    MetaBot Frontend                      │
│            (Vanilla HTML/CSS/JS — index.html)            │
│  Chat | Dashboard | Search | PII Scanner | Lineage       │
└────────────────────┬────────────────────────────────────┘
                     │ REST + SSE streaming
┌────────────────────▼────────────────────────────────────┐
│               MetaBot Backend (FastAPI)                  │
│                   main.py — Port 8000                    │
│                                                          │
│  /api/chat        → Anthropic Claude (streaming SSE)     │
│  /api/om/search   → OpenMetadata Search API              │
│  /api/om/lineage  → OpenMetadata Lineage API             │
│  /api/om/scan-all-pii → Column PII detection             │
│  /api/om/data-quality → DQ test results                  │
│  /api/om/stats    → Platform-wide counts                 │
└────────────────────┬────────────────────────────────────┘
                     │ REST API
┌────────────────────▼────────────────────────────────────┐
│              OpenMetadata (port 8585)                    │
│     Tables | Lineage | DQ Tests | Classifications        │
│     70+ connectors | MCP Server | REST API               │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- OpenMetadata running locally or in cloud ([Docker quickstart](https://docs.open-metadata.org/v1.2.x/quick-start/local-docker-deployment))
- Anthropic API key (for AI chat)

### 1. Clone and setup backend

```bash
cd metabot/backend
cp .env.example .env
# Edit .env with your credentials
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Open the frontend

```bash
# Simply open in browser:
open metabot/frontend/index.html
# OR serve with any static server:
cd frontend && python -m http.server 3000
```

### 3. Connect

1. Click **Connect OpenMetadata** in the header
2. Enter your OpenMetadata host (default: `http://localhost:8585`)
3. Enter your JWT token (from OM UI: Settings → Access Tokens)
4. Enter your Anthropic API key
5. Click **Connect**

---

## 🐳 Docker Deployment

```bash
cp backend/.env.example .env
# Fill in your values

docker-compose up -d
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## 🔌 API Reference

All endpoints accept `om_host` and `om_token` query params or use env defaults.

| Endpoint | Method | Description |
|---|---|---|
| `/api/chat` | POST | Streaming AI chat (SSE) |
| `/api/om/test` | POST | Test OM connection |
| `/api/om/stats` | GET | Platform-wide stats |
| `/api/om/search` | GET | Search entities |
| `/api/om/lineage` | POST | Get entity lineage |
| `/api/om/classify` | POST | Classify single table PII |
| `/api/om/scan-all-pii` | POST | Scan all tables for PII |
| `/api/om/data-quality` | GET | DQ test results |
| `/api/om/recent-activity` | GET | Activity feed |

**Full API docs:** `http://localhost:8000/docs`

---

## 🔑 Getting Your OpenMetadata JWT Token

1. Open OpenMetadata UI
2. Navigate to **Settings → Users**
3. Click on your user → **Access Token**
4. Generate a new token and copy it

---

## 🧠 How PII Detection Works

MetaBot scans column names against 10 PII pattern categories:

| Category | Detected patterns |
|---|---|
| Email | email, mail, e_mail, emailaddress |
| Phone | phone, mobile, cell, telephone |
| SSN | ssn, social_security, tax_id |
| Credit Card | credit_card, cardnumber, cc_number |
| Date of Birth | dob, date_of_birth, birthdate |
| Address | address, street, zipcode, postal_code |
| Name | first_name, last_name, fullname |
| IP Address | ip_address, ip_addr, client_ip |
| Passport | passport, passport_number |
| National ID | national_id, aadhaar, pan_number |

Risk levels:
- **HIGH**: 3+ PII columns in one table
- **MEDIUM**: 1-2 PII columns
- **LOW**: Pattern match but low confidence

---

## 🏆 Judging Criteria Alignment

| Criterion | How MetaBot addresses it |
|---|---|
| **Potential Impact** | Every data team needs governance automation; MetaBot makes it accessible |
| **Creativity & Innovation** | Conversational AI on top of OpenMetadata's full API surface |
| **Technical Excellence** | Streaming SSE, async Python, full REST integration, PII detection engine |
| **Best Use of OpenMetadata** | Uses Search, Lineage, DQ, Classification, Feeds, and MCP APIs |
| **User Experience** | Chat-first UI, quick actions, visual PII scanner, lineage graph |
| **Presentation Quality** | Live demo shows real-time governance in action |

---

## 📍 OpenMetadata APIs Used

- `GET /api/v1/search/query` — Full-text entity search
- `GET /api/v1/lineage/{type}/name/{fqn}` — Lineage graph
- `GET /api/v1/tables?fields=columns,tags` — Table metadata + columns
- `GET /api/v1/dataQuality/testCases?fields=testCaseResult` — DQ tests
- `GET /api/v1/feeds` — Activity feed
- `PATCH /api/v1/tables/{id}` — Apply classification tags
- `GET /api/v1/tables|topics|dashboards|pipelines` — Asset counts

---

## 🛠 Tech Stack

**Frontend:** Vanilla HTML5 + CSS3 + JavaScript (no framework — zero dependencies, maximum performance)  
**Backend:** FastAPI (Python) — async, streaming SSE support  
**AI:** Anthropic Claude claude-sonnet-4-20250514 via streaming API  
**Data:** OpenMetadata REST API v1  
**Fonts:** Syne (display) + DM Sans (body) + DM Mono (code)

---

## 📄 License

MIT — Built for the Back to the Metadata Hackathon by WeMakeDevs × OpenMetadata