import httpx                                                                                                                                                                                                                                                               
from shared.services.config import settings                                                                                                                                                                                                                                
                                                                                                                                                                                                                                                                             
HARYANA_DISTRICTS = [                                                            
      "Ambala", "Bhiwani", "Charki Dadri", "Faridabad", "Fatehabad",
      "Gurugram", "Hisar", "Jhajjar", "Jind", "Kaithal", "Karnal",
      "Kurukshetra", "Mahendragarh", "Nuh", "Palwal", "Panchkula",
      "Panipat", "Rewari", "Rohtak", "Sirsa", "Sonipat", "Yamunanagar",
  ]

DISTRICTS_PER_PAGE = 8


class GraphAPI:
      def __init__(self, access_token: str = "", graph_api_url: str = ""):
          self.access_token = access_token or settings.access_token
          self.base_url = graph_api_url or settings.graph_api_url
          self.headers = {
              "Authorization": f"Bearer {self.access_token}",
              "Content-Type": "application/json",
          }

      async def _post(self, phone_number_id: str, payload: dict) -> dict:
          url = f"{self.base_url}/{phone_number_id}/messages"
          async with httpx.AsyncClient(timeout=30.0) as client:
              resp = await client.post(url, json=payload, headers=self.headers)
              return resp.json()

      async def send_text(self, phone_number_id: str, to: str, text: str) -> dict:
          return await self._post(phone_number_id, {
              "messaging_product": "whatsapp",
              "to": to,
              "type": "text",
              "text": {"body": text},
          })

      async def send_interactive_buttons(self, phone_number_id: str, to: str,
                                         body_text: str, buttons: list[dict]) -> dict:
          return await self._post(phone_number_id, {
              "messaging_product": "whatsapp",
              "to": to,
              "type": "interactive",
              "interactive": {
                  "type": "button",
                  "body": {"text": body_text},
                  "action": {"buttons": buttons},
              },
          })

      async def send_interactive_list(self, phone_number_id: str, to: str,
                                      body_text: str, button_text: str,
                                      sections: list[dict]) -> dict:
          return await self._post(phone_number_id, {
              "messaging_product": "whatsapp",
              "to": to,
              "type": "interactive",
              "interactive": {
                  "type": "list",
                  "body": {"text": body_text},
                  "action": {"button": button_text, "sections": sections},
              },
          })

      async def send_district_menu(self, phone_number_id: str, to: str,
                                   districts: list[str] = None, page: int = 0) -> dict:
          districts = districts or HARYANA_DISTRICTS
          total_pages = (len(districts) + DISTRICTS_PER_PAGE - 1) // DISTRICTS_PER_PAGE
          start = page * DISTRICTS_PER_PAGE
          end = start + DISTRICTS_PER_PAGE
          page_districts = districts[start:end]

          rows = [{"id": f"dist_{d.lower().replace(' ', '_')}", "title": d}
                  for d in page_districts]

          if page > 0:
              rows.append({"id": "dist_prev", "title": "⬅️  Pichla"})
          if page < total_pages - 1:
              rows.append({"id": "dist_next", "title": "Agla ➡️ "})

          sections = [{"title": "Jila chunein", "rows": rows}]
          return await self.send_interactive_list(
              phone_number_id, to,
              body_text="Apna jila chunein:",
              button_text="Jila dekhein",
              sections=sections,
          )

      async def request_location(self, phone_number_id: str, to: str, text: str) -> dict:
          return await self._post(phone_number_id, {
              "messaging_product": "whatsapp",
              "to": to,
              "type": "interactive",
              "interactive": {
                  "type": "location_request_message",
                  "body": {"text": text},
                  "action": {"name": "send_location"},
              },
          })

      async def download_media(self, media_id: str) -> bytes:
          url = f"{self.base_url}/{media_id}"
          async with httpx.AsyncClient(timeout=30.0) as client:
              resp = await client.get(url, headers=self.headers)
              media_url = resp.json().get("url", "")
              media_resp = await client.get(media_url, headers=self.headers)
              return media_resp.content

      async def mark_read(self, phone_number_id: str, message_id: str) -> dict:
          return await self._post(phone_number_id, {
              "messaging_product": "whatsapp",
              "status": "read",
              "message_id": message_id,
          })