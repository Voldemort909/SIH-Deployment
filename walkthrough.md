# Walkthrough: Job Marketplace, AI Matching Engine & Moderation System

We have implemented the full **Job Marketplace and Student-Industry Matching System** for the College Placement & Career Development Platform.

---

## What Was Implemented

### 1. Job Marketplace Models & Database Schema
* **`Job` ([`backend/models/job.py`](file:///c:/Users/Voldemort/OneDrive/Documents/SIH%20PROJECT/backend/models/job.py))**:
  * Enhanced with `domain`, `ctc`, `eligible_batch_years`, `rejection_reason`.
  * Initial status defaults to `"Pending Approval"` for all industry-submitted jobs.
* **`JobSkill` ([`backend/models/skill.py`](file:///c:/Users/Voldemort/OneDrive/Documents/SIH%20PROJECT/backend/models/skill.py))**:
  * Added `priority` classification: `Critical`, `Important`, `Preferred`.
* **`Application` & `ApplicationStatusHistory` ([`backend/models/application.py`](file:///c:/Users/Voldemort/OneDrive/Documents/SIH%20PROJECT/backend/models/application.py))**:
  * Formalized stage transitions: `APPLIED` $\rightarrow$ `UNDER_REVIEW` $\rightarrow$ `SHORTLISTED` $\rightarrow$ `ASSESSMENT` $\rightarrow$ `INTERVIEW` $\rightarrow$ `SELECTED` / `REJECTED`.
  * Full audit trail logging timestamp, transition notes, and actor role.

---

### 2. Explainable Job Matching Service
* **`calculate_job_match` ([`backend/services/job_matcher.py`](file:///c:/Users/Voldemort/OneDrive/Documents/SIH%20PROJECT/backend/services/job_matcher.py))**:
  * Computes a transparent, 5-dimensional match score instead of a black box:
    1. **Prioritized Skill Match (50% weight)**:
       * **Critical Skills (50% skill weight)**: Missing critical skills severely penalize the skill sub-score.
       * **Important Skills (35% skill weight)**: Major boost when matched.
       * **Preferred Skills (15% skill weight)**: Bonus differentiators.
    2. **Role & Domain Fit (25% weight)**: Compares student preferred job roles and target domain against the opening.
    3. **Work Preference Alignment (15% weight)**: Evaluates job type (Full-time / Internship) and work location preferences.
    4. **Academic Eligibility (10% weight)**: Checks minimum CGPA, department/branch, and graduation batch year. If academic criteria fail, overall score is automatically capped below 50%.
    5. **Human-Readable Rationale**: Generates plain-English explanations detailing why the score was given, which skills are missing, and tips to improve candidate standing.

---

### 3. REST API Routes
* **Student Jobs API ([`backend/routes/jobs.py`](file:///c:/Users/Voldemort/OneDrive/Documents/SIH%20PROJECT/backend/routes/jobs.py))**:
  * `GET /api/jobs`: Multi-faceted search and filtering (`keyword`, `domain`, `job_type`, `location`, `skill`, `only_eligible`, `sort_by`).
  * `GET /api/jobs/<id>`: Full job details with explainable match breakdown.
  * `POST /api/jobs/<id>/apply`: 1-click candidate application submission.
* **Industry Recruiter API ([`backend/routes/industry.py`](file:///c:/Users/Voldemort/OneDrive/Documents/SIH%20PROJECT/backend/routes/industry.py))**:
  * `POST /api/industry/jobs`: Create new job listing with prioritized skills (starts in `Pending Approval`).
  * `GET /api/industry/jobs`: Retrieve all jobs posted by the recruiter.
  * `GET /api/industry/jobs/<id>/applications`: Retrieve candidate pipeline with match scores and resumes.
  * `PUT /api/industry/applications/<app_id>/status`: Advance application stage (`UNDER_REVIEW`, `SHORTLISTED`, `ASSESSMENT`, `INTERVIEW`, `SELECTED`, `REJECTED`) with reviewer feedback.
* **Admin Moderation API ([`backend/routes/admin.py`](file:///c:/Users/Voldemort/OneDrive/Documents/SIH%20PROJECT/backend/routes/admin.py))**:
  * `GET /api/admin/jobs/pending`: Moderation queue of pending job submissions.
  * `PUT /api/admin/jobs/<id>/approve`: Verify and publish job to students.
  * `PUT /api/admin/jobs/<id>/reject`: Reject job with feedback notes for the recruiter.
* **Student Applications API ([`backend/routes/student.py`](file:///c:/Users/Voldemort/OneDrive/Documents/SIH%20PROJECT/backend/routes/student.py))**:
  * `GET /api/students/applications`: View all submitted applications and complete timeline audit history.

---

### 4. Interactive Frontend User Interfaces

#### 1. Student Job Discovery & AI Match Engine ([`frontend/pages/student/jobs.html`](file:///c:/Users/Voldemort/OneDrive/Documents/SIH%20PROJECT/frontend/pages/student/jobs.html))
* Multi-faceted filter sidebar (Domain, Type, Location, Skill, Eligibility toggle, Sort Order).
* Color-coded match gauge (`High >= 75%` green, `Medium >= 50%` yellow, `Low < 50%` red).
* Prioritized skill tags (`Critical`, `Important`, `Preferred`).
* **"Explain Match" Modal**: Interactive view showing exact percentage breakdowns, itemized missing vs matched skills, and academic eligibility checklist.
* **1-Click Apply** with real-time button state transition (`Apply Now` $\rightarrow$ `Applied`).

#### 2. Student Applications & Status Audit ([`frontend/pages/student/applications.html`](file:///c:/Users/Voldemort/OneDrive/Documents/SIH%20PROJECT/frontend/pages/student/applications.html))
* KPI metrics for active applications, reviews, interviews, and selections.
* Status badges (`APPLIED`, `UNDER_REVIEW`, `SHORTLISTED`, `ASSESSMENT`, `INTERVIEW`, `SELECTED`, `REJECTED`).
* **"Track Status" Modal**: Interactive visual vertical timeline displaying all status changes with reviewer notes and timestamps.

#### 3. Recruiter Hub & Candidate Pipeline ([`frontend/pages/recruiter/jobs.html`](file:///c:/Users/Voldemort/OneDrive/Documents/SIH%20PROJECT/frontend/pages/recruiter/jobs.html))
* Post New Job modal with dynamic skill builder: recruiters tag skills with priorities (`Critical`, `Important`, `Preferred`).
* Job listings table displaying approval status (`Pending Approval`, `Published`, `Rejected`).
* **Candidate Pipeline Drawer**: Lists applicants sorted by AI match score, with applicant details and one-click status transitions (`SHORTLISTED`, `INTERVIEW`, `SELECTED`, etc.) with feedback notes.

#### 4. Placement Admin Moderation Queue ([`frontend/pages/admin/jobs.html`](file:///c:/Users/Voldemort/OneDrive/Documents/SIH%20PROJECT/frontend/pages/admin/jobs.html))
* Real-time pending queue displaying recruiters, companies, CTC, prioritized skills, and job descriptions.
* **Approve & Publish**: Instantly releases job to student marketplace.
* **Reject with Notes**: Captures feedback reasons for the recruiter.

---

## Verification Results

### Automated Test Suite
* Ran full test suite via `python -m unittest discover -s tests`:
  ```
  Ran 25 tests in 8.607s
  OK
  ```
  * `tests/test_jobs_marketplace.py` (3 integration tests for job creation, admin moderation, AI matching, and applicant lifecycle) $\rightarrow$ **PASSED**
  * `tests/test_resume.py` $\rightarrow$ **PASSED**
  * `tests/test_students.py` $\rightarrow$ **PASSED**
  * `tests/test_auth.py` $\rightarrow$ **PASSED**
  * `tests/test_models.py` $\rightarrow$ **PASSED**
  * `tests/test_health.py` $\rightarrow$ **PASSED**

### Live Server End-to-End Workflow Verification
* Executed [`scratch/verify_marketplace_live.py`](file:///c:/Users/Voldemort/OneDrive/Documents/SIH%20PROJECT/scratch/verify_marketplace_live.py) against active server on `http://127.0.0.1:5000`:
  ```
  === LIVE WORKFLOW TEST ===
  [OK] Admin logged in successfully.
  [OK] Recruiter registered with expert_id=5, Status='PENDING'
  [OK] Admin approved recruiter account: Status='APPROVED'
  [OK] Recruiter logged in.
  [OK] Job created with ID=4, Status='Pending Approval'
  [OK] Job 4 confirmed present in Admin Pending Queue.
  [OK] Admin approved job: Status='Published'
  [OK] Student registered and logged in.
  [OK] Student skills added (Python, Docker).
  [OK] Student Job Match Computed: Overall Score = 81.2%
       - Skill Match Score: 85.0%
       - Role Fit Score: 75.0%
       - Eligibility: Eligible=True
  [OK] Application submitted with ID=2, Status='APPLIED'
  [OK] Recruiter retrieved applicant pipeline: Found candidate with match score 81.2%
  [OK] Recruiter updated application status: New Status='SHORTLISTED'
  [OK] Student timeline verified: Stage='APPLIED', Notes='Application submitted by student.'

  ALL 11 END-TO-END MARKETPLACE & MATCHING CHECKS PASSED!
  ```

---

## How to Test in the Browser

1. Ensure the Flask server is running:
   ```bash
   .\venv\Scripts\python backend/app.py
   ```
2. Open the application landing page in your browser:
   **`http://127.0.0.1:5000/`**
3. **Test as Admin**:
   * Go to **`http://127.0.0.1:5000/pages/login.html`**.
   * Click **"Fill Default Admin"** (`admin@college.edu` / configured `ADMIN_DEFAULT_PASSWORD`) and Sign In.
   * You are automatically redirected to the **Moderation Queue** at `http://127.0.0.1:5000/pages/admin/jobs.html`.
   * Review pending jobs and click **"Approve & Publish"**.
4. **Test as Recruiter**:
   * Go to **`http://127.0.0.1:5000/pages/recruiter/jobs.html`**.
   * Click **"Post New Job Opening"**, specify domain, CTC, requirements, and add skills with priorities (`Critical`, `Important`, `Preferred`).
   * View the candidate pipeline and click **"Candidates"** $\rightarrow$ **"Change Status"** to advance candidate stages with notes.
5. **Test as Student**:
   * Navigate to **`http://127.0.0.1:5000/pages/student/jobs.html`**.
   * Discover published jobs, filter by domain/skills/eligibility.
   * Click **"Explain Match"** to inspect the 5-dimensional breakdown.
   * Click **"Apply Now"**, then navigate to **`http://127.0.0.1:5000/pages/student/applications.html`** to track status transitions and reviewer notes in real-time.
