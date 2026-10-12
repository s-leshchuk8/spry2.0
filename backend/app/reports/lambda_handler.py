"""report-builder Lambda (runs in the VPC).

Triggers: SQS message (EventBridge Scheduler or `make report-now`) or a direct invoke.
Image command: app.reports.lambda_handler.handler
"""
import json
import logging
import os
import re

import boto3

from .weekly import build_weekly_report, previous_iso_week, report_key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
WEEK_RE = re.compile(r"^\d{4}-W\d{2}$")


def _unpack(event: dict) -> tuple[dict, bool]:
    """Return (payload, came_from_sqs). Handles both an SQS record and a direct invoke."""
    records = event.get("Records") or []
    if records and records[0].get("eventSource") == "aws:sqs":
        try:
            return json.loads(records[0]["body"]), True
        except (ValueError, TypeError):
            return {}, True
    return event, False


def detect_trigger(event: dict) -> str:
    payload, from_sqs = _unpack(event)
    if from_sqs:
        return "schedule" if payload.get("source") == "schedule" else "sqs"
    return payload.get("source") or "direct"


def handler(event, context):
    payload, _ = _unpack(event)
    week = payload.get("week") or previous_iso_week()
    logger.info("report-builder triggered trigger=%s week=%s", detect_trigger(event), week)

    if not WEEK_RE.match(week):
        raise ValueError(f"Bad week {week!r}, expected e.g. 2026-W40")
    # DLQ experiment: `make report-break WEEK=2026-W38`, later `make report-fix`.
    if os.environ.get("FAIL_WEEK") == week:
        raise RuntimeError(f"forced failure for {week}")

    key = report_key(week)
    s3.put_object(Bucket=os.environ["REPORTS_BUCKET"], Key=key,
                  Body=build_weekly_report(week), ContentType="text/csv")
    logger.info("report-builder saved key=%s", key)
    return {"week": week, "key": key}
