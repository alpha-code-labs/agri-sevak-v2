from contextlib import asynccontextmanager                                                                                                                                                                                                                                 
                                                                                                                                                                                                                                                                             
from fastapi import FastAPI, Request, Response                                                                                                                                                                                                                             
from aiokafka import AIOKafkaProducer                                            
from redis.asyncio import Redis

from shared.services.config import settings
from shared.services.dedup import is_first_seen
from webhook_receiver.security import verify_hmac_signature
from webhook_receiver.producer import route_message
from webhook_receiver.metrics import instrumentator


producer: AIOKafkaProducer | None = None
redis: Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
      global producer, redis
      producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
      await producer.start()
      redis = Redis.from_url(settings.redis_url)
      yield
      await producer.stop()
      await redis.aclose()


app = FastAPI(lifespan=lifespan)
instrumentator.instrument(app).expose(app, endpoint="/metrics")


@app.get("/webhook")
async def verify(request: Request):
      """Meta webhook verification challenge."""
      params = request.query_params
      if params.get("hub.verify_token") == settings.verify_token:
          return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
      return Response(content="Forbidden", status_code=403)


@app.post("/webhook")
async def handle_webhook(request: Request):
      """Receive webhook, verify HMAC, dedup, route to Kafka."""
      raw_body = await request.body()
      signature = request.headers.get("x-hub-signature-256")

      if not verify_hmac_signature(raw_body, signature, settings.app_secret):
          return Response(content="Invalid signature", status_code=401)

      import json
      body = json.loads(raw_body)

      for entry in body.get("entry", []):
          for change in entry.get("changes", []):
              value = change.get("value", {})
              messages = value.get("messages", [])
              phone_number_id = value.get("metadata", {}).get("phone_number_id", "")

              for msg in messages:
                  msg_id = msg.get("id", "")
                  if not await is_first_seen(redis, msg_id, settings.dedup_ttl_seconds):
                      continue

                  msg["phone_number_id"] = phone_number_id
                  msg_type = msg.get("type", "text")
                  await route_message(producer, msg_type, msg)

      return Response(content="EVENT_RECEIVED", status_code=200)


@app.get("/health")
async def health():
      return {"status": "ok"}