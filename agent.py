import sys
import os
import argparse
from pathlib import Path

# Fix Windows console UTF-8 output
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from agents.smartstay_agent import SmartStayAgent

def print_separator(title: str = "", char: str = "=", width: int = 80):
    if title:
        padding = (width - len(title) - 2) // 2
        print(f"\n{char * padding} {title} {char * padding}")
    else:
        print(f"\n{char * width}")

def run_cli(user_query: str, record_transcript: bool = False, model_name: str = None):
    print_separator("SMARTSTAY: AI-POWERED PG FINDER (LEVEL 2 CAPSTONE)")
    print(f"User Query: {user_query}")
    if model_name:
        print(f"Active Model: {model_name}")

    agent = SmartStayAgent(model_name=model_name)

    # 1. Tool Discovery Phase
    print_separator("PHASE 1: MCP TOOL DISCOVERY")
    tools = agent.discover_tools()
    print(f"Discovered {len(tools)} tools across 2 MCP servers:")
    for t in tools:
        print(f"  • [{t['server']}] {t['name']}: {t['description']}")

    # 2. Agentic Execution
    print_separator("PHASE 2: DYNAMIC TOOL SELECTION & AGENTIC LOOP")
    result = agent.run(user_query)

    print(f"\nCompleted agent loop with {len(result['execution_trace'])} reasoning steps and {len(result['observations'])} tool observations.")
    for idx, obs in enumerate(result["observations"], 1):
        tool_name = obs.get("tool")
        res_summary = str(obs.get("result"))[:120] + "..." if len(str(obs.get("result"))) > 120 else str(obs.get("result"))
        print(f"  [Step {idx}] Tool: '{tool_name}' -> Observation: {res_summary}")

    # 3. Deterministic Validation Phase
    print_separator("PHASE 3: DETERMINISTIC VALIDATION")
    val = result["validation_result"]
    print(f"Validation Status: {'PASSED [OK]' if val['is_valid'] else 'FAILED [X]'}")
    if val["verified_items"]:
        print("Verified Checks:")
        for item in val["verified_items"]:
            print(f"  [+] {item}")
    if val["warnings"]:
        print("Warnings:")
        for w in val["warnings"]:
            print(f"  [!] {w}")
    if val["errors"]:
        print("Errors:")
        for e in val["errors"]:
            print(f"  [-] {e}")

    # 4. Reflection Phase
    print_separator("PHASE 4: ONE-SHOT REFLECTION & EVIDENCE AUDITING")
    ref = result["reflection_result"]
    print(f"Reflection Audit: {'Correction Not Needed' if not ref['needs_correction'] else 'Correction Applied'}")
    print(f"Critique: {ref['critique']}")

    # 5. Final Recommendations
    print_separator("PHASE 5: FINAL GROUNDED RECOMMENDATIONS")
    print(result["final_response"])
    print_separator("EXECUTION COMPLETE")

    if record_transcript:
        evidence_dir = Path("evidence")
        evidence_dir.mkdir(parents=True, exist_ok=True)
        transcript_file = evidence_dir / "demo_transcript.txt"
        with open(transcript_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"USER QUERY: {user_query}\n")
            f.write(f"{'='*80}\n")
            f.write(f"DISCOVERED TOOLS: {len(tools)}\n")
            f.write(f"OBSERVATIONS: {len(result['observations'])}\n")
            f.write(f"VALIDATION: {'PASSED' if val['is_valid'] else 'FAILED'}\n")
            f.write(f"REFLECTION CRITIQUE: {ref['critique']}\n")
            f.write(f"\nFINAL RESPONSE:\n{result['final_response']}\n")
        print(f"\nRecorded execution transcript to: {transcript_file.resolve()}")

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SmartStay AI PG Finder Agent CLI")
    parser.add_argument(
        "--query",
        type=str,
        default="Find a girls' PG in Ahmedabad under ₹8,000 per month, within 3 km of my college, with Wi-Fi and food.",
        help="Natural language query for the PG finder agent"
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="Record execution transcript to evidence/demo_transcript.txt"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Ollama model to use (default: mistral:7b or llama3.2:3b)"
    )
    args = parser.parse_args()

    run_cli(args.query, record_transcript=args.record, model_name=args.model)
