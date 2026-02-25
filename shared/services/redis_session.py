import json                                                                                                                                                                                                                                                                
import time                                                                                                                                                                                                                                                                
from enum import Enum                                                                                                                                                                                                                                                      
                                                                                                                                                                                                                                                                             
from pydantic import BaseModel                                                                                                                                                                                                                                             
from redis.asyncio import Redis                                                                                                                                                                                                                                            
                                                                                   

class SessionState(str, Enum):
      GREETING = "GREETING"
      DISTRICT_SELECT = "DISTRICT_SELECT"
      QUERY_COLLECT = "QUERY_COLLECT"
      QUERY_CONFIRM = "QUERY_CONFIRM"
      AGENT_PROCESSING = "AGENT_PROCESSING"


class Session(BaseModel):
      user_id: str
      session_id: str
      state: SessionState = SessionState.GREETING
      district: str | None = None
      inputs: list[dict] = []
      input_count: int = 0
      agent_memory: dict = {}
      tool_call_log: list[dict] = []
      created_at: float = 0.0
      updated_at: float = 0.0


def _key(user_id: str) -> str:
      return f"session:{user_id}"


async def get_session(redis: Redis, user_id: str) -> Session | None:
      """Load session from Redis. Returns None if not found or expired."""
      raw = await redis.get(_key(user_id))
      if not raw:
          return None
      return Session(**json.loads(raw))


async def create_session(redis: Redis, user_id: str, ttl_s: int = 300) -> Session:
      """Create a new session and save to Redis."""
      now = time.time()
      session = Session(
          user_id=user_id,
          session_id=f"{user_id}_{int(now)}",
          created_at=now,
          updated_at=now,
      )
      await redis.set(_key(user_id), session.model_dump_json(), ex=ttl_s)
      return session


async def save_session(redis: Redis, session: Session, ttl_s: int = 300) -> None:
      """Save an updated session back to Redis."""
      session.updated_at = time.time()
      await redis.set(_key(session.user_id), session.model_dump_json(), ex=ttl_s)


async def delete_session(redis: Redis, user_id: str) -> None:
      """Delete a session from Redis."""
      await redis.delete(_key(user_id))