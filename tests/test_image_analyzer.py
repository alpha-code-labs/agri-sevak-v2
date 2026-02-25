"""Test image analyzer tool."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.services.tools.image_analyzer import image_analyzer


async def main():
      # Test 1: Analyze a real image from Azure Blob
      # Replace with an actual blob name from your storage if you have one
      print("Test 1: Image analysis (requires real blob image)...")
      try:
          result = await image_analyzer.ainvoke({
              "blob_name": "test/sample_crop.jpg",
              "crop_name": "Wheat",
          })
          if result.get("error"):
              print(f"  Expected error (no test image): {result['error']}")
          else:
              print(f"  Diagnosis preview: {result['diagnosis'][:200]}...")
              print(f"  Safety: {result['safety']}")
      except Exception as e:
          print(f"  Expected error (no test image in blob): {e}")

      print()
      print("Image analyzer tool created successfully.")
      print("Full test requires a real crop image in Azure Blob Storage.")


if __name__ == "__main__":
      asyncio.run(main())