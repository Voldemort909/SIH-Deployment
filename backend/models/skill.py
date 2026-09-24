from backend.extensions import db
from backend.models.base import TimestampMixin


class Skill(db.Model, TimestampMixin):
    """
    Catalog of standardized technical and professional skills.
    """
    __tablename__ = "skills"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    category = db.Column(db.String(100), default="Technical", nullable=False, index=True)

    # Relationships
    student_skills = db.relationship("StudentSkill", back_populates="skill", cascade="all, delete-orphan")
    job_skills = db.relationship("JobSkill", back_populates="skill", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Skill id={self.id} name='{self.name}' category='{self.category}'>"


class StudentSkill(db.Model, TimestampMixin):
    """
    Junction table associating students with acquired skills.
    Tracks proficiency and verification status.
    """
    __tablename__ = "student_skills"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = db.Column(db.Integer, db.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    proficiency_level = db.Column(db.String(50), default="Intermediate", nullable=False)  # Beginner, Intermediate, Advanced, Expert
    is_verified = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("student_id", "skill_id", name="uq_student_skill"),
    )

    # Relationships
    student = db.relationship("Student", back_populates="student_skills")
    skill = db.relationship("Skill", back_populates="student_skills")

    @property
    def proficiency(self):
        return self.proficiency_level

    @proficiency.setter
    def proficiency(self, val):
        self.proficiency_level = val

    def __repr__(self):
        return f"<StudentSkill student_id={self.student_id} skill_id={self.skill_id}>"


class JobSkill(db.Model, TimestampMixin):
    """
    Junction table defining skills required or preferred for a job posting.
    """
    __tablename__ = "job_skills"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = db.Column(db.Integer, db.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    priority = db.Column(db.String(50), default="Important", nullable=False)  # Critical, Important, Preferred
    is_mandatory = db.Column(db.Boolean, default=True, nullable=False)
    min_proficiency = db.Column(db.String(50), default="Intermediate", nullable=False)

    __table_args__ = (
        db.UniqueConstraint("job_id", "skill_id", name="uq_job_skill"),
    )

    # Relationships
    job = db.relationship("Job", back_populates="required_skills")
    skill = db.relationship("Skill", back_populates="job_skills")

    def __repr__(self):
        return f"<JobSkill job_id={self.job_id} skill_id={self.skill_id}>"
