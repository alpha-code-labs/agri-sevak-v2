"""                                                                                                                                                                                                                                                                        
  Step 5.1 — Kafka Consumer                                                                                                                                                                                                                                                  
  AIOKafkaConsumer per topic with manual commit.                                                                                                                                                                                                                             
  On failure: don't commit → message auto-retries on next poll.                                                                                                                                                                                                              
  """                                                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                                                             
import asyncio                                                                                                                                                                                                                                                             
import json                                                                                                                                                                                                                                                                
import logging
from typing import Callable, Awaitable

from aiokafka import AIOKafkaConsumer

from shared.services.config import settings

logger = logging.getLogger(__name__)


async def start_consumer(
      topic: str,
      handler: Callable[[dict], Awaitable[None]],
      group_id: str = "agent-workers",
  ):
      """
      Start a Kafka consumer loop for a single topic.
   
      Args:
          topic: Kafka topic to consume from
          handler: async function that processes each message payload (dict)
          group_id: consumer group ID (all workers in same group share partitions)
      """
      consumer = AIOKafkaConsumer(
          topic,
          bootstrap_servers=settings.kafka_bootstrap_servers,
          group_id=group_id,
          enable_auto_commit=False,       # Manual commit — only after successful processing
          auto_offset_reset="earliest",   # Start from beginning if no committed offset
          value_deserializer=lambda v: json.loads(v.decode("utf-8")),
          key_deserializer=lambda k: k.decode("utf-8") if k else None,
          max_poll_interval_ms=300000,    # 5 min — agent can take up to 120s
          session_timeout_ms=30000,
      )

      await consumer.start()
      logger.info("Kafka consumer started: topic=%s group=%s", topic, group_id)

      try:
          async for message in consumer:
              logger.info(
                  "Received message: topic=%s partition=%d offset=%d key=%s",
                  message.topic, message.partition, message.offset, message.key,
              )
              try:
                  await handler(message.value)

                  # Only commit after successful processing
                  await consumer.commit()
                  logger.info("Committed offset %d for partition %d", message.offset, message.partition)

              except Exception as e:
                  # Don't commit — message will be re-delivered on next poll
                  logger.error(
                      "Failed to process message (offset=%d, key=%s): %s",
                      message.offset, message.key, e,
                      exc_info=True,
                  )
                  # Brief pause before consuming next message to avoid tight error loops
                  await asyncio.sleep(2)

      except asyncio.CancelledError:
          logger.info("Consumer cancelled, shutting down...")
      finally:
          await consumer.stop()
          logger.info("Kafka consumer stopped: topic=%s", topic)