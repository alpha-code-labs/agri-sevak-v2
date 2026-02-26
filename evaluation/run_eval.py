"""                                                                                                                                                                                                                                                                        
  Step 6.2 — Evaluation Runner                                                                                                                                                                                                                                               
  Runs the full golden dataset through the agent, captures results.                                                                                                                                                                                                          
  Saves raw results to evaluation/results/run_YYYY-MM-DD_HH-MM.jsonl
  """

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.services.agent import run_agent
from shared.services.safety_audit import safety_audit

GOLDEN_DATASET = Path(__file__).parent / "golden_dataset.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"


def load_golden_dataset() -> list[dict]:
      entries = []
      with open(GOLDEN_DATASET, "r") as f:
          for line in f:
              line = line.strip()
              if line:
                  entries.append(json.loads(line))
      return entries


async def run_single(entry: dict) -> dict:
      """Run a single evaluation query through the agent + safety audit."""
      start = time.perf_counter()

      try:
          # Run the agent — support multi-input entries
          user_inputs = entry.get("inputs", [entry["query"]])
          agent_result = await run_agent(
              user_inputs=user_inputs,
              district=entry["district"],
          )

          response = agent_result["response"]
          # Normalize response to string
          if isinstance(response, list):
              response = "\n".join(
                  part.get("text", str(part)) if isinstance(part, dict) else str(part)
                  for part in response
              )

          tool_calls = [tc["tool"] for tc in agent_result.get("tool_calls", [])]
          agent_duration = agent_result.get("duration_ms", 0)

          # Detect crop from tool calls
          crop_detected = ""
          for tc in agent_result.get("tool_calls", []):
              if tc["tool"] == "crop_detector":
                  # The crop is in the response, not the args — we'll extract from response later
                  crop_detected = "attempted"
                  break

          # Run safety audit
          audit_result = await safety_audit(
              agent_response=response,
              crop_name=entry.get("expected_crop", ""),
              district=entry["district"],
          )

          total_duration = (time.perf_counter() - start) * 1000

          return {
              "id": entry["id"],
              "query": entry["query"],
              "district": entry["district"],
              "category": entry["category"],
              "expected_crop": entry.get("expected_crop", ""),
              "expected_tools": entry.get("expected_tools", []),
              "expected_topics": entry.get("expected_topics", []),
              "banned_chemicals_must_not_appear": entry.get("banned_chemicals_must_not_appear", []),
              "actual_response": response,
              "actual_tools": tool_calls,
              "actual_tools_unique": list(dict.fromkeys(tool_calls)),
              "audited_response": audit_result["audited_response"],
              "safety_clean_before_audit": audit_result["is_safe_before_audit"],
              "safety_audit_applied": audit_result["audit_applied"],
              "banned_found_in_response": [c["chemical_name"] for c in audit_result.get("local_scan", [])],
              "agent_duration_ms": agent_duration,
              "total_duration_ms": round(total_duration, 1),
              "status": "success",
              "error": "",
          }

      except Exception as e:
          total_duration = (time.perf_counter() - start) * 1000
          return {
              "id": entry["id"],
              "query": entry["query"],
              "district": entry["district"],
              "category": entry["category"],
              "expected_crop": entry.get("expected_crop", ""),
              "expected_tools": entry.get("expected_tools", []),
              "expected_topics": entry.get("expected_topics", []),
              "banned_chemicals_must_not_appear": entry.get("banned_chemicals_must_not_appear", []),
              "actual_response": "",
              "actual_tools": [],
              "actual_tools_unique": [],
              "audited_response": "",
              "safety_clean_before_audit": False,
              "safety_audit_applied": False,
              "banned_found_in_response": [],
              "agent_duration_ms": 0,
              "total_duration_ms": round(total_duration, 1),
              "status": "error",
              "error": str(e),
          }


async def main():
      dataset = load_golden_dataset()
      print(f"Loaded {len(dataset)} queries from golden dataset")
      print("=" * 60)

      # Create results file
      RESULTS_DIR.mkdir(parents=True, exist_ok=True)
      timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
      results_file = RESULTS_DIR / f"run_{timestamp}.jsonl"

      results = []
      total_start = time.perf_counter()

      for i, entry in enumerate(dataset):
          print(f"\n[{i+1}/{len(dataset)}] {entry['id']} — {entry['query'][:50]}...")

          result = await run_single(entry)
          results.append(result)

          # Write incrementally (so partial results are saved if interrupted)
          with open(results_file, "a") as f:
              f.write(json.dumps(result, ensure_ascii=False) + "\n")

          status = result["status"]
          duration = result["total_duration_ms"]
          tools = result["actual_tools_unique"]
          print(f"  Status: {status} | Duration: {duration:.0f}ms | Tools: {tools}")

          if result.get("banned_found_in_response"):
              print(f"  WARNING — Banned chemicals found: {result['banned_found_in_response']}")

      total_time = time.perf_counter() - total_start

      # Summary
      print("\n" + "=" * 60)
      print(f"EVALUATION COMPLETE")
      print(f"  Queries: {len(results)}")
      print(f"  Success: {sum(1 for r in results if r['status'] == 'success')}")
      print(f"  Errors:  {sum(1 for r in results if r['status'] == 'error')}")
      print(f"  Total time: {total_time:.1f}s")
      print(f"  Avg per query: {total_time/len(results):.1f}s")
      print(f"  Results saved: {results_file}")
      print("=" * 60)


if __name__ == "__main__":
      asyncio.run(main())