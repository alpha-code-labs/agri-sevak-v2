import asyncio
from redis.asyncio import Redis
from shared.services.redis_session import (
      get_session, create_session, save_session, delete_session, SessionState
  )


async def main():
      redis = Redis.from_url("redis://localhost:6379/0")

      user = "919876543210"

      # Create session
      session = await create_session(redis, user)
      assert session.state == SessionState.GREETING
      assert session.user_id == user
      assert session.inputs == []
      print("Create OK")

      # Read session back
      loaded = await get_session(redis, user)
      assert loaded is not None
      assert loaded.user_id == user
      assert loaded.state == SessionState.GREETING
      print("Read OK")

      # Update session
      loaded.state = SessionState.DISTRICT_SELECT
      loaded.district = "Karnal"
      loaded.inputs.append({"type": "text", "data": "gehun me kide"})
      loaded.input_count = 1
      await save_session(redis, loaded)

      reloaded = await get_session(redis, user)
      assert reloaded.state == SessionState.DISTRICT_SELECT
      assert reloaded.district == "Karnal"
      assert len(reloaded.inputs) == 1
      assert reloaded.input_count == 1
      print("Update OK")

      # Delete session
      await delete_session(redis, user)
      gone = await get_session(redis, user)
      assert gone is None
      print("Delete OK")

      await redis.aclose()
      print("Redis session OK")


asyncio.run(main())