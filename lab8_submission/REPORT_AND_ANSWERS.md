# Lab 8 — Batch and streaming payments analytics

**Status:** Implementation and written answers prepared; AWS query results, four streaming experiments and cloud pipeline screenshot require actual execution. No invented metrics.

## Part 1 — Uklon architecture questions

**Real-time 10 minutes late:** matching and surge prices use stale GPS and demand. Drivers may appear in the wrong location, ETAs become unreliable, alerts arrive too late, and rides can be assigned inefficiently. **Batch one day late:** historical reports, model training and management dashboards lag, but a currently active ride can still be matched if the real-time path works.

**Why not Lambda for GPS?** GPS sends high-frequency, continuous traffic. MQTT connections to IoT Core avoid one HTTP/Lambda invocation per ping and allow persistent sessions; sending all pings through Lambda adds invocation overhead, expense and operational complexity. Lambda can still process selected events downstream.

**What would a startup omit?** Initially skip SageMaker training, separate Flink surge engine, elaborate lake ETL, complex CDC and multi-service splitting. Start with a small API, relational DB, object storage and scheduled SQL. Lose sophisticated live surge/driver-state scaling, independent service scaling, historical analytics efficiency and automated ML.

## Part 2 — Athena, Glue, Parquet

Run `sql/athena.sql` **statement by statement**, replacing `YOUR_BUCKET` with the personal S3 bucket in us-east-1. Copy public source first:

```bash
aws s3 sync s3://ucu-ooad-lab8-payments/payments/ s3://YOUR_BUCKET/payments/ --region us-east-1
```

The existing screenshot shows Glue table `lab_db.payments`, a JSON classification and `dt` partition; it does not establish query results or Athena statistics. Keep crawler table `payments` and manually created `payment_events` separate.

**Why DISTINCT before ROW_NUMBER?** Webhook delivery is at least once, so byte-equivalent records may repeat. First remove identical event rows, then order distinct events within each invoice and select the latest. Otherwise duplicates occupy ranks and inflate raw event statistics; if you filter rank=1 correctly, duplicates alone normally do **not** change the final one-row-per-invoice result, but waste processing and can complicate ties.

**Without deduplication:** counting webhook rows as payments inflates counts, failure shares may be biased toward repeated failures, and turnover may double-count payment status transitions. The correct final payment state comes from the most recent `modifiedDate`, not merely the last file row.

**Glue Crawler vs manual schema:** Screenshot shows `amount` and `ccy` as `int`, dates as `string`, `failureReason` as `string`, and `dt` as a `string` partition. A manual schema can deliberately use `bigint` for money and explicit timestamp parsing, giving control over type widths and business semantics. Optional `failureReason` is nullable; records without it yield NULL. Crawler discovers schema from samples, which can miss rare optional fields or infer undesirable types. Athena's `from_iso8601_timestamp` parses the ISO dates.

**JSON vs Parquet:** Columnar Parquet can read only needed columns and compress values; JSON scans larger textual records. Compare *actual* Athena `Data scanned` and `Run time` for Q3–Q5 with the same SQL logic. The ratio `JSON_bytes / Parquet_bytes` estimates the scan-based price reduction for the same pricing tier (minimum billing and other costs may apply). Time speedup is `JSON_seconds / Parquet_seconds`, which need not equal cost reduction.

**Scale results — enter actual query outputs:**

| Metric | Observed value |
|---|---|
| Raw events | NOT RUN |
| Distinct events | NOT RUN |
| Unique invoiceId | NOT RUN |
| Exact duplicate rows | NOT RUN |
| Late >60s | NOT RUN |
| Late >1 hour, % | NOT RUN |

**Query results:** Q3 turnover by merchant/currency — NOT RUN. Q4 failure rate by payment method/device — NOT RUN. Q5 peak hour UTC — NOT RUN. Q6 late event counts — NOT RUN.

| Query | JSON scanned | JSON runtime | Parquet scanned | Parquet runtime | Scan reduction |
|---|---|---|---|---|---|
| Q3 turnover | pending | pending | pending | pending | pending |
| Q4 failures | pending | pending | pending | pending | pending |
| Q5 hours | pending | pending | pending | pending | pending |

**Note:** Assignment says about one million payments, three million events, ~1% duplicate events and ~2% delayed 1–10 minutes; these are dataset descriptions, **not measured answers**. A >1h late count must be computed and should not be guessed.

## Part 3 — Redpanda experiments

The original repository's `producer.py` generates random payments rather than replaying the provided dataset; its `consumer.py` prints running total and success count but does not deduplicate, window by event time or alert. The replacement scripts in `streaming/` implement those lab requirements. They are separate files, so existing code is preserved.

1. Start the existing Docker Compose stack and confirm `payments` has 3 partitions in Console (`localhost:8080`). Download a source day:

```bash
aws s3 cp s3://ucu-ooad-lab8-payments/payments/dt=2026-10-01/events.jsonl ./events.jsonl --region us-east-1
python -m pip install -r requirements.txt
python streaming/consumer_windows.py --group lab8-test1 --grace 120 | tee experiment1.log
# In another terminal:
python streaming/producer_replay.py events.jsonl --rate 20
```

2. **Consumer stop/restart:** interrupt the consumer, leave the producer running, restart with the **same group ID**; inspect that committed offsets resume. Note: auto-commit is at-least-once, so a small number of events can be reprocessed after interruption; the demo's in-memory dedup state resets. For durable exactly-once semantics, persist state and offsets transactionally or use Flink.
3. **Two consumers:** run two copies with the same `--group` (ideally before replay). In Console check partition assignment: three partitions are shared between two members, typically 2+1, not guaranteed which member gets which. Save logs and Console screenshot.
4. **30% failure experiment:** use a **fresh topic or fresh consumer group** and `python streaming/producer_replay.py events.jsonl --failure-probability 0.30`. This changes terminal status events; alert prints when the measured window failure rate exceeds 10%. A random 30% target does not guarantee every small window crosses 10%.
5. **Zero late wait:** replay the identical original file into a fresh topic/group and compare `--grace 120` against `--grace 0`. Record `rejected_late` and window rates from both logs. With no grace, windows close earlier and more out-of-order events are rejected, potentially altering denominators and rates. **Caveat:** the example uses event-time max watermark, not wall-clock closure, and it prints remaining windows at end of replay. This is suitable for a lab demonstration but not a fully production-grade stateful stream processor.

| Experiment | Evidence / observed result |
|---|---|
| Consumer restarted; no permanent message loss | pending logs + offsets |
| Two consumers; partition assignments | pending Console screenshot |
| 30% failures; alerts | pending output |
| Grace 120 vs 0; rejected late and rates | pending two outputs |

**Why bound state?** The set of deduplication keys and window aggregates grows as events arrive. A production system stores state in Flink/RocksDB or Redis with a TTL covering maximum relevant lateness and retries; old windows and keys expire. A TTL that is too short can permit duplicates again.

**Important limitation:** Our example deduplicates identical JSON records and uses the latest terminal state **within each minute**, not across all minutes. A payment whose status changes in another minute can be counted in multiple windows; this is a per-window event-time metric, not an exact final-payment cohort metric. Define this distinction when presenting results.

## Part 4 — Kinesis to S3 to Athena

See `cloud/architecture.mmd`, `cloud/kinesis_producer.py` and `cloud/athena_stream.sql`. Use **AWS us-east-1**. Create a Kinesis Data Stream, an Amazon Data Firehose delivery stream **with Kinesis as source**, and S3 destination `s3://YOUR_BUCKET/streamed/`. Set delivery format to raw JSON (no JSON-to-Parquet conversion), configure buffering, and ensure Firehose IAM role can read Kinesis and write S3. Kinesis and Firehose are **separate resources**; neither is created by the supplied Python producer.

```bash
python cloud/kinesis_producer.py events.jsonl --stream YOUR_KINESIS_STREAM --region us-east-1 --rate 20
```

After Firehose writes objects, execute `cloud/athena_stream.sql` with the correct bucket. Capture the SQL editor, returned counts and S3 table location in one screenshot. Verify the objects contain newline-delimited JSON: the producer adds `\n` to each Kinesis record, but Firehose buffering/transform settings must preserve valid line boundaries.

**Comparison:** Local Redpanda stores an ordered, partitioned Kafka-compatible log and Python consumers compute windows locally. Cloud Kinesis is a managed streaming ingestion service; Firehose batches and delivers data into S3, while Athena queries persisted data afterward. This cloud path demonstrates streaming ingestion plus batch SQL, **not** real-time minute-window alerts unless a separate stream processor is added. Kinesis and Firehose are usage-billed; local Redpanda has no AWS charge but consumes laptop resources.

**Actual AWS cost:** NOT MEASURED. Record the region, running duration, provisioned/on-demand stream settings, amount ingested, Firehose delivery volume and Athena scanned bytes. Consult billing/cost explorer; a $0.00 bill may reflect free tier/credits rather than zero resource usage.

**Cleanup after evidence:** delete the Firehose delivery stream, then Kinesis Data Stream; optionally remove test S3 objects after screenshots, but preserve submitted results. Do not delete pre-existing buckets, databases or unrelated resources.

## Submission checklist (max 5 uploaded files + short online text)

- [ ] Part 2 SQL and actual Athena result screenshots/CSV, JSON vs Parquet scan and runtime figures.
- [ ] Part 2 exact scale answers and Glue schema comparison.
- [ ] Part 3 experiment logs (restart, two consumers, 30% failures, grace 0 vs 120).
- [ ] Part 4 pipeline diagram, producer source and real Athena screenshot of streamed data.
- [ ] Actual cloud cost estimate and deletion confirmation.

Suggested grouping into **up to five** uploads: (1) `REPORT_AND_ANSWERS.md` exported to PDF if needed, (2) SQL file, (3) streaming logs zipped, (4) cloud diagram + producer zipped, (5) evidence screenshots zipped. You can also submit the repository URL in online text if allowed by instructor.
