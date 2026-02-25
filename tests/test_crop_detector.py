import asyncio
from shared.services.tools.crop_detector import crop_detector, fuzzy_detect


def test_fuzzy_exact():
      result = fuzzy_detect("wheat")
      assert result["crop_name"] == "Wheat"
      assert result["source"] == "exact"
      print(f"Exact match OK — wheat → {result['crop_name']}")


def test_fuzzy_hindi():
      result = fuzzy_detect("गेहूं")
      assert result is not None
      assert result["crop_name"] == "Wheat"
      print(f"Hindi match OK — गेहूं → {result['crop_name']}")


def test_fuzzy_misspelling():
      result = fuzzy_detect("gehu")
      assert result is not None
      print(f"Misspelling OK — gehu → {result['crop_name']} ({result['confidence']})")


async def test_classifier_hindi_query():
      result = await crop_detector.ainvoke({"farmer_input": "gehun me kide lage hue hai"})
      assert result["crop_name"] == "Wheat"
      print(f"Classifier OK — 'gehun me kide lage hue hai' → {result['crop_name']} (source: {result['source']}, conf: {result['confidence']})")


async def test_classifier_variety():
      result = await crop_detector.ainvoke({"farmer_input": "WH 1270 me rog aa gya"})
      print(f"Variety OK — 'WH 1270 me rog aa gya' → {result['crop_name']} (source: {result['source']}, conf: {result['confidence']})")


async def test_no_crop():
      result = await crop_detector.ainvoke({"farmer_input": "aaj mausam kaisa hai"})
      print(f"No crop OK — 'aaj mausam kaisa hai' → crop: {result['crop_name']} (source: {result['source']}, conf: {result['confidence']})")


if __name__ == "__main__":
      test_fuzzy_exact()
      test_fuzzy_hindi()
      test_fuzzy_misspelling()
      asyncio.run(test_classifier_hindi_query())
      asyncio.run(test_classifier_variety())
      asyncio.run(test_no_crop())
      print("Crop detector OK")