# SmartStay Testing & Quality Assurance Report

This document details the test suite, coverage, edge cases, regression tests, and verification results for the SmartStay Level 2 capstone project.

---

## 1. Test Suite Summary

- **Framework**: `pytest` 9.2.0 with `pytest-asyncio`
- **Total Test Cases**: 39 automated tests (38 unit/regression/MCP tests + 1 live Ollama integration test)
- **Pass Rate**: **100% of unit/regression/MCP tests passing**
- **Test Command**:
  ```powershell
  .\.venv\Scripts\pytest.exe -v -m "not integration"
  ```

---

## 2. Test Files & Coverage Breakdown

### `tests/test_search.py` (Search & Database Logic)
| Test Case | Description | Result |
| :--- | :--- | :--- |
| `test_data_service_loads_records` | Verifies all PG listings load correctly from `database/pg_data.json` into Pydantic models. | **PASSED** |
| `test_search_girls_pgs` | Checks gender filtering for girls and co-ed listings. | **PASSED** |
| `test_search_boys_pgs` | Checks gender filtering for boys and co-ed listings. | **PASSED** |
| `test_search_by_area` | Verifies neighborhood area search (Navrangpura). | **PASSED** |
| `test_search_no_matching_pgs` | Tests handling of non-existent cities without crashing. | **PASSED** |
| `test_get_pg_details_valid` | Fetches record for valid PG ID (`pg_ahm_001`). | **PASSED** |
| `test_get_pg_details_invalid` | Returns `None` gracefully for missing IDs. | **PASSED** |

### `tests/test_mcp_tools.py` (MCP Tools & Protocol Execution)
| Test Case | Description | Result |
| :--- | :--- | :--- |
| `test_filter_by_budget_exact_boundary` | Tests boundary case where rent is exactly equal to budget limit (₹8,000). | **PASSED** |
| `test_filter_by_budget_invalid` | Verifies negative or zero budget yields an informative error dictionary. | **PASSED** |
| `test_check_amenities_present` | Tests listings that provide all requested facilities. | **PASSED** |
| `test_check_amenities_missing_mandatory` | Verifies listings missing mandatory amenities are excluded and tracked. | **PASSED** |
| `test_calculate_distance_valid` | Calculates straight-line Haversine distance with valid coordinates. | **PASSED** |
| `test_calculate_distance_missing_coordinates` | Safely handles missing/None coordinates without throwing unhandled exceptions. | **PASSED** |
| `test_calculate_distance_invalid_range` | Flags coordinates exceeding [-90, 90] or [-180, 180]. | **PASSED** |
| `test_compare_pgs_valid` | Generates side-by-side metric matrix and highlights for candidate PGs. | **PASSED** |
| `test_compare_pgs_empty` | Returns error when empty PG ID list is supplied. | **PASSED** |
| `test_rank_pgs_strict_distance_excludes_missing_gps` | **Fix 5 Blocker**: Strict distance excludes PGs with missing coordinates. | **PASSED** |
| `test_pg_mcp_client_tool_discovery` | **Fix 1 Blocker**: Discovers 7 tools over stdio MCP `ClientSession` from `pg_server.py`. | **PASSED** |
| `test_pg_mcp_client_call_tool` | **Fix 1 Blocker**: Executes `search_pgs` over stdio MCP `ClientSession`. | **PASSED** |
| `test_geocoding_known_landmark` | Tests coordinate resolution for landmark (LD College of Engineering). | **PASSED** |
| `test_geocoding_empty` | Safely handles empty location string queries. | **PASSED** |

### `tests/test_scoring.py` (0–100 Explainable Scoring Formula)
| Test Case | Description | Result |
| :--- | :--- | :--- |
| `test_scoring_within_budget_and_close` | Validates multi-factor score calculation within [0, 100]. | **PASSED** |
| `test_scoring_unverified_distance` | Assigns neutral midpoint score when coordinates are unrecorded. | **PASSED** |
| `test_rank_pgs_excludes_over_distance` | Excludes listings that exceed the user's maximum distance limit. | **PASSED** |

### `tests/test_validation.py` (Deterministic Guardrails & Factual Auditing)
| Test Case | Description | Result |
| :--- | :--- | :--- |
| `test_validation_passes_valid_recommendations` | Verifies compliant recommendations pass with zero errors. | **PASSED** |
| `test_validation_fails_budget_violation` | Catches and flags rent exceeding the user's budget. | **PASSED** |
| `test_validation_fails_gender_violation` | Rejects accommodation violating user gender restrictions. | **PASSED** |
| `test_validation_fails_missing_amenity` | Rejects listing missing a mandatory requested amenity. | **PASSED** |
| `test_validation_fails_ungrounded_pg_id` | Catches fabricated or non-existent PG IDs (hallucination guardrail). | **PASSED** |
| `test_validation_rejects_false_factual_claims` | **Fix 2 Blocker**: Rejects claimed false rent (₹1) and invented swimming pool. | **PASSED** |
| `test_validation_rejects_rejected_pgs_in_text` | **Fix 3 Blocker**: Fails validation if proposed text mentions excluded/rejected PGs. | **PASSED** |
| `test_validation_strict_distance_rejects_missing_gps` | **Fix 5 Blocker**: Fails validation if PG with missing GPS is proposed under strict distance limit. | **PASSED** |
| `test_reflection_correction_on_failure` | Demonstrates automatic removal of invalid listings via one-shot reflection. | **PASSED** |

### `tests/test_agent.py` (Agentic ReAct Loop & Intent Understanding)
| Test Case | Description | Result |
| :--- | :--- | :--- |
| `test_tool_discovery` | Discovers tools across connected MCP servers dynamically. | **PASSED** |
| `test_criteria_extraction` | Extracts budget, amenities, gender, and distance from natural language. | **PASSED** |
| `test_criteria_extraction_blocker_fixes` | **Fix 4 Blocker**: Verifies 'under 8k' -> 8000, 'within 3 km' -> distance, 'accommodation with Wi-Fi' -> no AC, swimming pool detected, 'my college' unassumed. | **PASSED** |
| `test_agent_dynamic_react_loop_mocked` | Tests full multi-step ReAct loop (Thought -> Action -> Observation -> Final Answer). | **PASSED** |
| `test_rejected_pg_removed_from_final_prose` | **Fix 3 Blocker**: Rebuilds final text so rejected PGs never appear in prose. | **PASSED** |
| `test_agent_handles_invalid_tool_call` | Handles unregistered tool names gracefully without terminating execution. | **PASSED** |
| `test_agent_no_matching_pgs` | Returns graceful message when no accommodations match constraints. | **PASSED** |
| `test_agent_stops_at_max_iterations` | Enforces loop limit to prevent runaway execution. | **PASSED** |
| `test_agent_live_ollama_end_to_end` | Live integration test with local Ollama LLM (`@pytest.mark.integration`). | **PASSED** |

---

## 3. Reviewer Blocker Remediation Summary

1. **Fix 1 (Custom FastMCP Protocol)**: Integrated `mcp_servers/pg_client.py` using official Python MCP SDK (`stdio_client` + `ClientSession`). Agent dispatches PG tool operations over the protocol.
2. **Fix 2 (Factual Claim Verification)**: Added deterministic fact verification in `services/validation_service.py` to compare text-asserted rents, facilities, and PG IDs against real records in `database/pg_data.json`.
3. **Fix 3 (Purging Excluded PGs from Prose)**: In `agents/smartstay_agent.py`, the final response is regenerated strictly using approved candidate IDs, guaranteeing rejected listings never survive into the final answer.
4. **Fix 4 (Robust Query Extraction)**: Overhauled `extract_criteria_from_query` with strict regex word boundaries (`\bac\b`), budget unit multipliers (`8k` -> 8000), distance-rent disambiguation, and removal of unverified assumptions (`my college` remains unassigned).
5. **Fix 5 (Strict Distance Validation)**: Modified `tools/pg_ranker.py` and `services/validation_service.py` so that when `max_distance_km` is requested, accommodations with missing/unverified GPS coordinates are strictly excluded from confirmed recommendations.
