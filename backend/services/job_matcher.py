"""
Explainable Job Match Scoring Engine.
Calculates transparent, multi-dimensional candidate-to-job match scores
based on weighted skill priorities (Critical, Important, Preferred),
role/domain alignment, student career preferences, and academic eligibility.
"""
from typing import Dict, Any, List, Set


def normalize(text: str) -> str:
    """Normalizes string for comparison."""
    if not text:
        return ""
    return text.strip().lower().replace("-", " ").replace(".", "")


def calculate_job_match(student, job) -> Dict[str, Any]:
    """
    Computes explainable match scores between a student and a job opening.
    Returns:
      - overall_match (0 - 100)
      - skill_match (0 - 100)
      - role_match (0 - 100)
      - preference_match (0 - 100)
      - eligibility (itemized eligibility criteria)
      - skill_details (critical, important, preferred breakdowns)
      - explanation (plain English explanation)
    """
    # 1. Gather all skills associated with student
    student_skills_set: Set[str] = set()
    for ss in student.student_skills:
        if ss.skill:
            student_skills_set.add(normalize(ss.skill.name))

    # Also include skills from primary resume if available
    primary_resume = next((r for r in student.resumes if r.is_primary), student.resumes[-1] if student.resumes else None)
    if primary_resume and primary_resume.analysis and primary_resume.analysis.parsed_skills_json:
        try:
            import json
            resume_skills = json.loads(primary_resume.analysis.parsed_skills_json)
            for s in resume_skills:
                if isinstance(s, dict) and "name" in s:
                    student_skills_set.add(normalize(s["name"]))
                elif isinstance(s, str):
                    student_skills_set.add(normalize(s))
        except Exception:
            pass

    # 2. Categorize Job Skills by Priority
    critical_skills = []
    important_skills = []
    preferred_skills = []

    for js in job.required_skills:
        skill_name = js.skill.name if js.skill else ""
        if not skill_name:
            continue
        p = (js.priority or "Important").capitalize()
        if p == "Critical":
            critical_skills.append(skill_name)
        elif p == "Preferred":
            preferred_skills.append(skill_name)
        else:
            important_skills.append(skill_name)

    # 3. Calculate Skill Match Score
    matched_skills = []
    missing_critical = []
    missing_important = []
    missing_preferred = []

    def check_match(s_name: str) -> bool:
        norm = normalize(s_name)
        return any(norm in cand or cand in norm for cand in student_skills_set)

    for s in critical_skills:
        if check_match(s):
            matched_skills.append(s)
        else:
            missing_critical.append(s)

    for s in important_skills:
        if check_match(s):
            matched_skills.append(s)
        else:
            missing_important.append(s)

    for s in preferred_skills:
        if check_match(s):
            matched_skills.append(s)
        else:
            missing_preferred.append(s)

    total_crit = len(critical_skills)
    total_imp = len(important_skills)
    total_pref = len(preferred_skills)

    crit_ratio = (total_crit - len(missing_critical)) / total_crit if total_crit > 0 else 1.0
    imp_ratio = (total_imp - len(missing_important)) / total_imp if total_imp > 0 else 1.0
    pref_ratio = (total_pref - len(missing_preferred)) / total_pref if total_pref > 0 else 1.0

    # Skill score weighting: Critical 50%, Important 35%, Preferred 15%
    if total_crit == 0 and total_imp == 0 and total_pref == 0:
        skill_match_score = 100.0
    else:
        weights_sum = (0.50 if total_crit > 0 else 0) + (0.35 if total_imp > 0 else 0) + (0.15 if total_pref > 0 else 0)
        weighted_sum = (crit_ratio * 0.50 if total_crit > 0 else 0) + \
                       (imp_ratio * 0.35 if total_imp > 0 else 0) + \
                       (pref_ratio * 0.15 if total_pref > 0 else 0)
        skill_match_score = round((weighted_sum / weights_sum) * 100.0, 1) if weights_sum > 0 else 100.0

    # 4. Role & Domain Match Score (0 - 100)
    role_score = 50.0  # Baseline
    job_title_norm = normalize(job.title)
    job_domain_norm = normalize(job.domain or "")
    dept_norm = normalize(student.department or "")

    # Department relevance
    if "computer" in dept_norm or "information" in dept_norm:
        if any(tech_kw in job_title_norm or tech_kw in job_domain_norm for tech_kw in ["software", "developer", "engineer", "full stack", "data", "web", "ai", "cloud"]):
            role_score += 25.0
    elif "electronics" in dept_norm:
        if any(ec_kw in job_title_norm for ec_kw in ["embedded", "iot", "firmware", "hardware", "engineer"]):
            role_score += 25.0

    # Check student career preferences
    pref = student.preferences
    if pref:
        if pref.preferred_domain and (normalize(pref.preferred_domain) in job_domain_norm or job_domain_norm in normalize(pref.preferred_domain)):
            role_score += 15.0
        if pref.preferred_roles and any(r.strip().lower() in job_title_norm for r in pref.preferred_roles.split(",")):
            role_score += 10.0

    role_match_score = min(round(role_score, 1), 100.0)

    # 5. Preference Match Score (Job Type & Location)
    pref_score = 60.0  # Baseline
    if pref:
        # Job Type check
        if pref.job_type_preference in ["Both", None, ""]:
            pref_score += 20.0
        elif pref.job_type_preference.lower() == job.job_type.lower():
            pref_score += 20.0
        else:
            pref_score += 5.0

        # Location check
        if pref.preferred_locations:
            job_loc_norm = normalize(job.location or "")
            if any(normalize(loc) in job_loc_norm for loc in pref.preferred_locations.split(",")):
                pref_score += 20.0
            elif "remote" in job_loc_norm or "hybrid" in job_loc_norm:
                pref_score += 15.0
            else:
                pref_score += 5.0
        else:
            pref_score += 15.0
    else:
        pref_score = 80.0

    preference_match_score = min(round(pref_score, 1), 100.0)

    # 6. Academic Eligibility Checks
    stu_cgpa = float(student.cgpa) if student.cgpa is not None else 0.0
    min_cgpa = float(job.min_cgpa) if job.min_cgpa is not None else 0.0
    cgpa_ok = stu_cgpa >= min_cgpa

    # Batch Year Check
    batch_ok = True
    if job.eligible_batch_years and student.batch_year:
        allowed_batches = [b.strip() for b in job.eligible_batch_years.split(",") if b.strip()]
        if allowed_batches:
            batch_ok = str(student.batch_year) in allowed_batches

    # Branch Check
    branch_ok = True
    if job.eligible_branches and student.department:
        allowed_branches = [b.strip().lower() for b in job.eligible_branches.split(",") if b.strip()]
        if allowed_branches:
            branch_ok = any(b in student.department.lower() for b in allowed_branches)

    is_eligible = cgpa_ok and batch_ok and branch_ok

    # 7. Overall Match Score Calculation
    # Weights: Skill Match 50%, Role Match 25%, Preference Match 25%
    overall = (skill_match_score * 0.50) + (role_match_score * 0.25) + (preference_match_score * 0.25)
    
    # If not eligible, cap overall match at 50% max to reflect requirement barrier
    if not is_eligible:
        overall = min(overall, 49.0)

    overall_match_score = round(overall, 1)

    # 8. Human-Readable Explanation
    reasons = []
    if is_eligible:
        reasons.append("You satisfy all academic criteria (CGPA, department, and graduation year).")
    else:
        failed = []
        if not cgpa_ok: failed.append(f"CGPA ({stu_cgpa} vs min required {min_cgpa})")
        if not batch_ok: failed.append(f"Graduation batch ({student.batch_year})")
        if not branch_ok: failed.append(f"Department ({student.department})")
        reasons.append(f"Eligibility warning: does not meet criteria for {', '.join(failed)}.")

    if len(missing_critical) == 0 and total_crit > 0:
        reasons.append("You match 100% of the Critical skills required for this position.")
    elif len(missing_critical) > 0:
        reasons.append(f"Missing {len(missing_critical)} Critical skill(s): {', '.join(missing_critical)}.")

    if len(missing_important) > 0:
        reasons.append(f"Consider learning {', '.join(missing_important[:2])} to increase your candidate standing.")

    if preference_match_score >= 80:
        reasons.append(f"Your preferences ({job.job_type}, location) strongly align with this opening.")

    explanation_text = " ".join(reasons)

    return {
        "overall_match": overall_match_score,
        "skill_match": skill_match_score,
        "role_match": role_match_score,
        "preference_match": preference_match_score,
        "eligibility": {
            "is_eligible": is_eligible,
            "cgpa": {
                "satisfied": cgpa_ok,
                "student_value": stu_cgpa,
                "required_min": min_cgpa,
                "detail": f"CGPA: {stu_cgpa} / {min_cgpa} min"
            },
            "batch": {
                "satisfied": batch_ok,
                "student_value": student.batch_year,
                "allowed_batches": job.eligible_batch_years or "All",
                "detail": f"Batch: {student.batch_year} ({'Eligible' if batch_ok else 'Ineligible'})"
            },
            "branch": {
                "satisfied": branch_ok,
                "student_value": student.department,
                "allowed_branches": job.eligible_branches or "All",
                "detail": f"Branch: {student.department} ({'Eligible' if branch_ok else 'Ineligible'})"
            }
        },
        "skill_details": {
            "matched_skills": matched_skills,
            "missing_critical": missing_critical,
            "missing_important": missing_important,
            "missing_preferred": missing_preferred,
            "counts": {
                "critical_total": total_crit,
                "critical_matched": total_crit - len(missing_critical),
                "important_total": total_imp,
                "important_matched": total_imp - len(missing_important),
                "preferred_total": total_pref,
                "preferred_matched": total_pref - len(missing_preferred),
                "total_skills": total_crit + total_imp + total_pref,
                "total_matched": len(matched_skills)
            }
        },
        "explanation": explanation_text
    }
