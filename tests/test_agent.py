"""Test LangGraph agent end-to-end."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.services.agent import run_agent


async def main():
      # Test 1: Wheat disease query
      print("Test 1: Wheat disease query...")
      print("=" * 60)
      result = await run_agent(
          user_inputs=["gehun me fungal rog lag gaya hai, kya karu?"],
          district="Hisar",
      )
      print(f"Response:\n{result['response'][:500]}")
      print(f"\nTool calls: {[tc['tool'] for tc in result['tool_calls']]}")
      print(f"Duration: {result['duration_ms']:.0f}ms")
      print()

      # Test 2: Weather query
      print("Test 2: Weather query...")
      print("=" * 60)
      result2 = await run_agent(
          user_inputs=["aaj mausam kaisa hai Karnal me?"],
          district="Karnal",
      )
      print(f"Response:\n{result2['response'][:500]}")
      print(f"\nTool calls: {[tc['tool'] for tc in result2['tool_calls']]}")
      print(f"Duration: {result2['duration_ms']:.0f}ms")
      print()

      print("Agent tests done.")


if __name__ == "__main__":
      asyncio.run(main())