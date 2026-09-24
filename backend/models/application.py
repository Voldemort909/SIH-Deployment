from datetime import datetime, timezone
from backend.extensions import db
from backend.models.base import TimestampMixin


class Application(db.Model, TimestampMixin):
    """
    Job application linking a student to a specific job opening.
    """
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True, index=True)
    current_status = db.Column(
        db.String(50),
        default="APPLIED",
        nullable=False,
        index=True
    )  # APPLIED, UNDER_REVIEW, SHORTLISTED, ASSESSMENT, INTERVIEW, SELECTED, REJECTED
    applied_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint("student_id", "job_id", name="uq_student_job_application"),
        db.Index("ix_applications_student_status", "student_id", "current_status"),
        db.Index("ix_applications_job_status", "job_id", "current_status"),
    )

    # Relationships
    student = db.relationship("Student", back_populates="applications")
    job = db.relationship("Job", back_populates="applications")
    resume = db.relationship("Resume", back_populates="applications")
    status_history = db.relationship("ApplicationStatusHistory", back_populates="application", cascade="all, delete-orphan", order_by="desc(ApplicationStatusHistory.created_at)")
    feedbacks = db.relationship("Feedback", back_populates="application", cascade="all, delete-orphan")
    placement_record = db.relationship("PlacementRecord", back_populates="application", uselist=False)
    @property
    def status(self):
        return self.current_status

    @status.setter
    def status(self, val):
        self.current_status = val

    def __repr__(self):
        return f"<Application id={self.id} student_id={self.student_id} job_id={self.job_id} status='{self.current_status}'>"


class ApplicationStatusHistory(db.Model, TimestampMixin):
    """
    Audit log of status changes for an application.
    """
    __tablename__ = "application_status_history"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    status = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    changed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    application = db.relationship("Application", back_populates="status_history")
    changed_by = db.relationship("User")

    def __repr__(self):
        return f"<ApplicationStatusHistory application_id={self.application_id} status='{self.status}'>"


class Feedback(db.Model, TimestampMixin):
    """
    Recruiter and interviewer feedback provided for candidates and drives.
    """
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id", ondelete="SET NULL"), nullable=True, index=True)
    given_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=True)  # 1 to 5 scale (overall)
    technical_rating = db.Column(db.Integer, nullable=True)  # 1 to 5 scale
    problem_solving_rating = db.Column(db.Integer, nullable=True)  # 1 to 5 scale
    communication_rating = db.Column(db.Integer, nullable=True)  # 1 to 5 scale
    recommendation = db.Column(db.String(50), nullable=True)  # Strong Hire, Hire, Hold, Reject
    is_visible_to_student = db.Column(db.Boolean, default=False, nullable=False)
    comments = db.Column(db.Text, nullable=False)
    feedback_type = db.Column(db.String(50), default="Interview", nullable=False)  # Interview, Assessment, Mentorship

    # Relationships
    application = db.relationship("Application", back_populates="feedbacks")
    given_by = db.relationship("User", foreign_keys=[given_by_user_id])
    target_student = db.relationship("Student", back_populates="feedback_received", foreign_keys=[target_student_id])

    def to_dict(self):
        reviewer_name = "Interviewer"
        if self.given_by:
            if self.given_by.industry_profile:
                exp = self.given_by.industry_profile
                reviewer_name = f"{exp.first_name} {exp.last_name} ({exp.company.name if exp.company else 'Recruiter'})"
            elif self.given_by.admin_profile:
                adm = self.given_by.admin_profile
                reviewer_name = f"{adm.first_name} {adm.last_name} (Placement Admin)"

        job_info = None
        if self.application and self.application.job:
            job_info = {
                "id": self.application.job.id,
                "title": self.application.job.title,
                "company": self.application.job.company.name if self.application.job.company else "Company"
            }

        return {
            "id": self.id,
            "application_id": self.application_id,
            "job": job_info,
            "student_id": self.target_student_id,
            "student_name": f"{self.target_student.first_name} {self.target_student.last_name}" if self.target_student else "Student",
            "reviewer_name": reviewer_name,
            "rating": self.rating,
            "technical_rating": self.technical_rating,
            "problem_solving_rating": self.problem_solving_rating,
            "communication_rating": self.communication_rating,
            "recommendation": self.recommendation,
            "is_visible_to_student": self.is_visible_to_student,
            "comments": self.comments,
            "feedback_type": self.feedback_type,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Feedback id={self.id} student_id={self.target_student_id} rating={self.rating}>"
