import asyncio
from shared.services.tools.weather_fetcher import weather_fetcher, DISTRICT_COORDS
from shared.services.config import settings


def test_all_districts_have_coords():
      from shared.services.graph_api import HARYANA_DISTRICTS
      for d in HARYANA_DISTRICTS:
          assert d in DISTRICT_COORDS, f"Missing coords for {d}"
      print(f"All {len(HARYANA_DISTRICTS)} districts have coordinates OK")


async def test_live_api():
      if not settings.weather_api_key:
          print("SKIP — no Weather API key in .env")
          return

      result = await weather_fetcher.ainvoke({"district": "Karnal"})
      assert "Karnal" in result
      assert "°C" in result
      print("Live API OK")
      print("---")
      print(result)


async def test_bad_district():
      result = await weather_fetcher.ainvoke({"district": "FakePlace"})
      assert "नहीं मिला" in result
      print("Bad district handled OK")


if __name__ == "__main__":
      test_all_districts_have_coords()
      asyncio.run(test_bad_district())
      asyncio.run(test_live_api())
      print("Weather fetcher OK")