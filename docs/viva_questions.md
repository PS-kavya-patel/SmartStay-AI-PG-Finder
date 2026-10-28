# SmartStay: Level 2 Capstone Viva Preparation Guide

This guide prepares you for viva and evaluation questions regarding the Model Context Protocol (MCP), ReAct loops, local LLMs, deterministic validation, and agent architecture.

---

### Q1: What is the Model Context Protocol (MCP), and why is it used here?
**Answer:**  
The Model Context Protocol (MCP) is an open standard developed by Anthropic that allows AI models to securely discover and connect to external data sources and tools.  
In SmartStay:
- MCP provides a standardized interface for exposing accommodation search and location services.
- The agent discovers tool definitions dynamically at runtime, decoupling the agent's reasoning engine from the underlying database and external APIs.
- We used the official Python SDK with `FastMCP` and `stdio` transport.

---

### Q2: Why split the system into two separate MCP servers?
**Answer:**  
In accordance with Level 2 architectural specifications, we maintain clean separation of concerns:
1. **Pre-Built Location MCP Server (`location-server`)**: Handles spatial intelligence — geocoding addresses and calculating straight-line distances. It has no knowledge of PG rental business logic.
2. **Custom SmartStay MCP Server (`smartstay-pg-server`)**: Handles PG domain operations — candidate searches, budget filtering, facility checks, side-by-side comparisons, and multi-factor ranking.

This separation ensures that either server can be swapped, scaled, or upgraded independently without breaking the other.

---

### Q3: What is the difference between dynamic tool selection and a hardcoded workflow?
**Answer:**  
In a hardcoded workflow, code runs in a fixed sequence regardless of the input.  
In **dynamic tool selection**:
- The agent inspects the user's specific request.
- If the user asks *"What is the rent of Shree Shanti Girls PG?"*, the agent chooses only `get_pg_details` or `search_pgs`. It does NOT execute geocoding or distance calculations.
- If the user asks for a complex query with budget, distance, and college coordinates, the agent dynamically decides to invoke `geocode_location`, `search_pgs`, `filter_by_budget`, `check_amenities`, and `rank_pgs`.

---

### Q4: Explain the ReAct (Reasoning + Acting) Agentic Loop.
**Answer:**  
The ReAct paradigm enables the LLM to interleave reasoning and action:
1. **Thought**: The model generates a reasoning step explaining what information is needed and which tool to use next.
2. **Action**: The model outputs the tool name (e.g. `Action: filter_by_budget`).
3. **Action Input**: The model formats arguments in structured JSON.
4. **Observation**: The system executes the tool via MCP and injects the concrete result back into the prompt context.
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
- Verifies that $\text{Rent} \le \text{Max Budget}$.
- Verifies that mandatory amenities actually exist in the record's facilities list.
- Verifies that the PG accommodates the requested gender.
- Verifies that all recommended PG IDs exist in the database (grounding check).

---

### Q7: Explain the One-Shot Reflection mechanism.
**Answer:**  
The Reflection Agent (`agents/reflection_agent.py`) audits the proposed draft against:
1. The user's original request.
2. The concrete tool observations gathered during the session.
3. The deterministic validation report.

If discrepancies or violations are detected (e.g., an over-budget listing), the reflection agent critiques the error and generates a corrected response. This corrected response is then re-validated through the deterministic validator before being displayed to the user.

---

### Q8: How does SmartStay handle distance and prevent misleading the user?
**Answer:**  
- SmartStay calculates distance using the **Haversine formula** over spherical coordinates.
- It explicitly labels the result as **straight-line distance** (`haversine_straight_line`).
- It **never claims straight-line distance is driving distance**.
- For listings where coordinates are missing (such as `pg_ahm_012` in our demo dataset), the system flags `Distance unverified` rather than guessing or fabricating coordinates.

---

### Q9: How does the explainable scoring formula work?
**Answer:**  
Total score is out of 100 points across four explainable factors:
1. **Budget Proximity (max 30 pts)**: Rewards accommodations priced below the user's maximum budget.
2. **Distance Proximity (max 30 pts)**: Walking distance ($\le 1$ km) gets 30 pts, scaling down to 5 pts for distant locations. Unverified coordinates receive a neutral 15 pts.
3. **Amenity Match (max 25 pts)**: Proportional to the ratio of requested amenities provided.
4. **User Rating (max 15 pts)**: Proportional to the verified user rating ($\frac{\text{Rating}}{5.0} \times 15$).

---

### Q10: How does the application ensure 100% reliability if the local LLM is slow or offline?
**Answer:**  
SmartStay incorporates a **graceful degradation architecture**:
- If Ollama is running and responsive, the LLM dynamically drives tool selection.
- If Ollama times out or is offline, the agent activates its fallback engine (`_deterministic_execution`), which resolves coordinates, filters listings, checks amenities, and scores accommodations deterministically.
- Deterministic validation and reflection auditing guarantee that the final recommendations are always 100% grounded in the real database.
