"""                                                                                                                                                                                                                                                                        
  Step 6.5 — Regression Comparison                                                                                                                                                                                                                                           
  Compares two scorecard JSON files side by side.                                                                                                                                                                                                                            
  Usage: python evaluation/compare.py [baseline.json] [new.json]                                                                                                                                                                                                             
  If no args given, compares the two most recent scorecards.                                                                                                                                                                                                                 
  """                                                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                                                             
import json                                                                                                                                                                                                                                                                
import sys
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"

METRIC_LABELS = {
      "crop_detection": "Crop detection accuracy",
      "tool_selection": "Tool selection F1",
      "safety": "Safety compliance",
      "relevance": "Response relevance (LLM)",
      "language": "Language compliance",
      "latency": "Latency",
  }

THRESHOLDS = {
      "crop_detection": 0.90,
      "tool_selection": 0.85,
      "safety": 1.00,
      "relevance": 0.75,
      "language": 0.90,
      "latency": 0.50,
  }

  # Metrics where a drop of more than this is a regression
REGRESSION_TOLERANCE = {
      "crop_detection": 0.02,
      "tool_selection": 0.03,
      "safety": 0.00,       # Zero tolerance for safety
      "relevance": 0.05,
      "language": 0.03,
      "latency": 0.10,
  }


def load_scorecard(filepath: Path) -> dict:
      with open(filepath, "r") as f:
          return json.load(f)


def main():
      # Find scorecard files
      scorecards = sorted(RESULTS_DIR.glob("scorecard_*.json"))

      if len(sys.argv) == 3:
          baseline_file = RESULTS_DIR / sys.argv[1]
          new_file = RESULTS_DIR / sys.argv[2]
      elif len(scorecards) >= 2:
          baseline_file = scorecards[-2]
          new_file = scorecards[-1]
      elif len(scorecards) == 1:
          print("Only one scorecard found. Need at least two runs to compare.")
          print(f"  Found: {scorecards[0].name}")
          print("Run the evaluation again after making changes to get a second scorecard.")
          sys.exit(0)
      else:
          print("No scorecard files found. Run evaluation first:")
          print("  python evaluation/run_eval.py")
          print("  python evaluation/scorecard.py")
          sys.exit(1)

      baseline = load_scorecard(baseline_file)
      new = load_scorecard(new_file)

      baseline_label = f"{baseline.get('commit', '?')} ({baseline_file.stem})"
      new_label = f"{new.get('commit', '?')} ({new_file.stem})"

      # Header
      print()
      print("=" * 62)
      print(f"  REGRESSION COMPARISON")
      print(f"  Baseline: {baseline_label}")
      print(f"  New:      {new_label}")
      print("=" * 62)
      print()

      # Metric comparison
      print(f"  {'METRIC':<28} {'BASELINE':>8}  {'NEW':>8}  {'DELTA':>10}")
      print(f"  {'─' * 56}")

      regressions = []
      improvements = []

      metrics = ["crop_detection", "tool_selection", "safety", "relevance", "language", "latency"]

      for metric in metrics:
          base_val = baseline.get("averages", {}).get(metric, 0)
          new_val = new.get("averages", {}).get(metric, 0)
          delta = new_val - base_val
          tolerance = REGRESSION_TOLERANCE[metric]

          label = METRIC_LABELS[metric]

          if metric == "latency":
              base_lat = baseline.get("avg_latency_s", 0)
              new_lat = new.get("avg_latency_s", 0)
              delta_lat = new_lat - base_lat
              delta_str = f"{delta_lat:+.1f}s"
              if delta_lat < -1:
                  delta_str += "  ^"  # faster = better
                  improvements.append(label)
              elif delta_lat > 2:
                  delta_str += "  SLOWER"
                  regressions.append(label)
              else:
                  delta_str += "  —"
              print(f"  {label:<28} {base_lat:>7.1f}s  {new_lat:>7.1f}s  {delta_str}")
          else:
              if delta > tolerance:
                  arrow = "  ^"
                  improvements.append(label)
              elif delta < -tolerance:
                  arrow = "  REGRESSION"
                  regressions.append(label)
              else:
                  arrow = "  —"

              print(f"  {label:<28} {base_val:>7.1%}  {new_val:>7.1%}  {delta:>+6.1%}{arrow}")

      # Overall
      print(f"  {'─' * 56}")
      base_overall = baseline.get("overall", 0)
      new_overall = new.get("overall", 0)
      delta_overall = new_overall - base_overall
      print(f"  {'OVERALL':<28} {base_overall:>7.1%}  {new_overall:>7.1%}  {delta_overall:>+6.1%}")

      # Category comparison
      print()
      print(f"  CATEGORY BREAKDOWN:")
      print(f"  {'─' * 56}")

      base_cats = baseline.get("category_breakdown", {})
      new_cats = new.get("category_breakdown", {})
      all_cats = sorted(set(list(base_cats.keys()) + list(new_cats.keys())))

      for cat in all_cats:
          b = base_cats.get(cat, {"passed": 0, "total": 0})
          n = new_cats.get(cat, {"passed": 0, "total": 0})
          b_pct = b["passed"] / b["total"] if b["total"] else 0
          n_pct = n["passed"] / n["total"] if n["total"] else 0
          delta = n_pct - b_pct

          marker = ""
          if delta > 0.05:
              marker = " ^"
          elif delta < -0.05:
              marker = " REGRESSION"

          print(f"  {cat:<22} {b['passed']:>2}/{b['total']:<2} {b_pct:>5.0%}  →  {n['passed']:>2}/{n['total']:<2} {n_pct:>5.0%}{marker}")

      # Verdict
      print()
      print(f"  {'─' * 56}")
      if regressions:
          print(f"  VERDICT: DO NOT SHIP — regressions in: {', '.join(regressions)}")
      elif improvements:
          print(f"  VERDICT: SHIP IT — improvements in: {', '.join(improvements)}")
      else:
          print(f"  VERDICT: NO CHANGE — metrics are stable")
      print("=" * 62)


if __name__ == "__main__":
      main()