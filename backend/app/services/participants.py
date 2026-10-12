from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Participant
from app.schemas import ParticipantCreate
from app.services.errors import ConflictError, NotFoundError


def list_participants(db: Session, q: str | None = None) -> Sequence[Participant]:
    query = select(Participant).order_by(Participant.name)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(or_(Participant.name.ilike(pattern), Participant.email.ilike(pattern)))
    return db.scalars(query).all()


def create_participant(db: Session, data: ParticipantCreate) -> Participant:
    participant = Participant(name=data.name, email=data.email)
    db.add(participant)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(f"Participant with email {data.email} already exists") from None
    return participant


def delete_participant(db: Session, participant_id: UUID) -> None:
    participant = db.get(Participant, participant_id)
    if participant is None:
        raise NotFoundError(f"Participant {participant_id} not found")
    db.delete(participant)
    db.commit()
