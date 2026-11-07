-- Replace YOUR_BUCKET and run in Athena database lab_db (region us-east-1).
-- Existing crawler table `payments` is NOT overwritten.
CREATE EXTERNAL TABLE IF NOT EXISTS lab_db.payment_events (
 invoiceId string, status string, failureReason string, amount bigint,
 finalAmount bigint, ccy int, reference string, createdDate string,
 modifiedDate string, receivedAt string, merchantId string,
 merchantName string, mcc int, customerId string, paymentMethod string, device string
)
PARTITIONED BY (dt string)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
STORED AS TEXTFILE
LOCATION 's3://YOUR_BUCKET/payments/';
MSCK REPAIR TABLE lab_db.payment_events;
SELECT COUNT(*) AS raw_events FROM lab_db.payment_events;

-- Exact duplicate removal BEFORE latest-event selection. Equal modifiedDate
-- ties are resolved by receivedAt and status for deterministic output.
CREATE OR REPLACE VIEW lab_db.payment_events_distinct AS
SELECT DISTINCT invoiceId,status,failureReason,amount,finalAmount,ccy,reference,
 createdDate,modifiedDate,receivedAt,merchantId,merchantName,mcc,
 customerId,paymentMethod,device,dt
FROM lab_db.payment_events;

CREATE OR REPLACE VIEW lab_db.payments_latest AS
SELECT invoiceId,status,failureReason,amount,finalAmount,ccy,reference,
 createdDate,modifiedDate,receivedAt,merchantId,merchantName,mcc,
 customerId,paymentMethod,device,dt
FROM (
 SELECT e.*, ROW_NUMBER() OVER (
 PARTITION BY invoiceId ORDER BY from_iso8601_timestamp(modifiedDate) DESC,
 from_iso8601_timestamp(receivedAt) DESC, status DESC) AS rn
 FROM lab_db.payment_events_distinct e
) WHERE rn=1;

-- Part 2: scale and duplicate counts (exact duplicate event rows).
SELECT (SELECT COUNT(*) FROM lab_db.payment_events) raw_events,
 (SELECT COUNT(*) FROM lab_db.payment_events_distinct) distinct_events,
 (SELECT COUNT(*) FROM lab_db.payments_latest) unique_invoices,
 (SELECT COUNT(*) FROM lab_db.payment_events) -
 (SELECT COUNT(*) FROM lab_db.payment_events_distinct) exact_duplicate_rows;

-- Late >60s and >1h; denominators include all raw events.
SELECT COUNT(*) total_events,
 COUNT_IF(date_diff('second',from_iso8601_timestamp(modifiedDate),from_iso8601_timestamp(receivedAt))>60) late_over_60s,
 COUNT_IF(date_diff('second',from_iso8601_timestamp(modifiedDate),from_iso8601_timestamp(receivedAt))>3600) late_over_1h,
 ROUND(100.0*COUNT_IF(date_diff('second',from_iso8601_timestamp(modifiedDate),from_iso8601_timestamp(receivedAt))>3600)/NULLIF(COUNT(*),0),4) late_over_1h_pct
FROM lab_db.payment_events;

-- Query 3: turnover, major currency units, success only.
SELECT merchantId,merchantName,ccy,COUNT(*) successful_payments,
 ROUND(SUM(finalAmount)/100.0,2) turnover
FROM lab_db.payments_latest WHERE status='success'
GROUP BY 1,2,3 ORDER BY turnover DESC;

-- Query 4: failure rate per method and device.
SELECT paymentMethod,device,COUNT(*) payments,
 COUNT_IF(status='failure') failed,
 ROUND(100.0*COUNT_IF(status='failure')/NULLIF(COUNT(*),0),2) failure_pct
FROM lab_db.payments_latest GROUP BY 1,2 ORDER BY failure_pct DESC;

-- Query 5: peak hours (UTC, by creation time).
SELECT hour(from_iso8601_timestamp(createdDate)) hour_utc,COUNT(*) payments
FROM lab_db.payments_latest GROUP BY 1 ORDER BY payments DESC;

-- Query 7: CTAS. Run only once, with a NEW/EMPTY curated prefix.
-- Change YOUR_BUCKET before running; do not rerun against a populated location.
CREATE TABLE lab_db.payments_parquet
WITH (format='PARQUET',external_location='s3://YOUR_BUCKET/curated/payments/',
 partitioned_by=ARRAY['dt']) AS
SELECT invoiceId,status,failureReason,amount,finalAmount,ccy,reference,
 createdDate,modifiedDate,receivedAt,merchantId,merchantName,mcc,
 customerId,paymentMethod,device,dt
FROM lab_db.payments_latest;

-- Repeat Q3–Q5 on Parquet; compare Athena Query statistics for each run.
SELECT merchantId,merchantName,ccy,COUNT(*) successful_payments,
 ROUND(SUM(finalAmount)/100.0,2) turnover
FROM lab_db.payments_parquet WHERE status='success'
GROUP BY 1,2,3 ORDER BY turnover DESC;
SELECT paymentMethod,device,COUNT(*) payments,COUNT_IF(status='failure') failed,
 ROUND(100.0*COUNT_IF(status='failure')/NULLIF(COUNT(*),0),2) failure_pct
FROM lab_db.payments_parquet GROUP BY 1,2 ORDER BY failure_pct DESC;
SELECT hour(from_iso8601_timestamp(createdDate)) hour_utc,COUNT(*) payments
FROM lab_db.payments_parquet GROUP BY 1 ORDER BY payments DESC;
