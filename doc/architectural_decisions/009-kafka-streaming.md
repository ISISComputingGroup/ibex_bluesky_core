# 9. Kafka streaming

## Status

Current

## Context

Many facilities stream bluesky documents to an event-bus for consumption by out-of-process listeners.
Event buses used for this purpose at other facilities include ZeroMQ, RabbitMQ, Kafka, Redis, NATS, and
others.

The capability this provides is that callbacks can be run in different processes or on other computers,
without holding up or interfering with the local `RunEngine`. Other groups at ISIS have expressed some
interest in being able to subscribe to bluesky documents.

## Decision

- We will stream our messages to Kafka, as opposed to some other message bus. This is because we already
have Kafka infrastructure available for other purposes (e.g. event data & sample-environment data).
- At the time of writing, we will not **depend** on Kafka for anything critical. This is because the 
central Kafka instance is not currently considered "reliable" in an experiment controls context. However,
streaming the documents will allow testing to be done. Kafka will eventually be deployed in a "reliable"
way accessible to each instrument.
- We will encode messages from bluesky using `msgpack` (with the `msgpack-numpy` extension), because:
  - It is the default encoder used by the upstream `bluesky-kafka` integration (though we are not using
that integration directly, as it has been soft-deprecated upstream)
  - It is a schema-less encoder, meaning we do not have to write/maintain fixed schemas for all the
documents allowed by `event-model`
  - It has reasonable performance in terms of encoding speed and message size
  - `msgpack` is very widely supported in a range of programming languages
- Kafka brokers will be configurable via an environment variable, `IBEX_BLUESKY_CORE_KAFKA_BROKER`

```{note}
Wherever Kafka is mentioned above, the actual implementation may be a Kafka-like (e.g. RedPanda).
```

### Alternatives considered

Encoding bluesky documents into JSON and then wrapping them in the
[`json_json.fbs` flatbuffers schema](https://github.com/ess-dmsc/streaming-data-types/blob/58793c3dfa060f60b4a933bc085f831744e43f17/schemas/json_json.fbs)
was considered.

We chose `msgpack` instead of json strings + flatbuffers because:
- It is more standard in the bluesky community
- Bluesky events will be streamed to a dedicated topic, which is unlikely to be confused with data
using any other schema.

Performance/storage impacts are unlikely to be noticeable for bluesky documents, but nonetheless:
- `msgpack`-encoded documents are 30-40% smaller than `json` + flatbuffers
for a typical bluesky document
- `msgpack`-encoding messages is ~5x faster than `json` + flatbuffers encoding
for a typical bluesky document.

## Justification & Consequences

We will stream bluesky documents to Kafka, encoded using `msgpack-numpy`.

At the time of writing this is purely to enable testing, and will not be used for "production" workflows.
