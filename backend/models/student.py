from backend.extensions import db
from backend.models.base import TimestampMixin


class StudentPreference(db.Model, TimestampMixin):
    """
    Career and employment preferences set by a student.
    """
    __tablename__ = "student_preferences"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    preferred_domain = db.Column(db.String(150), nullable=True)  # e.g. Full Stack, AI/ML, Cloud, Data Science
    preferred_roles = db.Column(db.Text, nullable=True)  # JSON string or comma-separated list of target roles
    preferred_locations = db.Column(db.Text, nullable=True)  # JSON or comma-separated locations
    expected_min_salary = db.Column(db.Numeric(12, 2), nullable=True)
    job_type_preference = db.Column(db.String(50), default="Both", nullable=False)  # Internship, Full-time, Both
    willing_to_relocate = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    student = db.relationship("Student", back_populates="preferences")

    def __repr__(self):
        return f"<StudentPreference student_id={self.student_id}>"


class Project(db.Model, TimestampMixin):
    """
    Academic or personal portfolio projects completed by a student.
    """
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    technologies_used = db.Column(db.Text, nullable=True)  # Comma-separated or JSON list of tech
    github_url = db.Column(db.String(255), nullable=True)
    live_url = db.Column(db.String(255), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)

    # Relationships
    student = db.relationship("Student", back_populates="projects")

    def __repr__(self):
        return f"<Project id={self.id} student_id={self.student_id} title='{self.title}'>"
