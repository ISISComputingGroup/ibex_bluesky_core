# Kafka

`ibex_bluesky_core` uses [the `bluesky-kafka` library](https://github.com/bluesky/bluesky-kafka) to send documents
emitted by the `RunEngine` to kafka. The kafka callback is automatically added by
{py:obj}`ibex_bluesky_core.run_engine.get_run_engine`, and so no user configuration is required - the callback is always
enabled.

Documents are encoded using [the `msgpack` format](https://msgpack.org/index.html) - using the `msgpack-numpy` library
to also handle numpy arrays transparently.

The kafka broker to send to can be controlled using the `IBEX_BLUESKY_CORE_KAFKA_BROKER` environment variable, if
an instrument needs to override the default. The kafka topic will be `<INSTRUMENT>_bluesky`, where `INSTRUMENT` is the
instrument name with any NDX or NDH prefix stripped.

The message key will always be `doc` for bluesky documents; specifying a non-null key enforces message ordering.
