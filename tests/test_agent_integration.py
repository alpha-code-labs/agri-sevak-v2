"""                                                                                                                                                                                                                                                                        
  Step 4.4 — End-to-end Agent Integration Tests                                                                                                                                                                                                                              
  5 scenarios testing the full pipeline: agent + safety audit.                                                                                                                                                                                                               
  """                                                                                                                                                                                                                                                                        
import asyncio                                                                                                                                                                                                                                                             
import sys                                                                                                                                                                                                                                                                 
import time                                                                                                                                                                                                                                                                
from pathlib import Path                                                         

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.services.agent import run_agent
from shared.services.safety_audit import safety_audit

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = ""):
      global PASS, FAIL
      if condition:
          PASS += 1
          print(f"  PASS — {name}")
      else:
          FAIL += 1
          print(f"  FAIL — {name} {detail}")


async def test_1_wheat_disease():
      """Scenario 1: Wheat disease text query — should use crop_detector + rag_retriever + safety_checker."""
      print("\n" + "=" * 60)
      print("TEST 1: Wheat disease query (text)")
      print("=" * 60)

      result = await run_agent(
          user_inputs=["gehun me pila ratua rog lag gaya hai, kya karu?"],
          district="Hisar",
      )

      tools_used = [tc["tool"] for tc in result["tool_calls"]]
      response = result["response"] if isinstance(result["response"], str) else str(result["response"])

      check("Agent returned a response", len(response) > 50)
      check("crop_detector was called", "crop_detector" in tools_used)
      check("rag_retriever was called", "rag_retriever" in tools_used)
      check("Response is in Hindi", any(c >= '\u0900' and c <= '\u097F' for c in response))

      # Run safety audit
      audited = await safety_audit(response, crop_name="Wheat", district="Hisar")
      check("Safety audit passed", audited["is_safe_before_audit"] or audited["audit_applied"])
      check("Audited response exists", len(audited["audited_response"]) > 50)

      print(f"  Duration: {result['duration_ms']:.0f}ms")
      print(f"  Tools: {tools_used}")
      print(f"  Response preview: {response[:150]}...")


async def test_2_plant_image():
      """Scenario 2: Plant image analysis — tests image_analyzer tool.
      Since we don't have a real blob image, we verify the agent attempts to use image_analyzer."""
      print("\n" + "=" * 60)
      print("TEST 2: Plant image query (simulated)")
      print("=" * 60)

      result = await run_agent(
          user_inputs=["maine apni fasal ki photo bheji hai, blob_name: crops/wheat_rust.jpg, isme kya rog hai?"],
          district="Karnal",
      )

      tools_used = [tc["tool"] for tc in result["tool_calls"]]
      response = result["response"] if isinstance(result["response"], str) else str(result["response"])

      check("Agent returned a response", len(response) > 20)
      # Agent should attempt image_analyzer (may fail due to no real blob, that's OK)
      check("image_analyzer was attempted", "image_analyzer" in tools_used,
            f"(tools used: {tools_used})")

      print(f"  Duration: {result['duration_ms']:.0f}ms")
      print(f"  Tools: {tools_used}")
      print(f"  Response preview: {response[:150]}...")


async def test_3_weather_query():
      """Scenario 3: Weather query — should use only weather_fetcher, no crop tools."""
      print("\n" + "=" * 60)
      print("TEST 3: Weather query")
      print("=" * 60)

      result = await run_agent(
          user_inputs=["aaj Karnal me mausam kaisa hai? kya sinchai karni chahiye?"],
          district="Karnal",
      )

      tools_used = [tc["tool"] for tc in result["tool_calls"]]
      response = result["response"] if isinstance(result["response"], str) else str(result["response"])

      check("Agent returned a response", len(response) > 50)
      check("weather_fetcher was called", "weather_fetcher" in tools_used)
      check("Response is in Hindi", any(c >= '\u0900' and c <= '\u097F' for c in response))

      print(f"  Duration: {result['duration_ms']:.0f}ms")
      print(f"  Tools: {tools_used}")
      print(f"  Response preview: {response[:150]}...")


async def test_4_unknown_crop():
      """Scenario 4: Unknown/ambiguous crop — agent should ask for clarification or attempt detection."""
      print("\n" + "=" * 60)
      print("TEST 4: Unknown crop (ambiguous input)")
      print("=" * 60)

      result = await run_agent(
          user_inputs=["mere khet me kuch patte peele ho rahe hai"],
          district="Rohtak",
      )

      tools_used = [tc["tool"] for tc in result["tool_calls"]]
      response = result["response"] if isinstance(result["response"], str) else str(result["response"])

      check("Agent returned a response", len(response) > 20)
      check("crop_detector was attempted", "crop_detector" in tools_used)
      check("Response is in Hindi", any(c >= '\u0900' and c <= '\u097F' for c in response))

      print(f"  Duration: {result['duration_ms']:.0f}ms")
      print(f"  Tools: {tools_used}")
      print(f"  Response preview: {response[:150]}...")


async def test_5_banned_pesticide_check():
      """Scenario 5: Query where RAG results might contain banned chemicals — safety audit must catch them."""
      print("\n" + "=" * 60)
      print("TEST 5: Banned pesticide safety check")
      print("=" * 60)

      # Simulate a response that contains a banned chemical
      fake_agent_response = (
          "किसान भाई, गेहूं में एफिड कीट के लिए फॉस्फामिडॉन (Phosphamidon) "
          "300 मिली प्रति एकड़ का छिड़काव करें। यह बहुत असरदार है। "
          "इसके अलावा मोनोक्रोटोफॉस (Monocrotophos) भी उपयोग कर सकते हैं।"
      )

      audited = await safety_audit(fake_agent_response, crop_name="Wheat", district="Hisar")

      banned_names = [c["chemical_name"] for c in audited["local_scan"]]
      check("Local scan caught Phosphamidon", "Phosphamidon" in banned_names)
      check("Local scan caught Monocrotophos", "Monocrotophos" in banned_names)
      check("Response was NOT safe before audit", not audited["is_safe_before_audit"])
      check("Audit was applied", audited["audit_applied"])
      check("Audited response exists", len(audited["audited_response"]) > 50)

      # Check that the audited response doesn't contain the banned chemicals
      audited_lower = audited["audited_response"].lower()
      check("Phosphamidon removed from final response", "phosphamidon" not in audited_lower)
      check("Monocrotophos removed from final response", "monocrotophos" not in audited_lower)

      print(f"  Banned found: {banned_names}")
      print(f"  Audited response preview: {audited['audited_response'][:200]}...")


async def main():
      global PASS, FAIL
      start = time.perf_counter()

      print("KCC Agentic AI — End-to-End Integration Tests")
      print("=" * 60)

      await test_1_wheat_disease()
      await test_2_plant_image()
      await test_3_weather_query()
      await test_4_unknown_crop()
      await test_5_banned_pesticide_check()

      total_time = time.perf_counter() - start

      print("\n" + "=" * 60)
      print(f"RESULTS: {PASS} passed, {FAIL} failed ({total_time:.1f}s total)")
      print("=" * 60)

      if FAIL > 0:
          sys.exit(1)


if __name__ == "__main__":
      asyncio.run(main())