"""Insert sample participants when SEED=true and the table is empty."""

from sqlalchemy import func, select

from app.config import settings
from app.db import SessionLocal
from app.models import Participant

SAMPLE_PARTICIPANTS = [
    ("Anna Kovalenko", "anna@example.com"),
    ("Oleh Shevchenko", "oleh@example.com"),
    ("Iryna Bondar", "iryna@example.com"),
    ("Taras Melnyk", "taras@example.com"),
    ("Sofia Tkachenko", "sofia@example.com"),
]


def main() -> None:
    if not settings.seed:
        return
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(Participant)):
            return
        db.add_all(Participant(name=name, email=email) for name, email in SAMPLE_PARTICIPANTS)
        db.commit()
        print(f"Seeded {len(SAMPLE_PARTICIPANTS)} participants")


if __name__ == "__main__":
    main()
