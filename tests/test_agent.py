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
    query = "Find a girls' PG in Ahmedabad under ₹8,000 per month, within 3 km of my college, with Wi-Fi and food."
    criteria = agent.extract_criteria_from_query(query)
    assert criteria.city == "Ahmedabad"
    assert criteria.gender == "girls"
    assert criteria.max_rent == 8000.0
    assert criteria.max_distance_km == 3.0
    assert "Wi-Fi" in criteria.required_amenities
    assert "Food" in criteria.required_amenities

def test_agent_dynamic_react_loop_mocked():
    agent = SmartStayAgent()
    query = "Find a girls' PG in Ahmedabad under ₹8,000"

    # Mock Ollama ReAct steps:
    # Step 1: Action: search_pgs
    # Step 2: Final Answer mentioning Shree Shanti Girls PG (pg_ahm_001, rent 7500 <= 8000)
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

def test_agent_handles_invalid_tool_call():
    agent = SmartStayAgent()
    err_res = agent._execute_tool("non_existent_tool_123", {})
    assert "not found" in err_res

def test_agent_no_matching_pgs():
    agent = SmartStayAgent()
    query = "Find a boys PG under ₹1,000 in Ahmedabad with swimming pool"
    # When no matches exist, agent reports safely
    with patch("ollama.Client.chat", side_effect=Exception("Unit test fallback")):
        result = agent.run(query)

    assert result["success"] is True
    assert len(result["recommended_pg_ids"]) == 0
    assert "No PG accommodations found" in result["final_response"] or "none" in result["final_response"].lower()

def test_agent_stops_at_max_iterations():
    agent = SmartStayAgent(max_iterations=2)
    # Loop that continuously calls a tool without Final Answer
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
