import httpx                                                                                                                                                                                                    
from langchain_core.tools import tool                                                                                                                                                                           
from shared.services.config import settings                                                                                                                                                                     
                                                                                                                                                                                                                  
DISTRICT_COORDS = {                                                                                                                                                                                             
      "Ambala": (30.3782, 76.7767),                                                                                                                                                                               
      "Bhiwani": (28.7930, 76.1320),                                               
      "Charki Dadri": (28.5921, 76.2711),
      "Faridabad": (28.4089, 77.3178),
      "Fatehabad": (29.5152, 75.4559),
      "Gurugram": (28.4595, 77.0266),
      "Hisar": (29.1492, 75.7217),
      "Jhajjar": (28.6063, 76.6556),
      "Jind": (29.3164, 76.3140),
      "Kaithal": (29.8015, 76.3998),
      "Karnal": (29.6857, 76.9905),
      "Kurukshetra": (29.9695, 76.8783),
      "Mahendragarh": (28.2824, 76.1536),
      "Nuh": (28.1000, 77.0000),
      "Palwal": (28.1487, 77.3320),
      "Panchkula": (30.6942, 76.8606),
      "Panipat": (29.3909, 76.9635),
      "Rewari": (28.1970, 76.6190),
      "Rohtak": (28.8955, 76.6066),
      "Sirsa": (29.5349, 75.0280),
      "Sonipat": (28.9931, 77.0151),
      "Yamunanagar": (30.1290, 77.2674),
  }

WEATHER_HINDI = {
      "Clear": "साफ़ ☀️",
      "Clouds": "बादल ☁️",
      "Rain": "बारिश ",
      "Drizzle": "बूंदाबांदी",
      "Thunderstorm": "आंधी-तूफान ",
      "Snow": "बर्फबारी ",
      "Mist": "धुंध 🌫️ ",
      "Haze": "धुंध 🌫️ ",
      "Fog": "कोहरा ",
      "Smoke": "धुआं 🌫️ ",
      "Dust": "धूल भरी 🌪️",
  }

WEEKDAYS_HINDI = ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"]


def _format_forecast(data: dict, district: str) -> str:
      """Format OpenWeatherMap 7-day forecast into Hindi text."""
      lines = [f"*🌤️  {district} — 7 दिन का मौसम:*\n"]

      daily = data.get("daily", [])[:7]
      for i, day in enumerate(daily):
          dt = day.get("dt", 0)
          import datetime
          date = datetime.datetime.fromtimestamp(dt)
          weekday = WEEKDAYS_HINDI[date.weekday()]

          temp_min = round(day.get("temp", {}).get("min", 0))
          temp_max = round(day.get("temp", {}).get("max", 0))
          weather_main = day.get("weather", [{}])[0].get("main", "Clear")
          weather_hindi = WEATHER_HINDI.get(weather_main, weather_main)
          humidity = day.get("humidity", 0)
          wind = round(day.get("wind_speed", 0) * 3.6)  # m/s to km/h

          lines.append(f"*{weekday}* ({date.strftime('%d/%m')})")
          lines.append(f"  {weather_hindi} | {temp_min}°–{temp_max}°C | नमी {humidity}% | हवा {wind} km/h")

      lines.append("\n🌱 _छिड़काव सुबह 6-9 बजे या शाम 4-6 बजे करें जब हवा कम हो।_")
      return "\n".join(lines)


@tool
async def weather_fetcher(district: str, lat: float | None = None, lon: float | None = None) -> str:
      """Get 7-day weather forecast for a Haryana district in Hindi. If lat/lon are provided, uses exact coordinates instead of district center."""
      if lat is not None and lon is not None:
          # Use exact coordinates from farmer's location pin
          pass
      else:
          coords = DISTRICT_COORDS.get(district)
          if not coords:
              return f"❌ जिला '{district}' नहीं मिला। कृपया सही जिला बताएं।"
          lat, lon = coords
      url = "https://api.openweathermap.org/data/3.0/onecall"
      params = {
          "lat": lat,
          "lon": lon,
          "exclude": "minutely,hourly,alerts",
          "units": "metric",
          "appid": settings.weather_api_key,
      }

      async with httpx.AsyncClient(timeout=15.0) as client:
          resp = await client.get(url, params=params)
          resp.raise_for_status()
          data = resp.json()

      return _format_forecast(data, district)