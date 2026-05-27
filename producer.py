"""
producer.py - Kafka Producer for Project AURA

This module provides a Kafka producer that publishes aura analysis requests
to the ``aura-analysis`` topic.  Each request is a JSON payload containing
a unique request ID, user ID, the raw text to analyse, and a UTC timestamp.

The producer is backed by ``confluent_kafka.Producer`` and exposes both a
class-based interface (``AuraProducer``) and a convenience factory function
(``create_producer``).

Dependencies:
    - confluent-kafka
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from confluent_kafka import Producer

# ---------------------------------------------------------------------------
# Module-level constants & logger
# ---------------------------------------------------------------------------
KAFKA_TOPIC: str = "aura-analysis"

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AuraProducer class
# ---------------------------------------------------------------------------

class AuraProducer:
    """High-level Kafka producer for submitting aura-analysis requests.

    Attributes:
        producer: The underlying ``confluent_kafka.Producer`` instance.
        topic: The Kafka topic to publish messages to.
    """

    def __init__(self, bootstrap_servers: str = "localhost:9092") -> None:
        """Initialise the producer with the given Kafka bootstrap servers.

        Args:
            bootstrap_servers: Comma-separated list of Kafka broker addresses.
                Defaults to ``"localhost:9092"``.
        """
        self._config: dict[str, str] = {
            "bootstrap.servers": bootstrap_servers,
            "client.id": "aura-producer",
        }
        self.producer: Producer = Producer(self._config)
        self.topic: str = KAFKA_TOPIC
        logger.info(
            "AuraProducer initialised (brokers=%s, topic=%s)",
            bootstrap_servers,
            self.topic,
        )

    # ------------------------------------------------------------------
    # Delivery callback
    # ------------------------------------------------------------------

    @staticmethod
    def delivery_report(err: Optional[object], msg: object) -> None:
        """Callback invoked by the producer on message delivery (or failure).

        Args:
            err: An error object if delivery failed, otherwise ``None``.
            msg: The ``confluent_kafka.Message`` that was delivered/failed.
        """
        if err is not None:
            logger.error("Message delivery failed: %s", err)
            print(f"[ERROR] Message delivery failed: {err}")
        else:
            logger.info(
                "Message delivered to %s [partition %s] @ offset %s",
                msg.topic(),
                msg.partition(),
                msg.offset(),
            )
            print(
                f"[OK] Message delivered to {msg.topic()} "
                f"[partition {msg.partition()}] @ offset {msg.offset()}"
            )

    # ------------------------------------------------------------------
    # Send event
    # ------------------------------------------------------------------

    def send_event(self, text: str, user_id: str = "anonymous") -> str:
        """Serialise and publish an aura-analysis request to Kafka.

        The payload is a JSON object with the following shape::

            {
                "request_id": "<uuid4>",
                "user_id": "<user_id>",
                "text": "<text>",
                "timestamp": "<ISO-8601 UTC>"
            }

        Args:
            text: The raw text to be analysed.
            user_id: An optional user identifier. Defaults to ``"anonymous"``.

        Returns:
            The generated ``request_id`` (UUID4 string) for this event.

        Raises:
            BufferError: If the internal producer queue is full.
            KafkaException: On other Kafka-level errors.
        """
        request_id: str = str(uuid4())
        payload: dict[str, str] = {
            "request_id": request_id,
            "user_id": user_id,
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        serialised: str = json.dumps(payload)

        self.producer.produce(
            topic=self.topic,
            value=serialised.encode("utf-8"),
            callback=self.delivery_report,
        )

        # Block until the message is delivered (or fails)
        self.producer.flush()

        logger.info(
            "Event sent — request_id=%s, user_id=%s, topic=%s",
            request_id,
            user_id,
            self.topic,
        )
        return request_id

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Flush any outstanding messages and release resources."""
        logger.info("Flushing and closing AuraProducer…")
        self.producer.flush()
        print("[INFO] AuraProducer closed.")


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

def create_producer(bootstrap_servers: str = "localhost:9092") -> AuraProducer:
    """Factory function to create and return an ``AuraProducer`` instance.

    Args:
        bootstrap_servers: Comma-separated list of Kafka broker addresses.
            Defaults to ``"localhost:9092"``.

    Returns:
        A ready-to-use ``AuraProducer``.
    """
    return AuraProducer(bootstrap_servers=bootstrap_servers)
