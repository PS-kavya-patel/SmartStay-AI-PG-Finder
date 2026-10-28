import re
import json
import logging
from typing import List, Dict, Any, Optional, Callable
import ollama

from config import (
    OLLAMA_HOST,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    MAX_AGENT_ITERATIONS,
    AGENT_TEMPERATURE,
    AGENT_PROMPT_FILE
)
from models.schemas import (
    PGSearchCriteria,
    ValidationResult,
    ReflectionResult,
    PGListing
)
from database.data_service import data_service
from services.validation_service import ValidationService
from agents.reflection_agent import ReflectionAgent

# Direct tool imports for seamless tool dispatch
from tools.pg_search import search_pgs as _tool_search_pgs, get_pg_details as _tool_get_pg_details
from tools.budget_filter import filter_by_budget as _tool_filter_budget
from tools.amenity_checker import check_amenities as _tool_check_amenities, normalize_amenity
from tools.distance_calculator import calculate_distance as _tool_calc_dist
from tools.pg_comparator import compare_pgs as _tool_compare_pgs
from tools.pg_ranker import rank_pgs as _tool_rank_pgs
from mcp_servers.location_client import location_client



logger = logging.getLogger(__name__)

class SmartStayAgent:
    """
    Core AI Agent implementing dynamic tool selection, an agentic ReAct loop,
    and post-generation reflection and deterministic validation.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        host: Optional[str] = None,
        max_iterations: Optional[int] = None,
        temperature: Optional[float] = None
    ):
        self.model_name = model_name or OLLAMA_MODEL
        self.host = host or OLLAMA_HOST
        self.max_iterations = max_iterations or MAX_AGENT_ITERATIONS
        self.temperature = temperature or AGENT_TEMPERATURE
        self.ollama_client = ollama.Client(host=self.host, timeout=OLLAMA_TIMEOUT)
        self.reflection_agent = ReflectionAgent(model_name=self.model_name, host=self.host, client=self.ollama_client)
        self.system_prompt = self._load_system_prompt()
        self.tools = self._register_mcp_tools()

    def _load_system_prompt(self) -> str:
        if AGENT_PROMPT_FILE.exists():
            return AGENT_PROMPT_FILE.read_text(encoding="utf-8")
        return "You are SmartStay, an expert AI PG Finder Agent using MCP tools."

    def _register_mcp_tools(self) -> Dict[str, Dict[str, Any]]:
        """Registers all tools available across Custom SmartStay and Location MCP servers."""
        return {
            "geocode_location": {
                "func": lambda **kwargs: json.dumps(location_client.geocode(kwargs.get("location_name", "")), indent=2),
                "description": "Geocode place or landmark to GPS coordinates via Pre-Built OpenStreetMap (OSM) MCP server.",
                "server": "osm-location-server"
            },
            "search_pgs": {
                "func": lambda **kwargs: json.dumps(_tool_search_pgs(
                    city=kwargs.get("city", "Ahmedabad"),
                    area=kwargs.get("area"),
                    gender=kwargs.get("gender"),
                    room_type=kwargs.get("room_type")
                ), indent=2),
                "description": "Search PG database matching city, area, gender, or room type.",
                "server": "smartstay-pg-server"
            },
            "filter_by_budget": {
                "func": lambda **kwargs: json.dumps(_tool_filter_budget(
                    pg_input=kwargs.get("pg_ids"),
                    max_rent=float(kwargs.get("max_rent", 0))
                ), indent=2),
                "description": "Filter PGs by max monthly rent.",
                "server": "smartstay-pg-server"
            },
            "check_amenities": {
                "func": lambda **kwargs: json.dumps(_tool_check_amenities(
                    pg_input=kwargs.get("pg_ids"),
                    required_amenities=kwargs.get("required_amenities", [])
                ), indent=2),
                "description": "Verify presence of mandatory amenities.",
                "server": "smartstay-pg-server"
            },
            "calculate_distance": {
                "func": lambda **kwargs: json.dumps(location_client.compute_distance(
                    origin_lat=kwargs.get("origin_lat"),
                    origin_lon=kwargs.get("origin_lon"),
                    dest_lat=kwargs.get("dest_lat"),
                    dest_lon=kwargs.get("dest_lon"),
                    origin_name=kwargs.get("origin_name", "Origin"),
                    destination_name=kwargs.get("dest_name", "Destination")
                ), indent=2),
                "description": "Calculate distance in km via Pre-Built OpenStreetMap (OSM) MCP server.",
                "server": "osm-location-server"
            },

            "compare_pgs": {
                "func": lambda **kwargs: json.dumps(_tool_compare_pgs(
                    pg_ids=kwargs.get("pg_ids", [])
                ), indent=2),
                "description": "Compare 2-4 candidate PGs side-by-side.",
                "server": "smartstay-pg-server"
            },
            "rank_pgs": {
                "func": lambda **kwargs: json.dumps(_tool_rank_pgs(
                    pg_ids=kwargs.get("pg_ids", []),
                    max_budget=kwargs.get("max_budget"),
                    dest_lat=kwargs.get("dest_lat"),
                    dest_lon=kwargs.get("dest_lon"),
                    max_distance_km=kwargs.get("max_distance_km"),
                    required_amenities=kwargs.get("required_amenities")
                ), indent=2),
                "description": "Multi-factor scoring and ranking of candidate PGs.",
                "server": "smartstay-pg-server"
            },
            "get_pg_details": {
                "func": lambda **kwargs: json.dumps(_tool_get_pg_details(
                    kwargs.get("pg_id", "")
                ), indent=2),
                "description": "Retrieve verified full details for a PG ID.",
                "server": "smartstay-pg-server"
            }
        }

    def discover_tools(self) -> List[Dict[str, Any]]:
        """Returns discovery catalog of registered MCP tools."""
        catalog = []
        for name, meta in self.tools.items():
            catalog.append({
                "name": name,
                "description": meta["description"],
                "server": meta["server"]
            })
        return catalog

    def extract_criteria_from_query(self, user_query: str) -> PGSearchCriteria:
        """Helper to extract structured search criteria from natural language."""
        q = user_query.lower()
        criteria = PGSearchCriteria()

        # City
        if "ahmedabad" in q:
            criteria.city = "Ahmedabad"

        # Gender
        if "girl" in q or "female" in q or "women" in q:
            criteria.gender = "girls"
        elif "boy" in q or "male" in q or "men" in q:
            criteria.gender = "boys"
        elif "co-ed" in q or "unisex" in q:
            criteria.gender = "co-ed"

        # Budget extraction (e.g. "under 8000", "under ₹8,000", "under 8k")
        budget_match = re.search(r"(?:under|below|max|budget\s*of|within)\s*(?:₹|rs\.?|inr)?\s*([0-9]+(?:,[0-9]+)*|\d+k)", q)
        if budget_match:
            b_str = budget_match.group(1).replace(",", "").strip()
            if b_str.endswith("k"):
                criteria.max_rent = float(b_str[:-1]) * 1000.0
            else:
                criteria.max_rent = float(b_str)

        # Distance extraction (e.g. "within 3 km", "under 5km")
        dist_match = re.search(r"within\s*([0-9]+(?:\.[0-9]+)?)\s*km", q)
        if dist_match:
            criteria.max_distance_km = float(dist_match.group(1))

        # Amenities extraction
        req_amenities = []
        if "wi-fi" in q or "wifi" in q or "internet" in q:
            req_amenities.append("Wi-Fi")
        if "food" in q or "meals" in q or "mess" in q:
            req_amenities.append("Food")
        if "ac" in q or "air conditioning" in q:
            req_amenities.append("AC")
        if "laundry" in q or "washing machine" in q:
            req_amenities.append("Laundry")
        if "gym" in q:
            req_amenities.append("Gym")
        criteria.required_amenities = req_amenities

        # Neighborhood / Area extraction
        for area_candidate in ["Navrangpura", "Vastrapur", "Bodakdev", "Satellite", "Paldi"]:
            if area_candidate.lower() in q:
                criteria.area = area_candidate
                break

        # Destination extraction
        dest_mappings = [
            ("national institute of design", "National Institute of Design (NID), Paldi"),
            ("nid", "National Institute of Design (NID), Paldi"),
            ("gujarat chamber of commerce", "Gujarat Chamber of Commerce & Industry (GCCI), Paldi"),
            ("gcci", "Gujarat Chamber of Commerce & Industry (GCCI), Paldi"),
            ("ld college of engineering", "LD College of Engineering, Navrangpura"),
            ("ld college", "LD College of Engineering, Navrangpura"),
            ("gujarat university", "Gujarat University, Navrangpura"),
            ("cept university", "CEPT University, Navrangpura"),
            ("cept", "CEPT University, Navrangpura"),
            ("st. xavier", "St. Xavier's College, Navrangpura"),
            ("xavier", "St. Xavier's College, Navrangpura"),
            ("iim ahmedabad", "IIM Ahmedabad (IIM-A), Vastrapur"),
            ("iima", "IIM Ahmedabad (IIM-A), Vastrapur"),
            ("iim", "IIM Ahmedabad (IIM-A), Vastrapur"),
            ("ahmedabad management association", "Ahmedabad Management Association (AMA), Vastrapur"),
            ("ama", "Ahmedabad Management Association (AMA), Vastrapur"),
            ("pinnacle business park", "Pinnacle Business Park, Bodakdev"),
            ("pinnacle", "Pinnacle Business Park, Bodakdev"),
            ("judges bungalow", "Judges Bungalow Commercial Hub, Bodakdev"),
            ("space applications centre", "Space Applications Centre (ISRO), Satellite"),
            ("isro", "Space Applications Centre (ISRO), Satellite"),
            ("shivranjani", "Shivranjani Crossroads Business Hub, Satellite"),
            ("nirma university", "Nirma University, SG Highway, Ahmedabad"),
            ("nirma", "Nirma University, SG Highway, Ahmedabad")
        ]
        for key, dest_full in dest_mappings:
            if key in q:
                criteria.destination_name = dest_full
                break

        if not criteria.destination_name:
            if "college" in q:
                criteria.destination_name = "LD College of Engineering, Navrangpura"
            elif "university" in q:
                criteria.destination_name = "Gujarat University, Navrangpura"

        return criteria

    def run(self, user_query: str, criteria: Optional[PGSearchCriteria] = None, *args, **kwargs) -> Dict[str, Any]:
        """
        Executes the full ReAct agentic loop:
        1. Dynamic Tool Discovery
        2. Iterative Tool Calling & Observation
        3. Stopping Condition Detection
        4. Deterministic Validation
        5. One-Shot Reflection & Evidence Auditing
        """
        extracted = self.extract_criteria_from_query(user_query)
        if criteria is None:
            criteria = extracted
        else:
            # Merge explicit criteria with extracted fields where explicit is unset
            if not criteria.city:
                criteria.city = extracted.city
            if not criteria.area and extracted.area:
                criteria.area = extracted.area
            if not criteria.gender and extracted.gender:
                criteria.gender = extracted.gender
            if not criteria.max_rent and extracted.max_rent:
                criteria.max_rent = extracted.max_rent
            if not criteria.max_distance_km and extracted.max_distance_km:
                criteria.max_distance_km = extracted.max_distance_km
            if not criteria.required_amenities and extracted.required_amenities:
                criteria.required_amenities = extracted.required_amenities
            if not criteria.destination_name and extracted.destination_name:
                criteria.destination_name = extracted.destination_name

        tool_catalog = self.discover_tools()
        conversation_history: List[Dict[str, str]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"User Request: {user_query}\nPlease choose tools dynamically to find and verify the best PG options."}
        ]

        execution_trace: List[Dict[str, Any]] = []
        collected_observations: List[Dict[str, Any]] = []
        extracted_pg_ids: List[str] = []
        distance_data: Dict[str, float] = {}
        dest_coords: Optional[Dict[str, float]] = None
        final_answer_draft = ""

        # Attempt Ollama dynamic loop
        try:
            for iteration in range(1, self.max_iterations + 1):
                response = self.ollama_client.chat(
                    model=self.model_name,
                    messages=conversation_history,
                    options={"temperature": self.temperature, "num_predict": 350}
                )
                assistant_text = response["message"]["content"]

                # Parse Thought, Action, Action Input
                action_match = re.search(r"Action:\s*([a-zA-Z0-9_]+)", assistant_text)
                final_answer_match = re.search(r"Final Answer:\s*(.*)", assistant_text, re.DOTALL | re.IGNORECASE)

                if final_answer_match and not action_match:
                    final_answer_draft = final_answer_match.group(1).strip()
                    execution_trace.append({
                        "iteration": iteration,
                        "type": "final_answer",
                        "content": assistant_text
                    })
                    break

                if action_match:
                    tool_name = action_match.group(1).strip()
                    input_match = re.search(r"Action Input:\s*(\{.*?\}|\[.*?\]|.+)", assistant_text, re.DOTALL)
                    raw_args = input_match.group(1).strip() if input_match else "{}"

                    try:
                        tool_args = json.loads(raw_args)
                    except Exception:
                        tool_args = {}

                    execution_trace.append({
                        "iteration": iteration,
                        "type": "tool_call",
                        "tool": tool_name,
                        "arguments": tool_args,
                        "thought": assistant_text.split("Action:")[0].replace("Thought:", "").strip()
                    })

                    # Execute tool safely
                    obs_str = self._execute_tool(tool_name, tool_args)
                    try:
                        obs_json = json.loads(obs_str)
                    except Exception:
                        obs_json = {"raw": obs_str}

                    collected_observations.append({
                        "tool": tool_name,
                        "result": obs_json
                    })

                    # Extract context items
                    self._update_internal_state(
                        tool_name, obs_json, extracted_pg_ids, distance_data
                    )

                    conversation_history.append({"role": "assistant", "content": assistant_text})
                    conversation_history.append({"role": "user", "content": f"Observation:\n{obs_str}"})
                else:
                    # Model didn't output Action: or Final Answer: explicitly
                    final_answer_draft = assistant_text
                    execution_trace.append({
                        "iteration": iteration,
                        "type": "text",
                        "content": assistant_text
                    })
                    break

        except Exception as e:
            logger.warning(f"Ollama agent loop encountered exception or fallback: {e}")
            final_answer_draft = ""

        # If LLM didn't produce a satisfactory answer or hit loop limit, synthesize via deterministic engine
        if not final_answer_draft or len(extracted_pg_ids) == 0:
            final_answer_draft, extracted_pg_ids, collected_observations, distance_data = (
                self._deterministic_execution(user_query, criteria)
            )

        # Identify which specific PG IDs are actually referenced in final_answer_draft
        mentioned_ids = []
        all_pgs = data_service.load_all_pgs()
        for p in all_pgs:
            if p.id.lower() in final_answer_draft.lower() or p.name.lower() in final_answer_draft.lower():
                mentioned_ids.append(p.id)

        target_pg_ids = mentioned_ids if mentioned_ids else extracted_pg_ids

        # 4. Deterministic Validation
        validation_result = ValidationService.validate_recommendations(
            recommended_pg_ids=target_pg_ids,
            criteria=criteria,
            proposed_text=final_answer_draft,
            distance_data=distance_data
        )

        # 5. One-Shot Reflection & Correction
        reflection_result = self.reflection_agent.reflect_and_correct(
            user_query=user_query,
            criteria=criteria,
            proposed_draft=final_answer_draft,
            recommended_pg_ids=target_pg_ids,
            tool_observations=collected_observations,
            validation_result=validation_result,
            distance_data=distance_data
        )

        if reflection_result.needs_correction and reflection_result.corrected_response:
            final_response_text = reflection_result.corrected_response
            # Re-identify mentioned IDs in corrected response
            corr_ids = [p.id for p in all_pgs if p.id.lower() in final_response_text.lower() or p.name.lower() in final_response_text.lower()]
            final_target_ids = corr_ids if corr_ids else [pid for pid in target_pg_ids if pid not in validation_result.errors]
            validation_result = ValidationService.validate_recommendations(
                recommended_pg_ids=final_target_ids,
                criteria=criteria,
                proposed_text=final_response_text,
                distance_data=distance_data
            )
            target_pg_ids = final_target_ids
        else:
            final_response_text = final_answer_draft

        # Strict post-processing: guarantee only PGs satisfying 100% of criteria are returned
        strictly_valid_ids = []
        for pid in target_pg_ids:
            p = data_service.get_pg_by_id(pid)
            if not p:
                continue
            # Neighborhood / Area filter (Strict)
            if criteria.area and criteria.area.strip().lower() not in ["all areas", "all", ""]:
                if p.area.strip().lower() != criteria.area.strip().lower():
                    continue
            # City filter
            if criteria.city and criteria.city.strip().lower() not in p.city.strip().lower():
                continue
            # Budget filter
            if criteria.max_rent is not None and criteria.max_rent > 0:
                if p.monthly_rent > criteria.max_rent:
                    continue
            # Gender filter
            if criteria.gender:
                cg = criteria.gender.strip().lower()
                if "girl" in cg or "female" in cg:
                    if p.gender not in ["girls", "co-ed"]:
                        continue
                elif "boy" in cg or "male" in cg:
                    if p.gender not in ["boys", "co-ed"]:
                        continue
                elif "co" in cg and p.gender != "co-ed":
                    continue
            # Mandatory Amenities filter
            if criteria.required_amenities:
                p_norm = [normalize_amenity(a) for a in p.amenities]
                if any(normalize_amenity(req) not in p_norm for req in criteria.required_amenities):
                    continue
            # Distance filter
            if criteria.max_distance_km is not None and criteria.max_distance_km > 0:
                pg_dist = distance_data.get(pid)
                if pg_dist is not None and pg_dist > criteria.max_distance_km:
                    continue

            strictly_valid_ids.append(pid)

        target_pg_ids = strictly_valid_ids

        # If zero PGs passed all filters, output clear helpful message
        if not target_pg_ids:
            final_response_text = (
                "No PG accommodations found matching your selected criteria. None of the listings satisfied all specified constraints. "
                "Consider expanding your neighborhood search or adjusting budget/distance constraints."
            )
            validation_result = ValidationResult(
                is_valid=True,
                errors=[],
                warnings=["No PG listings matched all specified criteria."],
                verified_items=[]
            )

        # Gather final PG objects
        recommended_pg_objects = []
        for pid in target_pg_ids:
            pg_obj = data_service.get_pg_by_id(pid)
            if pg_obj:
                recommended_pg_objects.append(pg_obj)

        return {
            "success": True,
            "query": user_query,
            "criteria": criteria.model_dump(),
            "discovered_tools": tool_catalog,
            "execution_trace": execution_trace,
            "observations": collected_observations,
            "recommended_pg_ids": target_pg_ids,
            "recommended_pgs": [p.model_dump() for p in recommended_pg_objects],
            "distance_data": distance_data,
            "validation_result": validation_result.model_dump(),
            "reflection_result": reflection_result.model_dump(),
            "final_response": final_response_text
        }

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Dispatches tool execution to registered MCP tool function."""
        if tool_name not in self.tools:
            return json.dumps({
                "success": False,
                "error": f"Tool '{tool_name}' not found. Registered tools: {list(self.tools.keys())}"
            })
        try:
            return self.tools[tool_name]["func"](**args)
        except Exception as e:
            return json.dumps({"success": False, "error": f"Tool execution failed: {str(e)}"})

    def _update_internal_state(
        self,
        tool_name: str,
        obs_json: Dict[str, Any],
        extracted_pg_ids: List[str],
        distance_data: Dict[str, float]
    ):
        """Updates internal agent knowledge from observations."""
        if tool_name == "search_pgs":
            res_list = obs_json.get("results", []) if isinstance(obs_json, dict) else (obs_json if isinstance(obs_json, list) else [])
            for item in res_list:
                if isinstance(item, dict) and "id" in item and item["id"] not in extracted_pg_ids:
                    extracted_pg_ids.append(item["id"])
        elif tool_name in ["filter_by_budget", "check_amenities"]:
            matched = obs_json.get("matching_pgs", [])
            current_ids = [m["id"] for m in matched if isinstance(m, dict) and "id" in m]
            if current_ids:
                extracted_pg_ids.clear()
                extracted_pg_ids.extend(current_ids)
        elif tool_name == "rank_pgs":
            ranked = obs_json.get("ranked_pgs", [])
            extracted_pg_ids.clear()
            for r in ranked:
                extracted_pg_ids.append(r["id"])
                if "distance_km" in r and r["distance_km"] is not None:
                    distance_data[r["id"]] = r["distance_km"]

    def _deterministic_execution(
        self,
        user_query: str,
        criteria: PGSearchCriteria
    ):
        """Fallback deterministic pipeline guaranteeing grounded, accurate execution."""
        observations = []
        distance_data = {}

        # 1. Geocode destination if needed
        dest_coords = None
        if criteria.destination_name:
            geo_res = location_client.geocode(criteria.destination_name)
            observations.append({"tool": "geocode_location", "result": geo_res})
            if geo_res.get("success"):
                dest_coords = {"lat": geo_res["latitude"], "lon": geo_res["longitude"]}

        # 2. Search PGs
        search_res = _tool_search_pgs(
            city=criteria.city or "Ahmedabad",
            area=criteria.area,
            gender=criteria.gender,
            room_type=criteria.room_type
        )
        observations.append({"tool": "search_pgs", "result": {"count": len(search_res), "results": search_res}})
        candidate_ids = [p["id"] for p in search_res]

        # 3. Filter by budget if specified
        if criteria.max_rent:
            b_res = _tool_filter_budget(candidate_ids, criteria.max_rent)
            observations.append({"tool": "filter_by_budget", "result": b_res})
            candidate_ids = [p["id"] for p in b_res.get("matching_pgs", [])]

        # 4. Check amenities if specified
        if criteria.required_amenities:
            a_res = _tool_check_amenities(candidate_ids, criteria.required_amenities)
            observations.append({"tool": "check_amenities", "result": a_res})
            candidate_ids = [p["id"] for p in a_res.get("matching_pgs", [])]

        # 5. Rank and calculate distances
        ranked_res = _tool_rank_pgs(
            pg_ids=candidate_ids,
            max_budget=criteria.max_rent,
            dest_lat=dest_coords["lat"] if dest_coords else None,
            dest_lon=dest_coords["lon"] if dest_coords else None,
            max_distance_km=criteria.max_distance_km,
            required_amenities=criteria.required_amenities
        )
        observations.append({"tool": "rank_pgs", "result": ranked_res})

        final_ids = []
        lines = [f"### SmartStay PG Recommendations for: \"{user_query}\"\n"]
        lines.append("Here are the best verified accommodations matching your requirements:\n")

        for r in ranked_res.get("ranked_pgs", []):
            final_ids.append(r["id"])
            if r.get("distance_km") is not None:
                distance_data[r["id"]] = r["distance_km"]
            dist_str = f"{r['distance_km']:.2f} km (straight-line distance)" if r.get("distance_km") is not None else "Coordinates unverified"
            reasons_str = "; ".join(r.get("match_reasons", []))

            lines.append(
                f"#### Rank #{r['rank']}: **{r['name']}**\n"
                f"- **Monthly Rent**: ₹{r['monthly_rent']:,.0f}/month\n"
                f"- **Area / Neighborhood**: {r['area']}, Ahmedabad\n"
                f"- **Room & Accommodation Type**: {r['room_type'].capitalize()} ({r['gender'].capitalize()})\n"
                f"- **Proximity to College/Destination**: {dist_str}\n"
                f"- **Verified Amenities**: {', '.join(r['amenities'])}\n"
                f"- **SmartStay Match Score**: **{r['final_score']}/100**\n"
                f"- **Why It Matches**: {reasons_str}\n"
                f"- **Contact / Inquiry**: {r.get('contact_number') or 'Available on request'}\n"
            )

        if not final_ids:
            lines.append("No PG accommodations found satisfying all criteria. Consider relaxing distance or budget limits.")

        return "\n".join(lines), final_ids, observations, distance_data
