from redis.asyncio import Redis                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                             
                                                                                                                                                                                                                                                                             
async def is_first_seen(redis: Redis, message_id: str, ttl_s: int = 3600) -> bool:
      """Returns True if this message_id has never been seen before. False if duplicate."""
      key = f"seen:wa:msg:{message_id}"
      ok = await redis.set(key, "1", nx=True, ex=ttl_s)
      return bool(ok)