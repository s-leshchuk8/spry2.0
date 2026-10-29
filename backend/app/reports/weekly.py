"""Weekly meetings report - plain logic, no AWS in here.

Run locally (inside the backend container):
    python -m app.reports.weekly 2026-W40

The table/column names are detected from the database, so this works with
your schema as long as it has a meetings table with a start time and either
an end time or a duration.
"""

import csv
import io
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import Interval, inspect, text

TABLE_CANDIDATES = ("meetings", "meeting")
START_CANDIDATES = (
    "starts_at",
    "start_time",
    "start_at",
    "started_at",
    "start",
    "begin_at",
    "scheduled_at",
    "date_time",
    "datetime",
    "start_date",
    "date",
)
END_CANDIDATES = ("ends_at", "end_time", "end_at", "ended_at", "end", "finish_at", "end_date")
DURATION_CANDIDATES = (
    "duration_minutes",
    "duration_min",
    "duration_mins",
    "duration",
    "duration_seconds",
    "duration_hours",
)
TITLE_CANDIDATES = ("title", "name", "subject", "topic")
PARTICIPANT_WORDS = ("participant", "attendee", "member", "guest")


def _get_engine():
    from app import db

    if hasattr(db, "engine"):
        return db.engine
    if hasattr(db, "get_engine"):
        return db.get_engine()
    if hasattr(db, "SessionLocal"):
        session = db.SessionLocal()
        try:
            return session.get_bind()
        finally:
            session.close()
    raise RuntimeError("app/db.py must expose `engine`, `get_engine()` or `SessionLocal`")


def previous_iso_week(today: date | None = None) -> str:
    today = today or datetime.now(UTC).date()
    year, week, _ = (today - timedelta(days=7)).isocalendar()
    return f"{year}-W{week:02d}"


def week_bounds(week: str) -> tuple[date, date]:
    year, wk = week.split("-W")
    start = date.fromisocalendar(int(year), int(wk), 1)
    return start, start + timedelta(days=7)


def shift_week(week: str, days: int) -> str:
    year, wk, _ = (week_bounds(week)[0] + timedelta(days=days)).isocalendar()
    return f"{year}-W{wk:02d}"


def report_key(week: str) -> str:
    # Same week -> same key -> the task is idempotent (overwrite, never duplicate).
    return f"reports/{week}.csv"


def _pick(columns: dict, candidates: tuple) -> str | None:
    lower = {name.lower(): name for name in columns}
    return next((lower[c] for c in candidates if c in lower), None)


def _detect(engine) -> dict:
    insp = inspect(engine)
    tables = insp.get_table_names()
    table = next((t for t in TABLE_CANDIDATES if t in tables), None)
    if table is None:
        raise RuntimeError(f"No meetings table found. Tables in the database: {tables}")
    columns = {c["name"]: c for c in insp.get_columns(table)}
    q = engine.dialect.identifier_preparer.quote

    start = _pick(columns, START_CANDIDATES)
    if start is None:
        raise RuntimeError(f"No start-time column in {table}. Columns: {list(columns)}")

    end = _pick(columns, END_CANDIDATES)
    if end:
        minutes = f"EXTRACT(EPOCH FROM (m.{q(end)} - m.{q(start)})) / 60.0"
    else:
        dur = _pick(columns, DURATION_CANDIDATES)
        if dur is None:
            raise RuntimeError(f"No end-time or duration column in {table}. Columns: {list(columns)}")
        if isinstance(columns[dur]["type"], Interval):
            minutes = f"EXTRACT(EPOCH FROM m.{q(dur)}) / 60.0"
        elif "sec" in dur.lower():
            minutes = f"m.{q(dur)} / 60.0"
        elif "hour" in dur.lower():
            minutes = f"m.{q(dur)} * 60.0"
        else:
            minutes = f"m.{q(dur)}"

    title = _pick(columns, TITLE_CANDIDATES)
    participants = "NULL"
    for t in tables:
        if not any(w in t.lower() for w in PARTICIPANT_WORDS):
            continue
        for fk in insp.get_foreign_keys(t):
            if fk["referred_table"] == table:
                participants = (
                    f"(SELECT count(*) FROM {q(t)} p "
                    f"WHERE p.{q(fk['constrained_columns'][0])} = m.{q(fk['referred_columns'][0])})"
                )
                break
        if participants != "NULL":
            break

    return {
        "from": f"{q(table)} m",
        "start": f"m.{q(start)}",
        "minutes": minutes,
        "title": f"m.{q(title)}" if title else "''",
        "participants": participants,
    }


def _totals(conn, s: dict, week: str) -> tuple[int, float]:
    d0, d1 = week_bounds(week)
    row = conn.execute(
        text(
            f"SELECT count(*) AS n, coalesce(sum({s['minutes']}), 0) / 60.0 AS hours "
            f"FROM {s['from']} WHERE {s['start']} >= :a AND {s['start']} < :b"
        ),
        {"a": datetime.combine(d0, time.min), "b": datetime.combine(d1, time.min)},
    ).one()
    return int(row.n), float(row.hours)


def build_weekly_report(week: str) -> bytes:
    """Query the meetings of one ISO week (e.g. "2026-W40") and return the CSV."""
    engine = _get_engine()
    s = _detect(engine)
    d0, d1 = week_bounds(week)
    with engine.connect() as conn:
        n, hours = _totals(conn, s, week)
        pn, phours = _totals(conn, s, shift_week(week, -7))
        longest = conn.execute(
            text(
                f"SELECT {s['title']} AS title, {s['start']} AS starts, "
                f"{s['minutes']} AS minutes, {s['participants']} AS participants "
                f"FROM {s['from']} WHERE {s['start']} >= :a AND {s['start']} < :b "
                f"ORDER BY minutes DESC NULLS LAST LIMIT 5"
            ),
            {"a": datetime.combine(d0, time.min), "b": datetime.combine(d1, time.min)},
        ).all()

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["week", week, f"{d0.isoformat()} .. {(d1 - timedelta(days=1)).isoformat()}"])
    w.writerow([])
    w.writerow(["metric", "this_week", "previous_week", "change"])
    w.writerow(["meetings", n, pn, n - pn])
    w.writerow(["total_hours", round(hours, 2), round(phours, 2), round(hours - phours, 2)])
    w.writerow([])
    w.writerow(["top5_longest_meetings"])
    w.writerow(["title", "start", "duration_minutes", "participants"])
    for r in longest:
        starts = r.starts.isoformat() if hasattr(r.starts, "isoformat") else str(r.starts)
        w.writerow(
            [r.title, starts, round(float(r.minutes or 0)), "" if r.participants is None else r.participants]
        )
    return out.getvalue().encode("utf-8")


if __name__ == "__main__":
    import sys

    print(build_weekly_report(sys.argv[1] if len(sys.argv) > 1 else previous_iso_week()).decode())
