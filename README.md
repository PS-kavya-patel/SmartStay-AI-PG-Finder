# SmartStay: AI-Powered PG Finder Agent Using MCP

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Model Context Protocol](https://img.shields.io/badge/MCP-Multi--Server-6366f1.svg)](https://modelcontextprotocol.io/)
[![Ollama](https://img.shields.io/badge/LLM-Ollama%20(Mistral%207B%20%7C%20Llama%203.2)-black.svg)](https://ollama.com/)
[![Tests](https://img.shields.io/badge/Pytest-33%20Passed%20(100%25)-emerald.svg)]()
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red.svg)](https://streamlit.io/)

**SmartStay** is an AI agent system for finding student and professional Paying Guest (PG) accommodations in Ahmedabad. Built using the **Model Context Protocol (MCP)**, local LLMs via **Ollama**, a **ReAct agentic loop**, **deterministic constraint verification**, and **one-shot reflection auditing**.

---

## 🌟 Key Architecture & Features

1. **Multi-Server MCP Architecture**:
   - **`smartstay-pg-server`** (FastMCP stdio): Accommodation searches, budget filtering, amenity verification, comparisons, and rankings.
   - **`location-server`** (FastMCP stdio): Geocoding, landmark resolution, and straight-line Haversine distance calculations.
2. **Dynamic Tool Selection & ReAct Loop**:
   - Discovers available MCP tools at runtime.
   - Interleaves reasoning (`Thought`), tool execution (`Action` & `Action Input`), and environment feedback (`Observation`).
3. **Dual-Layer Verification (Zero Hallucination)**:
   - **Deterministic Validation**: Pure algorithmic check verifying rent $\le$ budget, gender restrictions, mandatory facilities, and database grounding.
   - **One-Shot Reflection**: Evidence auditor reviewing the response draft against tool observations and validation results to correct any ungrounded statements.
4. **Transparent Multi-Criteria Scoring (0–100 pts)**:
   - Evaluates budget savings (30 pts), proximity (30 pts), amenities (25 pts), and ratings (15 pts).
5. **Two User Interfaces**:
   - **Interactive CLI**: Rich colored console demonstration with step-by-step observation trace and transcript recording.
   - **Streamlit Web Application**: Modern glassmorphic interface with metrics, interactive search modes, tabbed inspection, and side-by-side comparison tables.

---

## 📁 Repository Structure

```
smartstay-agent/
├── agent.py                    # CLI entrypoint with transcript recording
├── app.py                      # Interactive Streamlit Web Application
├── config.py                   # Central settings (Ollama model, timeouts, paths)
├── requirements.txt            # Locked Python dependencies
├── pytest.ini                  # Pytest configuration
├── .env.example                # Sample environment variables
├── .gitignore                  # Git ignore rules
├── README.md                   # Complete project documentation
│
├── agents/
│   ├── smartstay_agent.py      # Core ReAct agent with dynamic tool dispatch
│   └── reflection_agent.py     # One-shot reflection and evidence auditor
│
├── mcp_servers/
│   ├── pg_server.py            # Custom SmartStay FastMCP server (stdio)
│   ├── location_server.py      # Pre-built Location FastMCP server (stdio)
│   ├── location_client.py      # Location client wrapper & fallback catalog
│   └── server_config.json      # MCP multi-server registry configuration
│
├── tools/
│   ├── pg_search.py            # PG search & detail retrieval
│   ├── budget_filter.py        # Budget filter (rent <= max_budget)
│   ├── amenity_checker.py      # Mandatory amenity verification
│   ├── distance_calculator.py  # Haversine straight-line distance
│   ├── pg_comparator.py        # Side-by-side comparison matrix
│   └── pg_ranker.py            # Explainable scoring & ranker
│
├── models/
│   └── schemas.py              # Pydantic data schemas (Listings, Validation, Reflection)
│
├── database/
│   ├── pg_data.json            # Verified PG accommodation records
│   └── data_service.py         # Data loading, caching, and validation service
│
├── services/
│   ├── validation_service.py   # Deterministic constraint validator
│   └── scoring_service.py      # 0–100 explainable multi-factor scoring formula
│
├── prompts/
│   ├── agent_prompt.txt        # System prompt for ReAct agent
│   └── reflection_prompt.txt   # Prompt for evidence auditing agent
│
├── tests/
│   ├── test_search.py          # Search and data service unit tests
│   ├── test_mcp_tools.py       # MCP custom & location tool unit tests
│   ├── test_scoring.py         # Scoring and ranking unit tests
│   ├── test_validation.py      # Deterministic validation & reflection tests
│   └── test_agent.py           # ReAct loop, discovery, and edge-case tests
│
├── docs/
│   ├── architecture.md         # Component diagrams & data flow
│   ├── testing.md              # Test plan, edge cases, and results
│   └── viva_questions.md       # Comprehensive viva preparation guide
│
└── evidence/
    └── demo_transcript.txt     # Complete recorded demonstration transcript
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10 to 3.12 installed.
- [Ollama](https://ollama.com/) installed and running locally (`ollama run mistral:7b` or `ollama run llama3.2:3b`).

### 2. Setup Virtual Environment & Install Dependencies
Open PowerShell in the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 3. Run the CLI Demonstration
Run the standard capstone evaluation query:

```powershell
python agent.py --record --query "Find a girls' PG in Ahmedabad under ₹8,000 per month, within 3 km of my college, with Wi-Fi and food."
```

*(Output transcript is automatically recorded to `evidence/demo_transcript.txt`)*

To run with a specific model:
```powershell
python agent.py --model llama3.2:3b
```

### 4. Launch the Streamlit Web Application
```powershell
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

### 5. Run the Automated Test Suite
Run all unit and edge-case tests:
```powershell
pytest -v -m "not integration"
```
*(All 33 test cases pass in under 4 seconds!)*

To run live integration tests with Ollama:
```powershell
pytest -v -m "integration"
```

---

## 🎯 Capstone Completion Checklist

- [x] **Python environment & Ollama model** work properly
- [x] **PG dataset** loads and validates correctly via Pydantic
- [x] **Custom MCP tools** implemented and tested (`search`, `budget`, `amenities`, `distance`, `compare`, `rank`)
- [x] **Pre-built location MCP** connects and returns verified coordinates/distances
- [x] **Agent discovers tools dynamically** across both MCP servers
- [x] **Agent completes a working ReAct tool-call loop**
- [x] **One-shot reflection & deterministic validation** verify all constraints
- [x] **HTTP, tool, and missing coordinate errors** are handled safely
- [x] **Automated tests** cover edge cases and pass 100%
- [x] **CLI demonstration** is recorded in `evidence/demo_transcript.txt`
- [x] **Streamlit interface** works smoothly with identical agent logic
- [x] **Architecture, testing, and viva notes** are complete in `docs/`
