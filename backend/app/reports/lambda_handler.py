"""report-builder Lambda handler. Triggered by SQS (schedule / make report-now)
or by a direct invoke. Image Command: app.reports.lambda_handler.handler
"""

import json
import logging
import os

import boto3

from app.reports.weekly import build_weekly_report, previous_iso_week, report_key

log = logging.getLogger()
log.setLevel(logging.INFO)
s3 = boto3.client("s3")


def _payload(event: dict) -> dict:
    """Handle both shapes: SQS record and direct invocation."""
    if event.get("Records") and event["Records"][0].get("eventSource") == "aws:sqs":
        return json.loads(event["Records"][0]["body"])
    return event


def detect_trigger(event: dict) -> str:
    payload = _payload(event)
    if event is not payload:  # came through SQS
        return "schedule" if payload.get("source") == "schedule" else "sqs"
    return payload.get("source", "direct")


def handler(event, context):
    payload = _payload(event)
    week = payload.get("week") or previous_iso_week()
    log.info("report-builder triggered trigger=%s week=%s", detect_trigger(event), week)

    # For the DLQ experiment: set env FAIL_WEEK=2026-W38 and redeploy, then remove it.
    if os.environ.get("FAIL_WEEK") == week:
        raise RuntimeError(f"forced failure for {week}")

    key = report_key(week)
    s3.put_object(
        Bucket=os.environ["REPORTS_BUCKET"], Key=key, Body=build_weekly_report(week), ContentType="text/csv"
    )
    log.info("report-builder saved key=%s", key)
    return {"week": week, "key": key}
