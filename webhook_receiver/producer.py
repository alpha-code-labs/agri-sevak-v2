import json                                                                                                                                                                                                                                                                
from aiokafka import AIOKafkaProducer                                                                                                                                                                                                                                      
from shared.services.config import settings                                                                                                                                                                                                                                
                                                                                   

TOPIC_MAP = {
      "text": settings.kafka_topic_text,
      "interactive": settings.kafka_topic_text,
      "image": settings.kafka_topic_text,
      "audio": settings.kafka_topic_text,
  }


async def route_message(producer: AIOKafkaProducer, message_type: str, payload: dict):
      """Route a WhatsApp message to the correct Kafka topic by type."""
      topic = TOPIC_MAP.get(message_type, settings.kafka_topic_text)
      key = payload["from"].encode()
      value = json.dumps(payload).encode()
      await producer.send_and_wait(topic, value=value, key=key)