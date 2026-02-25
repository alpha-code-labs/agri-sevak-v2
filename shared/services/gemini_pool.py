import asyncio                                                                                                                                                                                                                                                             
from google import genai                                                                                                                                                                                                                                                   
from shared.services.config import settings                                                                                                                                                                                                                                
                                                                                   

class GeminiPool:
      def __init__(self, api_keys: list[str] = None):
          keys = api_keys or settings.gemini_keys_list
          if not keys:
              raise ValueError("No Gemini API keys provided")
          self._clients = [genai.Client(api_key=k) for k in keys]
          self._index = 0
          self._lock = asyncio.Lock()

      async def _next_client(self) -> genai.Client:
          async with self._lock:
              client = self._clients[self._index]
              self._index = (self._index + 1) % len(self._clients)
              return client

      async def generate(self, model: str, contents: str, temperature: float = 0) -> str:
          """Text-only generation with round-robin and 429 failover."""
          for attempt in range(len(self._clients)):
              client = await self._next_client()
              try:
                  resp = await asyncio.to_thread(
                      client.models.generate_content,
                      model=model,
                      contents=contents,
                      config={"temperature": temperature},
                  )
                  return (resp.text or "").strip()
              except Exception as e:
                  if "429" in str(e) and attempt < len(self._clients) - 1:
                      continue
                  raise

      async def generate_multimodal(self, model: str, image_bytes: bytes,
                                    text_prompt: str, temperature: float = 0) -> str:
          """Multimodal generation (image + text) with round-robin and 429 failover."""
          from google.genai.types import Part, Content

          image_part = Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
          text_part = Part.from_text(text_prompt)
          content = Content(parts=[image_part, text_part])

          for attempt in range(len(self._clients)):
              client = await self._next_client()
              try:
                  resp = await asyncio.to_thread(
                      client.models.generate_content,
                      model=model,
                      contents=content,
                      config={"temperature": temperature},
                  )
                  return (resp.text or "").strip()
              except Exception as e:
                  if "429" in str(e) and attempt < len(self._clients) - 1:
                      continue
                  raise
