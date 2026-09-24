# College Placement & Career Development Platform
> **Smart India Hackathon (SIH) Flagship Platform**  
> An enterprise-grade, role-based platform bridging **Students**, **Industry Experts / Recruiters**, and **Institutional Placement Cells (TPO)**.

---

## 1. Executive Summary & Core Value Proposition

The **College Placement & Career Development Platform** is designed to solve the critical visibility, alignment, and readiness gap between university engineering talent and modern industry expectations:
1. **Explainable AI & Diagnostics**: Our signature **"Why Am I Not Getting Selected?"** Placement Intelligence engine gives rejected and unplaced candidates an evidence-based conversion funnel, identifying exact recurring skill gaps (e.g. Docker, AWS, DSA) across their historical applications with actionable upskilling pathways.
2. **Deterministic ATS Resume Analysis**: Rule-based NLP heuristics and PyMuPDF text extraction calculate ATS compatibility scores (0-100), identify detected technical competencies, and highlight missing industry skills without black-box hallucinations.
3. **Multi-Tenant Enterprise Recruitment**: Verified recruiters publish job listings, execute talent discovery, create custom MCQ/coding assessments with auto-grading, schedule interactive workshops, and submit dimensional interview feedback.
4. **Data-Driven Institutional Placement Cell**: Placement officers track batch-wide placement rates, average/highest CTC, department-wise breakdowns, schedule multi-stage recruitment drives, monitor at-risk candidates, and log proactive counseling interventions.
5. **GDPR/DPDP-Compliant Alumni Network**: Institutional alumni directory with mentor flags and strict privacy controls masking personal phone/email unless explicit consent is granted.

---

## 2. System Architecture

```text
SIH PROJECT/
│
├── backend/
│   ├── app.py                      # Application factory, static routing & global error handlers
│   ├── config.py                   # Environment configuration (Dev, Test, Prod)
│   ├── extensions.py               # SQLAlchemy, Flask-Migrate, Flask-CORS instances
│   ├── seed_sih_demo.py            # High-fidelity SIH demo database seeder (7 Personas)
│   │
│   ├── models/                     # 27 Normalized SQLAlchemy ORM Models
│   │   ├── base.py                 # TimestampMixin (created_at, updated_at)
│   │   ├── user.py                 # User, Student, IndustryExpert, Admin
│   │   ├── student.py              # StudentPreference, Project
│   │   ├── company.py              # Company, CompanyHiringHistory
│   │   ├── skill.py                # Skill, StudentSkill, JobSkill
│   │   ├── job.py                  # Job
│   │   ├── resume.py               # Resume, ResumeAnalysis
│   │   ├── application.py          # Application, ApplicationStatusHistory, Feedback
│   │   ├── placement.py            # PlacementRecord, PlacementDrive, PlacementDriveStudent, Alumni, Announcement, StudentIntervention
│   │   ├── workshop.py             # Workshop, WorkshopRegistration
│   │   ├── assessment.py           # Assessment, AssessmentQuestion, AssessmentAttempt
│   │   └── notification.py         # Notification
│   │
│   ├── routes/                     # Blueprint HTTP controllers
│   │   ├── auth.py                 # JWT Authentication & role verification
│   │   ├── student.py              # Profile, ATS analysis, applications, intelligence, workshops, alumni
│   │   ├── industry.py             # Job creation, applicant pipeline, assessments, workshops
│   │   ├── admin.py                # Executive dashboard, drive scheduler, at-risk intervention, alumni
│   │   ├── jobs.py                 # Job marketplace & applicant submission
│   │   ├── analytics.py            # Platform-wide placement analytics & skill demand
│   │   └── health.py               # Liveness probe GET /api/health
│   │
│   ├── services/                   # Business logic layer
│   │   ├── placement_intelligence.py # "Why Am I Not Getting Selected?" funnel engine
│   │   ├── resume_analyzer.py      # PyMuPDF text parser & ATS scoring heuristics
│   │   ├── job_matcher.py          # Explainable candidate-job matching algorithm
│   │   ├── recommendation_engine.py# Collaborative & skill-based recommendations
│   │   ├── analytics_service.py    # Chart.js analytics aggregations & hiring trends
│   │   └── notification_service.py # Broadcast & targeted user alert dispatcher
│   │
│   └── utils/                      # Shared helpers
│       ├── auth.py                 # JWT decorators: @student_required, @industry_required, @admin_required
│       ├── response.py             # Standardized API response formatters
│       └── validation.py           # Input sanitization and validation schemas
│
├── frontend/                       # Vanilla Modern JS + Bootstrap 5 + Chart.js
│   ├── index.html                  # Landing portal & live service status
│   ├── css/                        # Responsive CSS stylesheets
│   ├── js/                         # Modular fetch APIs & state management
│   └── pages/                      # Role-specific dashboard views
│       ├── student/                # Dashboard, Jobs, Applications, Resume Analyzer,
│       │                           # Why-Not-Selected, Assessments, Workshops, Alumni
│       ├── recruiter/              # Dashboard, Post Job, Review Applicants, Assessments, Workshops
│       └── admin/                  # Dashboard, Approvals, Drives, At-Risk Interventions, Alumni
│
├── uploads/resumes/                # Isolated directory for candidate PDF resumes
├── .env.example                    # Environment template
└── requirements.txt                # Production dependencies
```

---

## 3. Quick Start & Setup

### Option A: Local Development (MySQL)

1. **Activate Virtual Environment**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. **Configure Environment (`.env`)**:
   Copy the example template to create your local `.env`:
   ```powershell
   copy .env.example .env
   ```
   *(On Linux/macOS: `cp .env.example .env`)*

   Start a local MySQL server, then configure `.env`:
   - Set a secure random `SECRET_KEY`
   - Configure `DEMO_USER_PASSWORD` (used when running the demo seed script)
   - Set `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD` for your MySQL database

3. **Initialize Database & Seed Demonstration Cohort**:
   ```powershell
   .\venv\Scripts\python backend/seed_sih_demo.py
   ```
   *(Or for a minimal setup with only core skills and an admin: `python backend/init_db.py`)*

4. **Start Web Server**:
   ```powershell
   .\venv\Scripts\python backend/app.py
   ```
   *The platform is live at `http://127.0.0.1:5000`.*

---

### Option B: Deploy the Python app to Render from GitHub (no app Dockerfile)

1. Push this project to a GitHub repository. In Render, choose **New → Blueprint** and connect that repository. The included `render.yaml` configures the Python build and Gunicorn web service.
2. Create a MySQL service in the same Render region. Render's [MySQL deployment guide](https://render.com/docs/deploy-mysql) uses a private MySQL service with a persistent disk. In the web service environment, set `DB_HOST` to the MySQL service's internal hostname and set the database name, username, and password to the values configured for that service.
3. `SECRET_KEY` is generated by the Blueprint. Set `CORS_ORIGINS` to `*` for the bundled frontend, or provide comma-separated origins if hosting it separately. `FLASK_ENV=production` and `DB_PORT=3306` are set by the Blueprint.
4. Deploy. The start command applies the committed Alembic migrations before Gunicorn starts. Check `https://<your-service>.onrender.com/api/health` after deployment.

Required Render variables:

| Variable | Value |
| --- | --- |
| `SECRET_KEY` | Generated by the Blueprint |
| `DB_HOST` | MySQL private service hostname shown by Render (without `:3306`) |
| `DB_PORT` | `3306` (set in `render.yaml`) |
| `DB_NAME` | Database name configured for MySQL |
| `DB_USER` | MySQL application user |
| `DB_PASSWORD` | Password for the MySQL application user |
| `FLASK_ENV` | `production` (set in `render.yaml`) |
| `CORS_ORIGINS` | `*` for the bundled frontend, or your frontend origin(s) |

Resume files are written under `UPLOAD_FOLDER` (default `uploads/resumes`). Render's service filesystem is ephemeral, so configure a persistent disk or external object storage before relying on uploaded resumes in production.

---

## 4. Demonstration Personas

The seed script creates 7 comprehensive demonstration profiles covering every role in the university placement lifecycle. All demo accounts use the password configured in your `.env` file via `DEMO_USER_PASSWORD` (default: `DemoPassword123!`):

| Role / Persona | Email | Password | Key Showcase Feature |
| :--- | :--- | :--- | :--- |
| **Placement Cell Head** | `admin@college.edu` | Configured via `DEMO_USER_PASSWORD` | TPO KPIs, schedule drives, at-risk counseling, approve recruiters/jobs, manage alumni |
| **Google Cloud Recruiter** | `recruiter@google.com` | Configured via `DEMO_USER_PASSWORD` | Verified recruiter: Post jobs, manage applicants, host Docker workshop, candidate ratings |
| **Startup Recruiter** | `recruiter@startup.io` | Configured via `DEMO_USER_PASSWORD` | Pending recruiter: Demonstrates TPO verification barrier & pending job moderation |
| **Placed Candidate** (Priya) | `priya@campus.edu` | Configured via `DEMO_USER_PASSWORD` | 9.15 CGPA, placed at Google Cloud (₹18.5 LPA), 92.5% ATS score, full offer audit trace |
| **Active Candidate** (Aman) | `aman@campus.edu` | Configured via `DEMO_USER_PASSWORD` | **Placement Intelligence Target**: 4 applications, recurring Docker/AWS gaps, upskilling loop |
| **At-Risk Candidate** (Rahul)| `rahul@campus.edu` | Configured via `DEMO_USER_PASSWORD` | 5.85 CGPA, 2 backlogs, open counselor intervention plan & remedial lab assignment |
| **Fresh Candidate** (Neha) | `neha@campus.edu` | Configured via `DEMO_USER_PASSWORD` | 2026 batch IT student exploring internships, fresh ATS analyzer, workshops & assessments |

---

## 5. Live Demonstration Scripts for Juries

### Demo 1: Student Persona & Placement Intelligence ("Why Am I Not Getting Selected?")
1. **Login**: Navigate to `/pages/auth/login.html` and sign in with `aman@campus.edu` using your configured `DEMO_USER_PASSWORD`.
2. **Student Dashboard**:
   - View recommended jobs matching Python/SQL skills.
   - Inspect primary resume ATS analysis badge (71.0%).
3. **Why Am I Not Getting Selected?**:
   - Click **"Why Am I Not Getting Selected?"** on navigation (`/why-not-selected`).
   - Observe conversion funnel: `4 Applications -> 3 Shortlisted -> 2 Interviews -> 0 Selected`.
   - Review the **Recurring Missing Skills** frequency chart:
     * `Docker` (appears in 4/4 applied jobs)
     * `AWS` (appears in 2/4 applied jobs)
     * `DSA` (appears in 2/4 applied jobs)
   - Inspect verified employer feedback quote from Google Cloud interviewer:
     > *"Candidate demonstrated strong algorithmic foundation and Python fundamentals. However, the role requires hands-on proficiency in containerization with Docker and cloud deployments on AWS..."*
   - Click the recommended **"Mastering Docker & Cloud Native Deployments"** workshop to register immediately.
4. **Alumni Mentors**:
   - Navigate to **Alumni Network** (`/alumni`).
   - Observe GDPR contact privacy: Vikramaditya Singh (Google) has contact info masked (`contact_masked: true`), whereas Ananya Roy (Microsoft) explicitly consented to share email.

---

### Demo 2: Industry Recruiter Persona
1. **Login**: Sign in with `recruiter@google.com` using your configured `DEMO_USER_PASSWORD`.
2. **Recruiter Portal**:
   - View applicant pipeline for *Cloud Software Engineer* opening.
   - Review candidate match scores with explainable skill overlap.
   - Update candidate application status (`SHORTLISTED` -> `INTERVIEW` -> `SELECTED`).
   - Submit dimensional candidate feedback (Overall rating, Technical rating, Problem Solving, Communication, Recommendation).
3. **Workshop & Assessment Engine**:
   - View scheduled *Mastering Docker & Cloud Native Deployments* workshop with student registrations.
   - Review *Cloud Infrastructure & Containerization Assessment* MCQ test questions and auto-graded submissions.

---

### Demo 3: Institutional Admin / Placement Cell (TPO)
1. **Login**: Sign in with `admin@college.edu` using your configured `DEMO_USER_PASSWORD`.
2. **Executive Placement KPIs**:
   - View real-time placement rate, batch statistics, highest CTC (₹18.5 LPA), and department breakdown.
3. **Pending Moderation Queue**:
   - Inspect pending company/recruiter request: `StartupTech AI` (`recruiter@startup.io`).
   - Approve or reject recruiter credentials with 1-click verification.
   - Review pending job posting: *Generative AI Application Intern* and approve it to publish immediately to the student marketplace.
4. **At-Risk Student Intervention**:
   - View algorithmic At-Risk Student list: `Rahul Gupta` flagged due to `< 6.0 CGPA` and `2 active backlogs`.
   - View open counseling intervention and log action plan updates.
5. **Campus Placement Drives**:
   - Manage multi-stage recruitment drives (Google Cloud, Microsoft Azure, AWS).
   - Filter eligible students by minimum CGPA, eligible branches, and maximum backlogs.

---

## 6. Security & Privacy Audit Verification

The platform uses the following security and privacy controls:

1. **Role-Based Access Control (RBAC)**:
   - `@student_required`, `@industry_required`, and `@admin_required` decorators inspect cryptographically signed JWT tokens.
   - Horizontal privilege escalation blocked: Student A cannot view/download Student B's private resume or modify Student B's profile/projects.
   - Non-admins attempting to call admin endpoints receive `403 Forbidden`.
2. **Recruiter Tenant Isolation**:
   - Recruiters can only modify applications, post assessments, and schedule workshops for jobs originating from their own organization.
3. **Password Security**:
   - Passwords salted and hashed via Werkzeug PBKDF2/SHA256, never stored or transmitted in plaintext.
4. **Alumni Privacy Guardrails**:
   - Student-facing and public alumni listings mask telephone numbers and email addresses unless `consent_share_contact` is explicitly set to `True`.
5. **SQL Injection Defense**:
   - SQLAlchemy ORM parameter binding across all search filters, job queries, and student filters. Tested against SQL injection payloads (`' OR '1'='1`, `DROP TABLE`, `UNION SELECT`).

---

## 7. Tech Stack Summary

- **Backend**: Python 3.11+, Flask 3.0, Flask-SQLAlchemy, Flask-Migrate, Flask-CORS, PyJWT, PyMuPDF, Gunicorn.
- **Frontend**: HTML5, Modern CSS3 (CSS Variables, Flexbox, Grid), Vanilla ES6+ JavaScript, Bootstrap 5, Chart.js.
- **Database**: MySQL with PyMySQL.
- **Hosting**: Render Python web service with Gunicorn.
