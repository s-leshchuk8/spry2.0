Lab 8 — Batch and Streaming Payments Analytics

Repository: https://github.com/s-leshchuk8/spry2.0

Part 1: Real-time delays affect live matching, location freshness and surge prices; batch delays affect historical reporting and model training. MQTT/IoT Core handles frequent GPS updates more efficiently than one Lambda invocation per ping. A small startup could postpone Flink, SageMaker, CDC and advanced lake transformations.

Part 2: Exact duplicate webhook events are removed before choosing the latest status for each invoiceId. This prevents inflated event statistics and avoids treating multiple status changes as independent payments. The manual schema offers predictable types, while Glue Crawler infers fields and partitions. Parquet should reduce scanned bytes; measured values are supplied in the evidence, once queries are run.

Part 3: The replay producer uses receivedAt ordering and invoiceId partition keys. The consumer uses modifiedDate event-time windows, exact-duplicate filtering, a configurable grace period and failure alerts above 10%. Kafka retains events while a consumer is offline; two members of one group divide the three partitions. A zero grace period rejects more out-of-order events than two minutes.

Part 4: Local producer -> Kinesis Data Streams -> Amazon Data Firehose -> S3 -> Glue/Athena. Redpanda performs local window analytics, while the cloud path persists streamed records for Athena SQL. Actual AWS costs and results must be inserted after deployment; cloud streams should be deleted afterward.

[Before submission: replace this note with the actual query numbers, experiment outputs, cloud screenshot and cost. Do not present pending work as completed.]
