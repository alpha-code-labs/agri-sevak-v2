"""                                                                                                                                                                                                                                                                        
  Step 5.3 — Worker Entry Point                                                                                                                                                                                                                                              
  On startup: load ML models, init Pinecone, init Gemini pool, start Kafka consumer loop.                                                                                                                                                                                    
  """                                                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                                                             
import os                                                                                                                                                                                                                                                                  
import sys                                                                                                                                                                                                                                                                 
import asyncio                                                                                                                                                                                                                                                             
import logging
import time
from functools import partial

from redis.asyncio import Redis

from shared.services.config import settings
from agent_worker.consumer import start_consumer
from agent_worker.handler import handle_message
from agent_worker.metrics import start_metrics_server

logging.basicConfig(
      level=logging.INFO,
      format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
      stream=sys.stdout,
  )
logger = logging.getLogger("worker")


def preload_models():
      """Pre-load ML models into memory so first request is fast."""
      t0 = time.perf_counter()

      # 1. Crop classifier (MuRIL fine-tuned, ~440MB)
      logger.info("Loading crop classifier from %s...", settings.crop_classifier_model_path)
      from shared.services.crop_classifier import CropClassifier
      classifier = CropClassifier(settings.crop_classifier_model_path)
      logger.info("  Crop classifier loaded (%d labels)", len(classifier.id_to_label))

      # 2. Sentence-transformer for RAG queries (~470MB)
      logger.info("Loading sentence-transformer: %s...", settings.sentence_transformer_model)
      from sentence_transformers import SentenceTransformer
      model = SentenceTransformer(settings.sentence_transformer_model)
      # Warm up with a dummy encode
      model.encode("test")
      logger.info("  Sentence-transformer loaded")

      # 3. Pinecone connection check
      logger.info("Connecting to Pinecone index: %s...", settings.pinecone_index_name)
      from pinecone import Pinecone
      pc = Pinecone(api_key=settings.pinecone_api_key)
      index = pc.Index(settings.pinecone_index_name)
      stats = index.describe_index_stats()
      logger.info("  Pinecone connected: %d vectors", stats.get("total_vector_count", 0))

      # 4. Gemini pool check
      logger.info("Verifying Gemini API keys...")
      keys = settings.gemini_keys_list
      if keys:
          logger.info("  %d Gemini API key(s) available", len(keys))
      else:
          logger.warning("  No Gemini API keys configured!")

      elapsed = time.perf_counter() - t0
      logger.info("All models pre-loaded in %.1fs", elapsed)


async def main():
      # Determine which topic to consume (set via env var, default to text)
      topic = os.environ.get("KAFKA_TOPIC", settings.kafka_topic_text)
      logger.info("Worker starting for topic: %s", topic)

      # Start Prometheus metrics server on port 9090
      start_metrics_server(port=9090)

      # Pre-load ML models (synchronous, before starting consumer)
      preload_models()

      # Connect to Redis
      redis = Redis.from_url(settings.redis_url, decode_responses=True)
      try:
          await redis.ping()
          logger.info("Redis connected: %s", settings.redis_url)
      except Exception as e:
          logger.error("Redis connection failed: %s", e)
          sys.exit(1)

      # Create handler with Redis injected
      async def handler(payload: dict):
          await handle_message(payload, redis=redis)

      # Start Kafka consumer loop (runs forever)
      logger.info("Starting Kafka consumer loop...")
      await start_consumer(topic=topic, handler=handler)


if __name__ == "__main__":
      asyncio.run(main())