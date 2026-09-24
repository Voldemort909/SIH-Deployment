from werkzeug.security import generate_password_hash, check_password_hash
from backend.extensions import db
from backend.models.base import TimestampMixin


class User(db.Model, TimestampMixin):
    """
    Central authentication and identity table.
    Eliminates duplicated auth logic across roles.
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, index=True)  # 'student', 'industry_expert', 'admin'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)

    def set_password(self, password):
        """Hashes the password securely using Werkzeug."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifies the password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    # 1:1 Role-specific profile relationships
    student_profile = db.relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")
    expert_profile = db.relationship("IndustryExpert", back_populates="user", uselist=False, cascade="all, delete-orphan")
    admin_profile = db.relationship("Admin", back_populates="user", uselist=False, cascade="all, delete-orphan")

    @property
    def industry_profile(self):
        """Convenient alias for expert_profile."""
        return self.expert_profile

    # Relationships
    notifications = db.relationship("Notification", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} email='{self.email}' role='{self.role}'>"


class Student(db.Model, TimestampMixin):
    """
    Detailed profile information for Student users.
    """
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    roll_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False, index=True)
    degree = db.Column(db.String(100), nullable=False)
    batch_year = db.Column(db.Integer, nullable=False, index=True)
    cgpa = db.Column(db.Numeric(4, 2), nullable=True)
    backlogs = db.Column(db.Integer, default=0, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    certifications = db.Column(db.Text, nullable=True)  # Text or JSON of certification details
    experience = db.Column(db.Text, nullable=True)      # Text or JSON of internships/work experience

    __table_args__ = (
        db.Index("ix_students_dept_batch", "department", "batch_year"),
    )

    # Relationships
    user = db.relationship("User", back_populates="student_profile")
    preferences = db.relationship("StudentPreference", back_populates="student", uselist=False, cascade="all, delete-orphan")
    resumes = db.relationship("Resume", back_populates="student", cascade="all, delete-orphan")
    student_skills = db.relationship("StudentSkill", back_populates="student", cascade="all, delete-orphan")
    projects = db.relationship("Project", back_populates="student", cascade="all, delete-orphan")
    applications = db.relationship("Application", back_populates="student", cascade="all, delete-orphan")
    placement_records = db.relationship("PlacementRecord", back_populates="student")
    workshop_registrations = db.relationship("WorkshopRegistration", back_populates="student", cascade="all, delete-orphan")
    assessment_attempts = db.relationship("AssessmentAttempt", back_populates="student", cascade="all, delete-orphan")
    placement_drives = db.relationship("PlacementDriveStudent", back_populates="student", cascade="all, delete-orphan")
    feedback_received = db.relationship("Feedback", back_populates="target_student", foreign_keys="Feedback.target_student_id", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Student id={self.id} roll='{self.roll_number}' name='{self.first_name} {self.last_name}'>"


class IndustryExpert(db.Model, TimestampMixin):
    """
    Profile information for Industry Experts and Corporate Recruiters.
    """
    __tablename__ = "industry_experts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    designation = db.Column(db.String(100), nullable=True)
    experience_years = db.Column(db.Integer, nullable=True)
    linkedin_url = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), default="PENDING", nullable=False, index=True)  # PENDING, APPROVED, REJECTED

    # Relationships
    user = db.relationship("User", back_populates="expert_profile")
    company = db.relationship("Company", back_populates="experts")
    workshops = db.relationship("Workshop", back_populates="instructor")
    posted_jobs = db.relationship("Job", back_populates="posted_by")

    def __repr__(self):
        return f"<IndustryExpert id={self.id} name='{self.first_name} {self.last_name}'>"


class Admin(db.Model, TimestampMixin):
    """
    Profile information for College Placement Cell and Institutional Admins.
    """
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    staff_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    designation = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True)

    # Relationships
    user = db.relationship("User", back_populates="admin_profile")

    def __repr__(self):
        return f"<Admin id={self.id} staff_id='{self.staff_id}' name='{self.first_name} {self.last_name}'>"
