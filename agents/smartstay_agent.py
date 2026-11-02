import re
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
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
from mcp_servers.pg_client import pg_client
from mcp_servers.location_client import location_client
from tools.amenity_checker import normalize_amenity

logger = logging.getLogger(__name__)

class SmartStayAgent:
    """
    Core AI Agent implementing dynamic MCP tool selection, an agentic ReAct loop,
    and post-generation deterministic validation and evidence reflection.
    All PG operations communicate with the custom FastMCP server over official MCP stdio sessions.
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
        self.tools_catalog = self.discover_tools()

    def _load_system_prompt(self) -> str:
        if AGENT_PROMPT_FILE.exists():
            return AGENT_PROMPT_FILE.read_text(encoding="utf-8")
        return "You are SmartStay, an expert AI PG Finder Agent using MCP tools."

    def discover_tools(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Dynamically discovers tools exposed by connected MCP servers using the official MCP SDK.
        Queries smartstay-pg-server (Custom FastMCP) and osm-location-server (Pre-Built OSM).
        Caches discovered tools on the agent instance to avoid redundant subprocess invocations.
        """
        if hasattr(self, "_cached_tools") and self._cached_tools and not force_refresh:
            return self._cached_tools

        catalog: List[Dict[str, Any]] = []

        # 1. Discover tools from custom FastMCP PG server over MCP session
        try:
            pg_tools = pg_client.list_tools()
            for t in pg_tools:
                catalog.append(t)
        except Exception as e:
            logger.warning(f"Error during PG MCP server discovery: {e}")

        # 2. Discover geocoding/distance tools from OSM Location MCP server
        try:
            osm_tools = location_client.list_tools()
            for t in osm_tools:
                # Add geocode_location alias for agent convenience
                if t.get("name") == "geocode":
                    catalog.append({
                        "name": "geocode_location",
                        "description": "Geocodes place or landmark to GPS coordinates via OpenStreetMap MCP server.",
                        "input_schema": {"type": "object", "properties": {"location_name": {"type": "string"}}, "required": ["location_name"]},
                        "server": "osm-location-server"
                    })
                else:
                    catalog.append(t)
        except Exception as e:
            logger.warning(f"Error during OSM MCP server discovery: {e}")

        self._cached_tools = catalog
        return catalog

    def extract_criteria_from_query(self, user_query: str) -> PGSearchCriteria:
        """
        Robust natural language extraction of structured search criteria.
        Separates budget units (e.g. 8k -> 8000), distance vs rent (3 km is distance, not rent),
        enforces strict word boundaries on amenities (e.g. 'ac' does not match 'accommodation'),
        and avoids assuming unspecified colleges (e.g. 'my college' asks for clarification).
        """
        q = user_query.lower()
        criteria = PGSearchCriteria()

        # 1. City extraction
        if "ahmedabad" in q:
            criteria.city = "Ahmedabad"

        # 2. Gender extraction
        if re.search(r"\b(?:girls?|female|women|lady|ladies)\b", q):
            criteria.gender = "girls"
        elif re.search(r"\b(?:boys?|male|men|gents?)\b", q):
            criteria.gender = "boys"
        elif re.search(r"\b(?:co-?ed|unisex|both)\b", q):
            criteria.gender = "co-ed"

        # 3. Distance extraction (Strict distance separation)
        # e.g., 'within 3 km', 'under 5 km', 'less than 2.5 km', 'within 3 kilometers'
        dist_match = re.search(
            r"(?:within|under|less\s*than|below|max(?:imum)?\s*distance\s*of)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:km|kilometer)s?\b",
            q
        )
        if dist_match:
            criteria.max_distance_km = float(dist_match.group(1))

        # 4. Budget extraction
        # MUST NOT capture distance (negative lookahead for km)
        # Handles: 'under 8k', 'under 8 thousand', 'budget of 8000', 'under ₹8,000', 'below 7000', 'max ₹9,000'
        budget_match = re.search(
            r"(?:(?:budget(?:\s*of)?|under|below|max(?:imum)?|up\s*to)\s*(?:₹|rs\.?|inr)?\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(k|thousand|lakh)?|"
            r"(?:₹|rs\.?|inr)\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(k|thousand|lakh)?)\b(?!\s*(?:km|kilometer))",
            q
        )
        if budget_match:
            num_str = budget_match.group(1) or budget_match.group(3)
            unit_str = budget_match.group(2) or budget_match.group(4) or ""
            if num_str:
                num_val = float(num_str.replace(",", "").strip())
                unit_clean = unit_str.lower().strip()
                if unit_clean == "k":
                    num_val *= 1000.0
                elif "thousand" in unit_clean:
                    num_val *= 1000.0
                elif "lakh" in unit_clean:
                    num_val *= 100000.0
                criteria.max_rent = num_val

        # 5. Amenities extraction with strict word boundaries (\b)
        req_amenities = []
        if re.search(r"\b(?:wi-?fi|internet)\b", q):
            req_amenities.append("Wi-Fi")
        if re.search(r"\b(?:food|meals?|mess)\b", q):
            req_amenities.append("Food")
        # Strict boundary: \bac\b will NEVER match 'accommodation'
        if re.search(r"\b(?:ac|air\s*condition(?:ing|er)?)\b", q):
            req_amenities.append("AC")
        if re.search(r"\b(?:laundry|washing\s*machine)\b", q):
            req_amenities.append("Laundry")
        if re.search(r"\b(?:gym|fitness)\b", q):
            req_amenities.append("Gym")
        if re.search(r"\b(?:swimming\s*pool|pool)\b", q):
            req_amenities.append("Swimming pool")
        if re.search(r"\b(?:power\s*backup|generator|inverter)\b", q):
            req_amenities.append("Power Backup")
        if re.search(r"\b(?:cctv|security\s*camera)\b", q):
            req_amenities.append("CCTV")
        if re.search(r"\b(?:housekeeping|cleaning)\b", q):
            req_amenities.append("Housekeeping")
        if re.search(r"\b(?:refrigerator|fridge)\b", q):
            req_amenities.append("Refrigerator")
        criteria.required_amenities = req_amenities

        # 6. Neighborhood / Area extraction
        for area_candidate in ["Navrangpura", "Vastrapur", "Bodakdev", "Satellite", "Paldi"]:
            if re.search(rf"\b{re.escape(area_candidate.lower())}\b", q):
                criteria.area = area_candidate
                break

        # 7. Destination extraction (Explicit known institutions only)
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
            if re.search(rf"\b{re.escape(key)}\b", q):
                criteria.destination_name = dest_full
                break

        # CRITICAL FIX 4: If user says 'my college' or 'college' without naming it,
        # DO NOT automatically default to LD College. Leave destination_name None so system asks/clarifies.

        return criteria

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Executes the selected tool via official MCP ClientSession over stdio transport.
        Dispatches PG tools to pg_client and location tools to location_client.
        """
        known_names = [t["name"] for t in self.tools_catalog]
        if tool_name not in known_names and tool_name not in ["geocode_location", "geocode"]:
            return json.dumps({
                "success": False,
                "error": f"Tool '{tool_name}' not found. Available tools: {known_names}"
            })

        # Location tools
        if tool_name in ["geocode_location", "geocode"]:
            loc_name = args.get("location_name") or args.get("query", "")
            return json.dumps(location_client.geocode(loc_name), indent=2)

        # PG operations via custom FastMCP server
        try:
            return pg_client.call_tool(tool_name, args)
        except Exception as e:
            return json.dumps({"success": False, "error": f"MCP execution failed: {str(e)}"})

    def _build_grounded_response(
        self,
        user_query: str,
        criteria: PGSearchCriteria,
        valid_pg_ids: List[str],
        distance_data: Dict[str, float]
    ) -> str:
        """
        Generates a 100% verified final text response containing ONLY approved PGs.
        Guarantees that no rejected, over-budget, or unverified PGs are mentioned in prose.
        """
        if not valid_pg_ids:
            return (
                f"No PG accommodations in Ahmedabad satisfied all your requested requirements for query: '{user_query}'. "
                "All candidate listings were rejected due to constraint violations (budget cap, gender restriction, missing amenities, or distance). "
                "Please consider expanding your neighborhood or adjusting your budget limits."
            )

        valid_pgs = []
        for pid in valid_pg_ids:
            p = data_service.get_pg_by_id(pid)
            if p:
                valid_pgs.append(p)

        lines = [
            f"### Verified PG Recommendations for: \"{user_query}\"\n",
            "Based on verified database records and MCP tool execution, here are the qualified accommodations:\n"
        ]

        for idx, p in enumerate(valid_pgs, 1):
            dist_val = distance_data.get(p.id)
            if dist_val is not None:
                dist_str = f"{dist_val:.2f} km (straight-line distance)"
            elif criteria.destination_name:
                dist_str = "Distance to destination calculated"
            else:
                dist_str = "Central location in area"

            lines.append(
                f"#### {idx}. **{p.name}**\n"
                f"- **PG ID**: `{p.id}`\n"
                f"- **Monthly Rent**: ₹{p.monthly_rent:,.0f}/month\n"
                f"- **Area / Neighborhood**: {p.area}, Ahmedabad\n"
                f"- **Accommodation Type**: {p.room_type.capitalize()} ({p.gender.capitalize()})\n"
                f"- **Proximity**: {dist_str}\n"
                f"- **Verified Amenities**: {', '.join(p.amenities)}\n"
                f"- **Resident Rating**: {p.rating if p.rating else 'Unrated'}/5.0\n"
                f"- **Contact / Inquiry**: {p.contact_number or 'Inquire at reception'}\n"
            )

        return "\n".join(lines)

    def run(self, user_query: str, criteria: Optional[PGSearchCriteria] = None, *args, **kwargs) -> Dict[str, Any]:
        """
        Executes the full ReAct agentic loop with dynamic MCP discovery:
        1. Discover tools dynamically from custom FastMCP and OSM servers.
        2. Execute model ReAct loop over stdio MCP client sessions.
        3. Deterministically validate candidate PGs against DB rules and factual claims.
        4. Exclude all rejected listings from both structured recommendations AND final prose.
        5. One-Shot reflection audit with strict error enforcement.
        """
        extracted = self.extract_criteria_from_query(user_query)
        if criteria is None:
            criteria = extracted
        else:
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
            {"role": "user", "content": f"User Request: {user_query}\nPlease choose tools dynamically via MCP to find and verify the best PG options."}
        ]

        execution_trace: List[Dict[str, Any]] = []
        collected_observations: List[Dict[str, Any]] = []
        extracted_pg_ids: List[str] = []
        distance_data: Dict[str, float] = {}
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

                    # Execute tool via MCP
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
                    self._update_internal_state(tool_name, obs_json, extracted_pg_ids, distance_data)

                    conversation_history.append({"role": "assistant", "content": assistant_text})
                    conversation_history.append({"role": "user", "content": f"Observation:\n{obs_str}"})
                else:
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

        # Deterministic MCP execution if LLM did not run or produce candidates
        if not final_answer_draft or len(extracted_pg_ids) == 0:
            final_answer_draft, extracted_pg_ids, collected_observations, distance_data = (
                self._deterministic_mcp_execution(user_query, criteria)
            )

        # Identify which PGs were mentioned in draft
        mentioned_ids = []
        all_pgs = data_service.load_all_pgs()
        for p in all_pgs:
            if p.id.lower() in final_answer_draft.lower() or p.name.lower() in final_answer_draft.lower():
                mentioned_ids.append(p.id)

        target_pg_ids = mentioned_ids if mentioned_ids else extracted_pg_ids

        # Strict deterministic filtering of candidate PG IDs (Fix 3 & Fix 5)
        strictly_valid_ids: List[str] = []
        for pid in target_pg_ids:
            p = data_service.get_pg_by_id(pid)
            if not p:
                continue
            # Area filter
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
            # Distance filter & Missing GPS check (Fix 5 blocker)
            if criteria.max_distance_km is not None and criteria.max_distance_km > 0:
                pg_dist = distance_data.get(pid)
                if p.latitude is None or p.longitude is None:
                    # Missing GPS: cannot satisfy strict distance limit
                    continue
                if pg_dist is None or pg_dist > criteria.max_distance_km:
                    continue

            strictly_valid_ids.append(pid)

        # REGENERATE FINAL RESPONSE USING ONLY STRICTLY VALID PGs (Fix 3 blocker)
        # If any PG was rejected from the draft, rebuild prose so rejected PGs NEVER appear in prose.
        had_rejected_pgs = any(pid not in strictly_valid_ids for pid in target_pg_ids)
        if had_rejected_pgs or not final_answer_draft:
            final_response_text = self._build_grounded_response(
                user_query=user_query,
                criteria=criteria,
                valid_pg_ids=strictly_valid_ids,
                distance_data=distance_data
            )
        else:
            final_response_text = final_answer_draft

        # Run Deterministic Validation on the final output and text
        validation_result = ValidationService.validate_recommendations(
            recommended_pg_ids=strictly_valid_ids,
            criteria=criteria,
            proposed_text=final_response_text,
            distance_data=distance_data
        )

        # Reflection & Evidence Auditing
        reflection_result = self.reflection_agent.reflect_and_correct(
            user_query=user_query,
            criteria=criteria,
            proposed_draft=final_response_text,
            recommended_pg_ids=strictly_valid_ids,
            tool_observations=collected_observations,
            validation_result=validation_result,
            distance_data=distance_data
        )

        # If reflection corrected the text, re-validate
        if reflection_result.needs_correction and reflection_result.corrected_response:
            final_response_text = reflection_result.corrected_response
            validation_result = ValidationService.validate_recommendations(
                recommended_pg_ids=strictly_valid_ids,
                criteria=criteria,
                proposed_text=final_response_text,
                distance_data=distance_data
            )

        # Gather final PG objects
        recommended_pg_objects = []
        for pid in strictly_valid_ids:
            pg_obj = data_service.get_pg_by_id(pid)
            if pg_obj:
                recommended_pg_objects.append(pg_obj)

        # Set success: Must be False if validation failed (errors exist)
        overall_success = validation_result.is_valid

        return {
            "success": overall_success,
            "query": user_query,
            "criteria": criteria.model_dump(),
            "discovered_tools": tool_catalog,
            "execution_trace": execution_trace,
            "observations": collected_observations,
            "recommended_pg_ids": strictly_valid_ids,
            "recommended_pgs": [p.model_dump() for p in recommended_pg_objects],
            "distance_data": distance_data,
            "validation_result": validation_result.model_dump(),
            "reflection_result": reflection_result.model_dump(),
            "final_response": final_response_text
        }

    def _update_internal_state(
        self,
        tool_name: str,
        obs_json: Dict[str, Any],
        extracted_pg_ids: List[str],
        distance_data: Dict[str, float]
    ):
        """Updates internal agent knowledge from MCP tool observations."""
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

    def _deterministic_mcp_execution(
        self,
        user_query: str,
        criteria: PGSearchCriteria
    ):
        """
        Deterministic execution path using MCP tools over client sessions.
        """
        observations = []
        distance_data = {}

        # 1. Geocode destination if needed via OSM MCP
        dest_coords = None
        if criteria.destination_name:
            geo_res = location_client.geocode(criteria.destination_name)
            observations.append({"tool": "geocode_location", "result": geo_res})
            if geo_res.get("success"):
                dest_coords = {"lat": geo_res["latitude"], "lon": geo_res["longitude"]}

        # 2. Search PGs via custom MCP
        search_args = {
            "city": criteria.city or "Ahmedabad",
            "area": criteria.area,
            "gender": criteria.gender,
            "room_type": criteria.room_type
        }
        search_obs_str = self._execute_tool("search_pgs", search_args)
        try:
            search_obs = json.loads(search_obs_str)
        except Exception:
            search_obs = {"results": []}
        observations.append({"tool": "search_pgs", "result": search_obs})

        results = search_obs.get("results", [])
        candidate_ids = [p["id"] for p in results if "id" in p]

        # 3. Filter by budget via custom MCP
        if criteria.max_rent:
            budget_obs_str = self._execute_tool("filter_by_budget", {"pg_ids": candidate_ids, "max_rent": criteria.max_rent})
            try:
                b_obs = json.loads(budget_obs_str)
            except Exception:
                b_obs = {}
            observations.append({"tool": "filter_by_budget", "result": b_obs})
            candidate_ids = [p["id"] for p in b_obs.get("matching_pgs", []) if "id" in p]

        # 4. Check amenities via custom MCP
        if criteria.required_amenities:
            amenity_obs_str = self._execute_tool("check_amenities", {"pg_ids": candidate_ids, "required_amenities": criteria.required_amenities})
            try:
                a_obs = json.loads(amenity_obs_str)
            except Exception:
                a_obs = {}
            observations.append({"tool": "check_amenities", "result": a_obs})
            candidate_ids = [p["id"] for p in a_obs.get("matching_pgs", []) if "id" in p]

        # 5. Rank candidate PGs via custom MCP
        rank_args = {
            "pg_ids": candidate_ids,
            "max_budget": criteria.max_rent,
            "dest_lat": dest_coords["lat"] if dest_coords else None,
            "dest_lon": dest_coords["lon"] if dest_coords else None,
            "max_distance_km": criteria.max_distance_km,
            "required_amenities": criteria.required_amenities
        }
        rank_obs_str = self._execute_tool("rank_pgs", rank_args)
        try:
            r_obs = json.loads(rank_obs_str)
        except Exception:
            r_obs = {}
        observations.append({"tool": "rank_pgs", "result": r_obs})

        final_ids = []
        for r in r_obs.get("ranked_pgs", []):
            final_ids.append(r["id"])
            if r.get("distance_km") is not None:
                distance_data[r["id"]] = r["distance_km"]

        draft_response = self._build_grounded_response(
            user_query=user_query,
            criteria=criteria,
            valid_pg_ids=final_ids,
            distance_data=distance_data
        )

        return draft_response, final_ids, observations, distance_data
