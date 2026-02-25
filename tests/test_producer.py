import asyncio
import json
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from webhook_receiver.producer import route_message


async def main():
      producer = AIOKafkaProducer(bootstrap_servers="localhost:9092")
      await producer.start()

      # Send a test text message
      payload = {"from": "919876543210", "type": "text", "text": {"body": "gehun me kide"}}
      await route_message(producer, "text", payload)
      await producer.stop()

      # Read it back
      consumer = AIOKafkaConsumer(
          "farmer-messages-text",
          bootstrap_servers="localhost:9092",
          group_id="test-group",
          auto_offset_reset="earliest",
      )
      await consumer.start()

      msg = await asyncio.wait_for(consumer.getone(), timeout=5)
      data = json.loads(msg.value.decode())

      assert data["from"] == "919876543210"
      assert data["text"]["body"] == "gehun me kide"
      assert msg.key == b"919876543210"

      await consumer.stop()
      print("Producer OK")


asyncio.run(main())