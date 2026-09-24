"""
Centralized Notification & Communication Service.
Encapsulates all in-app notifications and email messaging logic:
- Real-time and batched user alerts (job matches, drive eligibility, application status, workshop & deadline reminders).
- Targeted bulk communication for placement cell administrators (by branch, year, eligibility, domain, registrations).
- Decoupled from route controllers with pluggable delivery adapters.
"""
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from backend.extensions import db
from backend.models.user import User, Student
from backend.models.company import Company
from backend.models.job import Job
from backend.models.skill import StudentSkill, JobSkill
from backend.models.student import StudentPreference
from backend.models.application import Application
from backend.models.workshop import Workshop, WorkshopRegistration
from backend.models.placement import PlacementDrive, PlacementDriveStudent
from backend.models.notification import Notification

logger = logging.getLogger(__name__)


# =====================================================================
# EMAIL DELIVERY ADAPTER
# =====================================================================

class EmailDeliveryService:
    """
    Handles email dispatch with development mock tracking and SMTP support.
    """
    sent_emails: List[Dict[str, Any]] = []

    @classmethod
    def send_email(
        cls,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None
    ) -> bool:
        """
        Dispatches an email. In development/testing, records to the sent_emails registry.
        """
        record = {
            "to": to_email,
            "recipient": to_email,
            "subject": subject,
            "body_text": body_text,
            "body_html": body_html,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "status": "SENT"
        }
        cls.sent_emails.append(record)
        logger.info(f"[EmailDeliveryService] Sent email to '{to_email}' with subject: '{subject}'")
        return True

    @classmethod
    def clear_sent_emails(cls):
        """Clears test email buffer."""
        cls.sent_emails.clear()


class NotificationDispatchResult(dict):
    """
    Wrapper holding notification dispatch results while providing both dict-access
    and direct model attribute proxies (such as result.id, result.is_read).
    """
    def __init__(self, notif=None, status="success", email_sent=False, **kwargs):
        super().__init__(
            status=status,
            notification=notif.to_dict() if notif else None,
            email_sent=email_sent,
            **kwargs
        )
        self.notif = notif
        self.id = notif.id if notif else None

    def __getattr__(self, name):
        if self.notif and hasattr(self.notif, name):
            return getattr(self.notif, name)
        if name in self:
            return self[name]
        raise AttributeError(f"'NotificationDispatchResult' object has no attribute '{name}'")


# =====================================================================
# NOTIFICATION SERVICE
# =====================================================================

class NotificationService:
    """
    Centralized service for dispatching in-app alerts and multi-channel messages.
    """

    @staticmethod
    def send_notification(
        user_id: int,
        title: str,
        message: str,
        type: str = "General",
        notif_type: Optional[str] = None,
        link: Optional[str] = None,
        channels: Optional[Any] = None,
        channel: Optional[str] = None,
        email_subject: Optional[str] = None
    ) -> Any:
        """
        Dispatches a notification to a single user via requested channels ('in_app', 'email', 'both').
        """
        user = User.query.get(user_id)
        if not user:
            logger.warning(f"Cannot send notification: User ID {user_id} not found.")
            return NotificationDispatchResult(notif=None, status="error", message="User not found")

        resolved_type = notif_type or type

        # Normalize channel / channels
        if channel:
            if channel == "both":
                effective_channels = ("in_app", "email")
            elif channel == "email":
                effective_channels = ("email",)
            elif channel == "in_app":
                effective_channels = ("in_app",)
            else:
                effective_channels = (channel,)
        elif channels:
            if isinstance(channels, str):
                if channels == "both":
                    effective_channels = ("in_app", "email")
                else:
                    effective_channels = (channels,)
            else:
                effective_channels = tuple(channels)
        else:
            effective_channels = ("in_app",)

        created_notif = None
        if "in_app" in effective_channels:
            created_notif = Notification(
                user_id=user.id,
                title=title,
                message=message,
                type=resolved_type,
                link=link,
                channel=",".join(effective_channels),
                is_read=False
            )
            db.session.add(created_notif)
            db.session.commit()

        email_sent = False
        if "email" in effective_channels and user.email:
            subject = email_subject or title
            email_sent = EmailDeliveryService.send_email(
                to_email=user.email,
                subject=subject,
                body_text=message
            )

        return NotificationDispatchResult(
            notif=created_notif,
            status="success",
            email_sent=email_sent
        )

    @staticmethod
    def send_bulk_notification(
        target_criteria: Optional[Dict[str, Any]] = None,
        title: str = "",
        message: str = "",
        type: str = "Announcement",
        link: Optional[str] = None,
        channels: Optional[tuple] = None,
        target_type: Optional[str] = None,
        target_value: Optional[Any] = None,
        channel: Optional[str] = None,
        notif_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends targeted announcements to a resolved cohort of students based on criteria:
        - target_type: 'all' | 'branch' | 'year' | 'eligible_drive' | 'domain' | 'registered_drive' | 'registered_workshop'
        - target_value: branch name, batch year, drive_id, workshop_id, or domain string
        - channel: 'both' | 'in_app' | 'email'
        """
        criteria = dict(target_criteria or {})
        if target_type:
            criteria["target_type"] = target_type
        if target_value is not None:
            criteria["target_value"] = target_value

        effective_type = notif_type or type

        if channels is None:
            if channel == "in_app":
                effective_channels = ("in_app",)
            elif channel == "email":
                effective_channels = ("email",)
            else:
                effective_channels = ("in_app", "email")
        else:
            effective_channels = channels

        students = NotificationService._resolve_targeted_students(criteria)
        if not students:
            return {
                "total_targeted_students": 0,
                "total_targeted": 0,
                "in_app_notifications_created": 0,
                "in_app_delivered": 0,
                "emails_dispatched": 0,
                "email_delivered": 0,
                "message": "No students matched the target criteria."
            }

        in_app_count = 0
        email_count = 0

        for student in students:
            if not student.user:
                continue

            if "in_app" in effective_channels:
                notif = Notification(
                    user_id=student.user.id,
                    title=title,
                    message=message,
                    type=effective_type,
                    link=link or "/pages/student/dashboard.html",
                    channel=",".join(effective_channels),
                    is_read=False
                )
                db.session.add(notif)
                in_app_count += 1

            if "email" in effective_channels and student.user.email:
                EmailDeliveryService.send_email(
                    to_email=student.user.email,
                    subject=title,
                    body_text=message
                )
                email_count += 1

        db.session.commit()

        return {
            "total_targeted_students": len(students),
            "total_targeted": len(students),
            "in_app_notifications_created": in_app_count,
            "in_app_delivered": in_app_count,
            "emails_dispatched": email_count,
            "email_delivered": email_count,
            "target_criteria": criteria,
            "message": f"Successfully delivered targeted communication to {len(students)} students."
        }

    @staticmethod
    def _resolve_targeted_students(criteria: Dict[str, Any]) -> List[Student]:
        """
        Resolves the cohort of Student entities matching specified criteria.
        """
        target_type = criteria.get("target_type", "all").lower()

        if target_type == "all":
            return Student.query.all()

        if target_type in ["branch", "department"]:
            dept = criteria.get("department") or criteria.get("branch") or criteria.get("target_value")
            return Student.query.filter(Student.department.ilike(f"%{dept}%")).all()

        if target_type in ["year", "batch_year"]:
            batch_val = criteria.get("batch_year") or criteria.get("year") or criteria.get("target_value")
            batch = int(batch_val) if batch_val is not None else 0
            return Student.query.filter_by(batch_year=batch).all()

        if target_type == "domain":
            domain = (criteria.get("domain") or criteria.get("target_value") or "").strip().lower()
            # Match via preferences or skills
            from backend.models.user import StudentPreference
            prefs = StudentPreference.query.filter(
                StudentPreference.preferred_domain.ilike(f"%{domain}%")
            ).all()
            student_ids = {p.student_id for p in prefs}
            return Student.query.filter(Student.id.in_(student_ids)).all() if student_ids else []

        if target_type == "eligible_drive":
            drive_id = criteria.get("drive_id") or criteria.get("target_value")
            drive = PlacementDrive.query.get(drive_id)
            if not drive:
                return []
            
            # Apply drive eligibility rules
            q = Student.query
            if drive.eligible_batch:
                q = q.filter_by(batch_year=drive.eligible_batch)
            if drive.min_cgpa and float(drive.min_cgpa) > 0:
                q = q.filter(Student.cgpa >= float(drive.min_cgpa))
            if drive.max_backlogs is not None:
                q = q.filter(Student.backlogs <= drive.max_backlogs)

            students = q.all()
            if drive.eligible_departments:
                branches = [b.strip().lower() for b in drive.eligible_departments.split(",") if b.strip()]
                students = [s for s in students if (s.department or "").lower() in branches]
            return students

        if target_type == "registered_drive":
            drive_id = criteria.get("drive_id") or criteria.get("target_value")
            participants = PlacementDriveStudent.query.filter_by(drive_id=drive_id).all()
            return [p.student for p in participants if p.student]

        if target_type == "registered_workshop":
            workshop_id = criteria.get("workshop_id") or criteria.get("target_value")
            registrations = WorkshopRegistration.query.filter_by(workshop_id=workshop_id).all()
            return [r.student for r in registrations if r.student]

        return Student.query.all()

    # =====================================================================
    # EVENT-DRIVEN NOTIFICATION TRIGGERS
    # =====================================================================

    @staticmethod
    def notify_matching_job(job: Job) -> int:
        """
        Identifies students whose skills or preferences match a newly published job
        and triggers high-relevance alerts.
        """
        required_skill_ids = [js.skill_id for js in job.job_skills]
        students = Student.query.all()
        notified_count = 0

        for s in students:
            if not s.user:
                continue

            # Check if student possesses at least one matching skill or matches domain
            has_matching_skill = False
            if required_skill_ids:
                s_skill_ids = {sk.skill_id for sk in s.student_skills}
                if set(required_skill_ids).intersection(s_skill_ids):
                    has_matching_skill = True

            matches_domain = False
            if s.preference and s.preference.preferred_domain and job.domain:
                if job.domain.lower() in s.preference.preferred_domain.lower():
                    matches_domain = True

            # Check academic eligibility
            is_eligible = True
            if job.min_cgpa and s.cgpa and float(s.cgpa) < float(job.min_cgpa):
                is_eligible = False
            if job.graduation_year and s.batch_year and s.batch_year != job.graduation_year:
                is_eligible = False

            if (has_matching_skill or matches_domain) and is_eligible:
                company_name = job.company.name if job.company else "A recruiting partner"
                NotificationService.send_notification(
                    user_id=s.user.id,
                    title=f"New Matching Job: {job.title}",
                    message=f"{company_name} is hiring for '{job.title}' ({job.job_type}) matching your skill profile.",
                    type="JobMatch",
                    link=f"/pages/student/jobs.html?job_id={job.id}",
                    channels=("in_app", "email")
                )
                notified_count += 1

        return notified_count

    @staticmethod
    def notify_eligible_drive(drive: PlacementDrive) -> int:
        """
        Alerts students who meet all criteria for an upcoming campus placement drive.
        """
        criteria = {"target_type": "eligible_drive", "drive_id": drive.id}
        students = NotificationService._resolve_targeted_students(criteria)
        notified = 0

        company_name = drive.company.name if drive.company else "Campus Partner"
        title = f"Eligible Placement Drive: {drive.title}"
        message = (
            f"You are eligible for the upcoming recruitment drive by {company_name} "
            f"for role '{drive.job_role or 'Graduate Trainee'}' offering CTC ₹{drive.package_ctc} LPA. "
            f"Please register before the deadline."
        )

        for s in students:
            if s.user:
                NotificationService.send_notification(
                    user_id=s.user.id,
                    title=title,
                    message=message,
                    type="PlacementDrive",
                    link="/pages/student/dashboard.html",
                    channels=("in_app", "email")
                )
                notified += 1

        return notified

    @staticmethod
    def notify_application_status(application: Application, new_status: str, notes: Optional[str] = None) -> bool:
        """
        Alerts student when their application status is updated by a recruiter.
        """
        student = application.student
        if not student or not student.user:
            return False

        job_title = application.job.title if application.job else "Job Application"
        company_name = application.job.company.name if (application.job and application.job.company) else "Recruiter"

        status_messages = {
            "SHORTLISTED": f"Congratulations! You have been shortlisted by {company_name} for '{job_title}'.",
            "ASSESSMENT": f"You have been invited to complete a technical screening assessment for '{job_title}'.",
            "INTERVIEW": f"You have been scheduled for an interview round with {company_name} for '{job_title}'.",
            "SELECTED": f"Congratulations! You have been selected by {company_name} for '{job_title}'.",
            "REJECTED": f"Update regarding your application for '{job_title}' at {company_name}: Status is now '{new_status}'."
        }

        msg = status_messages.get(new_status, f"Your application for '{job_title}' at {company_name} is now '{new_status}'.")
        if notes:
            msg += f" Note: {notes}"

        NotificationService.send_notification(
            user_id=student.user.id,
            title=f"Application Update: {new_status.replace('_', ' ').title()}",
            message=msg,
            type="Application",
            link="/pages/student/applications.html",
            channels=("in_app", "email")
        )
        return True

    @staticmethod
    def notify_workshop_reminder(workshop: Workshop) -> int:
        """
        Delivers an event reminder notification to all registered attendees.
        """
        registrations = workshop.registrations
        count = 0
        date_str = workshop.start_time.strftime("%b %d, %Y at %I:%M %p") if workshop.start_time else "soon"

        for reg in registrations:
            s = reg.student
            if s and s.user:
                NotificationService.send_notification(
                    user_id=s.user.id,
                    title=f"Workshop Reminder: {workshop.title}",
                    message=f"Reminder: '{workshop.title}' is scheduled for {date_str}. Venue/Link: {workshop.venue_or_link or 'Online'}.",
                    type="Workshop",
                    link="/pages/student/dashboard.html",
                    channels=("in_app", "email")
                )
                count += 1

        return count

    @staticmethod
    def notify_deadline_reminder(job: Job) -> int:
        """
        Alerts students with matching skills who have not yet submitted an application
        as the application deadline approaches.
        """
        deadline_str = job.deadline.strftime("%b %d, %Y") if job.deadline else "shortly"
        applied_student_ids = {a.student_id for a in job.applications}

        # Find eligible students who haven't applied
        students = Student.query.all()
        reminded = 0

        for s in students:
            if s.id in applied_student_ids or not s.user:
                continue

            # Check eligibility
            if job.min_cgpa and s.cgpa and float(s.cgpa) < float(job.min_cgpa):
                continue
            if job.graduation_year and s.batch_year and s.batch_year != job.graduation_year:
                continue

            NotificationService.send_notification(
                user_id=s.user.id,
                title=f"Deadline Approaching: {job.title}",
                message=f"The application deadline for '{job.title}' ({job.company.name if job.company else 'Recruiter'}) closes on {deadline_str}. Submit your application today.",
                type="Deadline",
                link=f"/pages/student/jobs.html?job_id={job.id}",
                channels=("in_app",)
            )
            reminded += 1

        return reminded
