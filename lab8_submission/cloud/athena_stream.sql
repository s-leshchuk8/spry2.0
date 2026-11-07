-- Firehose must deliver newline-delimited JSON to s3://YOUR_BUCKET/streamed/
-- and the delivery stream must already have written objects.
CREATE EXTERNAL TABLE IF NOT EXISTS lab_db.streamed_payment_events (
 invoiceId string,status string,failureReason string,amount bigint,
 finalAmount bigint,ccy int,reference string,createdDate string,
 modifiedDate string,receivedAt string,merchantId string,merchantName string,
 mcc int,customerId string,paymentMethod string,device string
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
STORED AS TEXTFILE LOCATION 's3://YOUR_BUCKET/streamed/';
SELECT status,COUNT(*) AS events FROM lab_db.streamed_payment_events
GROUP BY status ORDER BY events DESC;
