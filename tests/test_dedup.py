import asyncio
from redis.asyncio import Redis
from shared.services.dedup import is_first_seen


async def main():
      redis = Redis.from_url("redis://localhost:6379/0")

      # First time — should be True
      result1 = await is_first_seen(redis, "test_msg_001")
      assert result1 == True, f"Expected True, got {result1}"

      # Second time same ID — should be False (duplicate)
      result2 = await is_first_seen(redis, "test_msg_001")
      assert result2 == False, f"Expected False, got {result2}"

      # Clean up
      await redis.delete("seen:wa:msg:test_msg_001")
      await redis.aclose()

      print("Dedup OK")
      
asyncio.run(main())