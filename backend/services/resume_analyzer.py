"""
Resume Parsing, Extraction, and Scoring Service.
Uses PyMuPDF (fitz) for safe text extraction, coupled with deterministic
rule-based NLP heuristics for structured candidate profile analysis.
Designed with BaseResumeAnalyzer ABC to allow future LLM / GenAI integration.
"""
from abc import ABC, abstractmethod
from io import BytesIO
import re
from typing import Dict, Any, List, Optional, Union
try:
    import pymupdf as fitz
except ImportError:
    import fitz


# Comprehensive Skill Catalog with Category Mapping
SKILL_CATALOG = {
    # Programming Languages
    "Python": ("Programming", [r"\bpython\b", r"\bpython3\b"]),
    "Java": ("Programming", [r"\bjava\b"]),
    "C++": ("Programming", [r"\bc\+\+\b", r"\bcpp\b"]),
    "C": ("Programming", [r"\bc\b(?!\+\+|#|\b\s*language)"]),
    "C#": ("Programming", [r"\bc#\b", r"\bc-sharp\b"]),
    "JavaScript": ("Programming", [r"\bjavascript\b", r"\bjs\b(?!\w)"]),
    "TypeScript": ("Programming", [r"\btypescript\b", r"\bts\b(?!\w)"]),
    "Go": ("Programming", [r"\bgolang\b", r"\bgo\s+language\b"]),
    "Rust": ("Programming", [r"\brust\b(?!\s*oxide)"]),
    "SQL": ("Programming", [r"\bsql\b"]),
    "R": ("Programming", [r"\br\s+programming\b", r"\br\s+language\b"]),
    "PHP": ("Programming", [r"\bphp\b"]),
    "Kotlin": ("Programming", [r"\bkotlin\b"]),
    "Swift": ("Programming", [r"\bswift\b(?!\s*transfer)"]),
    
    # Frameworks & Libraries
    "Flask": ("Backend Framework", [r"\bflask\b"]),
    "Django": ("Backend Framework", [r"\bdjango\b"]),
    "FastAPI": ("Backend Framework", [r"\bfastapi\b"]),
    "React": ("Frontend Framework", [r"\breact\b", r"\breactjs\b", r"\breact\.js\b"]),
    "Node.js": ("Backend Runtime", [r"\bnode\.?js\b", r"\bnodejs\b"]),
    "Express": ("Backend Framework", [r"\bexpress\.?js\b", r"\bexpress\b"]),
    "Angular": ("Frontend Framework", [r"\bangular\b", r"\bangularjs\b"]),
    "Vue": ("Frontend Framework", [r"\bvue\b", r"\bvue\.?js\b"]),
    "Spring Boot": ("Backend Framework", [r"\bspring\s*boot\b", r"\bspring\b"]),
    "ASP.NET": ("Backend Framework", [r"\basp\.net\b", r"\b\.net\s*core\b"]),
    "Next.js": ("Frontend Framework", [r"\bnext\.?js\b"]),
    "Redux": ("Frontend Framework", [r"\bredux\b"]),
    "Tailwind CSS": ("Frontend Framework", [r"\btailwind\b", r"\btailwindcss\b"]),
    "Bootstrap": ("Frontend Framework", [r"\bbootstrap\b"]),
    "HTML/CSS": ("Frontend Framework", [r"\bhtml5?\b", r"\bcss3?\b"]),
    
    # Data Science & Machine Learning
    "Pandas": ("Data Science", [r"\bpandas\b"]),
    "NumPy": ("Data Science", [r"\bnumpy\b"]),
    "Scikit-Learn": ("Data Science", [r"\bscikit-learn\b", r"\bsklearn\b"]),
    "TensorFlow": ("Data Science", [r"\btensorflow\b", r"\btf\b"]),
    "PyTorch": ("Data Science", [r"\bpytorch\b"]),
    "Machine Learning": ("Data Science", [r"\bmachine\s*learning\b", r"\bml\b"]),
    "Deep Learning": ("Data Science", [r"\bdeep\s*learning\b"]),
    "Data Analysis": ("Data Science", [r"\bdata\s*analysis\b", r"\bdata\s*analytics\b"]),
    "Data Visualization": ("Data Science", [r"\bdata\s*visualization\b", r"\bmatplotlib\b", r"\bseaborn\b"]),
    "NLP": ("Data Science", [r"\bnlp\b", r"\bnatural\s*language\s*processing\b"]),
    
    # Databases & Storage
    "MySQL": ("Database", [r"\bmysql\b"]),
    "PostgreSQL": ("Database", [r"\bpostgresql\b", r"\bpostgres\b"]),
    "MongoDB": ("Database", [r"\bmongodb\b", r"\bmongo\b"]),
    "SQLite": ("Database", [r"\bsqlite\b", r"\bsqlite3\b"]),
    "Redis": ("Database", [r"\bredis\b"]),
    "Oracle": ("Database", [r"\boracle\s*db\b", r"\boracle\s*database\b"]),
    
    # DevOps & Cloud
    "Docker": ("DevOps / Cloud", [r"\bdocker\b"]),
    "Kubernetes": ("DevOps / Cloud", [r"\bkubernetes\b", r"\bk8s\b"]),
    "AWS": ("DevOps / Cloud", [r"\baws\b", r"\bamazon\s*web\s*services\b"]),
    "GCP": ("DevOps / Cloud", [r"\bgcp\b", r"\bgoogle\s*cloud\b"]),
    "Azure": ("DevOps / Cloud", [r"\bazure\b", r"\bmicrosoft\s*azure\b"]),
    "Git": ("Tools & DevOps", [r"\bgit\b", r"\bgithub\b", r"\bgitlab\b"]),
    "Linux": ("DevOps / Cloud", [r"\blinux\b", r"\bubuntu\b", r"\bbash\b"]),
    "CI/CD": ("DevOps / Cloud", [r"\bci/cd\b", r"\bcontinuous\s*integration\b"]),
    "Terraform": ("DevOps / Cloud", [r"\bterraform\b"]),
    
    # Core CS & Software Architecture
    "Data Structures & Algorithms": ("Core CS", [r"\bdata\s*structures\b", r"\balgorithms\b", r"\bdsa\b"]),
    "Object-Oriented Programming": ("Core CS", [r"\bobject-oriented\b", r"\boop\b", r"\boops\b"]),
    "Database Management Systems": ("Core CS", [r"\bdatabase\s*management\b", r"\bdbms\b"]),
    "Operating Systems": ("Core CS", [r"\boperating\s*systems?\b", r"\bos\s*concepts\b"]),
    "Computer Networks": ("Core CS", [r"\bcomputer\s*networks?\b", r"\bnetworking\b"]),
    "REST APIs": ("Core CS", [r"\brest\s*apis?\b", r"\brestful\b", r"\brest\b"]),
    "System Design": ("Core CS", [r"\bsystem\s*design\b"]),
    "Microservices": ("Core CS", [r"\bmicroservices?\b"]),
    
    # Soft Skills & Methodologies
    "Problem Solving": ("Soft Skill", [r"\bproblem\s*solving\b"]),
    "Teamwork": ("Soft Skill", [r"\bteamwork\b", r"\bcollaboration\b"]),
    "Communication": ("Soft Skill", [r"\bcommunication\b", r"\binterpersonal\b"]),
    "Agile": ("Methodology", [r"\bagile\b", r"\bscrum\b"]),
    "Leadership": ("Soft Skill", [r"\bleadership\b"])
}

SECTION_PATTERNS = {
    "education": [r"\beducation\b", r"\bacademics?\b", r"\bqualifications?\b", r"\beducational\s*background\b"],
    "skills": [r"\bskills\b", r"\btechnical\s*skills\b", r"\bcore\s*competencies\b", r"\btechnologies\b", r"\btools\b"],
    "projects": [r"\bprojects?\b", r"\bacacademic\s*projects?\b", r"\bpersonal\s*projects?\b", r"\bkey\s*projects?\b"],
    "experience": [r"\bexperience\b", r"\bwork\s*experience\b", r"\binternships?\b", r"\bemployment\b", r"\bprofessional\s*experience\b"],
    "certifications": [r"\bcertifications?\b", r"\bcourses?\b", r"\blicenses?\b", r"\bachievements?\b", r"\bawards?\b"],
    "contact": [r"\bcontact\b", r"\bemail\b", r"\bphone\b", r"\blinkedin\b", r"\bgithub\b"]
}


class BaseResumeAnalyzer(ABC):
    """
    Abstract Base Class for Resume Analysis.
    Specifies standard extraction and scoring interfaces, enabling
    future LLM / GenAI analyzers to plug into the pipeline transparently.
    """

    @abstractmethod
    def extract_text(self, source: Union[str, bytes]) -> str:
        """Extracts clean text string from PDF file path or byte buffer."""
        pass

    @abstractmethod
    def parse_sections(self, text: str) -> Dict[str, str]:
        """Segments raw text into recognized resume sections."""
        pass

    @abstractmethod
    def extract_skills(self, text: str) -> List[Dict[str, str]]:
        """Identifies and categorizes technical and professional skills."""
        pass

    @abstractmethod
    def extract_education(self, text: str) -> Dict[str, Any]:
        """Extracts candidate degree, major, CGPA/percentage, and graduation batch."""
        pass

    @abstractmethod
    def extract_projects(self, text: str) -> List[Dict[str, Any]]:
        """Parses project titles, descriptions, technologies, and URLs."""
        pass

    @abstractmethod
    def extract_experience(self, text: str) -> List[Dict[str, Any]]:
        """Extracts work experience, internships, roles, and durations."""
        pass

    @abstractmethod
    def score_resume(self, parsed_data: Dict[str, Any], target_role_score: float = 70.0) -> Dict[str, Any]:
        """Calculates deterministic rubric score and actionable feedback."""
        pass


class RuleBasedResumeAnalyzer(BaseResumeAnalyzer):
    """
    Deterministic Resume Analyzer implementation using PyMuPDF and pattern matching.
    Provides fast, local, repeatable parsing without requiring external API keys.
    """

    def extract_text(self, source: Union[str, bytes]) -> str:
        """
        Safely extracts text using PyMuPDF (fitz).
        Guards against corrupt, encrypted, or image-only PDFs.
        """
        doc = None
        try:
            if isinstance(source, bytes):
                doc = fitz.open(stream=source, filetype="pdf")
            else:
                doc = fitz.open(source)

            if doc.is_encrypted:
                raise ValueError("PDF is encrypted or password-protected. Please upload an unlocked PDF.")

            if len(doc) == 0:
                raise ValueError("The uploaded PDF has 0 pages.")

            full_text_pages = []
            for page_index in range(len(doc)):
                page = doc[page_index]
                text = page.get_text("text")
                if text:
                    full_text_pages.append(text)

            combined_text = "\n".join(full_text_pages).strip()
            
            # Basic validation: ensure readable text was extracted
            if len(combined_text) < 30:
                raise ValueError(
                    "Insufficient readable text found in PDF. Scanned or image-only PDFs without an OCR layer are not supported."
                )

            # Normalize whitespaces and carriage returns
            combined_text = re.sub(r"\r\n", "\n", combined_text)
            combined_text = re.sub(r"[ \t]+", " ", combined_text)
            return combined_text

        except fitz.FileDataError as e:
            raise ValueError(f"Corrupt or invalid PDF file format: {str(e)}")
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Failed to process PDF document: {str(e)}")
        finally:
            if doc:
                doc.close()

    def parse_sections(self, text: str) -> Dict[str, str]:
        """
        Splits resume text into recognized standard sections using regex patterns.
        """
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        sections: Dict[str, List[str]] = {
            "header": [],
            "education": [],
            "skills": [],
            "projects": [],
            "experience": [],
            "certifications": [],
            "other": []
        }

        current_section = "header"

        for line in lines:
            line_lower = line.lower()
            # Check if line acts as a standalone section header (short line)
            is_header = False
            if len(line.split()) <= 4 and len(line) < 45:
                for sec_name, patterns in SECTION_PATTERNS.items():
                    if sec_name == "contact":
                        continue
                    if any(re.search(pat, line_lower) for pat in patterns):
                        current_section = sec_name
                        is_header = True
                        break

            if not is_header:
                sections[current_section].append(line)

        return {k: "\n".join(v) for k, v in sections.items()}

    def extract_skills(self, text: str) -> List[Dict[str, str]]:
        """
        Scans resume text against standard skill patterns with boundary detection.
        """
        extracted = []
        text_lower = f" {text.lower()} "

        for skill_name, (category, patterns) in SKILL_CATALOG.items():
            matched = False
            for pat in patterns:
                if re.search(pat, text_lower, re.IGNORECASE):
                    matched = True
                    break
            if matched:
                extracted.append({
                    "name": skill_name,
                    "category": category
                })

        # Sort alphabetically by name
        return sorted(extracted, key=lambda s: s["name"])

    def extract_education(self, text: str) -> Dict[str, Any]:
        """
        Extracts degree, major/department, CGPA, and batch year.
        """
        result = {
            "degree": None,
            "department": None,
            "cgpa": None,
            "graduation_year": None
        }

        # 1. Degree Detection
        degree_patterns = [
            (r"\bb\.?tech\b|\bbachelor\s+of\s+technology\b", "B.Tech"),
            (r"\bb\.?e\.?\b|\bbachelor\s+of\s+engineering\b", "B.E."),
            (r"\bm\.?tech\b|\bmaster\s+of\s+technology\b", "M.Tech"),
            (r"\bbca\b|\bbachelor\s+of\s+computer\s+applications?\b", "BCA"),
            (r"\bmca\b|\bmaster\s+of\s+computer\s+applications?\b", "MCA"),
            (r"\bb\.?sc\b|\bbachelor\s+of\s+science\b", "B.Sc"),
            (r"\bm\.?sc\b|\bmaster\s+of\s+science\b", "M.Sc")
        ]
        for pat, deg_label in degree_patterns:
            if re.search(pat, text, re.IGNORECASE):
                result["degree"] = deg_label
                break

        # 2. Department Detection
        dept_patterns = [
            (r"computer\s*science|cse|information\s*technology|it\b", "Computer Science & Engineering"),
            (r"electronics|electrical|ece|eee", "Electronics & Communication"),
            (r"mechanical|mech\b", "Mechanical Engineering"),
            (r"civil\b", "Civil Engineering"),
            (r"artificial\s*intelligence|ai\s*(&|and)?\s*ml|data\s*science", "AI & Data Science")
        ]
        for pat, dept_label in dept_patterns:
            if re.search(pat, text, re.IGNORECASE):
                result["department"] = dept_label
                break

        # 3. CGPA / Percentage Detection
        cgpa_match = re.search(r"(?:cgpa|gpa|score|pointer)\s*[:=-]?\s*([0-9]\.[0-9]{1,2})\s*(?:/\s*10)?", text, re.IGNORECASE)
        if cgpa_match:
            try:
                result["cgpa"] = float(cgpa_match.group(1))
            except ValueError:
                pass
        else:
            pct_match = re.search(r"([0-9]{2}(?:\.[0-9]{1,2})?)\s*%", text)
            if pct_match:
                try:
                    pct = float(pct_match.group(1))
                    result["cgpa"] = round(pct / 9.5, 2)  # Common Indian CBSE/VTU conversion
                except ValueError:
                    pass

        # 4. Graduation Year Detection (2018 - 2032)
        year_match = re.search(r"\b(202[0-9]|203[0-2])\b", text)
        if year_match:
            result["graduation_year"] = int(year_match.group(1))

        return result

    def extract_projects(self, text: str) -> List[Dict[str, Any]]:
        """
        Extracts projects, looking for project titles, tech tags, and links.
        """
        projects = []
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        # Find URLs
        github_links = re.findall(r"https?://github\.com/[a-zA-Z0-9_\-\.]+", text)
        live_links = re.findall(r"https?://[a-zA-Z0-9_\-\.]+\.(?:vercel\.app|netlify\.app|render\.com|herokuapp\.com|[a-z]{2,4})[a-zA-Z0-9_/\-\.]*", text)

        # Basic heuristic: look for lines that contain "project", "app", "system", "portal"
        for i, line in enumerate(lines):
            if any(term in line.lower() for term in ["portal", "platform", "system", "app", "engine", "tracker", "dashboard", "clone", "screener", "analyzer"]):
                if len(line) < 80 and not line.lower().startswith("worked on"):
                    title = line.strip(" -:*•")
                    desc = lines[i + 1] if i + 1 < len(lines) else ""
                    tech = ""
                    # Check if next line contains Tech / Technologies
                    for offset in range(1, 4):
                        if i + offset < len(lines) and any(k in lines[i + offset].lower() for k in ["tech:", "technologies:", "tools:", "stack:"]):
                            tech = lines[i + offset]
                            break
                    projects.append({
                        "title": title,
                        "description": desc[:200] if desc else None,
                        "technologies": tech if tech else None
                    })
            if len(projects) >= 5:
                break

        # Associate found links with first projects
        for idx, p in enumerate(projects):
            if idx < len(github_links):
                p["github_url"] = github_links[idx]
            if idx < len(live_links):
                p["live_url"] = live_links[idx]

        return projects

    def extract_experience(self, text: str) -> List[Dict[str, Any]]:
        """
        Extracts work experience, internships, or leadership positions.
        """
        experiences = []
        internship_matches = re.findall(r"(?:intern|internship|developer|trainee|engineer|lead|assistant)[^\n]{0,60}", text, re.IGNORECASE)
        for match in internship_matches[:4]:
            clean_role = match.strip(" -:*•")
            if len(clean_role) > 5 and not any(clean_role in e["role"] for e in experiences):
                experiences.append({
                    "role": clean_role,
                    "type": "Internship" if "intern" in clean_role.lower() else "Work Experience"
                })
        return experiences

    def score_resume(self, parsed_data: Dict[str, Any], target_role_score: float = 70.0) -> Dict[str, Any]:
        """
        Calculates a deterministic 100-point score across 6 clearly defined criteria:
        1. Resume Structure & Organization (Max 20 pts)
        2. Technical Skills Depth & Diversity (Max 25 pts)
        3. Portfolio Projects & Practical Evidence (Max 20 pts)
        4. Academic & Education Clarity (Max 15 pts)
        5. Experience & Internships (Max 10 pts)
        6. Target-Role Alignment & Keywords (Max 10 pts)
        """
        breakdown = {}
        strengths = []
        improvements = []

        # 1. Structure (Max 20 pts)
        sections = parsed_data.get("sections", {})
        contact_info = parsed_data.get("contact", {})
        struct_score = 0

        # Check contact completeness (5 pts)
        if contact_info.get("email"):
            struct_score += 2
        if contact_info.get("phone"):
            struct_score += 1.5
        if contact_info.get("linkedin") or contact_info.get("github"):
            struct_score += 1.5

        # Check key sections (15 pts: 3 pts each for education, skills, projects, experience, header)
        found_sections = []
        for sec in ["education", "skills", "projects", "experience"]:
            if sections.get(sec) and len(sections[sec]) > 20:
                struct_score += 3.75
                found_sections.append(sec.capitalize())

        breakdown["structure"] = {
            "score": round(min(struct_score, 20.0), 1),
            "max": 20,
            "details": f"Found sections: {', '.join(found_sections) if found_sections else 'Basic layout'}."
        }
        if struct_score >= 17:
            strengths.append("Clean and well-structured resume layout with standard section headers.")
        else:
            improvements.append("Ensure distinct section headings for Education, Technical Skills, Projects, and Experience.")

        # 2. Skills (Max 25 pts)
        skills = parsed_data.get("skills", [])
        skill_count = len(skills)
        categories = set(s["category"] for s in skills)
        skills_score = 0.0

        if skill_count >= 8:
            skills_score = 20.0
        elif skill_count >= 5:
            skills_score = 15.0
        elif skill_count >= 3:
            skills_score = 10.0
        elif skill_count >= 1:
            skills_score = 5.0

        # Category diversity bonus (up to 5 pts)
        if len(categories) >= 4:
            skills_score += 5.0
        elif len(categories) >= 2:
            skills_score += 3.0

        breakdown["skills"] = {
            "score": round(min(skills_score, 25.0), 1),
            "max": 25,
            "details": f"Detected {skill_count} technical skills across {len(categories)} distinct categories."
        }
        if skill_count >= 7:
            strengths.append(f"Strong skill representation ({skill_count} skills across {len(categories)} domain areas).")
        else:
            improvements.append("Broaden technical skills catalog by adding relevant tools, databases, and frameworks.")

        # 3. Projects (Max 20 pts)
        projects = parsed_data.get("projects", [])
        proj_count = len(projects)
        proj_score = 0.0

        if proj_count >= 3:
            proj_score = 15.0
        elif proj_count >= 2:
            proj_score = 12.0
        elif proj_count >= 1:
            proj_score = 8.0

        # Links bonus (up to 5 pts)
        has_links = any(isinstance(p, dict) and (p.get("github_url") or p.get("live_url")) for p in projects)
        if has_links:
            proj_score += 5.0

        breakdown["projects"] = {
            "score": round(min(proj_score, 20.0), 1),
            "max": 20,
            "details": f"Identified {proj_count} portfolio projects (GitHub/Demo links: {'Yes' if has_links else 'None detected'})."
        }
        if proj_score >= 15:
            strengths.append("Solid portfolio project presence with verifiable links.")
        else:
            improvements.append("Include 2-3 substantial projects with GitHub links and live deployment URLs.")

        # 4. Education (Max 15 pts)
        edu = parsed_data.get("education", {}) if isinstance(parsed_data.get("education"), dict) else {}
        edu_score = 0.0
        if edu.get("degree"):
            edu_score += 6.0
        if edu.get("department"):
            edu_score += 4.0
        if edu.get("cgpa"):
            edu_score += 3.0
        if edu.get("graduation_year"):
            edu_score += 2.0

        breakdown["education"] = {
            "score": round(min(edu_score, 15.0), 1),
            "max": 15,
            "details": f"Degree: {edu.get('degree') or 'Unspecified'} | Major: {edu.get('department') or 'Unspecified'} | CGPA: {edu.get('cgpa') or 'Not listed'}."
        }
        if edu_score >= 12:
            strengths.append("Clearly stated academic qualifications and graduation timeline.")
        else:
            improvements.append("Explicitly state degree name, department, CGPA, and expected graduation year.")

        # 5. Experience (Max 10 pts)
        exp = parsed_data.get("experience", [])
        exp_count = len(exp)
        exp_score = 0.0
        if exp_count >= 2:
            exp_score = 10.0
        elif exp_count == 1:
            exp_score = 7.0
        else:
            # Check for action verbs in raw text as partial credit
            action_verbs = ["developed", "built", "implemented", "designed", "optimized", "engineered", "collaborated"]
            raw_text = parsed_data.get("raw_text", "").lower()
            verb_count = sum(1 for v in action_verbs if v in raw_text)
            exp_score = min(float(verb_count), 4.0)

        breakdown["experience"] = {
            "score": round(min(exp_score, 10.0), 1),
            "max": 10,
            "details": f"{exp_count} internship/work experiences detected."
        }
        if exp_score >= 7:
            strengths.append("Valuable internship or industry experience demonstrated.")
        else:
            improvements.append("Add internship experience, open-source contributions, or campus technical leadership.")

        # 6. Target Role Relevance (Max 10 pts)
        # Scaled from the role match score (0-100% -> 0-10 pts)
        role_pts = (target_role_score / 100.0) * 10.0
        breakdown["role_relevance"] = {
            "score": round(min(role_pts, 10.0), 1),
            "max": 10,
            "details": f"Alignment score with target industry role: {target_role_score}%."
        }

        # Overall Total Score (Sum of all 6 criteria)
        total_score = round(
            breakdown["structure"]["score"] +
            breakdown["skills"]["score"] +
            breakdown["projects"]["score"] +
            breakdown["education"]["score"] +
            breakdown["experience"]["score"] +
            breakdown["role_relevance"]["score"],
            1
        )
        total_score = min(max(total_score, 0.0), 100.0)

        # Performance Tier Rating
        if total_score >= 80:
            rating_label = "Placement Ready (Excellent)"
        elif total_score >= 65:
            rating_label = "Competitive (Good Foundation)"
        elif total_score >= 50:
            rating_label = "Moderate (Needs Refinement)"
        else:
            rating_label = "Needs Substantial Improvement"

        return {
            "overall_score": total_score,
            "rating_label": rating_label,
            "score_breakdown": breakdown,
            "strengths": strengths,
            "improvements": improvements
        }

    def analyze_resume_pipeline(self, source: Union[str, bytes], target_role: str = "Software Engineer") -> Dict[str, Any]:
        """
        Executes the complete end-to-end resume intelligence pipeline:
        PDF -> Text Extraction -> Section Parsing -> Skill Extraction ->
        Education Extraction -> Project Extraction -> Experience Extraction ->
        Deterministic Scoring.
        """
        # Step 1: Text extraction via PyMuPDF
        raw_text = self.extract_text(source)

        # Step 2: Section parsing
        sections = self.parse_sections(raw_text)

        # Step 3: Contact details extraction
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", raw_text)
        phone_match = re.search(r"(?:\+?91[\-\s]?)?[6-9]\d{9}\b|\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", raw_text)
        linkedin_match = re.search(r"linkedin\.com/in/[\w\-]+", raw_text)
        github_match = re.search(r"github\.com/[\w\-]+", raw_text)

        contact = {
            "email": email_match.group(0) if email_match else None,
            "phone": phone_match.group(0) if phone_match else None,
            "linkedin": f"https://{linkedin_match.group(0)}" if linkedin_match else None,
            "github": f"https://{github_match.group(0)}" if github_match else None
        }

        # Step 4: Skills extraction
        skills = self.extract_skills(raw_text)

        # Step 5: Education extraction
        education = self.extract_education(sections.get("education", "") or raw_text)

        # Step 6: Projects extraction
        projects = self.extract_projects(sections.get("projects", "") or raw_text)

        # Step 7: Experience extraction
        experience = self.extract_experience(sections.get("experience", "") or raw_text)

        parsed_data = {
            "raw_text": raw_text,
            "sections": sections,
            "contact": contact,
            "skills": skills,
            "education": education,
            "projects": projects,
            "experience": experience
        }

        return parsed_data
