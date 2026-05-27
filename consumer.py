"""
consumer.py - Kafka Consumer Service for Project AURA

This module implements a long-running Kafka consumer that:

    1. Subscribes to the ``aura-analysis`` topic.
    2. Deserialises incoming JSON messages.
    3. Passes the extracted text through ``ai_service.analyze_personality()``.
    4. POSTs the enriched result to the Project AURA REST API at
       ``/internal/store_result``.

The service supports graceful shutdown via ``SIGINT`` / ``SIGTERM`` and
includes a configurable retry loop that waits for Kafka broker availability
before entering the main consumption loop.

Environment variables:
    KAFKA_BOOTSTRAP_SERVERS  – Kafka broker address (default: localhost:9092)
    API_URL                  – Base URL of the AURA REST API
                               (default: http://localhost:8000)

Dependencies:
    - confluent-kafka
    - requests
    - ai_service (local module)
"""

import json
import logging
import os
import signal
import sys
import time
from typing import Any, Optional

import requests
from confluent_kafka import Consumer, KafkaError, KafkaException

from ai_service import analyze_personality

# ---------------------------------------------------------------------------
# Module-level constants & logger
# ---------------------------------------------------------------------------
KAFKA_TOPIC: str = "aura-analysis"
KAFKA_BOOTSTRAP: str = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
API_URL: str = os.environ.get("API_URL", "http://localhost:8000")
CONSUMER_GROUP: str = "aura-consumer-group"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graceful shutdown flag
# ---------------------------------------------------------------------------
_shutdown_requested: bool = False


def _signal_handler(signum: int, frame: Any) -> None:
    """Handle SIGINT / SIGTERM by setting the shutdown flag.

    Args:
        signum: The signal number received.
        frame: The current stack frame (unused).
    """
    global _shutdown_requested
    sig_name = signal.Signals(signum).name if hasattr(signal, "Signals") else str(signum)
    print(f"\n[INFO] Received {sig_name} — initiating graceful shutdown…")
    logger.info("Received signal %s — shutting down.", sig_name)
    _shutdown_requested = True


# Register signal handlers (SIGTERM may not be available on all platforms)
signal.signal(signal.SIGINT, _signal_handler)
try:
    signal.signal(signal.SIGTERM, _signal_handler)
except (OSError, AttributeError):
    # SIGTERM is not supported on some Windows configurations
    pass


# ---------------------------------------------------------------------------
# Consumer factory
# ---------------------------------------------------------------------------

def _create_consumer() -> Consumer:
    """Create and return a configured ``confluent_kafka.Consumer``.

    Returns:
        A ``Consumer`` instance ready for topic subscription.
    """
    config: dict[str, Any] = {
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "group.id": CONSUMER_GROUP,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    }
    return Consumer(config)


# ---------------------------------------------------------------------------
# Result forwarding
# ---------------------------------------------------------------------------

def _post_result(result: dict[str, Any]) -> bool:
    """POST the analysis result to the REST API's internal endpoint.

    Args:
        result: The enriched analysis result dictionary.

    Returns:
        ``True`` if the POST succeeded (2xx), ``False`` otherwise.
    """
    url: str = f"{API_URL}/internal/store_result"
    try:
        response = requests.post(url, json=result, timeout=10)
        if response.ok:
            logger.info(
                "Result stored via API — request_id=%s, status=%d",
                result.get("request_id", "unknown"),
                response.status_code,
            )
            print(
                f"[OK] Result stored for request_id={result.get('request_id', 'unknown')} "
                f"(HTTP {response.status_code})"
            )
            return True
        else:
            logger.warning(
                "API returned non-OK status %d for request_id=%s: %s",
                response.status_code,
                result.get("request_id", "unknown"),
                response.text[:200],
            )
            print(
                f"[WARN] API returned HTTP {response.status_code} for "
                f"request_id={result.get('request_id', 'unknown')}"
            )
            return False
    except requests.ConnectionError as exc:
        logger.error("Connection error while posting result: %s", exc)
        print(f"[ERROR] Could not connect to API at {url}: {exc}")
        return False
    except requests.Timeout:
        logger.error("Timeout while posting result to %s", url)
        print(f"[ERROR] Request timed out posting to {url}")
        return False
    except requests.RequestException as exc:
        logger.error("Unexpected request error: %s", exc)
        print(f"[ERROR] Failed to post result: {exc}")
        return False


# ---------------------------------------------------------------------------
# Main consumer loop
# ---------------------------------------------------------------------------

def run_consumer() -> None:
    """Subscribe to the Kafka topic and process messages in a loop.

    Each incoming message is expected to be a JSON object with at least a
    ``text`` field.  The text is analysed via ``analyze_personality``, and
    the enriched result is forwarded to the REST API.

    The loop runs until ``_shutdown_requested`` is set (via signal handler
    or ``KeyboardInterrupt``).
    """
    global _shutdown_requested

    consumer: Consumer = _create_consumer()
    consumer.subscribe([KAFKA_TOPIC])

    # --- Startup banner ---------------------------------------------------
    print("=" * 60)
    print("  PROJECT AURA — Kafka Consumer Service")
    print(f"  Topic      : {KAFKA_TOPIC}")
    print(f"  Group      : {CONSUMER_GROUP}")
    print(f"  Brokers    : {KAFKA_BOOTSTRAP}")
    print(f"  API Target : {API_URL}")
    print("=" * 60)
    print("[INFO] Listening for messages… (Ctrl+C to stop)\n")
    logger.info("Consumer started — topic=%s, group=%s", KAFKA_TOPIC, CONSUMER_GROUP)

    try:
        while not _shutdown_requested:
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                # No message within the timeout window
                continue

            if msg.error():
                error: KafkaError = msg.error()
                if error.code() == KafkaError._PARTITION_EOF:
                    # End of partition — not a real error
                    logger.debug(
                        "Reached end of partition %s [%d] @ offset %d",
                        msg.topic(),
                        msg.partition(),
                        msg.offset(),
                    )
                    continue
                else:
                    logger.error("Consumer error: %s", error)
                    print(f"[ERROR] Consumer error: {error}")
                    continue

            # --- Process message -----------------------------------------
            try:
                raw_value: Optional[bytes] = msg.value()
                if raw_value is None:
                    logger.warning("Received message with empty value — skipping.")
                    continue

                payload: dict[str, Any] = json.loads(raw_value.decode("utf-8"))
                text: str = payload.get("text", "")
                request_id: str = payload.get("request_id", "unknown")
                user_id: str = payload.get("user_id", "anonymous")

                if not text.strip():
                    logger.warning(
                        "Empty text in message request_id=%s — skipping.", request_id
                    )
                    print(f"[WARN] Empty text for request_id={request_id} — skipped.")
                    continue

                print(f"[INFO] Processing request_id={request_id} (user={user_id})…")
                logger.info("Processing request_id=%s", request_id)

                # Run AI analysis
                result: dict[str, Any] = analyze_personality(text)

                # Enrich result with request metadata
                result["request_id"] = request_id
                result["user_id"] = user_id

                # Forward to API
                _post_result(result)

            except json.JSONDecodeError as exc:
                logger.error("Invalid JSON in message: %s", exc)
                print(f"[ERROR] Could not decode message JSON: {exc}")
            except Exception as exc:
                logger.exception("Unexpected error processing message: %s", exc)
                print(f"[ERROR] Unexpected error: {exc}")

    except KeyboardInterrupt:
        print("\n[INFO] KeyboardInterrupt received — shutting down…")
        logger.info("KeyboardInterrupt — shutting down consumer.")
    finally:
        print("[INFO] Closing Kafka consumer…")
        consumer.close()
        logger.info("Consumer closed.")
        print("[INFO] Consumer shutdown complete.")


# ---------------------------------------------------------------------------
# Kafka readiness check with retry
# ---------------------------------------------------------------------------

def _wait_for_kafka(max_retries: int = 30, retry_interval: float = 5.0) -> bool:
    """Block until Kafka brokers are reachable or retries are exhausted.

    The function creates a temporary consumer, attempts to list topics, and
    retries on failure.

    Args:
        max_retries: Maximum number of connection attempts.
        retry_interval: Seconds to wait between retries.

    Returns:
        ``True`` if Kafka became available, ``False`` if retries were
        exhausted.
    """
    for attempt in range(1, max_retries + 1):
        try:
            print(
                f"[INFO] Waiting for Kafka to be available… "
                f"(attempt {attempt}/{max_retries})"
            )
            logger.info("Kafka readiness check attempt %d/%d", attempt, max_retries)

            temp_consumer = Consumer(
                {
                    "bootstrap.servers": KAFKA_BOOTSTRAP,
                    "group.id": f"{CONSUMER_GROUP}-healthcheck",
                    "session.timeout.ms": 6000,
                }
            )
            # list_topics will raise if the broker is unreachable
            temp_consumer.list_topics(timeout=5)
            temp_consumer.close()

            print("[OK] Kafka is available!")
            logger.info("Kafka is reachable at %s", KAFKA_BOOTSTRAP)
            return True

        except KafkaException as exc:
            logger.warning("Kafka not ready (attempt %d): %s", attempt, exc)
            print(f"[WARN] Kafka not ready: {exc}")
        except Exception as exc:
            logger.warning("Unexpected error during readiness check: %s", exc)
            print(f"[WARN] Readiness check error: {exc}")

        if attempt < max_retries:
            time.sleep(retry_interval)

    print("[ERROR] Kafka did not become available within the retry window.")
    logger.error("Kafka readiness check exhausted after %d attempts.", max_retries)
    return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Basic logging configuration for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("=" * 60)
    print("  PROJECT AURA — Consumer Service Startup")
    print(f"  Kafka Brokers : {KAFKA_BOOTSTRAP}")
    print(f"  API URL       : {API_URL}")
    print(f"  Consumer Group: {CONSUMER_GROUP}")
    print("=" * 60)

    if not _wait_for_kafka():
        print("[FATAL] Exiting — Kafka is unreachable.")
        sys.exit(1)

    run_consumer()
