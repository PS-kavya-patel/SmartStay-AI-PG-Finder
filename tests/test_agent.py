import pytest
from unittest.mock import patch, MagicMock
from agents.smartstay_agent import SmartStayAgent

def test_tool_discovery():
    agent = SmartStayAgent()
    tools = agent.discover_tools()
    assert len(tools) >= 7
    tool_names = [t["name"] for t in tools]
    assert "search_pgs" in tool_names
    assert "filter_by_budget" in tool_names
    assert "check_amenities" in tool_names
    assert "geocode_location" in tool_names
    assert "rank_pgs" in tool_names

def test_criteria_extraction():
    agent = SmartStayAgent()
    query = "Find a girls' PG in Ahmedabad under ₹8,000 per month, within 3 km of CEPT University, with Wi-Fi and food."
    criteria = agent.extract_criteria_from_query(query)
    assert criteria.city == "Ahmedabad"
    assert criteria.gender == "girls"
    assert criteria.max_rent == 8000.0
    assert criteria.max_distance_km == 3.0
    assert "Wi-Fi" in criteria.required_amenities
    assert "Food" in criteria.required_amenities
    assert criteria.destination_name == "CEPT University, Navrangpura"

def test_criteria_extraction_blocker_fixes():
    """Fix 4 Blocker: Regression tests for budget units, distance vs rent, and amenity boundaries."""
    agent = SmartStayAgent()

    # 1. Under 8k -> 8000.0 (not 8)
    c1 = agent.extract_criteria_from_query("Find PG under 8k")
    assert c1.max_rent == 8000.0

    # 2. Within 3 km -> distance=3.0, NOT rent=3
    c2 = agent.extract_criteria_from_query("Find PG within 3 km")
    assert c2.max_distance_km == 3.0
    assert c2.max_rent is None

    # 3. Accommodation with Wi-Fi -> Wi-Fi only, AC must NOT be extracted from 'accommodation'
    c3 = agent.extract_criteria_from_query("Find accommodation with Wi-Fi")
    assert "Wi-Fi" in c3.required_amenities
    assert "AC" not in c3.required_amenities

    # 4. Swimming pool -> detected as requested amenity
    c4 = agent.extract_criteria_from_query("Find PG with swimming pool")
    assert "Swimming pool" in c4.required_amenities

    # 5. 'My college' -> must NOT automatically assume LD College without clarification
    c5 = agent.extract_criteria_from_query("Find a girls PG near my college")
    assert c5.destination_name is None

def test_agent_dynamic_react_loop_mocked():
    agent = SmartStayAgent()
    query = "Find a girls' PG in Ahmedabad under ₹8,000"

    mock_responses = [
        {"message": {"content": 'Thought: Search for girls PGs in Ahmedabad.\nAction: search_pgs\nAction Input: {"city": "Ahmedabad", "gender": "girls"}'}},
        {"message": {"content": 'Thought: Found suitable PGs.\nFinal Answer: I recommend Shree Shanti Girls PG (pg_ahm_001) in Navrangpura with monthly rent of ₹7,500.'}}
    ]

    with patch("ollama.Client.chat", side_effect=mock_responses):
        result = agent.run(query)

    assert result["success"] is True
    assert len(result["execution_trace"]) >= 1
    assert "final_response" in result
    assert "pg_ahm_001" in result["recommended_pg_ids"]
    assert result["validation_result"]["is_valid"] is True

def test_rejected_pg_removed_from_final_prose():
    """Fix 3 Blocker: An over-budget PG (pg_ahm_005) must not appear in the final response text."""
    agent = SmartStayAgent()
    query = "Find a girls' PG under ₹8,000"

    # Model proposes both pg_ahm_001 (rent 7500 <= 8000) and pg_ahm_005 (rent 12000 > 8000)
    mock_responses = [
        {"message": {"content": 'Thought: Search for girls PGs.\nAction: search_pgs\nAction Input: {"city": "Ahmedabad", "gender": "girls"}'}},
        {"message": {"content": 'Thought: Recommending options.\nFinal Answer: I recommend Shree Shanti Girls PG (pg_ahm_001) and Sunrise Luxury PG (pg_ahm_005).'}}
    ]

    with patch("ollama.Client.chat", side_effect=mock_responses):
        result = agent.run(query)

    # pg_ahm_005 must be rejected
    assert "pg_ahm_005" not in result["recommended_pg_ids"]
    assert "pg_ahm_001" in result["recommended_pg_ids"]
    # pg_ahm_005 MUST NOT be mentioned in the final prose!
    assert "pg_ahm_005" not in result["final_response"].lower()
    assert "sunrise luxury" not in result["final_response"].lower()
    assert "pg_ahm_001" in result["final_response"].lower()

def test_agent_handles_invalid_tool_call():
    agent = SmartStayAgent()
    err_res = agent._execute_tool("non_existent_tool_123", {})
    assert "not found" in err_res

def test_agent_no_matching_pgs():
    agent = SmartStayAgent()
    query = "Find a boys PG under ₹1,000 in Ahmedabad with swimming pool"
    with patch("ollama.Client.chat", side_effect=Exception("Unit test fallback")):
        result = agent.run(query)

    assert result["success"] is True
    assert len(result["recommended_pg_ids"]) == 0
    assert "no pg accommodations" in result["final_response"].lower()

def test_agent_stops_at_max_iterations():
    agent = SmartStayAgent(max_iterations=2)
    mock_call = {"message": {"content": 'Thought: Need more info.\nAction: search_pgs\nAction Input: {"city": "Ahmedabad"}'}}

    with patch("ollama.Client.chat", return_value=mock_call):
        result = agent.run("Find PG in Ahmedabad")

    assert result["success"] is True
    assert len(result["execution_trace"]) <= 2

@pytest.mark.integration
def test_agent_live_ollama_end_to_end():
    """Live integration test invoking local Ollama model."""
    agent = SmartStayAgent()
    query = "Find a girls' PG in Ahmedabad under ₹8,000 per month with Wi-Fi and food."
    result = agent.run(query)
    assert result["success"] is True
    assert len(result["recommended_pg_ids"]) > 0
    assert result["validation_result"]["is_valid"] is True
