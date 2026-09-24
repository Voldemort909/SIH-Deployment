from backend.extensions import db
from backend.models.base import TimestampMixin


class Notification(db.Model, TimestampMixin):
    """
    User notification messages, system alerts, and status updates.
    """
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default="General", nullable=False, index=True)  # Placement, Application, Workshop, Assessment, General
    link = db.Column(db.String(255), nullable=True)  # Actionable URL/route
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    channel = db.Column(db.String(50), default="in_app", nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="notifications")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "type": self.type,
            "link": self.link,
            "is_read": self.is_read,
            "channel": self.channel,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Notification id={self.id} user_id={self.user_id} title='{self.title}' read={self.is_read}>"
