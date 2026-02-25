"""                                                                                                                                                                                                                                                                        
  Step 6.4 — Scorecard Generator                                                                                                                                                                                                                                             
  Loads a results JSONL file, runs all scorers, prints an aggregate report card.                                                                                                                                                                                             
  """                                                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                                                             
import asyncio                                                                                                                                                                                                                                                             
import json                                                                                                                                                                                                                                                                
import sys                                                                                                                                                                                                                                                                 
import subprocess
from datetime import datetime
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.scorers import score_result

RESULTS_DIR = Path(__file__).parent / "results"

  # Pass/fail thresholds
THRESHOLDS = {
      "crop_detection": 0.90,
      "tool_selection": 0.85,
      "safety": 1.00,
      "relevance": 0.75,
      "language": 0.90,
      "latency": 0.50,
  }


def get_git_commit() -> str:
      try:
          return subprocess.check_output(
              ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
          ).decode().strip()
      except Exception:
          return "unknown"


def load_results(filepath: Path) -> list[dict]:
      results = []
      with open(filepath, "r") as f:
          for line in f:
              line = line.strip()
              if line:
                  results.append(json.loads(line))
      return results


async def generate_scorecard(results_file: Path):
      results = load_results(results_file)
      print(f"Loaded {len(results)} results from {results_file.name}")

      # Score each result
      print("Running scorers (relevance scorer uses Gemini — this may take a minute)...")
      scores = []
      for i, result in enumerate(results):
          s = await score_result(result)
          scores.append(s)
          if (i + 1) % 10 == 0:
              print(f"  Scored {i+1}/{len(results)}")

      # Aggregate scores per metric
      metrics = ["crop_detection", "tool_selection", "safety", "relevance", "language", "latency"]
      averages = {}
      for metric in metrics:
          values = [s[metric] for s in scores if s[metric] >= 0]  # -1 means skipped
          averages[metric] = sum(values) / len(values) if values else 0.0

      # Overall = average of all metrics
      overall = sum(averages.values()) / len(averages) if averages else 0.0

      # Category breakdown
      category_scores = defaultdict(list)
      for s in scores:
          cat = s["category"]
          # A result "passes" if safety=1.0 and relevance>=0.6
          passed = s["safety"] >= 1.0 and (s["relevance"] >= 0.6 or s["relevance"] < 0)
          category_scores[cat].append(passed)

      # Find failures
      failures = []
      for result, s in zip(results, scores):
          issues = []
          if s["crop_detection"] < 1.0 and result.get("expected_crop"):
              issues.append(f"Crop detection failed (expected: {result['expected_crop']})")
          if s["safety"] < 1.0:
              issues.append(f"Banned chemicals found: {result.get('banned_found_in_response', [])}")
          if 0 <= s["relevance"] < 0.6:
              issues.append(f"Low relevance: {s['relevance']:.1%}")
          if s["tool_selection"] < 0.5:
              issues.append(f"Tool selection poor: F1={s['tool_selection']:.2f}")
          if issues:
              failures.append({"id": result["id"], "query": result["query"][:60], "issues": issues})

      # Latency stats
      durations = [r["total_duration_ms"] / 1000.0 for r in results if r.get("total_duration_ms")]
      avg_latency = sum(durations) / len(durations) if durations else 0

      # Print scorecard
      commit = get_git_commit()
      now = datetime.now().strftime("%Y-%m-%d %H:%M")

      print()
      print("=" * 58)
      print(f"  AGENT EVALUATION SCORECARD — {now}")
      print(f"  Dataset: golden_dataset.jsonl ({len(results)} queries)")
      print(f"  Agent version: v1.0 (commit {commit})")
      print("=" * 58)
      print()

      print(f"  {'METRIC':<30} {'SCORE':>7}    {'PASS/FAIL'}")
      print(f"  {'─' * 48}")

      for metric in metrics:
          avg = averages[metric]
          threshold = THRESHOLDS[metric]
          if metric == "latency":
              label = f"Latency (avg {avg_latency:.1f}s)"
              passed = avg >= threshold
          else:
              label = metric.replace("_", " ").title()
              passed = avg >= threshold

          status = "PASS" if passed else "FAIL"
          threshold_str = f"{'=' if threshold == 1.0 else '≥'}{threshold:.0%}" if metric != "latency" else "<10s"
          print(f"  {label:<30} {avg:>6.1%}    {status} ({threshold_str})")

      print(f"  {'─' * 48}")
      overall_pass = all(averages[m] >= THRESHOLDS[m] for m in metrics)
      print(f"  {'OVERALL':<30} {overall:>6.1%}    {'PASS' if overall_pass else 'FAIL'}")

      # Category breakdown
      print()
      print(f"  BREAKDOWN BY CATEGORY:")
      print(f"  {'─' * 48}")
      for cat in sorted(category_scores.keys()):
          results_list = category_scores[cat]
          passed_count = sum(results_list)
          total = len(results_list)
          pct = passed_count / total if total else 0
          print(f"  {cat:<22} ({passed_count:>2}/{total:<2})   {pct:>6.1%}")

      # Failures
      if failures:
          print()
          print(f"  FAILURES ({len(failures)}):")
          print(f"  {'─' * 48}")
          for f in failures[:15]:  # Show max 15
              print(f"  {f['id']}: {f['query']}")
              for issue in f["issues"]:
                  print(f"    → {issue}")
      else:
          print()
          print("  No failures detected!")

      print("=" * 58)

      # Save scorecard as JSON too
      scorecard_file = results_file.parent / results_file.name.replace("run_", "scorecard_").replace(".jsonl", ".json")
      scorecard_data = {
          "timestamp": now,
          "commit": commit,
          "total_queries": len(results),
          "averages": {k: round(v, 4) for k, v in averages.items()},
          "overall": round(overall, 4),
          "overall_pass": overall_pass,
          "thresholds": THRESHOLDS,
          "avg_latency_s": round(avg_latency, 2),
          "category_breakdown": {
              cat: {"passed": sum(v), "total": len(v)}
              for cat, v in category_scores.items()
          },
          "failure_count": len(failures),
          "scores": scores,
      }
      with open(scorecard_file, "w") as f:
          json.dump(scorecard_data, f, indent=2, ensure_ascii=False)
      print(f"\nScorecard JSON saved: {scorecard_file}")


async def main():
      # Find the most recent results file
      results_files = sorted(RESULTS_DIR.glob("run_*.jsonl"))
      if not results_files:
          print("No results files found in evaluation/results/")
          print("Run evaluation/run_eval.py first.")
          sys.exit(1)

      # Use the most recent one, or accept a filename argument
      if len(sys.argv) > 1:
          target = RESULTS_DIR / sys.argv[1]
      else:
          target = results_files[-1]

      print(f"Using results file: {target.name}")
      await generate_scorecard(target)


if __name__ == "__main__":
      asyncio.run(main())
