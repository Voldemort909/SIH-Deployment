from backend.extensions import db
from backend.models.base import TimestampMixin


class PlacementRecord(db.Model, TimestampMixin):
    """
    Official placement offer record confirming recruitment outcome.
    """
    __tablename__ = "placement_records"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id", ondelete="SET NULL"), unique=True, nullable=True, index=True)
    package_ctc = db.Column(db.Numeric(12, 2), nullable=False)  # Annual CTC in Lakhs or Currency
    offer_letter_url = db.Column(db.String(255), nullable=True)
    offer_date = db.Column(db.Date, nullable=True)
    acceptance_status = db.Column(db.String(50), default="Pending", nullable=False)  # Pending, Accepted, Declined

    __table_args__ = (
        db.Index("ix_placement_records_student_company", "student_id", "company_id"),
    )

    # Relationships
    student = db.relationship("Student", back_populates="placement_records")
    company = db.relationship("Company", back_populates="placement_records")
    job = db.relationship("Job", back_populates="placement_records")
    application = db.relationship("Application", back_populates="placement_record")

    def __repr__(self):
        return f"<PlacementRecord id={self.id} student_id={self.student_id} company_id={self.company_id} ctc={self.package_ctc}>"


class PlacementDrive(db.Model, TimestampMixin):
    """
    On-campus or virtual recruitment drive scheduled by the placement cell.
    """
    __tablename__ = "placement_drives"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    academic_year = db.Column(db.String(20), nullable=False, index=True)  # e.g., '2025-2026'
    drive_date = db.Column(db.DateTime(timezone=True), nullable=False)
    eligible_batch = db.Column(db.Integer, nullable=False, index=True)   # Graduation year
    min_cgpa = db.Column(db.Numeric(4, 2), default=0.0, nullable=False)
    max_backlogs = db.Column(db.Integer, default=0, nullable=False)
    eligible_departments = db.Column(db.Text, nullable=True)  # Comma-separated or JSON list
    job_role = db.Column(db.String(150), nullable=True)
    package_ctc = db.Column(db.String(100), nullable=True)
    required_skills = db.Column(db.Text, nullable=True)  # Comma-separated or JSON
    current_stage = db.Column(db.String(50), default="Registration", nullable=False, index=True)  # Registration, Shortlisting, Assessment, Interview, Selection, Offer, Completed
    status = db.Column(db.String(50), default="Scheduled", nullable=False, index=True)  # Scheduled, Ongoing, Completed, Cancelled

    __table_args__ = (
        db.Index("ix_placement_drives_year_status", "academic_year", "status"),
    )

    # Relationships
    company = db.relationship("Company", back_populates="placement_drives")
    participating_students = db.relationship("PlacementDriveStudent", back_populates="drive", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PlacementDrive id={self.id} title='{self.title}' company_id={self.company_id} stage='{self.current_stage}'>"


class PlacementDriveStudent(db.Model, TimestampMixin):
    """
    Junction table tracking student eligibility, registration, and progression in a drive.
    """
    __tablename__ = "placement_drive_students"

    id = db.Column(db.Integer, primary_key=True)
    drive_id = db.Column(db.Integer, db.ForeignKey("placement_drives.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    registration_status = db.Column(db.String(50), default="Registered", nullable=False)  # Registered, Attended, Absent
    stage = db.Column(db.String(50), default="Registration", nullable=False, index=True)  # Registration, Shortlisted, Assessment, Interview, Selected, Offered, Rejected
    offered_ctc = db.Column(db.Numeric(12, 2), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    shortlisted = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("drive_id", "student_id", name="uq_drive_student"),
    )

    # Relationships
    drive = db.relationship("PlacementDrive", back_populates="participating_students")
    student = db.relationship("Student", back_populates="placement_drives")

    def __repr__(self):
        return f"<PlacementDriveStudent drive_id={self.drive_id} student_id={self.student_id} stage='{self.stage}'>"


class Alumni(db.Model, TimestampMixin):
    """
    Directory of college graduates for mentorship, career networking, and referrals.
    """
    __tablename__ = "alumni"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False, index=True)
    phone = db.Column(db.String(50), nullable=True)
    graduation_year = db.Column(db.Integer, nullable=False, index=True)
    department = db.Column(db.String(100), nullable=True)
    current_company = db.Column(db.String(150), nullable=True, index=True)
    current_role = db.Column(db.String(150), nullable=True)
    linkedin_url = db.Column(db.String(255), nullable=True)
    willing_to_mentor = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=True, nullable=False)
    consent_share_contact = db.Column(db.Boolean, default=False, nullable=False)

    @property
    def branch(self):
        return self.department

    @branch.setter
    def branch(self, val):
        self.department = val

    # Relationships
    student = db.relationship("Student")

    def to_public_dict(self, include_private=False):
        """
        Public-facing alumni profile.
        Strictly enforces privacy: does NOT expose email or private contacts without explicit consent.
        """
        show_contact = include_private or bool(self.consent_share_contact)
        return {
            "id": self.id,
            "name": self.name,
            "graduation_year": self.graduation_year,
            "branch": self.department,
            "department": self.department,
            "current_company": self.current_company,
            "role": self.current_role,
            "current_role": self.current_role,
            "linkedin_profile": self.linkedin_url,
            "linkedin_url": self.linkedin_url,
            "is_willing_to_mentor": self.willing_to_mentor,
            "is_verified": self.is_verified,
            "contact_email": self.email if show_contact else None,
            "contact_phone": self.phone if show_contact else None,
            "contact_masked": not show_contact
        }

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "graduation_year": self.graduation_year,
            "branch": self.department,
            "department": self.department,
            "current_company": self.current_company,
            "role": self.current_role,
            "current_role": self.current_role,
            "linkedin_url": self.linkedin_url,
            "linkedin_profile": self.linkedin_url,
            "is_willing_to_mentor": self.willing_to_mentor,
            "is_verified": self.is_verified,
            "consent_share_contact": self.consent_share_contact
        }

    def __repr__(self):
        return f"<Alumni id={self.id} name='{self.name}' company='{self.current_company}' verified={self.is_verified}>"


class Announcement(db.Model, TimestampMixin):
    """
    Broadcast announcements from the college placement cell to students.
    """
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    target_audience = db.Column(db.String(50), default="ALL", nullable=False)  # ALL, DEPARTMENT, BATCH
    target_value = db.Column(db.String(100), nullable=True)  # e.g., 'Computer Science' or '2026'
    posted_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    priority = db.Column(db.String(50), default="Normal", nullable=False)  # Normal, High, Urgent

    # Relationships
    posted_by = db.relationship("User")

    def __repr__(self):
        return f"<Announcement id={self.id} title='{self.title}' target='{self.target_audience}'>"


class StudentIntervention(db.Model, TimestampMixin):
    """
    Proactive support and counseling interventions recorded by the placement cell for at-risk candidates.
    """
    __tablename__ = "student_interventions"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    risk_indicators = db.Column(db.Text, nullable=True)  # JSON string or comma-separated list of identified risk factors
    intervention_type = db.Column(db.String(100), default="Counseling Session", nullable=False)  # Counseling Session, Resume Review, Technical Bootcamp, Mock Interview, 1-on-1 Mentorship
    action_plan = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default="OPEN", nullable=False, index=True)  # OPEN, IN_PROGRESS, RESOLVED

    # Relationships
    student = db.relationship("Student", backref=db.backref("interventions", cascade="all, delete-orphan"))
    assigned_admin = db.relationship("User")

    def __repr__(self):
        return f"<StudentIntervention id={self.id} student_id={self.student_id} status='{self.status}'>"

