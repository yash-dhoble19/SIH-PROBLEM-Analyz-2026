# 🚀 Smart India Hackathon (SIH) 2026 Problem Statement Analyzer & AI Intelligence Platform

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PostgreSQL-Neon%20%2B%20pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="Neon Postgres + pgvector" />
  <img src="https://img.shields.io/badge/AI%20Agents-Multi--Agent%20Pipeline-FF6F00?style=for-the-badge&logo=openai&logoColor=white" alt="Multi-Agent AI" />
  <img src="https://img.shields.io/badge/Tests-9%2F9%20Passing-brightgreen?style=for-the-badge&logo=pytest&logoColor=white" alt="Tests" />
  <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="License" />
</p>

---

## 🌟 Overview

The **SIH 2026 Problem Statement Analyzer & AI Intelligence Platform** is an enterprise-grade solution designed to extract, analyze, match, and architect solutions for all Smart India Hackathon 2026 problem statements.

It combines a **high-throughput web scraping engine**, a **dual-database architecture (SQLite + Neon PostgreSQL with `pgvector`)**, an **autonomous multi-agent AI pipeline**, and an **interactive real-time web dashboard** to provide complete visibility, repository gap analysis, and tailored AI prompt generation for hackathon teams.

---

## ✨ Key Features

### 1. 🕷️ High-Performance Scraping & Data Extraction Pipeline
- **100% Data Integrity**: Extracts all **226 SIH 2026 problem statements** from the official portal ([sih.gov.in/sih2026PS](https://www.sih.gov.in/sih2026PS)) in under **5 seconds**.
- **Deep Modal Extraction**: Recursively parses Bootstrap modals to capture full, un-truncated **Background**, **Description**, **Expected Solutions**, **Organization/Ministry**, **Category**, **Theme**, **Submitted Ideas Counter**, **Deadlines**, **Dataset URLs**, and **YouTube reference links**.
- **Idempotent Storage & Dual-Engine Sync**:
  - Local **SQLite** database (`data/sih_2026.db`) with `UPSERT` deduplication.
  - Cloud **Neon Serverless PostgreSQL** with `pgvector` vector embeddings.
- **Instant Clean Exports**: Exports structured data to UTF-8 CSV (`data/processed/sih_2026_problem_statements.csv`) and formatted JSON.

### 2. 🧠 Multi-Agent AI Analysis Engine
A modular agent ecosystem located in `platform_core/agents/`:
- **Repository Explorer Agent**: Connects to public/private GitHub repositories, analyzes architecture, technology stacks, file trees, and complexity.
- **Problem Analyst Agent**: Breaks down problem statements into functional requirements, technical constraints, and scoring criteria.
- **Matching Agent & Semantic Vector Search**: Uses 384-dimensional dense vector embeddings combined with keyword matching to rank the best-suited problem statements for any given codebase.
- **Gap Analysis Agent**: Compares existing repository capabilities against SIH problem requirements to produce a structured **Gap Matrix** (*Implemented*, *Partially Implemented*, *Missing*).
- **Solution Architect Agent**: Formulates high-level system designs, component topologies, and database schema recommendations.
- **Prompt Generator Agent**: Creates modular, production-ready prompts formatted for Claude 3.7, GPT-4o, and Gemini to rapidly implement missing features.
- **Autonomous Pipeline Orchestrator**: Coordinates agent execution with real-time progress tracking, caching, and state isolation.

### 3. 🛡️ Enterprise Security & Guardrails
- **SSRF Defense**: Strict validation of GitHub repository URLs to prevent internal network scanning.
- **Secret Redaction**: Automatically detects and masks API tokens, private keys, and environment credentials (`[REDACTED_SECRET]`).
- **Resilient Networking**: Exponential backoff retries and SSL certificate fallback.

### 4. 📊 Interactive Web Dashboard & API
- **FastAPI REST API**: Fully documented interactive OpenAPI/Swagger endpoints (`/docs`).
- **Interactive UI**:
  - Live KPI Counters (Software vs. Hardware distribution, Themes, Ministries).
  - Instant debounced multi-keyword search.
  - Interactive Chart.js analytics.
  - 1-Click "Copy AI Prompt" generation for LLM coding workflows.
  - LocalStorage-backed bookmarking and favorites.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    A[SIH Portal: sih.gov.in] -->|Scrape & Parse| B[Scraper Engine]
    B -->|Persist| C[(SQLite DB)]
    B -->|Sync / Migrate| D[(Neon PostgreSQL + pgvector)]
    
    E[GitHub Repository] -->|Analyze Codebase| F[Repository Explorer Agent]
    
    D --> G[Multi-Agent Pipeline Orchestrator]
    F --> G
    
    subgraph Multi-Agent AI Pipeline
        G --> H[Problem Analyst Agent]
        G --> I[Semantic Matching Agent]
        G --> J[Gap Analysis Agent]
        G --> K[Solution Architect Agent]
        G --> L[Prompt Generator Agent]
    end
    
    G --> M[FastAPI REST API Layer]
    M --> N[Interactive Web Dashboard]
    M --> O[CSV / JSON / Prompt Exporters]
```

---

## 📁 Repository Structure

```
SIH-PROBLEM-Analyz-2026/
│
├── platform_core/                     # Core Intelligence Platform
│   ├── agents/                        # Autonomous AI Agents
│   │   ├── architecture_agent.py      # Architecture planning
│   │   ├── base.py                    # Base agent interface & execution lifecycle
│   │   ├── explorer_agent.py          # GitHub repo scanning
│   │   ├── gap_analysis_agent.py      # Requirement vs codebase gap matrix
│   │   ├── matching_agent.py          # Vector semantic matching
│   │   ├── orchestrator.py            # Workflow pipeline coordinator
│   │   ├── problem_analyst_agent.py   # Domain requirement extractor
│   │   ├── prompt_generator_agent.py  # AI coding prompt builder
│   │   ├── solution_architect_agent.py# Solution designer
│   │   └── understanding_agent.py     # Code understanding & summary
│   ├── ai/                            # AI & Vector Embeddings
│   │   ├── embeddings.py              # 384-dim dense embedding engine
│   │   └── providers.py               # Multi-LLM provider connectors (OpenAI, Gemini, Claude)
│   ├── api/                           # FastAPI Endpoints & Routers
│   │   ├── routes_admin.py            # Scraper & database management endpoints
│   │   ├── routes_analysis.py         # AI analysis & gap computation routes
│   │   ├── routes_problems.py         # Problem search & filter routes
│   │   └── schemas.py                 # Pydantic request/response models
│   ├── database/                      # Neon PostgreSQL & pgvector Layer
│   │   ├── connection.py              # SQLAlchemy engine & session management
│   │   └── models.py                  # ORM models (ProblemStatement, Repository, etc.)
│   ├── github/                        # GitHub Client & Security
│   │   ├── analyzer.py                # AST & file-pattern code analyzer
│   │   ├── client.py                  # Resilient GitHub API client
│   │   └── security.py                # SSRF guard & credential sanitizer
│   └── config.py                      # Global application settings & Pydantic config
│
├── scraper/                           # SIH Web Scraping Engine
│   ├── client.py                      # HTTP client with exponential backoff & SSL fallback
│   ├── database.py                    # SQLite storage layer with UPSERT
│   ├── exporter.py                    # CSV (utf-8-sig) & JSON exporter
│   ├── models.py                      # Pydantic validation schemas
│   ├── parser.py                      # DOM and modal HTML-to-Markdown parser
│   ├── scraper.py                     # Pipeline orchestrator
│   └── utils.py                       # Text cleaning & section segmenter
│
├── static/                            # Interactive Web Dashboard
│   ├── index.html                     # Responsive UI layout
│   ├── css/dashboard.css              # Custom styling & dark mode
│   └── js/dashboard.js                # Search, chart, and filtering logic
│
├── data/                              # Data Storage
│   ├── raw/sih2026PS_raw.html         # Raw HTML snapshot
│   ├── processed/                     # Clean CSV and JSON exports
│   └── sih_2026.db                    # SQLite database
│
├── scripts/                           # Migration & Utility Scripts
│   └── migrate_sqlite_to_neon.py      # SQLite to Neon PostgreSQL data migration
│
├── tests/                             # Test Suite
│   ├── fixtures/                      # Test HTML fixtures
│   ├── test_agent_pipeline.py         # Multi-agent workflow tests
│   ├── test_database.py               # Database integrity tests
│   ├── test_gap_analysis.py           # Gap matrix verification tests
│   ├── test_models.py                 # Pydantic schema validation tests
│   ├── test_multi_repo_isolation.py   # Multi-tenant / multi-repo isolation tests
│   ├── test_parser.py                 # Parser & cleaner unit tests
│   ├── test_platform.py               # Platform integration tests
│   ├── test_scraper.py                # End-to-end scraper mock tests
│   └── run_tests.py                   # Automated unified test runner
│
├── app.py                             # Main FastAPI Application Entrypoint
├── main.py                            # Scraper CLI Tool
├── requirements.txt                   # Project Dependencies
├── .env.example                       # Environment Configuration Template
├── .gitignore                         # Git Ignore Rules
└── README.md                          # Documentation
```

---

## ⚡ Quick Start

### 1. Prerequisites
- **Python 3.11+** (Python 3.12 recommended)
- **Git**

### 2. Clone the Repository
```bash
git clone https://github.com/yash-dhoble19/SIH-PROBLEM-Analyz-2026.git
cd SIH-PROBLEM-Analyz-2026
```

### 3. Set Up Virtual Environment & Dependencies
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the example environment file and configure your settings:
```bash
cp .env.example .env
```

Edit `.env` (optional API keys for online LLM providers; offline engines are built-in):
```ini
DATABASE_URL=postgresql://neondb_owner:password@ep-sample.us-east-2.aws.neon.tech/neondb?sslmode=require
AI_PROVIDER=auto
EMBEDDING_PROVIDER=auto
LOCAL_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
GITHUB_TOKEN=
PORT=8000
HOST=127.0.0.1
```

`EMBEDDING_PROVIDER=auto` uses the local MiniLM sentence-transformer and never
contacts OpenAI or Google. Set it explicitly to `openai` or `google` only when
you have configured that provider's key. After changing embedding backends,
regenerate persisted problem-statement vectors once:

```bash
python scripts/rebuild_embeddings.py
```

---

## 🚀 Usage

### 🌐 1. Launch the Interactive Dashboard
```bash
python app.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser to access:
- **Live Search & Filter**: Filter problem statements by category (`Software` / `Hardware`), 17 themes, or 34 ministries.
- **Deep Modal Detail**: View full background, requirements, and expected solution specs.
- **AI Prompt Exporter**: 1-click prompt generator ready for LLMs.
- **Repository Analysis**: Paste any GitHub URL to run gap analysis and problem statement matching.

---

### 💻 2. Scraper CLI Options
```bash
# Run full scrape and export to SQLite, CSV, and JSON
python main.py

# Export only CSV
python main.py --output csv

# Export only JSON
python main.py --output json

# Re-run parsing from cached raw HTML (offline mode)
python main.py --use-cache
```

---

### 🔄 3. Database Migration (SQLite ➔ Neon PostgreSQL)
To sync your local SQLite data to a cloud Neon PostgreSQL database with `pgvector`:
```bash
python scripts/migrate_sqlite_to_neon.py
```

---

## 📡 REST API Documentation

When the application is running, open **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)** to view the Swagger UI:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/stats` | Returns total problem statement count, software vs hardware breakdown, top themes |
| `GET` | `/api/filters` | Returns available categories, themes, and organizations |
| `GET` | `/api/problems` | Search and paginate problem statements with multi-parameter filtering |
| `GET` | `/api/problems/{id}` | Detailed single problem statement data |
| `POST` | `/api/analyze-repo` | Trigger GitHub repository analysis and AI problem statement matching |
| `POST` | `/api/gap-analysis` | Compute gap matrix between a repository and a target problem statement |
| `POST` | `/api/generate-prompts` | Generate implementation prompts for LLMs |
| `POST` | `/api/admin/scrape` | Trigger live scrape and database update |

---

## 📊 Database Schema (`problem_statements`)

| Column | Type | Description |
| :--- | :--- | :--- |
| `problem_statement_id` | **TEXT (PK)** | Unique identifier (e.g. `SIH26001`) |
| `serial_number` | **INTEGER** | Sequential table row index |
| `problem_statement_number` | **TEXT** | Numeric ID (e.g. `26001`) |
| `title` | **TEXT** | Complete problem statement title |
| `organization` | **TEXT** | Submitting ministry / agency |
| `department` | **TEXT** | Department name |
| `category` | **TEXT** | `Software` or `Hardware` |
| `theme` | **TEXT** | Domain (e.g. `Disaster Management`, `MedTech`) |
| `submitted_ideas_count` | **TEXT** | Submissions counter (e.g. `0/500`) |
| `deadline_for_idea_submission` | **TEXT** | Submission deadline |
| `background` | **TEXT** | Problem background context |
| `description` | **TEXT** | Full detailed description |
| `expected_solution` | **TEXT** | Technical solution specifications |
| `youtube_link` | **TEXT** | Reference video URL |
| `dataset_link` | **TEXT** | Provided dataset URL |
| `contact_info` | **TEXT** | Ministry / organization contact |
| `search_text` | **TEXT** | Unified text for RAG and AI vector embeddings |

---

## 🧪 Testing

Run the full automated test suite:
```bash
python tests/run_tests.py
```
Or with pytest:
```bash
python -m pytest -v
```

All 9 validation test suites test:
- Database connection & schema integrity (all 226 records verified)
- API endpoint metrics, query filters, and pagination
- GitHub URL parser, SSRF validation, and secret sanitization
- 384-dimensional vector embedding generation
- Multi-agent pipeline execution & gap matrix calculations

---

## 🤝 Contributing

Contributions are welcome! To contribute:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** - see the LICENSE file for details.

---

<p align="center">
  Developed for <b>Smart India Hackathon (SIH) 2026</b> 🇮🇳
</p>
