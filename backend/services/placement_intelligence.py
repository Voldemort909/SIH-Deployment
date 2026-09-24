"""
Placement Intelligence Service: "Why Am I Not Getting Selected?"
Evidence-based diagnosis of student application outcomes, recurring skill gaps,
interview feedback, readiness indicators, and actionable upskilling recommendations.
"""
import logging
from typing import Dict, Any, List, Optional
from collections import Counter
from datetime import datetime, timezone

from backend.extensions import db
from backend.models.user import Student, User
from backend.models.application import Application, Feedback, ApplicationStatusHistory
from backend.models.job import Job
from backend.models.skill import Skill, StudentSkill, JobSkill
from backend.models.resume import Resume, ResumeAnalysis
from backend.models.assessment import AssessmentAttempt
from backend.models.workshop import Workshop, WorkshopRegistration
from backend.models.company import Company
from backend.models.placement import PlacementDriveStudent

logger = logging.getLogger(__name__)


class PlacementIntelligenceService:
    """
    Evidence-based diagnosis engine for campus recruitment conversion.
    Analyzes application history, job requirements, recurring skill gaps,
    employer feedback, and generates tailored upskilling roadmaps.
    """

    @staticmethod
    def diagnose_selection_bottlenecks(student_id: int) -> Dict[str, Any]:
        """
        Executes full diagnostic evaluation for a student to determine why
        they may not be converting applications into final offers.
        """
        student = Student.query.get(student_id)
        if not student:
            return {
                "status": "error",
                "message": f"Student with ID {student_id} not found"
            }

        # 1. Fetch Student Applications
        applications = Application.query.filter_by(student_id=student.id).all()

        # 2. Compute Application Funnel & Identify Bottleneck
        funnel_data = PlacementIntelligenceService._compute_application_funnel(applications)

        # 3. Analyze Job Requirements vs Student Skills (Recurring Patterns)
        skill_analysis = PlacementIntelligenceService._analyze_recurring_skill_patterns(student, applications)

        # 4. Extract & Distinguish Verified Employer Feedback
        feedback_analysis = PlacementIntelligenceService._extract_employer_feedback(student, applications)

        # 5. Readiness & Profile Health (ATS, Projects, Assessments)
        readiness_data = PlacementIntelligenceService._analyze_readiness_metrics(student)

        # 6. Synthesize Actionable Upskilling Recommendations
        recommendations = PlacementIntelligenceService._generate_actionable_recommendations(
            student=student,
            missing_skills=skill_analysis["recurring_skill_gaps"],
            funnel=funnel_data
        )

        return {
            "status": "success",
            "data": {
                "student_id": student.id,
                "student_name": f"{student.first_name} {student.last_name}",
                "department": student.department,
                "batch_year": student.batch_year,
                "cgpa": float(student.cgpa) if student.cgpa is not None else None,
                "funnel": funnel_data,
                "skill_patterns": skill_analysis,
                "employer_feedback": feedback_analysis,
                "readiness": readiness_data,
                "recommendations": recommendations,
                "disclaimer": (
                    "Important: Inferences above are derived from requirement frequencies across your "
                    "applied job postings. A requirement is treated as a potential skill gap, not a confirmed "
                    "rejection reason, unless validated by explicit employer feedback."
                ),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        }

    # =========================================================================
    # 1. APPLICATION FUNNEL & BOTTLENECK DETECTION
    # =========================================================================

    @staticmethod
    def _compute_application_funnel(applications: List[Application]) -> Dict[str, Any]:
        """
        Computes stage-by-stage conversion rates and identifies the primary recruitment bottleneck.
        """
        total = len(applications)

        # Stage buckets
        status_counts = Counter(app.current_status.upper() for app in applications)

        applied_count = total
        under_review_count = status_counts.get("UNDER_REVIEW", 0)
        shortlisted_count = (
            status_counts.get("SHORTLISTED", 0) +
            status_counts.get("ASSESSMENT", 0) +
            status_counts.get("INTERVIEW", 0) +
            status_counts.get("SELECTED", 0) +
            status_counts.get("OFFERED", 0)
        )
        assessment_count = (
            status_counts.get("ASSESSMENT", 0) +
            status_counts.get("INTERVIEW", 0) +
            status_counts.get("SELECTED", 0) +
            status_counts.get("OFFERED", 0)
        )
        interview_count = (
            status_counts.get("INTERVIEW", 0) +
            status_counts.get("SELECTED", 0) +
            status_counts.get("OFFERED", 0)
        )
        selected_count = status_counts.get("SELECTED", 0) + status_counts.get("OFFERED", 0)
        rejected_count = status_counts.get("REJECTED", 0)

        # Conversion rates
        shortlisting_rate = round((shortlisted_count / total * 100), 1) if total > 0 else 0.0
        shortlist_to_interview_rate = round((interview_count / shortlisted_count * 100), 1) if shortlisted_count > 0 else 0.0
        interview_to_selection_rate = round((selected_count / interview_count * 100), 1) if interview_count > 0 else 0.0
        overall_selection_rate = round((selected_count / total * 100), 1) if total > 0 else 0.0

        # Bottleneck Stage Detection
        if total == 0:
            bottleneck_stage = "No Application History"
            bottleneck_summary = "You haven't submitted any job applications yet."
            bottleneck_detail = "Submit applications to campus drives or job listings to unlock diagnostic analysis."
            bottleneck_severity = "INFO"
        elif shortlisting_rate < 30.0:
            bottleneck_stage = "Resume Screening & Profile Matching"
            bottleneck_summary = f"Low shortlisting rate ({shortlisting_rate}%). Majority of applications drop off at initial screening."
            bottleneck_detail = (
                "Based on your application history, applications are predominantly filtered out before the shortlist "
                "or assessment phase. This typically points to resume ATS alignment, missing critical keywords, "
                "or portfolio project gaps relative to job specifications."
            )
            bottleneck_severity = "HIGH"
        elif shortlist_to_interview_rate < 35.0:
            bottleneck_stage = "Pre-Interview Assessment Stage"
            bottleneck_summary = f"Shortlist-to-Interview conversion is low ({shortlist_to_interview_rate}%)."
            bottleneck_detail = (
                "Based on your application history, you successfully clear initial screening but drop off before "
                "reaching technical or HR interview rounds. Focus on data structures, algorithmic tests, and screening assessments."
            )
            bottleneck_severity = "HIGH"
        elif interview_to_selection_rate < 30.0:
            bottleneck_stage = "Interview & Final Evaluation Stage"
            bottleneck_summary = f"Interview conversion is low ({interview_to_selection_rate}% from {interview_count} interviews)."
            bottleneck_detail = (
                "Based on your application history, you successfully reach interview rounds but face challenges converting "
                "them into final job offers. Focus on system architecture articulation, behavioral questions, and mock interview practice."
            )
            bottleneck_severity = "HIGH"
        else:
            bottleneck_stage = "Healthy Progression"
            bottleneck_summary = f"Steady conversion across stages ({shortlisting_rate}% shortlist, {overall_selection_rate}% selected)."
            bottleneck_detail = (
                "Your application conversion rates are balanced. Continue maintaining profile quality and targeting high-affinity roles."
            )
            bottleneck_severity = "LOW"

        return {
            "total_applications": total,
            "shortlisted_count": shortlisted_count,
            "interview_count": interview_count,
            "selected_count": selected_count,
            "rejected_count": rejected_count,
            "stage_breakdown": {
                "applied": applied_count,
                "under_review": under_review_count,
                "shortlisted": shortlisted_count,
                "assessment": assessment_count,
                "interview": interview_count,
                "selected": selected_count,
                "rejected": rejected_count
            },
            "conversion_rates": {
                "shortlisting_rate": shortlisting_rate,
                "shortlist_to_interview_rate": shortlist_to_interview_rate,
                "interview_to_selection_rate": interview_to_selection_rate,
                "overall_selection_rate": overall_selection_rate
            },
            "bottleneck": {
                "stage": bottleneck_stage,
                "summary": bottleneck_summary,
                "detail": bottleneck_detail,
                "severity": bottleneck_severity
            }
        }

    # =========================================================================
    # 2. JOB REQUIREMENTS VS STUDENT SKILLS (RECURRING PATTERNS)
    # =========================================================================

    @staticmethod
    def _analyze_recurring_skill_patterns(student: Student, applications: List[Application]) -> Dict[str, Any]:
        """
        Scans all jobs the student applied for, extracts skill demands, counts frequency,
        and isolates recurring skill gaps without speculating beyond data.
        """
        # Student skills (normalized to lowercase for matching, mapped to original case)
        student_skills_map = {
            ss.skill.name.lower(): ss.skill.name
            for ss in student.student_skills
            if ss.skill
        }
        student_skill_list = list(student_skills_map.values())

        applied_jobs = [app.job for app in applications if app.job]
        total_applied_jobs = len(applied_jobs)

        if total_applied_jobs == 0:
            return {
                "total_applied_jobs": 0,
                "student_skills": student_skill_list,
                "demanded_skills_frequency": [],
                "matched_skills_in_applications": [],
                "recurring_skill_gaps": [],
                "summary_statement": "No application data available to analyze recurring skill patterns."
            }

        # Count frequency of each required skill across applied jobs
        skill_counts: Counter = Counter()
        skill_priority_map: Dict[str, Counter] = {}
        skill_original_name: Dict[str, str] = {}

        for job in applied_jobs:
            job_skills = JobSkill.query.filter_by(job_id=job.id).all()
            for js in job_skills:
                if js.skill:
                    s_name = js.skill.name
                    s_key = s_name.lower()
                    skill_counts[s_key] += 1
                    skill_original_name[s_key] = s_name

                    if s_key not in skill_priority_map:
                        skill_priority_map[s_key] = Counter()
                    skill_priority_map[s_key][js.priority] += 1

        # Separate matched vs missing
        matched_list = []
        gaps_list = []

        for s_key, count in skill_counts.most_common():
            orig_name = skill_original_name[s_key]
            pct = round((count / total_applied_jobs * 100), 1)
            priority_dist = dict(skill_priority_map.get(s_key, {}))
            is_critical = priority_dist.get("Critical", 0) > 0

            item = {
                "skill": orig_name,
                "frequency": count,
                "total_applied_jobs": total_applied_jobs,
                "percentage_in_applied_jobs": pct,
                "priority_breakdown": priority_dist,
                "is_critical": is_critical
            }

            if s_key in student_skills_map:
                item["status"] = "Acquired"
                matched_list.append(item)
            else:
                item["status"] = "Potential Skill Gap"
                item["evidence_statement"] = (
                    f"Based on your application history, {orig_name} appears in {count} of {total_applied_jobs} "
                    f"applied jobs ({pct}%), but is not currently present in your profile."
                )
                item["insight"] = "This requirement appears frequently in the roles you applied for."
                gaps_list.append(item)

        # Generate evidence-based narrative
        top_gaps = [g["skill"] for g in gaps_list[:3]]
        if top_gaps:
            summary_statement = (
                f"Based on your application history across {total_applied_jobs} jobs, "
                f"{', '.join(top_gaps)} appear frequently in job requirements but are not listed on your profile. "
                f"These represent potential skill gaps worth addressing."
            )
        else:
            summary_statement = (
                f"Based on your application history across {total_applied_jobs} jobs, "
                f"your profile skills closely match the technical requirements of the roles applied for."
            )

        return {
            "total_applied_jobs": total_applied_jobs,
            "student_skills": student_skill_list,
            "demanded_skills_frequency": [
                {
                    "skill": skill_original_name[k],
                    "frequency": c,
                    "percentage": round(c / total_applied_jobs * 100, 1)
                }
                for k, c in skill_counts.most_common(10)
            ],
            "matched_skills_in_applications": matched_list,
            "recurring_skill_gaps": gaps_list,
            "summary_statement": summary_statement
        }

    # =========================================================================
    # 3. VERIFIED EMPLOYER & INTERVIEW FEEDBACK
    # =========================================================================

    @staticmethod
    def _extract_employer_feedback(student: Student, applications: List[Application]) -> Dict[str, Any]:
        """
        Extracts verified recruiter/interviewer feedback from the Feedback model.
        Strict rule: Never claim a skill caused rejection unless explicit feedback exists.
        Distinguishes verified employer feedback with 'Employer feedback indicates...'.
        """
        app_ids = [app.id for app in applications]
        feedbacks = Feedback.query.filter(
            (Feedback.target_student_id == student.id) |
            (Feedback.application_id.in_(app_ids) if app_ids else False)
        ).all()

        if not feedbacks:
            return {
                "has_employer_feedback": False,
                "feedback_count": 0,
                "notice": "No explicit employer feedback has been recorded for your applications yet.",
                "notice_detail": "Insights in this diagnosis represent statistical requirement patterns, not confirmed employer remarks.",
                "average_ratings": None,
                "verified_feedback_entries": []
            }

        entries = []
        tech_ratings = []
        prob_ratings = []
        comm_ratings = []
        overall_ratings = []

        for fb in feedbacks:
            company_name = "Recruiter"
            job_title = "Applied Role"
            if fb.application and fb.application.job:
                job_title = fb.application.job.title
                if fb.application.job.company:
                    company_name = fb.application.job.company.name

            if fb.technical_rating:
                tech_ratings.append(fb.technical_rating)
            if fb.problem_solving_rating:
                prob_ratings.append(fb.problem_solving_rating)
            if fb.communication_rating:
                comm_ratings.append(fb.communication_rating)
            if fb.rating:
                overall_ratings.append(fb.rating)

            entries.append({
                "id": fb.id,
                "company_name": company_name,
                "job_title": job_title,
                "feedback_type": fb.feedback_type,
                "recommendation": fb.recommendation,
                "ratings": {
                    "overall": fb.rating,
                    "technical": fb.technical_rating,
                    "problem_solving": fb.problem_solving_rating,
                    "communication": fb.communication_rating
                },
                "comments": fb.comments,
                "evidence_statement": f"Employer feedback indicates: \"{fb.comments}\"",
                "created_at": fb.created_at.isoformat() if fb.created_at else None
            })

        avg_ratings = {
            "overall": round(sum(overall_ratings) / len(overall_ratings), 1) if overall_ratings else None,
            "technical": round(sum(tech_ratings) / len(tech_ratings), 1) if tech_ratings else None,
            "problem_solving": round(sum(prob_ratings) / len(prob_ratings), 1) if prob_ratings else None,
            "communication": round(sum(comm_ratings) / len(comm_ratings), 1) if comm_ratings else None,
        }

        return {
            "has_employer_feedback": True,
            "feedback_count": len(entries),
            "notice": "Verified employer feedback is available for your applications.",
            "average_ratings": avg_ratings,
            "verified_feedback_entries": entries
        }

    # =========================================================================
    # 4. READINESS & PROFILE HEALTH INDICATORS
    # =========================================================================

    @staticmethod
    def _analyze_readiness_metrics(student: Student) -> Dict[str, Any]:
        """
        Aggregates ATS score, portfolio projects count, and assessment test performance.
        """
        # Resume ATS
        primary_resume = (
            Resume.query.filter_by(student_id=student.id, is_primary=True).first() or
            Resume.query.filter_by(student_id=student.id).order_by(Resume.updated_at.desc()).first()
        )
        ats_score = None
        resume_name = None
        if primary_resume:
            resume_name = primary_resume.file_name
            if primary_resume.analysis and primary_resume.analysis.overall_score is not None:
                ats_score = float(primary_resume.analysis.overall_score)

        # Projects
        projects = student.projects or []
        project_count = len(projects)
        project_titles = [p.title for p in projects]

        # Assessment Attempts
        attempts = AssessmentAttempt.query.filter_by(student_id=student.id).all()
        total_attempts = len(attempts)
        passed_attempts = sum(1 for a in attempts if a.passed)
        avg_score = round(sum(a.score_percentage for a in attempts) / total_attempts, 1) if total_attempts > 0 else None
        pass_rate = round((passed_attempts / total_attempts * 100), 1) if total_attempts > 0 else None

        # Placement Drive Stages
        drive_records = PlacementDriveStudent.query.filter_by(student_id=student.id).all()
        drive_stages = Counter(d.stage for d in drive_records)

        return {
            "resume": {
                "has_resume": primary_resume is not None,
                "file_name": resume_name,
                "ats_score": ats_score,
                "status": (
                    "Optimal" if ats_score and ats_score >= 70
                    else "Needs Improvement" if ats_score and ats_score >= 50
                    else "Critically Low / Not Analyzed"
                )
            },
            "projects": {
                "total_projects": project_count,
                "project_titles": project_titles,
                "status": (
                    "Strong Portfolio" if project_count >= 3
                    else "Adequate (2 Projects)" if project_count == 2
                    else "Minimal (Recommend 2-3 projects)"
                )
            },
            "assessments": {
                "total_attempts": total_attempts,
                "passed_attempts": passed_attempts,
                "pass_rate": pass_rate,
                "average_score": avg_score
            },
            "campus_drives": {
                "registered_drives_count": len(drive_records),
                "stages_reached": dict(drive_stages)
            }
        }

    # =========================================================================
    # 5. ACTIONABLE UPSKILLING ROADMAP
    # =========================================================================

    @staticmethod
    def _generate_actionable_recommendations(
        student: Student,
        missing_skills: List[Dict[str, Any]],
        funnel: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generates actionable, evidence-based suggestions:
        - Skills to improve (ranked by occurrence in applied jobs)
        - Concrete portfolio projects to build
        - Relevant active workshops from database
        - Suitable alternative job roles on platform
        - Recommended corporate partners
        """
        # 1. Skills to Improve (top 5 missing from applied jobs)
        skills_to_improve = [
            {
                "skill": gap["skill"],
                "reason": f"Required in {gap['frequency']} applied job(s) ({gap['percentage_in_applied_jobs']}%)",
                "priority": "High" if gap.get("is_critical") or gap["frequency"] >= 2 else "Medium"
            }
            for gap in missing_skills[:5]
        ]

        # 2. Tailored Projects to Build targeting missing skills
        gap_names = [g["skill"].lower() for g in missing_skills[:4]]
        suggested_projects = []

        if any(k in gap_names for k in ["docker", "kubernetes", "aws", "devops", "cloud"]):
            suggested_projects.append({
                "title": "Containerized Microservices CI/CD Pipeline",
                "target_skills": ["Docker", "AWS", "CI/CD", "Linux"],
                "description": "Develop a multi-service REST application containerized with Docker, automated via GitHub Actions, and deployed on AWS EC2 or ECS."
            })

        if any(k in gap_names for k in ["dsa", "algorithms", "data structures", "system design"]):
            suggested_projects.append({
                "title": "Interactive Algorithm Visualizer & Performance Benchmarker",
                "target_skills": ["Data Structures", "Algorithms", "System Design"],
                "description": "Build an algorithmic visualizer demonstrating dynamic programming, graph traversal, and tree indexing with comparative complexity benchmarks."
            })

        if any(k in gap_names for k in ["react", "node", "full stack", "mongodb", "postgresql", "sql"]):
            suggested_projects.append({
                "title": "Full-Stack Enterprise Workflow Management Dashboard",
                "target_skills": ["React", "PostgreSQL / SQL", "REST API", "JWT"],
                "description": "Implement an end-to-end full stack dashboard featuring role-based authentication, relational schema indexing, and real-time state management."
            })

        if any(k in gap_names for k in ["python", "machine learning", "pandas", "data science", "nlp"]):
            suggested_projects.append({
                "title": "Predictive Analytics & Recommendation Engine",
                "target_skills": ["Python", "Pandas", "Scikit-Learn", "FastAPI"],
                "description": "Build a predictive machine learning pipeline with automated data preprocessing, model inference APIs, and performance evaluation matrices."
            })

        # Fallback project if none matched specific keywords
        if not suggested_projects:
            suggested_projects.append({
                "title": "Production-Grade Distributed Web Service",
                "target_skills": ["Backend Architecture", "SQL Database", "API Testing"],
                "description": "Create a modular REST API complete with automated integration tests, OpenAPI documentation, and relational database migrations."
            })

        # 3. Relevant Active Platform Workshops
        workshops = Workshop.query.order_by(Workshop.start_time.asc()).all()
        relevant_workshops = []
        student_registered_ws = {
            wr.workshop_id for wr in WorkshopRegistration.query.filter_by(student_id=student.id).all()
        }

        for ws in workshops:
            ws_text = f"{ws.title} {ws.description or ''}".lower()
            is_relevant = any(k in ws_text for k in gap_names) or any(
                k in ws_text for k in ["interview", "placement", "prep", "resume", "dsa", "coding"]
            )
            if is_relevant or len(relevant_workshops) < 2:
                instructor_name = "Industry Expert"
                if ws.instructor:
                    instructor_name = f"{ws.instructor.first_name} {ws.instructor.last_name}"
                    if ws.instructor.company:
                        instructor_name += f" ({ws.instructor.company.name})"

                relevant_workshops.append({
                    "id": ws.id,
                    "title": ws.title,
                    "description": ws.description,
                    "instructor": instructor_name,
                    "start_time": ws.start_time.isoformat() if ws.start_time else None,
                    "venue_or_link": ws.venue_or_link,
                    "max_capacity": ws.max_capacity,
                    "registrations_count": len(ws.registrations),
                    "is_already_registered": ws.id in student_registered_ws
                })
            if len(relevant_workshops) >= 3:
                break

        # 4. Suitable Alternative Job Roles
        student_skill_ids = {ss.skill_id for ss in student.student_skills}
        published_jobs = Job.query.filter_by(status="Published").all()
        suitable_roles = []

        for job in published_jobs:
            # Check eligibility
            if student.cgpa and job.min_cgpa and float(student.cgpa) < float(job.min_cgpa):
                continue
            if job.eligible_branches:
                branches = [b.strip().lower() for b in job.eligible_branches.split(",")]
                if student.department and student.department.lower() not in branches:
                    continue

            job_req_skills = JobSkill.query.filter_by(job_id=job.id).all()
            if not job_req_skills:
                continue

            matched_count = sum(1 for js in job_req_skills if js.skill_id in student_skill_ids)
            total_req = len(job_req_skills)
            affinity = round((matched_count / total_req * 100), 1)

            if affinity >= 50.0:
                suitable_roles.append({
                    "job_id": job.id,
                    "title": job.title,
                    "company": job.company.name if job.company else "Partner Company",
                    "domain": job.domain,
                    "job_type": job.job_type,
                    "ctc": job.ctc,
                    "affinity_pct": affinity,
                    "matched_skills_count": matched_count,
                    "total_required_skills": total_req
                })

        suitable_roles.sort(key=lambda x: x["affinity_pct"], reverse=True)
        suitable_roles = suitable_roles[:4]

        # 5. Recommended Companies
        rec_companies = []
        seen_companies = set()
        for role in suitable_roles:
            c_name = role["company"]
            if c_name not in seen_companies:
                seen_companies.add(c_name)
                rec_companies.append({
                    "name": c_name,
                    "matching_role": role["title"],
                    "affinity": role["affinity_pct"]
                })

        return {
            "skills_to_improve": skills_to_improve,
            "suggested_projects": suggested_projects[:3],
            "relevant_workshops": relevant_workshops,
            "suitable_job_roles": suitable_roles,
            "recommended_companies": rec_companies[:3]
        }
