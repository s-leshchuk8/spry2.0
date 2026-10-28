import os
import logging
from email.message import EmailMessage
from urllib.parse import unquote_plus

import boto3

log = logging.getLogger()
log.setLevel(logging.INFO)
s3 = boto3.client("s3")
ses = boto3.client("sesv2")


def handler(event, context):
    # Runs outside the VPC. NEVER write into reports/ from here (it would trigger itself).
    for rec in event.get("Records", []):
        bucket = rec["s3"]["bucket"]["name"]
        key = unquote_plus(rec["s3"]["object"]["key"])
        log.info("report-mailer triggered trigger=s3 bucket=%s key=%s", bucket, key)
        if not (key.startswith("reports/") and key.endswith(".csv")):
            continue
        body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        name = key.rsplit("/", 1)[-1]
        to = [a.strip() for a in os.environ["RECIPIENTS"].split(",") if a.strip()]
        msg = EmailMessage()
        msg["Subject"] = "Weekly meetings report: " + name
        msg["From"] = os.environ["SENDER"]
        msg["To"] = ", ".join(to)
        msg.set_content("Hello! Your weekly meetings report is attached.")
        msg.add_attachment(body, maintype="text", subtype="csv", filename=name)
        ses.send_email(Content={"Raw": {"Data": msg.as_bytes()}},
                       FromEmailAddress=os.environ["SENDER"],
                       Destination={"ToAddresses": to})
        log.info("report-mailer sent key=%s to=%s", key, to)