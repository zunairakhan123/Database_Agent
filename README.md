# Enterprise Agentic Business Intelligence Platform

**A secure, natural-language interface for federated data analysis — powered by LangGraph, Groq, and DuckDB.**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Node](https://img.shields.io/badge/Node.js-18%2B-green)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)
![React](https://img.shields.io/badge/Frontend-React-61DAFB)
![DuckDB](https://img.shields.io/badge/Engine-DuckDB-FFF000)
![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-8A2BE2)
![License](https://img.shields.io/badge/License-TBD-lightgrey)

An enterprise-grade, multi-agent Data Analytics platform that lets users query, join, and unify fragmented data sources (PostgreSQL, CSVs, Google Sheets) via automated, AST-validated SQL generation — without writing a single line of SQL.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [System Architecture](#️-system-architecture)
- [Core Execution Phases](#️-core-execution-phases)
- [Repository Structure](#-repository-structure)
- [Getting Started](#-getting-started)
- [Configuration](#-configuration)
- [Contributing](#-contributing)
- [License](#-license)

---

## Overview

This platform provides a secure, natural language interface for federated data analysis, allowing users to seamlessly query, join, and unify fragmented data sources via automated, AST-validated SQL generation. It combines a deterministic LangGraph reasoning pipeline, a zero-copy DuckDB query engine, and an automated semantic layer to deliver safe, explainable, business-ready analytics.

---

## ✨ Key Features

### Agentic SQL Orchestration
- **Multi-Node Reasoning Graph** — Built on LangGraph to strictly decouple intent routing, context retrieval, SQL generation, and validation into atomic, testable execution nodes.
- **Concurrent Multi-Chat Capability:** Supports isolated, multi-threaded conversational sessions. Users can run parallel analytical explorations within the same workspace without polluting the LLM's context window or state history.
- **Graceful Error Sanitization** — A dedicated routing node intercepts raw database stack traces (e.g., DuckDB Binder Errors) and translates them into polite, non-technical business responses, ensuring a leak-proof presentation layer.

### Federated Data Ingestion
- **Zero-Copy Querying** — Utilizes DuckDB to query across distributed, heterogeneous sources without requiring centralized ETL duplication.
- **Multi-Source Staging Cart** — A split-pane connection interface allowing users to stage and attach multiple datasets concurrently into a unified workspace.
- **Dynamic Entity Unification** — The LLM is structurally prompted to differentiate between Data Enrichment (using strict `JOIN` rules) and Data Unification (dynamically using `UNION ALL` for fragmented logs).

### Enterprise Security & Guardrails
- **AST Read-Only Validation** — Intercepts generated SQL and parses the Abstract Syntax Tree (AST) via `sqlglot`. Mathematically whitelists read operations (`SELECT`, `UNION`, `INTERSECT`) while completely blocking destructive mutations (`DROP`, `DELETE`, `UPDATE`).
- **Intent Guardrails** — Structured output models route off-topic or non-analytical queries away from the execution engine instantly.

### Automated Semantic Layer
- **LLM-Powered Metric Drafting** — Leverages Groq (`openai/gpt-oss-20b`) via strict schema validation to automatically extract physical schemas and draft usable business metrics and synonyms.
- **Hybrid RRF Retrieval** — Injects context into the agent using a Reciprocal Rank Fusion hybrid search against a persistent SQLite metadata registry, featuring programmatic namespace normalization to prevent catalog misalignments.

### Interactive Visualization & Topology
- **Interactive ERD Mapper:** A visual, drag-and-drop Entity Relationship Diagram (ERD) interface that allows users to map logical joins, define cardinality (1:1, 1:N), and establish cross-database relationships (e.g., joining a Postgres table directly to a CSV). These visual links instantly compile into the backend's semantic join rules.
- **Dynamic Charting Engine:** An intelligent frontend rendering engine that auto-detects numerical vs. categorical data types to instantly generate dynamic, multi-metric charts. It maps axes dynamically based on the LLM's structured output.
- **State Preservation:** Employs strict dimensional viewport locking and session hydration to preserve chat history, chart configurations, and ERD layouts seamlessly across page transitions without layout shifts.

### Workspace & Session Management
- **Persistent History Registry:** A dedicated root dashboard backed by SQLite session state allows users to safely pause, manage, and resume past analytical sessions without losing their conversational or data context.
- **Non-Linear Ingestion:** The architecture supports a non-linear data flow, enabling users to attach new datasets concurrently to active workspaces without dropping their existing semantic context.
- **Race Condition Mitigation:** The frontend interface implements strict dimensional locking during form expansions and patches React hydration loops to prevent UI state drift during complex navigation.

---

## Tech Stack

| Layer                  | Technology                                    |
|----------------------- |-----------------------------------------------|
| Orchestration          | LangGraph                                     |
| LLM Inference          | Groq / Local model                            |
| Query Engine           | DuckDB                                        |
| SQL Validation         | `sqlglot` (AST-based)                         |
| Metadata Registry      | SQLite                                        |
| Backend API            | FastAPI                                       |
| Frontend               | React (SPA)                                   |
| Data Sources Supported | PostgreSQL,MySQL, CSV,Excel,Google Sheets     |

---

## System Architecture

The core reasoning engine is built on **LangGraph**, utilizing a deterministic node-based workflow to ensure query safety, semantic accuracy, and robust error handling.

```
┌────────────────┐   NL Query   ┌──────────────────┐
│ React Frontend │ ───────────▶ │ FastAPI Backend  │
└────────────────┘              └────────┬─────────┘
                                          │
                                          ▼
                                 ┌──────────────────┐
                                 │   analyze_input   │
                                 └───┬──────────┬────┘
                          Valid BI Query    Off-Topic
                                 │              │
                                 ▼              ▼
                     ┌────────────────────┐  ┌───────────────────┐
                     │  retrieve_context  │  │  Reject & Return  │
                     └──────────┬─────────┘  └───────────────────┘
                     RRF Semantic Search
                                │
                                ▼
                     ┌────────────────────┐
              ┌─────▶│    generate_sql    │
              │      │  (Groq gpt-oss-20b)│
              │      └──────────┬─────────┘
              │                 ▼
   Execution Error     ┌────────────────────────┐
   (< 3 retries)       │  validate_and_execute  │
              │        └───┬────────────────┬───┘
              │   AST Safe + Success   Max Retries / AST Violation
              │            │                 │
              │            ▼                 ▼
              │  ┌───────────────────┐ ┌───────────────────┐
              │  │  Return DataFrame │ │  sanitize_error   │
              │  └───────────────────┘ └─────────┬─────────┘
              │                                  │ Masked Error
              └──────────────────────────────────┤
                                                 ▼
                                        ┌───────────────────┐
                                        │  Client Response  │
                                        └───────────────────┘
```

---

## Core Execution Phases

The agentic workflow operates through highly constrained execution nodes located in `backend/app/agent/`:

| # | Node                    | Responsibility |
|---|--------------------------|-----------------|
| 1 | `analyze_input`          | Primary gatekeeper. Uses structured output routing to block non-analytical queries (e.g., coding requests, casual chat) and restricts the LLM strictly to business intelligence domains. |
| 2 | `retrieve_context`       | Executes Hybrid Reciprocal Rank Fusion (RRF) against the persistent metadata registry. Programmatically normalizes namespaces across databases and files to guarantee pristine context injection without LLM hallucinations. |
| 3 | `generate_sql`           | Powered by Groq (`openai/gpt-oss-20b`). Employs a strict topology guardrail to separate Data Enrichment from Data Unification. Refuses multi-table relationships unless explicitly defined in the semantic layer. |
| 4 | `validate_and_execute`   | Parses generated SQL into an Abstract Syntax Tree via `sqlglot` prior to execution. Explicitly permits read-only operations while mathematically blocking destructive commands. |
| 5 | `sanitize_error`         | Client-facing safety node. Intercepts backend stack traces on fatal database errors and translates them into polite business logic to prevent architecture leakage. |

---

## Repository Structure

The project follows a modular, domain-driven design pattern:

```
├── backend/
│   ├── app/
│   │   ├── agent/                  # Core LangGraph orchestration
│   │   │   ├── ast_validator.py    # SQL syntax and security validation
│   │   │   ├── graph.py            # State machine definition
│   │   │   ├── nodes.py            # Execution nodes & LLM prompts
│   │   │   ├── semantic_drafter.py # Automated metric generation
│   │   │   └── state.py            # TypedDict graph state
│   │   ├── api/                    # FastAPI Endpoints
│   │   │   ├── agent.py            # Chat/Query endpoints
│   │   │   ├── catalog.py          # ERD and schema endpoints
│   │   │   ├── connections.py      # Database/File attachment routes
│   │   │   └── metadata.py         # Semantic layer management
│   │   ├── core/                   # Application Config & Security
│   │   │   ├── schema_models.py    # Pydantic validation schemas
│   │   │   ├── security.py         # Auth & Middleware
│   │   │   └── semantic_models.py  # Pydantic semantic models
│   │   ├── database/               # Data Access Layer
│   │   │   ├── duckdb_engine.py       # DuckDB core execution
│   │   │   ├── gsheets_connector.py   # Google Sheets integration
│   │   │   ├── metadata_extractor.py  # Schema introspection
│   │   │   ├── metadata_store.py      # SQLite registry management
│   │   │   ├── pool_manager.py        # Connection pooling
│   │   │   ├── semantic_store.py      # Business logic persistence
│   │   │   └── session_manager.py     # Ephemeral session handling
│   │   └── main.py                 # FastAPI application entry point
│   ├── .env                        # Environment variables
│   └── requirements.txt            # Python dependencies
├── frontend/                       # React SPA
├── tests/                          # Backend test suites
└── venv/                           # Python virtual environment
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Groq API Key

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/zunairakhan123/your-repo-name.git
cd your-repo-name
```

**2. Backend setup**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**3. Environment variables**

Create a `.env` file in the `backend` directory (see [Configuration](#-configuration) below).

**4. Frontend setup**

```bash
cd ../frontend
npm install
```

### Running the Application

**Terminal 1 — FastAPI Backend**

```bash
cd backend
source venv/bin/activate  # Ensure venv is active
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — React Frontend**

```bash
cd frontend
npm run dev
```

Navigate to [http://localhost:5173](http://localhost:5173) to access the main Dashboard and start connecting your data sources.

---

## Configuration

| Variable       | Required | Description                                  |
|----------------|:--------:|-----------------------------------------------|
| `GROQ_API_KEY` |    ✅    | API key used for LLM inference via Groq (`openai/gpt-oss-20b`). |

> Set these in `backend/.env`. Do not commit `.env` files to version control.

---

## Contributing

Contributions are welcome. Please open an issue to discuss significant changes before submitting a pull request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes
4. Push to the branch and open a Pull Request

---

##  License

This project is licensed under the MIT License. See the `LICENSE` file for complete details.
