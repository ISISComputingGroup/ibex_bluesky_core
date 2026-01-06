import logging
import os
import socket
from typing import Any

import msgpack_numpy
from bluesky.callbacks import CallbackBase
from confluent_kafka import Producer

logger = logging.getLogger(__name__)


DEFAULT_KAFKA_BROKER = "livedata.isis.cclrc.ac.uk:31092"


def get_kafka_topic_name() -> str:
    """Get the name of the bluesky Kafka topic for this machine."""
    computer_name = os.environ.get("COMPUTERNAME", socket.gethostname()).upper()
    computer_name = computer_name.upper()
    if computer_name.startswith(("NDX", "NDH")):
        name = computer_name[3:]
    else:
        name = computer_name

    return f"{name}_bluesky"


class KafkaCallback(CallbackBase):
    """Forward all bluesky documents to Kafka.

    Documents are sent to Kafka encoded using the MsgPack format with
    the ``msgpack_numpy`` extension to allow efficiently encoding arrays.

    .. note::

        This callback is automatically configured by
        :py:obj:`ibex_bluesky_core.run_engine.get_run_engine`, and does not need
        to be configured manually.
    """

    def __init__(
        self,
        *,
        bootstrap_servers: list[str] | None = None,
        topic: str | None = None,
        key: str,
        kafka_config: dict[str, Any],
    ) -> None:
        super().__init__()

        self._topic = topic or get_kafka_topic_name()
        self._key = msgpack_numpy.dumps(key)

        if "bootstrap.servers" in kafka_config:
            raise ValueError(
                "Do not specify bootstrap.servers in kafka config, use bootstrap_servers argument."
            )

        if bootstrap_servers is None:
            bootstrap_servers = [
                os.environ.get("IBEX_BLUESKY_CORE_KAFKA_BROKER", DEFAULT_KAFKA_BROKER)
            ]

        kafka_config["bootstrap.servers"] = ",".join(bootstrap_servers)

        self._producer = Producer(kafka_config)

    def __call__(
        self, name: str, doc: dict[str, Any], validate: bool = False
    ) -> tuple[str, dict[str, Any]]:
        try:
            data = msgpack_numpy.dumps([name, doc])
            self._producer.produce(topic=self._topic, key=self._key, value=data)
        except Exception:
            # If we can't produce to kafka, log and carry on. We don't want
            # kafka failures to kill a scan - kafka is currently considered
            # 'non-critical'.
            logger.exception("Failed to publish Kafka message")

        return name, doc
