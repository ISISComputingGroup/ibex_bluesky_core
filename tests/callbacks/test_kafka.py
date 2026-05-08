import re
from unittest import mock

import pytest

from ibex_bluesky_core.callbacks._kafka import KafkaCallback, get_kafka_topic_name


def test_get_kafka_topic_name():
    with mock.patch("ibex_bluesky_core.callbacks._kafka.os.environ.get", return_value="FOO"):
        assert get_kafka_topic_name() == "FOO_bluesky"

    with mock.patch("ibex_bluesky_core.callbacks._kafka.os.environ.get", return_value="NDXBAR"):
        assert get_kafka_topic_name() == "BAR_bluesky"

    with mock.patch("ibex_bluesky_core.callbacks._kafka.os.environ.get", return_value="NDHBAZ"):
        assert get_kafka_topic_name() == "BAZ_bluesky"


def test_init_kafka_callback_with_duplicate_bootstrap_servers():
    with pytest.raises(
        ValueError,
        match=re.escape(
            "Do not specify bootstrap.servers in kafka config, use bootstrap_servers argument."
        ),
    ):
        KafkaCallback(bootstrap_servers=["abc"], kafka_config={"bootstrap.servers": "foo"}, key="")


def test_exceptions_suppressed():
    cb = KafkaCallback(bootstrap_servers=["abc"], kafka_config={}, key="")
    with mock.patch(
        "ibex_bluesky_core.callbacks._kafka.msgpack_numpy.dumps", side_effect=ValueError
    ):
        cb("start", {})
