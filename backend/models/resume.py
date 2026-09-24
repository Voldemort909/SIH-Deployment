from backend.extensions import db
from backend.models.base import TimestampMixin


class Resume(db.Model, TimestampMixin):
    """
    Uploaded resume files associated with student profiles.
    """
    __tablename__ = "resumes"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = db.Column(db.String(255), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)  # in bytes
    is_primary = db.Column(db.Boolean, default=False, nullable=False)
    version = db.Column(db.Integer, default=1, nullable=False)

    @property
    def filename(self):
        return self.file_name

    @filename.setter
    def filename(self, val):
        self.file_name = val

    # Relationships
    student = db.relationship("Student", back_populates="resumes")
    analysis = db.relationship("ResumeAnalysis", back_populates="resume", uselist=False, cascade="all, delete-orphan")
    applications = db.relationship("Application", back_populates="resume")

    def __repr__(self):
        return f"<Resume id={self.id} student_id={self.student_id} file_name='{self.file_name}'>"


class ResumeAnalysis(db.Model, TimestampMixin):
    """
    Automated NLP / PyMuPDF parsing and scoring results for a resume.
    """
    __tablename__ = "resume_analysis"

    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    overall_score = db.Column(db.Numeric(5, 2), nullable=True)  # Score out of 100
    parsed_skills_json = db.Column(db.Text, nullable=True)     # JSON string of detected skills
    skill_gap_json = db.Column(db.Text, nullable=True)         # JSON string of missing/recommended skills
    strengths_json = db.Column(db.Text, nullable=True)         # JSON string of candidate strengths
    improvements_json = db.Column(db.Text, nullable=True)      # JSON string of suggested improvements
    extracted_text = db.Column(db.Text, nullable=True)         # Raw text extracted via PyMuPDF

    @property
    def ats_score(self):
        return self.overall_score

    @ats_score.setter
    def ats_score(self, val):
        self.overall_score = val

    # Relationships
    resume = db.relationship("Resume", back_populates="analysis")

    def __repr__(self):
        return f"<ResumeAnalysis id={self.id} resume_id={self.resume_id} score={self.overall_score}>"
