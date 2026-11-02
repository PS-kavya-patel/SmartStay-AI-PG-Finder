# SmartStay: Level 2 Capstone Viva Preparation Guide

This guide prepares you for viva and evaluation questions regarding the Model Context Protocol (MCP), ReAct loops, local LLMs, deterministic validation, scoring algorithms, and agent architecture.

---

## Part 1: Core Architectural Concepts

### Q1: What is the Model Context Protocol (MCP), and why is it used here?
**Answer:**  
The Model Context Protocol (MCP) is an open standard developed by Anthropic that allows AI models to securely discover and connect to external data sources and tools.  
In SmartStay:
- MCP provides a standardized interface for exposing accommodation search and location services.
- The agent discovers tool definitions dynamically at runtime via `session.list_tools()`, decoupling the agent's reasoning engine from the underlying database and external APIs.
- We use the official Python SDK (`mcp`) with `FastMCP` and `stdio` transport.

---

### Q2: Why split the system into two separate MCP servers?
**Answer:**  
In accordance with Level 2 architectural specifications, we maintain clean separation of concerns:
1. **Pre-Built Location MCP Server (`osm-location-server` / `osm-mcp`)**: Handles spatial intelligence — geocoding addresses and calculating route and straight-line distances via OpenStreetMap. It has no knowledge of PG rental business logic.
2. **Custom SmartStay MCP Server (`smartstay-pg-server`)**: Handles PG domain operations — candidate searches, budget filtering, facility checks, side-by-side comparisons, and multi-factor ranking.

This separation ensures that either server can be swapped, scaled, or upgraded independently without breaking the other.

---

### Q3: What is the difference between dynamic tool selection and a hardcoded workflow?
**Answer:**  
In a hardcoded workflow, code runs in a fixed sequence regardless of the input.  
In **dynamic tool selection**:
- The agent inspects the user's specific request.
- If the user asks *"What is the rent of Shree Shanti Girls PG?"*, the agent chooses only `get_pg_details` or `search_pgs`. It does NOT execute geocoding or distance calculations.
- If the user asks for a complex query with budget, distance, and landmark coordinates, the agent dynamically decides to invoke `geocode_location`, `search_pgs`, `filter_by_budget`, `check_amenities`, and `rank_pgs`.

---

### Q4: Explain the ReAct (Reasoning + Acting) Agentic Loop.
**Answer:**  
The ReAct paradigm enables the LLM to interleave reasoning and action:
1. **Thought**: The model generates a reasoning step explaining what information is needed and which tool to use next.
2. **Action**: The model outputs the tool name (e.g. `Action: filter_by_budget`).
3. **Action Input**: The model formats arguments in structured JSON.
4. **Observation**: The system executes the tool via MCP (`session.call_tool()`) and injects the concrete result back into the prompt context.
5. **Final Answer**: When all required constraints are satisfied, the model transitions to outputting its final recommendation.

---

### Q5: What stopping conditions are implemented to prevent infinite loops?
**Answer:**  
We implement three explicit stopping guardrails:
1. **Model Signal**: When the model outputs `Final Answer:`, the loop immediately breaks.
2. **Maximum Iterations (`MAX_AGENT_ITERATIONS = 6`)**: If the model fails to produce a final answer within 6 iterations, the loop halts safely.
3. **Timeout Fallback**: If an external LLM or API call times out, the system seamlessly transitions to the deterministic execution engine to guarantee a verified response.

---

### Q6: How does deterministic validation differ from asking an LLM to review its own writing?
**Answer:**  
Merely prompting an LLM to "check your work" is prone to the same biases and hallucinations that created the original mistake.  
In contrast, our **Deterministic Validation Service (`services/validation_service.py`)**:
- Executes pure, non-LLM Python verification against ground-truth database records.
- Extracts factual claims (claimed rent, claimed amenities, claimed IDs) from the AI's generated prose and strictly checks them against database ground truth.
- Verifies that $\text{Rent} \le \text{Max Budget}$.
- Verifies that mandatory amenities actually exist in the record's facilities list.
- Verifies that the PG accommodates the requested gender.
- Verifies that all recommended PG IDs exist in the database (grounding check) and that no rejected/excluded PGs are recommended in prose.
- Enforces strict distance compliance: if a maximum distance is specified, accommodations with missing coordinates are rejected.

---

### Q7: Explain the One-Shot Reflection mechanism.
**Answer:**  
The Reflection Agent (`agents/reflection_agent.py`) audits the proposed draft against:
1. The user's original request.
2. The concrete tool observations gathered during the session.
3. The deterministic validation report.

**Hard Priority Rule:** If the deterministic validation fails (`initial_val.is_valid is False`), the reflection agent *cannot* override it. The agent either uses the LLM to repair the text to match ground-truth, or uses a deterministic fallback generator (`_fallback_correction`) to present only verified listings with true attributes.

---

### Q8: How does SmartStay handle distance and prevent misleading the user?
**Answer:**  
- SmartStay calculates distance using the **Haversine formula** over spherical coordinates.
- It explicitly labels the result as **straight-line distance** (`haversine_straight_line`).
- It **never claims straight-line distance is driving distance**.
- For listings where coordinates are missing (such as `pg_ahm_012` in our demo dataset):
  - Under a **strict distance constraint** (`max_distance_km`), the PG is **excluded** from ranking because proximity cannot be verified.
  - When no distance constraint is specified, it is retained but marked `Distance unverified` with a distance score of 0.0.

---

### Q9: How does the explainable scoring formula work?
**Answer:**  
Total score is out of 100 points across four explainable factors (defined in `services/scoring_service.py`):
1. **Budget Proximity (max 30 pts)**:
   - If $\text{Rent} \le \text{Max Budget}$: Baseline $20.0 + \min\left(\frac{\text{Savings}}{\text{Budget}} \times 10, 10.0\right)$.
   - If $\text{Rent} > \text{Max Budget}$: $0.0$ pts (disqualified).
2. **Distance Proximity (max 30 pts)**:
   - $\le 1.0\text{ km}$: $30.0$ pts (immediate walking distance).
   - $1.0 - 2.0\text{ km}$: $25.0$ pts.
   - $2.0 - 3.0\text{ km}$: $20.0$ pts.
   - $3.0 - 5.0\text{ km}$: $12.0$ pts.
   - $> 5.0\text{ km}$: Linear decay down to $0.0$ pts.
   - Missing coordinates: Excluded if strict distance constraint is set; $0.0$ pts if no distance constraint.
3. **Amenity Match (max 25 pts)**:
   - $\text{Score} = 25.0 \times \frac{\text{Matched Amenities}}{\text{Requested Amenities}}$.
4. **User Rating (max 15 pts)**:
   - $\text{Score} = 15.0 \times \frac{\text{Rating}}{5.0}$.

---

### Q10: How does the application ensure 100% reliability if the local LLM is slow or offline?
**Answer:**  
SmartStay incorporates a **graceful degradation architecture**:
- If Ollama is running and responsive, the LLM dynamically drives tool selection through the ReAct loop.
- If Ollama times out or is offline, the agent activates its fallback engine (`_deterministic_execution`), which executes the tool pipeline via MCP, resolves coordinates, filters listings, checks amenities, and scores accommodations deterministically.
- Deterministic validation and reflection auditing guarantee that the final recommendations are always 100% grounded in the real database.

---

## Part 2: Reviewer Defence Questions & Answers

### Q11: Show me the agent invoking your custom MCP server over stdio right now. Where in the logs do we see the initialize handshake and the call_tool message for search_pgs?
**Answer:**  
- **Client Implementation:** `mcp_servers/pg_client.py` uses `StdioServerParameters` pointing to `python -u mcp_servers/pg_server.py`. It opens a `stdio_client` and creates an MCP `ClientSession`.
- **Handshake:** The client invokes `await session.initialize()`, sending the standard JSON-RPC 2.0 initialization message.
- **Dynamic Discovery:** `await session.list_tools()` discovers all 7 registered FastMCP tools dynamically: `search_pgs`, `filter_by_budget`, `check_amenities`, `calculate_distance`, `compare_pgs`, `rank_pgs`, and `get_pg_details`.
- **Tool Invocation:** The agent invokes `pg_client.call_tool("search_pgs", {"city": "Ahmedabad", "gender": "girls"})`. The MCP server responds via stdio with the list of matching PG records.
- **Verification Evidence:** `evidence/demo_transcript.txt` lines 18–45 capture the MCP tool discovery and Phase 2 tool calls. Unit tests `test_pg_mcp_client_tool_discovery` and `test_pg_mcp_client_call_tool` in `tests/test_mcp_tools.py` run this stdio handshake on every test suite execution.

---

### Q12: Why did Shree Shanti Girls PG pass validation at ₹1 rent with a swimming pool during our probe, and how does your validation code now prevent that?
**Answer:**  
- **Root Cause of Old Bug:** The previous validation service checked only whether the recommended PG IDs existed in the database and whether their stored database rent was $\le$ budget. It never parsed the *AI draft text* to verify if the text claimed false attributes.
- **The Fix (`services/validation_service.py`):**
  1. `extract_claimed_rent(text)` parses the text for rent mentions (e.g., `₹1`, `₹1/month`, `Rs 1`) associated with each PG. It compares claimed rent against `record["rent_per_month"]`. If `claimed_rent < record_rent * 0.9` or `claimed_rent > record_rent * 1.1`, validation fails with `"Factual error: Shree Shanti Girls PG claims rent of ₹1, but actual rent is ₹7,500"`.
  2. `extract_claimed_amenities(text)` scans for facility mentions like `swimming pool`. If the text claims an amenity not in `record["amenities"]`, validation fails with `"Factual error: Shree Shanti Girls PG claims amenity 'swimming pool' which is not in verified database"`.
  3. Regression test `test_validation_rejects_false_factual_claims` explicitly reproduces this scenario and verifies rejection.

---

### Q13: Walk me through what happens when a user asks for "within 3 km of LD College under 8k". Which component extracts each number, and what does it send to the tools?
**Answer:**  
1. **Extraction Component:** `SmartStayAgent.extract_criteria_from_query()` in `agents/smartstay_agent.py`.
2. **Budget Extraction:**
   - Matches regex `r'(?:under|below|max|budget(?:\s+of)?|upto|up\s+to|within)\s*(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d+)?)\s*(k|thousand)?'`
   - Sees `under 8k` $\rightarrow$ parses `8`, applies multiplier $k = 1000 \rightarrow \mathbf{₹8,000}$.
3. **Distance Extraction:**
   - Matches regex `r'(?:within|under|less\s+than|max|upto|up\s+to)?\s*(\d+(?:\.\d+)?)\s*(?:km|kms|kilometers|kilometres)'`
   - Sees `within 3 km` $\rightarrow$ extracts distance $\mathbf{3.0\text{ km}}$. Notice it does NOT confuse "within" for budget because "km" is matched.
4. **Landmark Extraction:**
   - Matches known landmarks or prepositional patterns `r'(?:near|around|close\s+to|at|in|of)\s+([A-Za-z0-9\s]+)'` $\rightarrow$ identifies `"LD College"`.
5. **Tool Dispatch:**
   - Invokes `location_client.geocode("LD College, Ahmedabad")` $\rightarrow (23.0338, 72.5466)$.
   - Invokes `pg_client.call_tool("filter_by_budget", {"pg_ids": [...], "max_rent": 8000.0})`.
   - Invokes `pg_client.call_tool("calculate_distance", {"pg_id": id, "dest_lat": 23.0338, "dest_lon": 72.5466})`.

---

### Q14: Why is a PG with missing coordinates excluded when the user gives a strict distance limit, but included when they do not?
**Answer:**  
- **Strict Distance Limit Given (`max_distance_km is not None`):**  
  If a student specifies "within 2 km of LD College", proximity is a mandatory hard filter. Because `pg_ahm_012` has no GPS coordinates in the database, its distance is unprovable. Presenting it as a match could place a student kilometers away from their college. Therefore, `tools/pg_ranker.py` appends it to `excluded_by_distance` with reason `"Distance unverified (coordinates missing)"`.
- **No Distance Limit Given (`max_distance_km is None`):**  
  If the student only specifies budget and amenities (e.g. "Girls PG under 9000 with WiFi"), proximity is not a disqualifier. The listing is included in the ranking, receives $0.0$ distance score, and is explicitly labeled `is_distance_verified: False` with `"Distance: Unverified"`.

---

### Q15: If the reflection auditor decides a response is fine, but the deterministic validator reports an error, which one wins? Where in the code is that priority enforced?
**Answer:**  
**The deterministic validator ALWAYS wins.**  
In `agents/reflection_agent.py`, line 96:
```python
effective_passed = model_passed and initial_val.is_valid
```
Even if the LLM reflection auditor says `is_valid: true`, if `initial_val.is_valid` is `False`, `effective_passed` remains `False`. The reflection agent is forced to trigger correction. Furthermore, if the model fails to produce a valid corrected draft, `_fallback_correction` deterministically constructs clean, truthful output using only verified PG records from the database.

---

### Q16: How did you establish the ground truth for your synthetic Ahmedabad PG dataset, and why does pg_ahm_012 lack coordinates?
**Answer:**  
- **Dataset Provenance:** Stored in `data/pg_records.json`. It contains 12 realistic accommodations across key student hubs in Ahmedabad (Navrangpura, Gulbai Tekra, Vastrapur, Memnagar, Naranpura).
- **Coordinate Grounding:** Real GPS coordinates for 11 listings were verified against OpenStreetMap coordinates for their respective neighborhoods.
- **Purpose of `pg_ahm_012`:** `pg_ahm_012` ("Radhe Krishna Co-Living") was deliberately created with `latitude: null` and `longitude: null` to test edge-case handling. In real-world data feeds, address geocoding frequently fails. A robust AI agent must handle missing coordinates safely: excluding them under strict distance requests, and flagging them as unverified rather than hallucinating coordinates.

---

### Q17: Why did your agent previously assume LD College when the user did not name a landmark, and how does it now behave when no landmark is mentioned?
**Answer:**  
- **Previous Flaw:** The query extractor had a fallback default `landmark = "LD College of Engineering"` whenever no landmark was found in the text. This caused unprompted distance calculations for general searches like "Girls PG under ₹8,000".
- **Current Implementation:** In `agents/smartstay_agent.py`, the fallback was completely removed:
  ```python
  # Only assign landmark if explicitly matched in query; do NOT default to LD College
  landmark = landmark_match.group(1).strip() if landmark_match else None
  ```
- If the user does not specify a landmark, `landmark` is `None`, no unnecessary geocoding is performed, and listings are evaluated on budget, amenities, and ratings.

---

### Q18: Recreate the exact score for Shiv Shakti Boys PG against a ₹9,000 budget, 3 km distance request, and AC requirement using the documented formula.
**Answer:**  
From `data/pg_records.json`, Shiv Shakti Boys PG (`pg_ahm_003`):
- Rent: ₹8,000 / month
- Amenities: WiFi, AC, Food, Laundry, CCTV
- Coordinates: (23.0365, 72.5480) $\rightarrow$ Haversine distance to LD College (23.0338, 72.5466) is **0.33 km**.
- Verified Rating: **4.6 / 5.0**

**Score Breakdown (Total out of 100):**
1. **Budget Proximity (max 30 pts):**  
   $\text{Rent} = 8000 \le \text{Budget} = 9000$.  
   $\text{Savings} = 9000 - 8000 = 1000$.  
   $\text{Score} = 20.0 + \min\left(\frac{1000}{9000} \times 10, 10.0\right) = 20.0 + 1.11 = \mathbf{21.11\text{ pts}}$.
2. **Distance Proximity (max 30 pts):**  
   $\text{Distance} = 0.33\text{ km} \le 1.0\text{ km} \rightarrow \mathbf{30.00\text{ pts}}$ (immediate walking distance).
3. **Amenity Match (max 25 pts):**  
   Requested: `["ac"]`. Matched: `ac` present.  
   $\text{Score} = 25.0 \times \frac{1}{1} = \mathbf{25.00\text{ pts}}$.
4. **User Rating (max 15 pts):**  
   $\text{Score} = 15.0 \times \frac{4.6}{5.0} = \mathbf{13.80\text{ pts}}$.

$$\mathbf{\text{Total Score}} = 21.11 + 30.00 + 25.00 + 13.80 = \mathbf{89.91\text{ / }100}$$
*(Ranks #1 among matching accommodations)*
