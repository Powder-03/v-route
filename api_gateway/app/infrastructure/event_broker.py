import json
import logging
from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)

class EventBroker:
    """
    Handles asynchronous telemetry streams to Kafka topics.
    We isolate the aiokafka implementation logic here.
    """
    def __init__(self, broker_url: str):
        self.broker_url = broker_url
        self.producer: AIOKafkaProducer = None

    async def connect(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.broker_url,
            # Implicitly serialize the dictionary into JSON utf-8 encoded payload
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await self.producer.start()
        logger.info("Kafka AIO producer successfully connected.")

    async def publish_telemetry(self, topic: str, data: dict):
        if not self.producer:
            logger.error("Kafka producer not initialized.")
            return
        
        # Fire-and-forget payload over network
        await self.producer.send(topic, value=data)

    async def close(self):
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka AIO producer stopped.")
