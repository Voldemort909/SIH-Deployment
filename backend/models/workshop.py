from backend.extensions import db
from backend.models.base import TimestampMixin


class Workshop(db.Model, TimestampMixin):
    """
    Skill-development webinars, seminars, and technical workshops.
    """
    __tablename__ = "workshops"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    instructor_id = db.Column(db.Integer, db.ForeignKey("industry_experts.id", ondelete="SET NULL"), nullable=True, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    start_time = db.Column(db.DateTime(timezone=True), nullable=False)
    end_time = db.Column(db.DateTime(timezone=True), nullable=False)
    venue_or_link = db.Column(db.String(255), nullable=True)
    max_capacity = db.Column(db.Integer, default=100, nullable=False)

    # Relationships
    instructor = db.relationship("IndustryExpert", back_populates="workshops")
    company = db.relationship("Company", back_populates="workshops")
    registrations = db.relationship("WorkshopRegistration", back_populates="workshop", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Workshop id={self.id} title='{self.title}'>"


class WorkshopRegistration(db.Model, TimestampMixin):
    """
    Student registration and attendance tracker for workshops.
    """
    __tablename__ = "workshop_registrations"

    id = db.Column(db.Integer, primary_key=True)
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    attendance_status = db.Column(db.String(50), default="Registered", nullable=False)  # Registered, Attended, Absent

    __table_args__ = (
        db.UniqueConstraint("workshop_id", "student_id", name="uq_workshop_student"),
    )

    # Relationships
    workshop = db.relationship("Workshop", back_populates="registrations")
    student = db.relationship("Student", back_populates="workshop_registrations")

    def __repr__(self):
        return f"<WorkshopRegistration workshop_id={self.workshop_id} student_id={self.student_id}>"
