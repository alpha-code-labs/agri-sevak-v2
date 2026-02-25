"""Test RAG retriever tool."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.services.tools.rag_retriever import rag_retriever


async def main():
      # Test 1: Query that should hit Pinecone (wheat is in the corpus)
      print("Test 1: Wheat disease query (should hit Pinecone RAG)...")
      result = await rag_retriever.ainvoke({
          "query": "gehun me fungal rog ka ilaj",
          "crop_name": "wheat",
      })
      print(f"  Source: {result['source']}")
      print(f"  Evidence count: {len(result['evidence'])}")
      if result["evidence"]:
          print(f"  Top match score: {result['evidence'][0].get('score', 'N/A')}")
          print(f"  Text preview: {result['evidence'][0]['text'][:150]}...")
      print(f"  Safety: {result['safety']}")
      print()

      # Test 2: Query for a crop that might not have exact match
      print("Test 2: Paddy pest query...")
      result2 = await rag_retriever.ainvoke({
          "query": "dhan me kide lage hue hai kya karu",
          "crop_name": "paddy_dhan",
      })
      print(f"  Source: {result2['source']}")
      print(f"  Evidence count: {len(result2['evidence'])}")
      print(f"  Safety safe: {result2['safety'].get('is_safe', 'N/A')}")
      print()

      print("RAG retriever tests done.")


if __name__ == "__main__":
      asyncio.run(main())