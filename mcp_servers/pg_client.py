import sys
import os
import json
import logging
import asyncio
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any, Optional

# Official Model Context Protocol (MCP) Python Client SDK
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BASE_DIR = Path(__file__).resolve().parent.parent
logger = logging.getLogger(__name__)

class PGClient:
    """
    Official MCP Client interface for interacting with the custom SmartStay PG MCP server (pg_server.py).
    Communicates via official MCP Python SDK (stdio_client + ClientSession) over standard I/O.
    """

    def __init__(self, timeout: float = 12.0):
        self.timeout = timeout
        self.server_path = BASE_DIR / "mcp_servers" / "pg_server.py"

    def _get_server_params(self) -> StdioServerParameters:
        """Constructs StdioServerParameters to launch the FastMCP PG server as a subprocess."""
        env = {**os.environ, "PYTHONUNBUFFERED": "1"}
        return StdioServerParameters(
            command=sys.executable,
            args=["-u", str(self.server_path)],
            env=env
        )

    async def list_tools_async(self) -> List[Dict[str, Any]]:
        """
        Discovers tools exposed by the custom FastMCP server using the official MCP SDK.
        Returns a list of dicts with tool name, description, and input schema.
        """
        server_params = self._get_server_params()
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                discovered = []
                for t in tools_result.tools:
                    discovered.append({
                        "name": t.name,
                        "description": t.description or "",
                        "input_schema": t.inputSchema if hasattr(t, "inputSchema") else getattr(t, "input_schema", {}),
                        "server": "smartstay-pg-server"
                    })
                return discovered

    def list_tools(self) -> List[Dict[str, Any]]:
        """Synchronous wrapper for discovering tools via official MCP SDK."""
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            future = pool.submit(lambda: asyncio.run(self.list_tools_async()))
            return future.result(timeout=self.timeout)
        except Exception as e:
            logger.warning(f"MCP client tool discovery encountered error: {e}. Falling back to default schemas.")
            # Fallback metadata if subprocess is blocked in restricted environments
            return [
                {
                    "name": "search_pgs",
                    "description": "Search PG database matching city, area, gender, or room type.",
                    "input_schema": {"type": "object", "properties": {"city": {"type": "string"}, "area": {"type": "string"}, "gender": {"type": "string"}, "room_type": {"type": "string"}}},
                    "server": "smartstay-pg-server"
                },
                {
                    "name": "filter_by_budget",
                    "description": "Filter PGs by max monthly rent.",
                    "input_schema": {"type": "object", "properties": {"pg_ids": {"type": "array", "items": {"type": "string"}}, "max_rent": {"type": "number"}}, "required": ["max_rent"]},
                    "server": "smartstay-pg-server"
                },
                {
                    "name": "check_amenities",
                    "description": "Verify presence of mandatory amenities.",
                    "input_schema": {"type": "object", "properties": {"pg_ids": {"type": "array", "items": {"type": "string"}}, "required_amenities": {"type": "array", "items": {"type": "string"}}}, "required": ["required_amenities"]},
                    "server": "smartstay-pg-server"
                },
                {
                    "name": "calculate_distance",
                    "description": "Calculate straight-line distance in km between two sets of coordinates.",
                    "input_schema": {"type": "object", "properties": {"origin_lat": {"type": "number"}, "origin_lon": {"type": "number"}, "dest_lat": {"type": "number"}, "dest_lon": {"type": "number"}}},
                    "server": "smartstay-pg-server"
                },
                {
                    "name": "compare_pgs",
                    "description": "Compare candidate PGs side-by-side.",
                    "input_schema": {"type": "object", "properties": {"pg_ids": {"type": "array", "items": {"type": "string"}}}, "required": ["pg_ids"]},
                    "server": "smartstay-pg-server"
                },
                {
                    "name": "rank_pgs",
                    "description": "Multi-factor scoring and ranking of candidate PGs.",
                    "input_schema": {"type": "object", "properties": {"pg_ids": {"type": "array", "items": {"type": "string"}}, "max_budget": {"type": "number"}, "dest_lat": {"type": "number"}, "dest_lon": {"type": "number"}, "max_distance_km": {"type": "number"}}, "required": ["pg_ids"]},
                    "server": "smartstay-pg-server"
                },
                {
                    "name": "get_pg_details",
                    "description": "Retrieve verified full details for a PG ID.",
                    "input_schema": {"type": "object", "properties": {"pg_id": {"type": "string"}}, "required": ["pg_id"]},
                    "server": "smartstay-pg-server"
                }
            ]
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

    async def call_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Executes a tool on the custom FastMCP server using the official MCP SDK:
        stdio_client -> ClientSession -> session.initialize() -> session.call_tool()
        """
        server_params = self._get_server_params()
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                if result.content and len(result.content) > 0:
                    return result.content[0].text
                return json.dumps({"success": True, "result": "Tool executed with empty content."})

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Synchronous wrapper for calling a tool on the custom FastMCP server over MCP."""
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            future = pool.submit(lambda: asyncio.run(self.call_tool_async(tool_name, arguments)))
            return future.result(timeout=self.timeout)
        except Exception as e:
            logger.warning(f"MCP tool call '{tool_name}' failed via stdio: {e}. Executing direct fallback.")
            return self._local_fallback_call(tool_name, arguments)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

    def _local_fallback_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Emergency local dispatch if MCP process is unreachable."""
        from tools.pg_search import search_pgs, get_pg_details
        from tools.budget_filter import filter_by_budget
        from tools.amenity_checker import check_amenities
        from tools.distance_calculator import calculate_distance
        from tools.pg_comparator import compare_pgs
        from tools.pg_ranker import rank_pgs

        if tool_name == "search_pgs":
            res = search_pgs(
                city=arguments.get("city", "Ahmedabad"),
                area=arguments.get("area"),
                gender=arguments.get("gender"),
                room_type=arguments.get("room_type")
            )
            return json.dumps({"success": True, "count": len(res), "results": res}, indent=2)
        elif tool_name == "filter_by_budget":
            res = filter_by_budget(pg_input=arguments.get("pg_ids"), max_rent=float(arguments.get("max_rent", 0)))
            return json.dumps(res, indent=2)
        elif tool_name == "check_amenities":
            res = check_amenities(pg_input=arguments.get("pg_ids"), required_amenities=arguments.get("required_amenities", []))
            return json.dumps(res, indent=2)
        elif tool_name == "calculate_distance":
            res = calculate_distance(
                origin_lat=arguments.get("origin_lat"),
                origin_lon=arguments.get("origin_lon"),
                dest_lat=arguments.get("dest_lat"),
                dest_lon=arguments.get("dest_lon"),
                origin_name=arguments.get("origin_name", "Origin"),
                dest_name=arguments.get("dest_name", "Destination")
            )
            return json.dumps(res, indent=2)
        elif tool_name == "compare_pgs":
            res = compare_pgs(pg_ids=arguments.get("pg_ids", []))
            return json.dumps(res, indent=2)
        elif tool_name == "rank_pgs":
            res = rank_pgs(
                pg_ids=arguments.get("pg_ids", []),
                max_budget=arguments.get("max_budget"),
                dest_lat=arguments.get("dest_lat"),
                dest_lon=arguments.get("dest_lon"),
                max_distance_km=arguments.get("max_distance_km"),
                required_amenities=arguments.get("required_amenities")
            )
            return json.dumps(res, indent=2)
        elif tool_name == "get_pg_details":
            details = get_pg_details(arguments.get("pg_id", ""))
            return json.dumps({"success": bool(details), "details": details}, indent=2)
        else:
            return json.dumps({"success": False, "error": f"Unknown tool '{tool_name}'"})

pg_client = PGClient()
