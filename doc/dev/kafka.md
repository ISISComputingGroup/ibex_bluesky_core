# Kafka

`ibex_bluesky_core` uses {py:obj}`~ibex_bluesky_core.callbacks.KafkaCallback` to send documents
emitted by the {py:obj}`~bluesky.run_engine.RunEngine` to Kafka. The Kafka callback is automatically added by
{py:obj}`ibex_bluesky_core.run_engine.get_run_engine`, and so no user configuration is required - the callback is always
enabled.

Documents are encoded using [the `msgpack` format](https://msgpack.org/index.html) - using the `msgpack-numpy` library
to also handle numpy arrays transparently.

The Kafka broker to send to can be controlled using the `IBEX_BLUESKY_CORE_KAFKA_BROKER` environment variable, if
an instrument needs to override the default. The Kafka topic will be `<INSTRUMENT>_bluesky`, where `INSTRUMENT` is the
instrument name with any NDX or NDH prefix stripped.

The message key will always be `doc` for bluesky documents; specifying a non-null key enforces message ordering.
