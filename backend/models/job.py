from backend.extensions import db
from backend.models.base import TimestampMixin


class Job(db.Model, TimestampMixin):
    """
    Job vacancy or internship posting created by a company or industry expert.
    """
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    posted_by_expert_id = db.Column(db.Integer, db.ForeignKey("industry_experts.id", ondelete="SET NULL"), nullable=True, index=True)
    title = db.Column(db.String(150), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    job_type = db.Column(db.String(50), default="Full-time", nullable=False, index=True)  # Full-time, Internship, Contract
    location = db.Column(db.String(150), nullable=True)
    domain = db.Column(db.String(100), default="Software Engineering", nullable=False, index=True)  # Software Engineering, Data Science, etc.
    ctc = db.Column(db.String(100), nullable=True)  # e.g. '₹8 - ₹12 LPA' or '₹35,000/month'
    min_salary = db.Column(db.Numeric(12, 2), nullable=True)
    max_salary = db.Column(db.Numeric(12, 2), nullable=True)
    min_cgpa = db.Column(db.Numeric(4, 2), default=0.0, nullable=False)
    eligible_branches = db.Column(db.Text, nullable=True)  # Comma-separated: 'Computer Science,Information Technology'
    eligible_batch_years = db.Column(db.String(100), nullable=True)  # Comma-separated: '2025,2026'
    deadline = db.Column(db.DateTime(timezone=True), nullable=True)
    status = db.Column(db.String(50), default="Pending Approval", nullable=False, index=True)  # Pending Approval, Published, Closed, Rejected
    rejection_reason = db.Column(db.Text, nullable=True)
 
    __table_args__ = (
        db.Index("ix_jobs_company_status", "company_id", "status"),
        db.Index("ix_jobs_domain_status", "domain", "status"),
    )

    # Relationships
    company = db.relationship("Company", back_populates="jobs")
    posted_by = db.relationship("IndustryExpert", back_populates="posted_jobs")
    required_skills = db.relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")

    @property
    def job_skills(self):
        return self.required_skills

    applications = db.relationship("Application", back_populates="job", cascade="all, delete-orphan")
    placement_records = db.relationship("PlacementRecord", back_populates="job")

    def __repr__(self):
        return f"<Job id={self.id} title='{self.title}' company_id={self.company_id} status='{self.status}'>"
