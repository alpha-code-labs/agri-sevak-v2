import asyncio                                                                                                                                                                                                                                                             
from shared.services.gemini_pool import GeminiPool                                                                                                                                                                                                                         
from shared.services.config import settings                                                                                                                                                                                                                                
                                                                                                                                                                                                                                                                             
                                                                                                                                                                                                                                                                             
async def main():                                                                                                                                                                                                                                                          
      keys = settings.gemini_keys_list                                                                                                                                                                                                                                       
      if not keys:                                                                 
          print("SKIP — no Gemini API keys in .env")
          return

      pool = GeminiPool(api_keys=keys)

      # Test round-robin index advances
      assert pool._index == 0
      client1 = await pool._next_client()
      assert pool._index == 1 % len(keys)
      print(f"Round-robin OK — {len(keys)} key(s) loaded")

      # Test a real API call
      response = await pool.generate(
          model=settings.gemini_model_fast,
          contents="Reply with exactly: HELLO",
      )
      assert len(response) > 0
      print(f"API call OK — response: {response}")

      print("Gemini pool OK")


asyncio.run(main())