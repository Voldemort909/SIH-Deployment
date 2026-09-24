from datetime import datetime, timezone
from backend.extensions import db


class TimestampMixin:
    """
    Reusable timestamp mixin providing created_at and updated_at
    timestamps for all database models.
    """
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
