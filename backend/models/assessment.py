from datetime import datetime, timezone
from backend.extensions import db
from backend.models.base import TimestampMixin


class Assessment(db.Model, TimestampMixin):
    """
    Skill evaluations, pre-placement screening tests, and technical quizzes.
    """
    __tablename__ = "assessments"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    duration_minutes = db.Column(db.Integer, default=60, nullable=False)
    passing_score = db.Column(db.Numeric(5, 2), default=40.0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    company = db.relationship("Company", back_populates="assessments")
    job = db.relationship("Job", backref=db.backref("job_assessments", lazy=True))
    questions = db.relationship("AssessmentQuestion", back_populates="assessment", cascade="all, delete-orphan")
    attempts = db.relationship("AssessmentAttempt", back_populates="assessment", cascade="all, delete-orphan")

    def to_dict(self, include_questions=False, include_answer=True):
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "company_id": self.company_id,
            "company_name": self.company.name if self.company else None,
            "job_id": self.job_id,
            "job_title": self.job.title if self.job else None,
            "duration_minutes": self.duration_minutes,
            "passing_score": float(self.passing_score) if self.passing_score is not None else 40.0,
            "is_active": self.is_active,
            "total_questions": len(self.questions),
            "total_attempts": len(self.attempts),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        if include_questions:
            data["questions"] = [q.to_dict(include_answer=include_answer) for q in self.questions]
        return data

    def __repr__(self):
        return f"<Assessment id={self.id} title='{self.title}'>"


class AssessmentQuestion(db.Model, TimestampMixin):
    """
    Individual question within an assessment.
    """
    __tablename__ = "assessment_questions"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), default="MCQ", nullable=False)  # MCQ, Coding, ShortAnswer
    options_json = db.Column(db.Text, nullable=True)  # JSON array of answer choices
    correct_answer = db.Column(db.Text, nullable=False)
    marks = db.Column(db.Numeric(4, 2), default=1.0, nullable=False)

    # Relationships
    assessment = db.relationship("Assessment", back_populates="questions")

    def to_dict(self, include_answer=True):
        import json
        options = []
        if self.options_json:
            try:
                options = json.loads(self.options_json)
            except Exception:
                options = []

        data = {
            "id": self.id,
            "assessment_id": self.assessment_id,
            "question_text": self.question_text,
            "question_type": self.question_type,
            "options": options,
            "marks": float(self.marks) if self.marks is not None else 1.0
        }
        if include_answer:
            data["correct_answer"] = self.correct_answer
        return data

    def __repr__(self):
        return f"<AssessmentQuestion id={self.id} assessment_id={self.assessment_id}>"


class AssessmentAttempt(db.Model, TimestampMixin):
    """
    Student test execution session, score, and passing verdict.
    """
    __tablename__ = "assessment_attempts"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    score = db.Column(db.Numeric(5, 2), default=0.0, nullable=False)
    passed = db.Column(db.Boolean, default=False, nullable=False)
    answers_json = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    assessment = db.relationship("Assessment", back_populates="attempts")
    student = db.relationship("Student", back_populates="assessment_attempts")

    @property
    def score_percentage(self):
        return float(self.score) if self.score is not None else 0.0

    def to_dict(self):
        import json
        answers = {}
        if self.answers_json:
            try:
                answers = json.loads(self.answers_json)
            except Exception:
                answers = {}

        return {
            "id": self.id,
            "assessment_id": self.assessment_id,
            "assessment_title": self.assessment.title if self.assessment else "Assessment",
            "student_id": self.student_id,
            "student_name": f"{self.student.first_name} {self.student.last_name}" if self.student else "Student",
            "student_roll": self.student.roll_number if self.student else "N/A",
            "student_dept": self.student.department if self.student else "N/A",
            "score": float(self.score) if self.score is not None else 0.0,
            "passed": self.passed,
            "answers": answers,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

    def __repr__(self):
        return f"<AssessmentAttempt id={self.id} assessment_id={self.assessment_id} student_id={self.student_id} score={self.score}>"
