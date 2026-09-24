from backend.extensions import db
from backend.models.base import TimestampMixin


class Company(db.Model, TimestampMixin):
    """
    Corporate partner, recruiting agency, or employer profile.
    """
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False, index=True)
    website = db.Column(db.String(255), nullable=True)
    industry_type = db.Column(db.String(100), nullable=True, index=True)
    location = db.Column(db.String(150), nullable=True)
    description = db.Column(db.Text, nullable=True)
    logo_url = db.Column(db.String(255), nullable=True)
    domains = db.Column(db.String(255), nullable=True)
    recruitment_process = db.Column(db.Text, nullable=True)
    videos_json = db.Column(db.Text, nullable=True)

    @property
    def locations(self):
        return self.location

    @locations.setter
    def locations(self, value):
        self.location = value

    # Relationships
    experts = db.relationship("IndustryExpert", back_populates="company")
    jobs = db.relationship("Job", back_populates="company", cascade="all, delete-orphan")
    workshops = db.relationship("Workshop", back_populates="company")
    placement_drives = db.relationship("PlacementDrive", back_populates="company", cascade="all, delete-orphan")
    assessments = db.relationship("Assessment", back_populates="company")
    placement_records = db.relationship("PlacementRecord", back_populates="company")
    hiring_history = db.relationship("CompanyHiringHistory", back_populates="company", cascade="all, delete-orphan", order_by="desc(CompanyHiringHistory.hiring_year)")

    def to_dict(self):
        import json
        videos = []
        if self.videos_json:
            try:
                videos = json.loads(self.videos_json)
            except Exception:
                videos = []

        return {
            "id": self.id,
            "name": self.name,
            "website": self.website,
            "industry": self.industry_type,
            "industry_type": self.industry_type,
            "location": self.location,
            "description": self.description,
            "logo_url": self.logo_url,
            "domains": self.domains,
            "recruitment_process": self.recruitment_process,
            "videos": videos,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Company id={self.id} name='{self.name}'>"


class CompanyHiringHistory(db.Model, TimestampMixin):
    """
    Historical recruitment performance metrics for an employer partner:
    - Hiring year
    - Students selected
    - Offers count
    - Average CTC and Highest CTC
    """
    __tablename__ = "company_hiring_histories"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    hiring_year = db.Column(db.Integer, nullable=False, index=True)
    students_selected = db.Column(db.Integer, default=0, nullable=False)
    offers_count = db.Column(db.Integer, default=0, nullable=False)
    average_ctc = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    highest_ctc = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("company_id", "hiring_year", name="uq_company_hiring_year"),
    )

    # Relationships
    company = db.relationship("Company", back_populates="hiring_history")

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "company_name": self.company.name if self.company else None,
            "hiring_year": self.hiring_year,
            "students_selected": self.students_selected,
            "offers_count": self.offers_count,
            "average_ctc": float(self.average_ctc) if self.average_ctc is not None else 0.0,
            "highest_ctc": float(self.highest_ctc) if self.highest_ctc is not None else 0.0,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<CompanyHiringHistory company_id={self.company_id} year={self.hiring_year} selected={self.students_selected}>"

