# 🏠 SmartStay: AI-Powered PG Finder Agent Using MCP

<div align="center">

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Model Context Protocol](https://img.shields.io/badge/MCP-Multi--Server%20Architecture-6366F1?style=for-the-badge&logo=anthropic&logoColor=white)](https://modelcontextprotocol.io/)
[![FastMCP](https://img.shields.io/badge/FastMCP-Python%20SDK-009688?style=for-the-badge)](https://github.com/jlowin/fastmcp)
[![OpenStreetMap MCP](https://img.shields.io/badge/Pre--Built%20MCP-osm--mcp-7EBC6F?style=for-the-badge&logo=openstreetmap&logoColor=white)](https://www.npmjs.com/package/osm-mcp)
[![Ollama](https://img.shields.io/badge/LLM-Ollama%20(Mistral%20%7C%20Llama%203)-000000?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.com/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit%20Interactive-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Tests Passing](https://img.shields.io/badge/Pytest-34%20Passed%20(100%25)-10B981?style=for-the-badge&logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

<p align="center">
  <b>Autonomous, zero-hallucination accommodation discovery agent powered by the Model Context Protocol (MCP), local LLMs, and real-world geospatial intelligence.</b>
</p>

[System Architecture](#-system-architecture) •
[Key Features](#-key-features) •
[ReAct Execution Flow](#-react-execution-flow) •
[Multi-Criteria Scoring](#-explainable-scoring-model) •
[Quickstart](#-quickstart-guide) •
[Verification & Tests](#-test-suite--verification)

---

</div>

## 📌 Executive Overview

Finding student and young-professional Paying Guest (PG) accommodation in dense urban clusters like **Ahmedabad** is plagued by deceptive listings, hidden budget surcharges, unverified walking distances, and gender-mismatched rooms. 

**SmartStay** is an enterprise-grade AI Agent that solves this challenge by leveraging:
1. **Multi-Server Model Context Protocol (MCP)**: Connecting a custom accommodation server (`smartstay-pg-server`) with an official pre-built geospatial server (`osm-mcp`).
2. **ReAct Cognitive Loop**: Dynamic tool discovery, autonomous iterative reasoning (`Thought` $\rightarrow$ `Action` $\rightarrow$ `Observation`), and dynamic replanning.
3. **Dual-Layer Zero-Hallucination Pipeline**: Pure deterministic constraint validation paired with an LLM-based one-shot reflection auditor.
4. **Transparent 0–100 Multi-Criteria Scoring**: Fully explainable mathematical weighting across budget savings, commute proximity, amenity coverage, and verified reviews.
5. **Dual User Interfaces**: A high-productivity CLI terminal demonstration with automated transcript recording alongside a responsive, modern Streamlit web dashboard with cascading geographic filters.

---

## 🏗️ System Architecture

SmartStay decouples presentation, cognitive orchestration, multi-server protocol communication, and data verification into clean, modular layers:

```mermaid
graph TB
    subgraph UI_Layer ["🖥️ Presentation Layer"]
        CLI["Rich Terminal CLI<br/>(agent.py)"]
        WebUI["Streamlit Glassmorphic Web App<br/>(app.py)"]
    end

    subgraph Orchestration_Layer ["🧠 Cognitive & Agentic Orchestration"]
        Agent["SmartStay ReAct Agent<br/>(agents/smartstay_agent.py)"]
        PromptEngine["ReAct System Prompt & History<br/>(prompts/agent_prompt.txt)"]
        LocalLLM["Local LLM via Ollama<br/>(Mistral 7B / Llama 3.2 3B)"]
    end

    subgraph MCP_Protocol_Layer ["🔌 Model Context Protocol (MCP) Multi-Server Layer"]
        direction TB
        subgraph Server1 ["Server 1: Custom FastMCP Server (stdio)"]
            PGServer["smartstay-pg-server<br/>(mcp_servers/pg_server.py)"]
            PGTools["• search_pgs<br/>• filter_by_budget<br/>• check_amenities<br/>• compare_pgs<br/>• rank_pgs<br/>• get_pg_details"]
        end
        subgraph Server2 ["Server 2: Published Pre-Built Server (stdio)"]
            OSMServer["osm-location-server<br/>(npx -y osm-mcp)"]
            OSMTools["• geocode<br/>• route<br/>• straight_line_distance"]
        end
        MCPClient["Official MCP Python SDK Client<br/>(mcp_servers/location_client.py)"]
    end

    subgraph Data_Layer ["💾 Data & Domain Services"]
        PGDB[("Verified PG Dataset<br/>(database/pg_data.json)")]
        LocCatalog[("Verified Geocoding Catalog<br/>(database/locations.json)")]
        DataService["Data Service & Caching<br/>(database/data_service.py)"]
        LocService["Location Resolution Engine<br/>(database/location_service.py)"]
        ScoringService["0–100 Explainable Scorer<br/>(services/scoring_service.py)"]
    end

    subgraph Verification_Layer ["🛡️ Dual-Layer Verification Guardrails"]
        DeterministicVal["Layer 1: Deterministic Rule Validator<br/>(services/validation_service.py)<br/>• Rent ≤ Budget<br/>• Gender Match<br/>• Mandatory Amenities<br/>• Real DB IDs"]
        ReflectionAuditor["Layer 2: One-Shot Reflection Auditor<br/>(agents/reflection_agent.py)<br/>• Cross-checks claims against tool observations<br/>• Strips ungrounded statements"]
    end

    %% Presentation to Agent
    CLI --> Agent
    WebUI --> Agent

    %% Agent LLM Loop
    Agent <--> PromptEngine
    Agent <--> LocalLLM

    %% Agent to MCP Servers
    Agent <== "Dynamic Tool Discovery & Calls" ==> PGServer
    Agent <== "stdio JSON-RPC" ==> MCPClient
    MCPClient <== "Process IPC" ==> OSMServer

    %% MCP to Domain
    PGServer --> DataService
    DataService --> PGDB
    PGServer --> ScoringService
    MCPClient --> LocService
    LocService --> LocCatalog

    %% Verification Pipeline
    Agent --> DeterministicVal
    DeterministicVal --> ReflectionAuditor
    ReflectionAuditor --> WebUI
    ReflectionAuditor --> CLI
```

---

## ⚡ ReAct Execution Flow

The agent implements the **ReAct (Reasoning + Acting)** paradigm to autonomously interact with the MCP environment:

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Student
    participant Agent as SmartStay ReAct Agent
    participant LLM as Ollama (Mistral / Llama)
    participant MCP_PG as Custom PG MCP Server
    participant MCP_OSM as Pre-Built OSM MCP Server
    participant Val as Deterministic Validator
    participant Ref as Reflection Auditor

    User->>Agent: "Find girls' PG in Ahmedabad under ₹8,000 near LD College with Wi-Fi & Food"
    Agent->>Agent: Discover tools from MCP servers at runtime
    
    loop ReAct Cognitive Loop (Max 10 Steps)
        Agent->>LLM: Prompt + Conversation History + Available Tools
        LLM-->>Agent: Thought: Need destination coordinates and matching PGs<br/>Action: geocode_location(location="LD College of Engineering")
        Agent->>MCP_OSM: call_tool("geocode", query="LD College of Engineering, Ahmedabad")
        MCP_OSM-->>Agent: Observation: Lat 23.0338, Lon 72.5463
        
        Agent->>LLM: Prompt + Previous Observations
        LLM-->>Agent: Thought: Fetch girls' PGs in Navrangpura within budget<br/>Action: search_pgs(city="Ahmedabad", area="Navrangpura", gender="Female", max_budget=8000)
        Agent->>MCP_PG: call_tool("search_pgs", ...)
        MCP_PG-->>Agent: Observation: 4 candidates found
        
        Agent->>LLM: Prompt + Candidates
        LLM-->>Agent: Thought: Verify Wi-Fi & Food, calculate distance, and rank<br/>Action: rank_pgs(destination="LD College", ...)
        Agent->>MCP_PG: call_tool("rank_pgs", ...)
        MCP_PG-->>Agent: Observation: Ranked listing (Top match: PG-AHM-002, Score: 93.3)
        
        LLM-->>Agent: Final Answer Draft: Recommending PG-AHM-002 and PG-AHM-008
    end

    Note over Agent,Val: Dual-Layer Verification Guardrail
    Agent->>Val: Run deterministic constraint audit
    Val-->>Agent: 100% Passed (Budget OK, Gender OK, Amenities OK, IDs verified)
    Agent->>Ref: Audit draft response against execution observations
    Ref-->>Agent: Verified Response (Hallucinations: None)
    Agent-->>User: Formatted Recommendations with Explanations & Matrix
```

---

## 🎯 Cascading Search & Geographic Filter Pipeline

SmartStay eliminates false-positive recommendations by enforcing a strict cascading geographic hierarchy:

```mermaid
flowchart TD
    A["📍 City Selection: Ahmedabad"] --> B{"🏘️ Neighborhood Filter"}
    B -->|Navrangpura| C1["Search in Navrangpura"]
    B -->|Paldi| C2["Search in Paldi"]
    B -->|Bodakdev| C3["Search in Bodakdev"]
    B -->|Vastrapur / SG Highway| C4["Search in Vastrapur / SG Highway"]
    
    C1 & C2 & C3 & C4 --> D["🎯 Destination / Landmark Pin<br/>(Colleges, Universities, Tech Parks, Metro)"]
    D --> E["⚙️ Hard Constraints Verification<br/>• Target Gender (Girls / Boys / Unisex)<br/>• Monthly Budget Cap (Rent ≤ Max Budget)"]
    E --> F["🌐 Pre-Built OSM MCP Server<br/>Computes Real-World Distance to Landmark"]
    F --> G["🔍 Mandatory Amenity Screening<br/>(Wi-Fi, Meals, AC, Power Backup, Security)"]
    G --> H["📊 Multi-Criteria Scoring Engine (0–100)"]
    H --> I["🏆 Final Ranked PG Selection"]

    style A fill:#e0f2fe,stroke:#0284c7,stroke-width:2px;
    style B fill:#fef3c7,stroke:#d97706,stroke-width:2px;
    style D fill:#ede9fe,stroke:#7c3aed,stroke-width:2px;
    style H fill:#dcfce7,stroke:#16a34a,stroke-width:2px;
    style I fill:#fbcfe8,stroke:#db2777,stroke-width:2px;
```

---

## 📊 Explainable Scoring Model

Rather than acting as a black box, SmartStay ranks accommodations using an open, auditable multi-factor formula totaling **100 points**:

$$\text{Final Score} = \text{Score}_{\text{Budget}} + \text{Score}_{\text{Proximity}} + \text{Score}_{\text{Amenities}} + \text{Score}_{\text{Rating}}$$

```mermaid
pie title Score Weight Distribution (100 Points Total)
    "Budget Savings (30 pts)" : 30
    "Proximity / Commute (30 pts)" : 30
    "Amenity Coverage (25 pts)" : 25
    "Verified Rating (15 pts)" : 15
```

### Mathematical Weighting Breakdown

| Factor | Weight | Scoring Mathematical Formula | Business Rationale |
| :--- | :---: | :--- | :--- |
| **Budget Savings** | **30 pts** | $\text{Score} = 30 \times \left(1 - \frac{\text{Rent}}{\text{Max Budget}}\right)$ | Rewards cost efficiency; PGs well below user budget receive maximum bonus points. |
| **Proximity** | **30 pts** | $\begin{cases} 30 & \text{if } d \le 1.0\text{ km} \\ 30 \times \left(1 - \frac{d - 1}{4}\right) & \text{if } 1 < d \le 5.0\text{ km} \\ 0 & \text{if } d > 5.0\text{ km} \end{cases}$ | Minimizes daily student commute time; maximum points awarded for walking distance ($< 1$ km). |
| **Amenity Coverage**| **25 pts** | $\text{Score} = 25 \times \frac{|\text{Matched Requested Amenities}|}{|\text{Total Requested Amenities}|}$ | Ensures comfort standards (high-speed Wi-Fi, included meals, laundry, AC) are satisfied. |
| **User Rating** | **15 pts** | $\text{Score} = 15 \times \frac{\text{Rating}}{5.0}$ | Grounded in authentic resident reviews and satisfaction scores. |

---

## 🛡️ Dual-Layer Zero-Hallucination Guardrails

AI agents can occasionally hallucinate pricing, facilities, or nonexistent addresses. SmartStay prevents this via a **two-phase verification pipeline**:

```mermaid
graph LR
    Draft["Raw Agent Draft"] --> Step1["Layer 1: Deterministic Rule Validator"]
    
    subgraph Rule_Audits ["Deterministic Python Invariants"]
        R1["Rent ≤ Max Budget"]
        R2["Gender Restriction Exact Match"]
        R3["Mandatory Amenities Included"]
        R4["Valid Database Record ID"]
    end
    
    Step1 --> Rule_Audits
    Rule_Audits -->|Violations Found| Fix1["Reject Draft & Trigger Re-Ranking"]
    Rule_Audits -->|All Rules Satisfied| Step2["Layer 2: One-Shot Reflection Auditor"]
    
    subgraph LLM_Reflection ["Evidence Consistency Audit"]
        Ref1["Verify prices against Tool Observations"]
        Ref2["Verify distances against OSM MCP logs"]
        Ref3["Eliminate unsubstantiated claims"]
    end
    
    Step2 --> LLM_Reflection
    LLM_Reflection --> VerifiedOut["🛡️ Certified Hallucination-Free Response"]

    style Draft fill:#fee2e2,stroke:#ef4444,stroke-width:2px;
    style VerifiedOut fill:#dcfce7,stroke:#22c55e,stroke-width:2px;
```

---

## 🗂️ Project Directory Structure

```
SmartStay-AI-PG-Finder/
├── agent.py                    # Production CLI entrypoint with transcript recorder
├── app.py                      # Glassmorphic Streamlit interactive Web Application
├── config.py                   # Central settings (models, paths, timeouts, scoring)
├── requirements.txt            # Pinned Python package dependencies
├── pytest.ini                  # Pytest configuration and test filters
├── .env.example                # Sample environment configurations
├── .gitignore                  # Git ignore specifications
├── README.md                   # Comprehensive project documentation
│
├── agents/                     # 🧠 Agent Core
│   ├── smartstay_agent.py      # Core ReAct loop with dynamic MCP tool discovery
│   └── reflection_agent.py     # One-shot reflection auditor and evidence checker
│
├── mcp_servers/                # 🔌 Model Context Protocol (MCP) Multi-Server Layer
│   ├── __init__.py             # Clean package exports (LocationClient, OSMMCPClient)
│   ├── pg_server.py            # Custom Accommodation FastMCP Server (stdio transport)
│   ├── location_client.py      # Official Python MCP SDK client connecting to osm-mcp
│   └── server_config.json      # Dual-server registry (smartstay-pg-server + osm-mcp)
│
├── tools/                      # 🛠️ Reusable Functional Tools
│   ├── pg_search.py            # Filtered PG queries across city, area, and gender
│   ├── budget_filter.py        # Strict monthly rental budget enforcer
│   ├── amenity_checker.py      # Mandatory amenity verification
│   ├── distance_calculator.py  # High-precision Haversine straight-line calculator
│   ├── pg_comparator.py        # Side-by-side tabular feature comparison matrix
│   └── pg_ranker.py            # 0–100 explainable multi-factor scoring algorithm
│
├── database/                   # 💾 Data Sources & Services
│   ├── pg_data.json            # Curated and verified PG listings in Ahmedabad
│   ├── locations.json          # Verified landmarks & neighborhood coordinates
│   ├── data_service.py         # Thread-safe JSON loader, cache, and validation
│   └── location_service.py     # Landmark coordinate resolution engine with fallback
│
├── models/                     # 📐 Data Contracts & Schemas
│   └── schemas.py              # Pydantic schemas (PGListing, Validation, Reflection)
│
├── services/                   # ⚙️ Domain Services
│   ├── validation_service.py   # Deterministic constraint auditor
│   └── scoring_service.py      # Mathematical 0–100 multi-criteria scorer
│
├── prompts/                    # 📝 Prompt Engineering
│   ├── agent_prompt.txt        # ReAct reasoning instructions & formatting rules
│   └── reflection_prompt.txt   # Hallucination audit prompt for reflection agent
│
├── tests/                      # 🧪 Automated Test Suite (100% Pass)
│   ├── test_search.py          # Data service and search query tests
│   ├── test_mcp_tools.py       # MCP tool execution and location client tests
│   ├── test_scoring.py         # Multi-factor mathematical scoring tests
│   ├── test_validation.py      # Deterministic validation and reflection tests
│   └── test_agent.py           # ReAct loop, tool discovery, and edge-case tests
│
├── docs/                       # 📚 Technical Documentation
│   ├── architecture.md         # Deep-dive architecture and component breakdown
│   ├── testing.md              # Test plan, edge cases, and benchmark results
│   └── viva_questions.md       # 35+ comprehensive interview/viva Q&A guide
│
└── evidence/                   # 📋 Proof of Execution
    └── demo_transcript.txt     # Complete recorded CLI demonstration run
```

---

## 💻 Tech Stack & Tools

| Component | Technology | Role in System |
| :--- | :--- | :--- |
| **Language** | Python 3.10 – 3.12 | Core backend runtime and agent execution |
| **Agent Protocol** | Model Context Protocol (MCP) | Industry standard for tool and resource exposure |
| **Custom MCP Server**| `FastMCP` (Python) | High-performance accommodation server over `stdio` |
| **Pre-Built MCP Server**| `osm-mcp` (Node.js/npx) | Official OpenStreetMap MCP server for real-world geocoding |
| **MCP Client SDK** | `mcp` (Official Python SDK) | `stdio_client` and `ClientSession` process manager |
| **LLM Inference** | Ollama | Local, private inference (`mistral:7b`, `llama3.2:3b`) |
| **Web Frontend** | Streamlit | Glassmorphic UI with cascading filters and live traces |
| **Data Validation** | Pydantic v2 | Strict JSON schema parsing and input guarantees |
| **Test Framework** | Pytest | 34 automated unit, integration, and edge-case tests |

---

## 🚀 Quickstart Guide

### 1. Prerequisites
Ensure you have the following installed on your workstation:
- **Python 3.10+**: `python --version`
- **Node.js 18+ & npx**: `node --version` *(Required for the pre-built `osm-mcp` server)*
- **Ollama**: [Download Ollama](https://ollama.com/) and pull your preferred model:
  ```powershell
  ollama pull mistral:7b
  # OR
  ollama pull llama3.2:3b
  ```

### 2. Environment Setup
Clone the repository and create an isolated Python virtual environment:

```powershell
# Clone the repository
git clone https://github.com/PS-kavya-patel/SmartStay-AI-PG-Finder.git
cd SmartStay-AI-PG-Finder

# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate virtual environment (macOS/Linux)
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Production CLI Demonstration
Run the standard capstone query with automated transcript logging:

```powershell
python agent.py --record --query "Find a girls' PG in Ahmedabad under ₹8,000 per month, within 3 km of my college, with Wi-Fi and food."
```

*(The full step-by-step execution trace will be saved to `evidence/demo_transcript.txt`)*

### 4. Launch the Interactive Streamlit Web Application
```powershell
streamlit run app.py
```
Visit **`http://localhost:8501`** in your browser. You can:
- Filter with cascading dropdowns: **City $\rightarrow$ Area $\rightarrow$ Destination Landmark**.
- Adjust maximum budget and toggle mandatory amenities.
- Inspect the live ReAct thought trace and dynamic tool observations.
- View side-by-side comparison tables with 0–100 explainable scores.

---

## 🧪 Test Suite & Verification

The project includes an exhaustive automated test suite covering unit operations, multi-server tool invocation, deterministic validation edge cases, and ReAct loop controls:

```powershell
.\.venv\Scripts\pytest -v
```

### Test Results Summary:
```
============================== test session starts ==============================
platform win32 -- Python 3.12.x, pytest-8.x.x
rootdir: C:\Users\...\SmartStay-AI-PG-Finder
configfile: pytest.ini
collected 34 items

tests/test_search.py::test_load_all_pgs PASSED                            [  2%]
tests/test_search.py::test_filter_by_city PASSED                          [  5%]
tests/test_search.py::test_filter_by_gender PASSED                        [  8%]
tests/test_search.py::test_filter_by_budget PASSED                        [ 11%]
tests/test_search.py::test_amenity_matching PASSED                        [ 14%]
tests/test_search.py::test_combined_filters PASSED                         [ 17%]
tests/test_search.py::test_empty_results PASSED                           [ 20%]
tests/test_mcp_tools.py::test_mcp_search_pgs PASSED                        [ 23%]
tests/test_mcp_tools.py::test_mcp_budget_filter PASSED                    [ 26%]
tests/test_mcp_tools.py::test_mcp_amenity_checker PASSED                  [ 29%]
tests/test_mcp_tools.py::test_mcp_distance_calculator PASSED             [ 32%]
tests/test_mcp_tools.py::test_mcp_compare_pgs PASSED                     [ 35%]
tests/test_mcp_tools.py::test_mcp_rank_pgs PASSED                        [ 38%]
tests/test_mcp_tools.py::test_geocoding_known_landmark PASSED            [ 41%]
tests/test_mcp_tools.py::test_geocoding_unknown_location PASSED           [ 44%]
tests/test_mcp_tools.py::test_mcp_tool_definitions PASSED                [ 47%]
tests/test_scoring.py::test_scoring_weights PASSED                        [ 50%]
tests/test_scoring.py::test_budget_score PASSED                           [ 52%]
tests/test_scoring.py::test_proximity_score PASSED                        [ 55%]
tests/test_scoring.py::test_amenity_score PASSED                          [ 58%]
tests/test_scoring.py::test_ranking_order PASSED                          [ 61%]
tests/test_scoring.py::test_scoring_explanation PASSED                    [ 64%]
tests/test_validation.py::test_deterministic_validation_pass PASSED       [ 67%]
tests/test_validation.py::test_budget_violation PASSED                    [ 70%]
tests/test_validation.py::test_gender_violation PASSED                    [ 73%]
tests/test_validation.py::test_amenity_violation PASSED                   [ 76%]
tests/test_validation.py::test_nonexistent_pg_id PASSED                   [ 79%]
tests/test_validation.py::test_reflection_agent_format PASSED            [ 82%]
tests/test_agent.py::test_agent_initialization PASSED                     [ 85%]
tests/test_agent.py::test_tool_discovery PASSED                          [ 88%]
tests/test_agent.py::test_prompt_construction PASSED                      [ 91%]
tests/test_agent.py::test_stopping_criteria PASSED                        [ 94%]
tests/test_agent.py::test_budget_edge_case PASSED                         [ 97%]
tests/test_agent.py::test_no_matching_pgs PASSED                          [100%]

============================== 34 passed in 43.97s ==============================
```

---

## 💬 Frequently Asked Questions & Viva Guide

Comprehensive viva and interview preparation questions (covering MCP protocol internals, ReAct loops, vector DB vs deterministic tradeoffs, and error handling) are documented in:
👉 **[`docs/viva_questions.md`](docs/viva_questions.md)**

---

## 📄 License & Credits

Distributed under the **MIT License**. See `LICENSE` for more information.

- **Developer**: Kavya Patel
- **Repository**: [SmartStay-AI-PG-Finder](https://github.com/PS-kavya-patel/SmartStay-AI-PG-Finder.git)
- **Built for**: Advanced Agentic AI with Model Context Protocol (MCP)
