"""
SIH Demo Presentation Database Seeder
====================================
Populates the database with realistic, high-fidelity presentation data:
- Platform Admin: admin@college.edu
- Corporate Recruiters:
    * Google Cloud: recruiter@google.com (Approved)
    * Microsoft: recruiter@microsoft.com (Approved)
    * StartupTech: recruiter@startup.io (Pending Verification)
- Student Cohort:
    * Priya Sharma (Placed): priya@campus.edu (Placed at Google Cloud, 18.5 LPA)
    * Aman Verma (Active / Intelligence Target): aman@campus.edu
      (Has 4 apps, 0 offers, recurring Docker/AWS/DSA gaps for "Why Am I Not Getting Selected?")
    * Rahul Gupta (At-Risk): rahul@campus.edu
      (CGPA 5.8, 2 backlogs, flagged with open placement intervention)
    * Neha Patel (Fresh Candidate): neha@campus.edu (IT 2026 Batch)
- Verified Alumni Network (with GDPR-compliant contact privacy masking)
- Historical Placement Records & Company Hiring Trends
- Dynamic Skill Demand & Curated Upskilling Workshops
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
from datetime import datetime, timezone, timedelta, date

from backend.app import create_app
from backend.extensions import db
from backend.models.user import User, Student, IndustryExpert, Admin
from backend.models.company import Company, CompanyHiringHistory
from backend.models.job import Job
from backend.models.skill import Skill, JobSkill, StudentSkill
from backend.models.student import Project, StudentPreference
from backend.models.resume import Resume, ResumeAnalysis
from backend.models.application import Application, ApplicationStatusHistory, Feedback
from backend.models.placement import (
    PlacementRecord,
    PlacementDrive,
    PlacementDriveStudent,
    Alumni,
    Announcement,
    StudentIntervention
)
from backend.models.workshop import Workshop, WorkshopRegistration
from backend.models.assessment import Assessment, AssessmentQuestion, AssessmentAttempt
from backend.models.notification import Notification


def get_demo_passwords():
    """
    Retrieve demo account passwords strictly from environment variables.
    Fails safely if required environment variables are not configured,
    preventing insecure hardcoded default passwords in public repositories.
    """
    demo_password = os.getenv("DEMO_USER_PASSWORD")
    admin_password = os.getenv("DEMO_ADMIN_PASSWORD") or demo_password
    recruiter_password = os.getenv("DEMO_RECRUITER_PASSWORD") or demo_password
    student_password = os.getenv("DEMO_STUDENT_PASSWORD") or demo_password

    missing_vars = []
    if not admin_password:
        missing_vars.append("DEMO_ADMIN_PASSWORD (or DEMO_USER_PASSWORD)")
    if not recruiter_password:
        missing_vars.append("DEMO_RECRUITER_PASSWORD (or DEMO_USER_PASSWORD)")
    if not student_password:
        missing_vars.append("DEMO_STUDENT_PASSWORD (or DEMO_USER_PASSWORD)")

    if missing_vars:
        error_msg = (
            "\n[SECURITY CONFIGURATION ERROR] Missing required environment variable(s) for demo seeding:\n"
            + "\n".join(f"  * {v}" for v in missing_vars)
            + "\n\nPlease configure DEMO_USER_PASSWORD (or individual DEMO_ADMIN_PASSWORD, "
            "DEMO_RECRUITER_PASSWORD, DEMO_STUDENT_PASSWORD) in your .env file before running "
            "this seed script.\nDefault fallback passwords have been removed for public repository security."
        )
        print(error_msg, file=sys.stderr)
        raise ValueError(
            "Missing required demo password environment variables: " + ", ".join(missing_vars)
        )

    return admin_password, recruiter_password, student_password


def seed_database():
    app = create_app()
    with app.app_context():
        admin_password, recruiter_password, student_password = get_demo_passwords()

        print("Initializing database tables...")
        db.create_all()

        # --------------------------------------------------------------------
        # 1. ADMIN USER & PROFILE
        # --------------------------------------------------------------------
        admin_user = User.query.filter_by(email="admin@college.edu").first()
        if not admin_user:
            admin_user = User(
                email="admin@college.edu",
                role="admin",
                is_active=True,
                is_verified=True
            )
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.flush()

            admin_prof = Admin(
                user_id=admin_user.id,
                first_name="Dr. Rajesh",
                last_name="Kulkarni",
                staff_id="TPO-1001",
                designation="Head of Training & Placements",
                department="Central Placement Office"
            )
            db.session.add(admin_prof)
            print(" Created Admin: admin@college.edu")
        else:
            admin_user.set_password(admin_password)
            print(" Admin already exists. Password updated.")

        # --------------------------------------------------------------------
        # 2. COMPANIES
        # --------------------------------------------------------------------
        companies_data = [
            {
                "name": "Google Cloud",
                "industry_type": "Cloud & Artificial Intelligence",
                "location": "Bengaluru, Hyderabad, Mountain View",
                "website": "https://cloud.google.com",
                "description": "Global enterprise cloud platform powering scalable infrastructure, big data analytics, and generative AI models.",
                "domains": "Cloud Computing, Distributed Systems, ML Ops",
                "recruitment_process": "1. Online Coding & Aptitude Assessment\n2. System Architecture Evaluation\n3. Two Technical Rounds\n4. Googliness & Leadership Interview"
            },
            {
                "name": "Microsoft India",
                "industry_type": "Enterprise Software & Cloud",
                "location": "Hyderabad, Bengaluru, Noida",
                "website": "https://www.microsoft.com",
                "description": "Leading global provider of Azure cloud, operating systems, and intelligent enterprise productivity suites.",
                "domains": "Cloud Services, Operating Systems, AI Solutions",
                "recruitment_process": "1. Online Assessment\n2. Technical Problem Solving Round\n3. System Design Round\n4. Behavioral & Culture Fit"
            },
            {
                "name": "Amazon Web Services",
                "industry_type": "Cloud Infrastructure & E-Commerce",
                "location": "Bengaluru, Hyderabad, Chennai",
                "website": "https://aws.amazon.com",
                "description": "World's most comprehensive and broadly adopted cloud platform, offering over 200 fully featured services.",
                "domains": "Distributed Systems, DevOps, High-Scale Web Services",
                "recruitment_process": "1. Online Debugging & Coding Test\n2. System Design Interview\n3. Leadership Principles Evaluation"
            },
            {
                "name": "Zomato",
                "industry_type": "Food Tech & Hyperlocal Logistics",
                "location": "Gurugram, Bengaluru",
                "website": "https://www.zomato.com",
                "description": "Hyperlocal quick commerce and restaurant discovery network serving millions of food delivery orders daily.",
                "domains": "Mobile Engineering, High-Throughput APIs, Logistics Optimization",
                "recruitment_process": "1. Machine Coding Round\n2. Low-Level Design\n3. Culture & High-Ownership Fit"
            },
            {
                "name": "StartupTech AI",
                "industry_type": "Generative AI & LLM Automation",
                "location": "Bengaluru, Remote",
                "website": "https://startuptech.ai",
                "description": "Y-Combinator backed startup building autonomous AI workforce agents for modern enterprise workflows.",
                "domains": "Full Stack, AI Agents, Python Microservices",
                "recruitment_process": "1. Take-Home Coding Challenge\n2. Live Pair Programming\n3. Founder Alignment Call"
            }
        ]

        companies = {}
        for cdata in companies_data:
            comp = Company.query.filter_by(name=cdata["name"]).first()
            if not comp:
                comp = Company(**cdata)
                db.session.add(comp)
                db.session.flush()
                print(f" Created Company: {comp.name}")
            companies[comp.name] = comp

        # --------------------------------------------------------------------
        # 3. COMPANY HIRING HISTORIES (Placement Analytics)
        # --------------------------------------------------------------------
        hiring_histories = [
            # Google Cloud
            (companies["Google Cloud"].id, 2023, 14, 18, 16.5, 24.0),
            (companies["Google Cloud"].id, 2024, 18, 22, 17.8, 28.5),
            (companies["Google Cloud"].id, 2025, 21, 26, 18.5, 32.0),
            # Microsoft
            (companies["Microsoft India"].id, 2023, 19, 25, 15.2, 22.0),
            (companies["Microsoft India"].id, 2024, 24, 30, 16.4, 26.0),
            (companies["Microsoft India"].id, 2025, 28, 34, 17.5, 30.5),
            # AWS
            (companies["Amazon Web Services"].id, 2023, 25, 32, 14.8, 26.0),
            (companies["Amazon Web Services"].id, 2024, 31, 38, 15.9, 29.0),
            (companies["Amazon Web Services"].id, 2025, 35, 42, 16.8, 33.0),
            # Zomato
            (companies["Zomato"].id, 2024, 12, 15, 11.5, 18.0),
            (companies["Zomato"].id, 2025, 16, 20, 13.2, 21.0),
        ]

        for cid, yr, sel, off, avg_ctc, high_ctc in hiring_histories:
            hh = CompanyHiringHistory.query.filter_by(company_id=cid, hiring_year=yr).first()
            if not hh:
                hh = CompanyHiringHistory(
                    company_id=cid,
                    hiring_year=yr,
                    students_selected=sel,
                    offers_count=off,
                    average_ctc=avg_ctc,
                    highest_ctc=high_ctc
                )
                db.session.add(hh)

        # --------------------------------------------------------------------
        # 4. INDUSTRY EXPERTS / RECRUITERS
        # --------------------------------------------------------------------
        recruiters_data = [
            {
                "email": "recruiter@google.com",
                "company": companies["Google Cloud"],
                "first_name": "Siddharth",
                "last_name": "Nair",
                "designation": "Staff University Recruiter",
                "experience_years": 9,
                "linkedin_url": "https://linkedin.com/in/siddharth-nair-google",
                "status": "APPROVED"
            },
            {
                "email": "recruiter@microsoft.com",
                "company": companies["Microsoft India"],
                "first_name": "Pooja",
                "last_name": "Iyer",
                "designation": "Talent Acquisition Lead",
                "experience_years": 7,
                "linkedin_url": "https://linkedin.com/in/pooja-iyer-msft",
                "status": "APPROVED"
            },
            {
                "email": "recruiter@startup.io",
                "company": companies["StartupTech AI"],
                "first_name": "Karan",
                "last_name": "Mehta",
                "designation": "Head of People & Culture",
                "experience_years": 4,
                "linkedin_url": "https://linkedin.com/in/karan-mehta-founder",
                "status": "PENDING"
            }
        ]

        industry_experts = {}
        for rdata in recruiters_data:
            u = User.query.filter_by(email=rdata["email"]).first()
            if not u:
                u = User(
                    email=rdata["email"],
                    role="industry_expert",
                    is_active=True,
                    is_verified=(rdata["status"] == "APPROVED")
                )
                u.set_password(recruiter_password)
                db.session.add(u)
                db.session.flush()

                exp = IndustryExpert(
                    user_id=u.id,
                    company_id=rdata["company"].id,
                    first_name=rdata["first_name"],
                    last_name=rdata["last_name"],
                    designation=rdata["designation"],
                    experience_years=rdata["experience_years"],
                    linkedin_url=rdata["linkedin_url"],
                    status=rdata["status"]
                )
                db.session.add(exp)
                db.session.flush()
                print(f" Created Recruiter: {rdata['email']} ({rdata['status']})")
                industry_experts[rdata["email"]] = exp
            else:
                u.set_password(recruiter_password)
                industry_experts[rdata["email"]] = u.industry_profile

        # --------------------------------------------------------------------
        # 5. CORE SKILLS CATALOGUE
        # --------------------------------------------------------------------
        skills_pool = [
            ("Python", "Programming"),
            ("SQL", "Database"),
            ("Docker", "DevOps & Cloud"),
            ("AWS", "DevOps & Cloud"),
            ("Data Structures & Algorithms", "Core CS"),
            ("Flask", "Web Development"),
            ("Kubernetes", "DevOps & Cloud"),
            ("React", "Frontend"),
            ("FastAPI", "Web Development"),
            ("System Design", "Core CS"),
            ("Machine Learning", "AI & ML"),
            ("Git", "Tools & Version Control"),
            ("Java", "Programming")
        ]
        skills_dict = {}
        for sname, scat in skills_pool:
            sk = Skill.query.filter_by(name=sname).first()
            if not sk:
                sk = Skill(name=sname, category=scat)
                db.session.add(sk)
                db.session.flush()
            skills_dict[sname] = sk

        # --------------------------------------------------------------------
        # 6. STUDENTS COHORT
        # --------------------------------------------------------------------
        students_info = [
            {
                "email": "priya@campus.edu",
                "roll": "CS2025-042",
                "first_name": "Priya",
                "last_name": "Sharma",
                "department": "Computer Science",
                "degree": "B.Tech Computer Science & Engineering",
                "batch_year": 2025,
                "cgpa": 9.15,
                "backlogs": 0,
                "phone": "+91-00000-00001",
                "skills": [
                    ("Python", "Expert"),
                    ("Data Structures & Algorithms", "Advanced"),
                    ("SQL", "Advanced"),
                    ("Docker", "Intermediate"),
                    ("AWS", "Intermediate"),
                    ("Kubernetes", "Intermediate"),
                    ("React", "Advanced")
                ],
                "ats_score": 92.5
            },
            {
                "email": "aman@campus.edu",
                "roll": "CS2025-089",
                "first_name": "Aman",
                "last_name": "Verma",
                "department": "Computer Science",
                "degree": "B.Tech Computer Science & Engineering",
                "batch_year": 2025,
                "cgpa": 7.92,
                "backlogs": 0,
                "phone": "+91-00000-00002",
                "skills": [
                    ("Python", "Advanced"),
                    ("Flask", "Intermediate"),
                    ("SQL", "Intermediate"),
                    ("Git", "Intermediate")
                ],
                "ats_score": 71.0
            },
            {
                "email": "rahul@campus.edu",
                "roll": "EC2025-015",
                "first_name": "Rahul",
                "last_name": "Gupta",
                "department": "Electronics & Communication",
                "degree": "B.Tech Electronics & Communication",
                "batch_year": 2025,
                "cgpa": 5.85,
                "backlogs": 2,
                "phone": "+91-00000-00003",
                "skills": [
                    ("Java", "Beginner"),
                    ("SQL", "Beginner")
                ],
                "ats_score": 46.0
            },
            {
                "email": "neha@campus.edu",
                "roll": "IT2026-004",
                "first_name": "Neha",
                "last_name": "Patel",
                "department": "Information Technology",
                "degree": "B.Tech Information Technology",
                "batch_year": 2026,
                "cgpa": 8.45,
                "backlogs": 0,
                "phone": "+91-00000-00004",
                "skills": [
                    ("Python", "Intermediate"),
                    ("React", "Advanced"),
                    ("FastAPI", "Intermediate"),
                    ("Git", "Advanced")
                ],
                "ats_score": 83.0
            }
        ]

        students_dict = {}
        for sdata in students_info:
            u = User.query.filter_by(email=sdata["email"]).first()
            if not u:
                u = User(
                    email=sdata["email"],
                    role="student",
                    is_active=True,
                    is_verified=True
                )
                u.set_password(student_password)
                db.session.add(u)
                db.session.flush()

                stud = Student(
                    user_id=u.id,
                    roll_number=sdata["roll"],
                    first_name=sdata["first_name"],
                    last_name=sdata["last_name"],
                    department=sdata["department"],
                    degree=sdata["degree"],
                    batch_year=sdata["batch_year"],
                    cgpa=sdata["cgpa"],
                    backlogs=sdata["backlogs"],
                    phone=sdata["phone"]
                )
                db.session.add(stud)
                db.session.flush()

                # Add Student Skills
                for sk_name, prof in sdata["skills"]:
                    if sk_name in skills_dict:
                        db.session.add(StudentSkill(
                            student_id=stud.id,
                            skill_id=skills_dict[sk_name].id,
                            proficiency_level=prof
                        ))

                # Add Resume & Analysis
                res = Resume(
                    student_id=stud.id,
                    file_name=f"{stud.first_name.lower()}_resume.pdf",
                    file_path=f"uploads/resumes/{stud.first_name.lower()}_resume.pdf",
                    file_size=15420,
                    is_primary=True
                )
                db.session.add(res)
                db.session.flush()

                analysis = ResumeAnalysis(
                    resume_id=res.id,
                    overall_score=sdata["ats_score"],
                    parsed_skills_json=json.dumps([sk[0] for sk in sdata["skills"]]),
                    strengths_json=json.dumps([
                        "Strong education credentials",
                        "Clear structured technical layout"
                    ]),
                    improvements_json=json.dumps([
                        "Highlight high-impact quantified metrics in technical projects.",
                        "Add industry-standard containerization tools like Docker to stand out in backend roles."
                    ]),
                    skill_gap_json=json.dumps(["Docker", "AWS", "Kubernetes"]) if sdata["first_name"] == "Aman" else "[]"
                )
                db.session.add(analysis)

                # Add Student Preferences
                db.session.add(StudentPreference(
                    student_id=stud.id,
                    preferred_domain="Cloud & Distributed Systems",
                    preferred_locations="Bengaluru, Hyderabad, Remote",
                    preferred_roles="Software Engineer, Cloud Developer",
                    expected_min_salary=800000
                ))

                print(f" Created Student: {sdata['email']} (Roll: {sdata['roll']})")
                students_dict[sdata["email"]] = stud
            else:
                u.set_password(student_password)
                students_dict[sdata["email"]] = u.student_profile

        # --------------------------------------------------------------------
        # 7. PROACTIVE INTERVENTION FOR AT-RISK STUDENT (Rahul Gupta)
        # --------------------------------------------------------------------
        rahul_stud = students_dict["rahul@campus.edu"]
        existing_itv = StudentIntervention.query.filter_by(student_id=rahul_stud.id).first()
        if not existing_itv:
            itv = StudentIntervention(
                student_id=rahul_stud.id,
                admin_id=admin_user.id,
                risk_indicators=json.dumps([
                    "Active academic backlogs (2)",
                    "Low cumulative CGPA (5.85)",
                    "Below threshold ATS resume score (46%)"
                ]),
                intervention_type="Academic Counseling & Resume Workshop",
                action_plan="1. Mandatory enrollment in Department Remedial Programming Lab.\n2. One-on-one resume rewrite with Career Center mentor.\n3. Scheduled clearance of 2 backlog papers before 8th semester.",
                notes="Student exhibited good problem-solving interest; advised structured preparation schedule.",
                status="OPEN"
            )
            db.session.add(itv)
            print(" Created Proactive Intervention for Rahul Gupta")

        # --------------------------------------------------------------------
        # 8. JOB LISTINGS (Student Marketplace)
        # --------------------------------------------------------------------
        google_rec = industry_experts["recruiter@google.com"]
        msft_rec = industry_experts["recruiter@microsoft.com"]

        jobs_data = [
            {
                "title": "Cloud Software Engineer",
                "company": companies["Google Cloud"],
                "expert": google_rec,
                "description": "Develop and maintain mission-critical cloud native services on Google Cloud Platform. You will build high-throughput microservices using Python and Go, packaged with Docker and deployed onto Kubernetes clusters.",
                "job_type": "Full-time",
                "location": "Bengaluru, Karnataka",
                "domain": "Software Engineering",
                "ctc": "₹18.0 - ₹24.0 LPA",
                "min_salary": 1800000,
                "max_salary": 2400000,
                "min_cgpa": 7.5,
                "eligible_branches": "Computer Science,Information Technology,Electronics",
                "eligible_batch_years": "2025",
                "deadline": datetime.now(timezone.utc) + timedelta(days=20),
                "status": "Published",
                "skills": [
                    ("Python", "Required"),
                    ("Docker", "Required"),
                    ("AWS", "Preferred"),
                    ("Data Structures & Algorithms", "Required"),
                    ("SQL", "Required")
                ]
            },
            {
                "title": "Software Development Engineer - Azure Core",
                "company": companies["Microsoft India"],
                "expert": msft_rec,
                "description": "Design resilient cloud infrastructure and distributed orchestration services for Microsoft Azure. Strong algorithmic skills, containerization familiarity, and systems programming are essential.",
                "job_type": "Full-time",
                "location": "Hyderabad, Telangana",
                "domain": "Software Engineering",
                "ctc": "₹16.0 - ₹22.0 LPA",
                "min_salary": 1600000,
                "max_salary": 2200000,
                "min_cgpa": 7.0,
                "eligible_branches": "Computer Science,Information Technology",
                "eligible_batch_years": "2025",
                "deadline": datetime.now(timezone.utc) + timedelta(days=25),
                "status": "Published",
                "skills": [
                    ("Data Structures & Algorithms", "Required"),
                    ("Python", "Required"),
                    ("Docker", "Required"),
                    ("Kubernetes", "Preferred")
                ]
            },
            {
                "title": "Cloud DevOps Engineer",
                "company": companies["Amazon Web Services"],
                "expert": None,
                "description": "Automate cloud deployment pipelines, monitor reliability metrics, and construct zero-downtime infrastructure using AWS, Docker, and Kubernetes.",
                "job_type": "Full-time",
                "location": "Bengaluru, Karnataka",
                "domain": "DevOps & Infrastructure",
                "ctc": "₹15.0 - ₹20.0 LPA",
                "min_salary": 1500000,
                "max_salary": 2000000,
                "min_cgpa": 7.0,
                "eligible_branches": "Computer Science,Information Technology,Electronics",
                "eligible_batch_years": "2025",
                "deadline": datetime.now(timezone.utc) + timedelta(days=15),
                "status": "Published",
                "skills": [
                    ("AWS", "Required"),
                    ("Docker", "Required"),
                    ("Kubernetes", "Required"),
                    ("Python", "Preferred")
                ]
            },
            {
                "title": "Backend API Developer",
                "company": companies["Zomato"],
                "expert": None,
                "description": "Scale high-traffic order fulfillment and payment gateway APIs serving peak traffic during dinner rushes. Build RESTful and gRPC endpoints in Python and Flask.",
                "job_type": "Full-time",
                "location": "Gurugram, Haryana",
                "domain": "Software Engineering",
                "ctc": "₹12.0 - ₹16.0 LPA",
                "min_salary": 1200000,
                "max_salary": 1600000,
                "min_cgpa": 6.5,
                "eligible_branches": "Computer Science,Information Technology",
                "eligible_batch_years": "2025,2026",
                "deadline": datetime.now(timezone.utc) + timedelta(days=30),
                "status": "Published",
                "skills": [
                    ("Python", "Required"),
                    ("Flask", "Required"),
                    ("SQL", "Required"),
                    ("Docker", "Preferred")
                ]
            },
            {
                "title": "Generative AI Application Intern",
                "company": companies["StartupTech AI"],
                "expert": industry_experts["recruiter@startup.io"],
                "description": "Construct autonomous workflow agents and fine-tune open source LLMs. Fast-paced startup environment with high technical ownership.",
                "job_type": "Internship",
                "location": "Bengaluru, Remote",
                "domain": "Artificial Intelligence",
                "ctc": "₹45,000 / month",
                "min_salary": 45000,
                "max_salary": 45000,
                "min_cgpa": 7.0,
                "eligible_branches": "Computer Science,Information Technology",
                "eligible_batch_years": "2025,2026",
                "deadline": datetime.now(timezone.utc) + timedelta(days=10),
                "status": "Pending Approval",
                "skills": [
                    ("Python", "Required"),
                    ("Machine Learning", "Required"),
                    ("FastAPI", "Preferred")
                ]
            }
        ]

        jobs_dict = {}
        for jdata in jobs_data:
            job = Job.query.filter_by(title=jdata["title"], company_id=jdata["company"].id).first()
            if not job:
                job = Job(
                    company_id=jdata["company"].id,
                    posted_by_expert_id=jdata["expert"].id if jdata["expert"] else None,
                    title=jdata["title"],
                    description=jdata["description"],
                    job_type=jdata["job_type"],
                    location=jdata["location"],
                    domain=jdata["domain"],
                    ctc=jdata["ctc"],
                    min_salary=jdata["min_salary"],
                    max_salary=jdata["max_salary"],
                    min_cgpa=jdata["min_cgpa"],
                    eligible_branches=jdata["eligible_branches"],
                    eligible_batch_years=jdata["eligible_batch_years"],
                    deadline=jdata["deadline"],
                    status=jdata["status"]
                )
                db.session.add(job)
                db.session.flush()

                for sk_name, prio in jdata["skills"]:
                    if sk_name in skills_dict:
                        db.session.add(JobSkill(
                            job_id=job.id,
                            skill_id=skills_dict[sk_name].id,
                            priority=prio
                        ))
                print(f" Created Job: '{job.title}' ({job.status})")
            jobs_dict[jdata["title"]] = job

        # --------------------------------------------------------------------
        # 9. APPLICATIONS & THE SIGNATURE INTELLIGENCE COHORT (Aman Verma)
        # --------------------------------------------------------------------
        aman = students_dict["aman@campus.edu"]
        priya = students_dict["priya@campus.edu"]

        # Priya: Applied to Google Cloud and Selected with 18.5 LPA
        google_job = jobs_dict["Cloud Software Engineer"]
        priya_app = Application.query.filter_by(student_id=priya.id, job_id=google_job.id).first()
        if not priya_app:
            priya_app = Application(
                student_id=priya.id,
                job_id=google_job.id,
                resume_id=priya.resumes[0].id if priya.resumes else None,
                current_status="SELECTED"
            )
            db.session.add(priya_app)
            db.session.flush()

            prec = PlacementRecord(
                student_id=priya.id,
                company_id=companies["Google Cloud"].id,
                job_id=google_job.id,
                application_id=priya_app.id,
                package_ctc=18.50,
                offer_date=date.today() - timedelta(days=15),
                acceptance_status="Accepted"
            )
            db.session.add(prec)
            print(" Created Placement Record: Priya Sharma -> Google Cloud (INR 18.5 LPA)")

        # Aman Verma: 4 applications demonstrating "Why Am I Not Getting Selected?"
        aman_resume_id = aman.resumes[0].id if aman.resumes else None

        apps_for_aman = [
            (jobs_dict["Cloud Software Engineer"], "REJECTED"),
            (jobs_dict["Software Development Engineer - Azure Core"], "REJECTED"),
            (jobs_dict["Cloud DevOps Engineer"], "REJECTED"),
            (jobs_dict["Backend API Developer"], "UNDER_REVIEW")
        ]

        for target_job, final_st in apps_for_aman:
            a_app = Application.query.filter_by(student_id=aman.id, job_id=target_job.id).first()
            if not a_app:
                a_app = Application(
                    student_id=aman.id,
                    job_id=target_job.id,
                    resume_id=aman_resume_id,
                    current_status=final_st
                )
                db.session.add(a_app)
                db.session.flush()

                db.session.add(ApplicationStatusHistory(
                    application_id=a_app.id,
                    status="APPLIED",
                    notes="Online application submitted via campus portal."
                ))
                if final_st in ["REJECTED", "UNDER_REVIEW"]:
                    db.session.add(ApplicationStatusHistory(
                        application_id=a_app.id,
                        status="SHORTLISTED",
                        notes="Candidate profile shortlisted based on academic criteria."
                    ))
                if final_st == "REJECTED" and target_job.title != "Cloud DevOps Engineer":
                    db.session.add(ApplicationStatusHistory(
                        application_id=a_app.id,
                        status="INTERVIEW",
                        notes="Technical screening round conducted."
                    ))
                db.session.add(ApplicationStatusHistory(
                    application_id=a_app.id,
                    status=final_st,
                    notes=f"Outcome updated to {final_st}."
                ))

                if target_job.title == "Cloud Software Engineer":
                    fb = Feedback(
                        application_id=a_app.id,
                        given_by_user_id=google_rec.user.id,
                        target_student_id=aman.id,
                        rating=3,
                        technical_rating=3,
                        problem_solving_rating=4,
                        communication_rating=4,
                        recommendation="Hold",
                        is_visible_to_student=True,
                        feedback_type="Interview",
                        comments="Candidate demonstrated strong algorithmic foundation and Python fundamentals. However, the role requires hands-on proficiency in containerization with Docker and cloud deployments on AWS or GCP. We recommend upskilling in Docker container lifecycles and microservices orchestration."
                    )
                    db.session.add(fb)

        print(" Configured Intelligence Case Study for Aman Verma (4 applications, recurring Docker/AWS/DSA gaps)")

        # --------------------------------------------------------------------
        # 10. PLACEMENT DRIVES
        # --------------------------------------------------------------------
        drives_data = [
            {
                "title": "Google Cloud Annual Campus Hiring 2025",
                "company": companies["Google Cloud"],
                "academic_year": "2024-2025",
                "drive_date": datetime.now(timezone.utc) - timedelta(days=20),
                "eligible_batch": 2025,
                "min_cgpa": 7.5,
                "max_backlogs": 0,
                "eligible_departments": "Computer Science, Information Technology, Electronics",
                "job_role": "Cloud Software Engineer",
                "package_ctc": "18.5 LPA",
                "required_skills": "Python, Docker, SQL, AWS",
                "current_stage": "Completed",
                "status": "Completed"
            },
            {
                "title": "Microsoft Azure Premier Hiring 2025",
                "company": companies["Microsoft India"],
                "academic_year": "2024-2025",
                "drive_date": datetime.now(timezone.utc) + timedelta(days=5),
                "eligible_batch": 2025,
                "min_cgpa": 7.0,
                "max_backlogs": 0,
                "eligible_departments": "Computer Science, Information Technology",
                "job_role": "Software Development Engineer",
                "package_ctc": "16.5 LPA",
                "required_skills": "Data Structures & Algorithms, Python, Docker",
                "current_stage": "Interview",
                "status": "Ongoing"
            },
            {
                "title": "AWS Cloud Foundations Graduate Drive 2026",
                "company": companies["Amazon Web Services"],
                "academic_year": "2025-2026",
                "drive_date": datetime.now(timezone.utc) + timedelta(days=35),
                "eligible_batch": 2026,
                "min_cgpa": 7.0,
                "max_backlogs": 0,
                "eligible_departments": "Computer Science, Information Technology, Electronics",
                "job_role": "Cloud DevOps Engineer",
                "package_ctc": "15.0 LPA",
                "required_skills": "AWS, Docker, Linux",
                "current_stage": "Registration",
                "status": "Scheduled"
            }
        ]

        for ddata in drives_data:
            drv = PlacementDrive.query.filter_by(title=ddata["title"]).first()
            if not drv:
                drv = PlacementDrive(
                    company_id=ddata["company"].id,
                    title=ddata["title"],
                    academic_year=ddata["academic_year"],
                    drive_date=ddata["drive_date"],
                    eligible_batch=ddata["eligible_batch"],
                    min_cgpa=ddata["min_cgpa"],
                    max_backlogs=ddata["max_backlogs"],
                    eligible_departments=ddata["eligible_departments"],
                    job_role=ddata["job_role"],
                    package_ctc=ddata["package_ctc"],
                    required_skills=ddata["required_skills"],
                    current_stage=ddata["current_stage"],
                    status=ddata["status"]
                )
                db.session.add(drv)
                db.session.flush()

                if ddata["title"].startswith("Google"):
                    db.session.add(PlacementDriveStudent(
                        drive_id=drv.id,
                        student_id=priya.id,
                        registration_status="Attended",
                        stage="Selected",
                        offered_ctc=18.5,
                        shortlisted=True
                    ))
                print(f" Created Placement Drive: {drv.title}")

        # --------------------------------------------------------------------
        # 11. WORKSHOPS (Upskilling Recommendations)
        # --------------------------------------------------------------------
        workshops_data = [
            {
                "title": "Mastering Docker & Cloud Native Deployments",
                "description": "Hands-on masterclass covering container fundamentals, multi-stage Docker builds, Kubernetes manifests, and cloud production deployment best practices.",
                "company": companies["Google Cloud"],
                "instructor": google_rec,
                "start_time": datetime.now(timezone.utc) + timedelta(days=4),
                "end_time": datetime.now(timezone.utc) + timedelta(days=4, hours=3),
                "venue_or_link": "https://meet.google.com/sih-docker-upskill",
                "max_capacity": 150
            },
            {
                "title": "Architecting Scalable Microservices on AWS",
                "description": "Deep-dive workshop into serverless architecture, AWS ECS, VPC networking, and high-availability database replication.",
                "company": companies["Amazon Web Services"],
                "instructor": None,
                "start_time": datetime.now(timezone.utc) + timedelta(days=8),
                "end_time": datetime.now(timezone.utc) + timedelta(days=8, hours=2, minutes=30),
                "venue_or_link": "https://meet.google.com/sih-aws-architecture",
                "max_capacity": 200
            }
        ]

        for wdata in workshops_data:
            w = Workshop.query.filter_by(title=wdata["title"]).first()
            if not w:
                w = Workshop(
                    title=wdata["title"],
                    description=wdata["description"],
                    company_id=wdata["company"].id if wdata["company"] else None,
                    instructor_id=wdata["instructor"].id if wdata["instructor"] else None,
                    start_time=wdata["start_time"],
                    end_time=wdata["end_time"],
                    venue_or_link=wdata["venue_or_link"],
                    max_capacity=wdata["max_capacity"]
                )
                db.session.add(w)
                db.session.flush()

                if "Docker" in w.title:
                    reg = WorkshopRegistration(
                        workshop_id=w.id,
                        student_id=aman.id,
                        attendance_status="Registered"
                    )
                    db.session.add(reg)
                print(f" Created Workshop: {w.title}")

        # --------------------------------------------------------------------
        # 12. TECHNICAL ASSESSMENTS
        # --------------------------------------------------------------------
        ass_title = "Cloud Infrastructure & Containerization Assessment"
        ass = Assessment.query.filter_by(title=ass_title).first()
        if not ass:
            ass = Assessment(
                title=ass_title,
                description="Evaluate candidate competence in Dockerfile instructions, container networking, and Kubernetes pod configurations.",
                company_id=companies["Google Cloud"].id,
                duration_minutes=45,
                passing_score=60.0,
                is_active=True
            )
            db.session.add(ass)
            db.session.flush()

            q1 = AssessmentQuestion(
                assessment_id=ass.id,
                question_text="Which Dockerfile instruction specifies the command that will always be executed when the container starts?",
                question_type="MCQ",
                marks=1,
                options_json=json.dumps(["RUN", "ENTRYPOINT", "EXPOSE", "VOLUME"]),
                correct_answer="ENTRYPOINT"
            )
            q2 = AssessmentQuestion(
                assessment_id=ass.id,
                question_text="In Kubernetes, what is the smallest deployable computing unit that can be created and managed?",
                question_type="MCQ",
                marks=1,
                options_json=json.dumps(["Node", "Pod", "Service", "ConfigMap"]),
                correct_answer="Pod"
            )
            db.session.add(q1)
            db.session.add(q2)

            attempt = AssessmentAttempt(
                assessment_id=ass.id,
                student_id=aman.id,
                score=50.0,
                passed=False,
                answers_json=json.dumps({"1": "ENTRYPOINT", "2": "Node"}),
                completed_at=datetime.now(timezone.utc) - timedelta(days=2)
            )
            db.session.add(attempt)
            print(f" Created Assessment: {ass.title} with attempt for Aman")

        # --------------------------------------------------------------------
        # 13. VERIFIED ALUMNI NETWORK (Privacy Compliant)
        # --------------------------------------------------------------------
        alumni_data = [
            {
                "name": "Vikramaditya Singh",
                "email": "vikram.singh@alumni.college.edu",
                "phone": "+91-00000-00011",
                "graduation_year": 2021,
                "department": "Computer Science",
                "current_company": "Google Cloud",
                "current_role": "Senior Cloud Infrastructure Engineer",
                "linkedin_url": "https://linkedin.com/in/fictional-alumni-vikram",
                "willing_to_mentor": True,
                "is_verified": True,
                "consent_share_contact": False
            },
            {
                "name": "Ananya Roy",
                "email": "ananya.roy@alumni.college.edu",
                "phone": "+91-00000-00012",
                "graduation_year": 2022,
                "department": "Computer Science",
                "current_company": "Microsoft India",
                "current_role": "Product Manager II - Azure AI",
                "linkedin_url": "https://linkedin.com/in/fictional-alumni-ananya",
                "willing_to_mentor": True,
                "is_verified": True,
                "consent_share_contact": True
            },
            {
                "name": "Rohan Deshmukh",
                "email": "rohan.deshmukh@alumni.college.edu",
                "phone": "+91-00000-00013",
                "graduation_year": 2020,
                "department": "Information Technology",
                "current_company": "Amazon Web Services",
                "current_role": "Software Development Engineer III",
                "linkedin_url": "https://linkedin.com/in/fictional-alumni-rohan",
                "willing_to_mentor": True,
                "is_verified": True,
                "consent_share_contact": True
            },
            {
                "name": "Kavita Sen",
                "email": "kavita.sen@alumni.college.edu",
                "phone": "+91-00000-00014",
                "graduation_year": 2023,
                "department": "Electronics & Communication",
                "current_company": "Qualcomm",
                "current_role": "Hardware System Validation Engineer",
                "linkedin_url": "https://linkedin.com/in/fictional-alumni-kavita",
                "willing_to_mentor": True,
                "is_verified": True,
                "consent_share_contact": False
            }
        ]

        for adata in alumni_data:
            alm = Alumni.query.filter_by(email=adata["email"]).first()
            if not alm:
                alm = Alumni(**adata)
                db.session.add(alm)
                print(f" Created Alumni: {alm.name} ({alm.current_company}, Consent: {alm.consent_share_contact})")

        # --------------------------------------------------------------------
        # 14. ANNOUNCEMENTS & NOTIFICATIONS
        # --------------------------------------------------------------------
        ann_title = "Welcome to the 2025-2026 Campus Placement Season"
        ann = Announcement.query.filter_by(title=ann_title).first()
        if not ann:
            ann = Announcement(
                title=ann_title,
                content="The centralized placement cell is pleased to kickstart recruitment drives for Google Cloud, Microsoft, and AWS. Ensure your primary resumes are updated and run ATS resume checks regularly.",
                target_audience="ALL",
                posted_by_id=admin_user.id,
                priority="High"
            )
            db.session.add(ann)

        db.session.commit()
        print("\n==========================================================")
        print(" SIH Demo Presentation Dataset Successfully Seeded!")
        print("==========================================================")
        print("Demonstration Accounts Configured:")
        print("1. Institutional Admin : admin@college.edu")
        print("2. Google Recruiter    : recruiter@google.com")
        print("3. Startup Recruiter   : recruiter@startup.io")
        print("4. Placed Student      : priya@campus.edu")
        print("5. Active Student      : aman@campus.edu")
        print("6. At-Risk Student     : rahul@campus.edu")
        print("7. Fresh Candidate     : neha@campus.edu")
        print("----------------------------------------------------------")
        print("Demo Account Passwords:")
        print("  Configured via environment variables (DEMO_USER_PASSWORD or DEMO_*_PASSWORD in .env)")
        print("  (Loaded securely from your local environment)")
        print("==========================================================")


if __name__ == "__main__":
    seed_database()
