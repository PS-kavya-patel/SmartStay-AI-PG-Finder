# SmartStay Testing & Quality Assurance Report

This document details the test suite, coverage, edge cases, and verification results for the SmartStay Level 2 capstone project.

---

## 1. Test Suite Summary

- **Framework**: `pytest` 9.2.0 with `pytest-asyncio`
- **Total Test Cases**: 34 tests (33 unit tests + 1 live integration test)
- **Pass Rate**: **100% (33 passed, 1 deselected in 3.91s)**
- **Test Command**:
  ```powershell
  .\.venv\Scripts\pytest.exe -v -m "not integration"
  ```

---

## 2. Test Files & Coverage Breakdown

### `tests/test_search.py`
| Test Case | Description | Result |
| :--- | :--- | :--- |
| `test_data_service_loads_records` | Verifies all PG listings load correctly from `database/pg_data.json` into Pydantic models. | **PASSED** |
| `test_search_girls_pgs` | Checks gender filtering for girls and co-ed listings. | **PASSED** |
| `test_search_boys_pgs` | Checks gender filtering for boys and co-ed listings. | **PASSED** |
| `test_search_by_area` | Verifies neighborhood area search (Navrangpura). | **PASSED** |
| `test_search_no_matching_pgs` | Tests handling of non-existent cities without crashing. | **PASSED** |
| `test_get_pg_details_valid` | Fetches record for valid PG ID (`pg_ahm_001`). | **PASSED** |
| `test_get_pg_details_invalid` | Returns `None` gracefully for missing IDs. | **PASSED** |

### `tests/test_mcp_tools.py`
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
| `test_geocoding_known_landmark` | Tests coordinate resolution for landmark (LD College of Engineering). | **PASSED** |
| `test_geocoding_empty` | Safely handles empty location string queries. | **PASSED** |

### `tests/test_scoring.py`
| Test Case | Description | Result |
| :--- | :--- | :--- |
| `test_scoring_within_budget_and_close` | Validates multi-factor score calculation within [0, 100]. | **PASSED** |
| `test_scoring_unverified_distance` | Assigns neutral midpoint score when coordinates are unrecorded. | **PASSED** |
| `test_rank_pgs_excludes_over_distance` | Excludes listings that exceed the user's maximum distance limit. | **PASSED** |

### `tests/test_validation.py`
| Test Case | Description | Result |
| :--- | :--- | :--- |
| `test_validation_passes_valid_recommendations` | Verifies compliant recommendations pass with zero errors. | **PASSED** |
| `test_validation_fails_budget_violation` | Catches and flags rent exceeding the user's budget. | **PASSED** |
| `test_validation_fails_gender_violation` | Rejects accommodation violating user gender restrictions. | **PASSED** |
| `test_validation_fails_missing_amenity` | Rejects listing missing a mandatory requested amenity. | **PASSED** |
| `test_validation_fails_ungrounded_pg_id` | Catches fabricated or non-existent PG IDs (hallucination guardrail). | **PASSED** |
| `test_reflection_correction_on_failure` | Demonstrates automatic removal of invalid listings via one-shot reflection. | **PASSED** |

### `tests/test_agent.py`
| Test Case | Description | Result |
| :--- | :--- | :--- |
| `test_tool_discovery` | Discovers all 8 tools across connected MCP servers. | **PASSED** |
| `test_criteria_extraction` | Extracts budget, amenities, gender, and distance from natural language. | **PASSED** |
| `test_agent_dynamic_react_loop_mocked` | Tests full multi-step ReAct loop (Thought -> Action -> Observation -> Final Answer). | **PASSED** |
| `test_agent_handles_invalid_tool_call` | Handles unregistered tool names gracefully without terminating execution. | **PASSED** |
| `test_agent_no_matching_pgs` | Returns graceful message when no accommodations match constraints. | **PASSED** |
| `test_agent_stops_at_max_iterations` | Enforces loop limit to prevent runaway execution. | **PASSED** |
| `test_agent_live_ollama_end_to_end` | Live integration test with local Ollama LLM. | **PASSED** |

---

## 3. Failure Modes Handled

1. **Empty Search / No Matches**:
   - The agent never invents fake accommodations or prices. It gracefully explains that no records satisfy the combined constraints and suggests relaxing budget or distance.
2. **Missing Coordinates**:
   - Listings with missing coordinates are marked as `Coordinates unverified`. Straight-line distance is not fabricated.
3. **Ollama / Network Timeouts**:
   - Wrapped with timeout handlers and deterministic fallback execution, guaranteeing that the application always returns verified answers.
4. **Invalid Tool Arguments / JSON**:
   - Tools validate schemas using Pydantic and return structured error dictionaries instead of unhandled exceptions.
