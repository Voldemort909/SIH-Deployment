"""
Recommendation & Skill-Gap Analysis Engine.
Provides deterministic, rule-based comparison between candidate skills
and industry target role profiles. Produces categorized gap analytics
and curated project blueprints to improve placement readiness.
"""
from typing import List, Dict, Any


ROLE_BENCHMARKS: Dict[str, Dict[str, Any]] = {
    "Software Engineer": {
        "critical_skills": ["Data Structures & Algorithms", "Object-Oriented Programming", "Python", "Java", "C++", "Database Management Systems"],
        "required_skills": [
            "Data Structures & Algorithms",
            "Object-Oriented Programming",
            "Database Management Systems",
            "Operating Systems",
            "Git",
            "Problem Solving"
        ],
        "secondary_skills": [
            "Python", "Java", "C++", "SQL", "MySQL", "REST APIs", "Docker", "Linux", "System Design"
        ],
        "project_blueprints": [
            {
                "title": "High-Throughput URL Shortener & Analytics Service",
                "difficulty": "Intermediate",
                "technologies": ["Python", "Flask", "Redis", "PostgreSQL", "Docker"],
                "description": "Design a scalable REST service with base62 encoding, custom aliases, click rate analytics, and Redis caching."
            },
            {
                "title": "Distributed Task Scheduler & Job Queue",
                "difficulty": "Advanced",
                "technologies": ["Java", "Spring Boot", "MySQL", "RabbitMQ"],
                "description": "Implement an asynchronous background worker engine handling retry mechanisms, priority scheduling, and worker heartbeat checks."
            }
        ]
    },
    "Full-Stack Developer": {
        "critical_skills": ["JavaScript", "React", "Node.js", "Python", "Flask", "REST APIs", "MySQL"],
        "required_skills": [
            "JavaScript",
            "React",
            "REST APIs",
            "MySQL",
            "Git",
            "HTML/CSS"
        ],
        "secondary_skills": [
            "TypeScript", "Node.js", "Flask", "PostgreSQL", "MongoDB", "Docker", "Redux", "Tailwind CSS"
        ],
        "project_blueprints": [
            {
                "title": "Collaborative Real-Time Kanban Board",
                "difficulty": "Intermediate",
                "technologies": ["React", "TypeScript", "Node.js", "PostgreSQL", "WebSockets"],
                "description": "Build a multi-user board with drag-and-drop cards, column management, activity feeds, and live cursor updates."
            },
            {
                "title": "E-Commerce Micro-Store with Payment Gateway Integration",
                "difficulty": "Advanced",
                "technologies": ["React", "Flask", "Stripe API", "MySQL", "Docker"],
                "description": "Full-fledged shopping platform featuring inventory management, JWT authentication, cart persistence, and webhook handling."
            }
        ]
    },
    "Data Scientist": {
        "critical_skills": ["Python", "Machine Learning", "SQL", "Pandas", "NumPy", "Data Analysis"],
        "required_skills": [
            "Python",
            "Machine Learning",
            "SQL",
            "Data Analysis",
            "Pandas",
            "NumPy"
        ],
        "secondary_skills": [
            "Scikit-Learn", "Data Visualization", "Matplotlib", "Seaborn", "Statistics", "Deep Learning", "PostgreSQL"
        ],
        "project_blueprints": [
            {
                "title": "Customer Churn Prediction & Feature Importance Dashboard",
                "difficulty": "Intermediate",
                "technologies": ["Python", "Scikit-Learn", "Pandas", "Streamlit", "XGBoost"],
                "description": "Analyze multi-variable user churn patterns, train gradient-boosted trees, and expose interactive what-if threshold simulators."
            },
            {
                "title": "Automated Financial Fraud Detection Engine",
                "difficulty": "Advanced",
                "technologies": ["Python", "Imbalanced-Learn", "Isolation Forest", "FastAPI"],
                "description": "Detect anomalous credit card transactions using anomaly detection, precision-recall curve tuning, and real-time inference endpoints."
            }
        ]
    },
    "DevOps / Cloud Engineer": {
        "critical_skills": ["Docker", "Kubernetes", "AWS", "Linux", "CI/CD", "Git"],
        "required_skills": [
            "Docker",
            "Linux",
            "Git",
            "CI/CD",
            "AWS"
        ],
        "secondary_skills": [
            "Kubernetes", "Terraform", "Bash", "Python", "Networking", "Prometheus", "Grafana"
        ],
        "project_blueprints": [
            {
                "title": "Automated Multi-Stage CI/CD Pipeline on GitHub Actions",
                "difficulty": "Intermediate",
                "technologies": ["Docker", "GitHub Actions", "AWS ECS", "Trivy", "Terraform"],
                "description": "Build automated linting, container vulnerability scanning, test execution, and blue/green production deployment on AWS."
            },
            {
                "title": "Self-Healing Kubernetes Cluster Monitoring Stack",
                "difficulty": "Advanced",
                "technologies": ["Kubernetes", "Helm", "Prometheus", "Grafana", "Alertmanager"],
                "description": "Deploy a multi-node cluster observing CPU/memory saturation, custom latency SLIs, and automated pod autoscaling."
            }
        ]
    },
    "Frontend Engineer": {
        "critical_skills": ["JavaScript", "TypeScript", "React", "HTML/CSS", "Git"],
        "required_skills": [
            "JavaScript",
            "React",
            "HTML/CSS",
            "Git",
            "Responsive Web Design"
        ],
        "secondary_skills": [
            "TypeScript", "Redux", "Tailwind CSS", "Bootstrap", "Next.js", "Web Performance", "Accessibility (a11y)"
        ],
        "project_blueprints": [
            {
                "title": "Accessible Design System & Interactive UI Component Library",
                "difficulty": "Intermediate",
                "technologies": ["TypeScript", "React", "Storybook", "Tailwind CSS"],
                "description": "Craft production-ready accessible components (Modals, Comboboxes, Data Grids) adhering to WCAG 2.1 AA standards."
            },
            {
                "title": "Offline-First Progressive Web App (PWA) Reader",
                "difficulty": "Advanced",
                "technologies": ["React", "Service Workers", "IndexedDB", "Web Push API"],
                "description": "A high-performance markdown content portal with offline document caching, sync background workers, and installable PWA manifest."
            }
        ]
    },
    "Backend Engineer": {
        "critical_skills": ["Python", "Java", "Flask", "Django", "SQL", "REST APIs", "Database Management Systems"],
        "required_skills": [
            "Python",
            "Database Management Systems",
            "REST APIs",
            "SQL",
            "Git"
        ],
        "secondary_skills": [
            "Flask", "FastAPI", "Django", "PostgreSQL", "MySQL", "Redis", "Docker", "Microservices", "System Design"
        ],
        "project_blueprints": [
            {
                "title": "Role-Based Multi-Tenant SaaS Authentication & Billing API",
                "difficulty": "Intermediate",
                "technologies": ["Python", "FastAPI", "PostgreSQL", "SQLAlchemy", "JWT"],
                "description": "Create a multi-tenant authorization backend with tenant isolation, rate limiting, and Stripe customer subscriptions."
            },
            {
                "title": "Scalable Real-Time Event Logging & Ingestion Service",
                "difficulty": "Advanced",
                "technologies": ["Python", "Kafka", "PostgreSQL", "ClickHouse", "Docker"],
                "description": "Process 10,000+ telemetry events per second with schema validation, batching buffers, and analytical aggregations."
            }
        ]
    }
}


def normalize_skill(skill_name: str) -> str:
    """Normalizes skill naming for fuzzy/standardized comparison."""
    return skill_name.strip().lower().replace("-", " ").replace(".", "")


def get_supported_roles() -> List[str]:
    """Returns list of supported target industry roles."""
    return list(ROLE_BENCHMARKS.keys())


def analyze_skill_gap(extracted_skills: List[str], target_role: str = "Software Engineer") -> Dict[str, Any]:
    """
    Performs comprehensive skill-gap analysis comparing candidate's extracted skills
    against target industry role benchmark requirements.
    """
    benchmark = ROLE_BENCHMARKS.get(target_role, ROLE_BENCHMARKS["Software Engineer"])
    
    # Normalize candidate skills
    candidate_lookup = {normalize_skill(s): s for s in extracted_skills}
    
    matched_skills = []
    missing_required = []
    missing_critical = []
    
    all_role_skills = benchmark["required_skills"] + benchmark["secondary_skills"]
    critical_skills = benchmark.get("critical_skills", benchmark["required_skills"][:3])
    
    # Evaluate role matches
    for req in all_role_skills:
        norm_req = normalize_skill(req)
        matched = False
        for c_norm, c_orig in candidate_lookup.items():
            if norm_req in c_norm or c_norm in norm_req:
                matched = True
                matched_skills.append(req)
                break
        if not matched:
            missing_required.append(req)
            if req in critical_skills:
                missing_critical.append(req)

    # De-duplicate lists
    matched_skills = sorted(list(set(matched_skills)))
    missing_required = sorted(list(set(missing_required)))
    missing_critical = sorted(list(set(missing_critical)))
    
    # Skills the candidate possesses that are outside the target role specification
    other_skills = [
        s for s in extracted_skills
        if not any(normalize_skill(s) in normalize_skill(m) or normalize_skill(m) in normalize_skill(s) for m in matched_skills)
    ]
    
    # Role match percentage calculation
    total_role_skills_count = len(set(all_role_skills))
    match_ratio = len(matched_skills) / max(total_role_skills_count, 1)
    # Give heavy bonus if critical skills are covered
    critical_matches = len([c for c in critical_skills if c in matched_skills])
    critical_ratio = critical_matches / max(len(critical_skills), 1)
    
    weighted_score = round((match_ratio * 0.4 + critical_ratio * 0.6) * 100, 1)
    weighted_score = min(max(weighted_score, 0.0), 100.0)

    # Prioritized recommended skills (critical missing first, then secondary missing)
    recommended_skills = missing_critical + [s for s in missing_required if s not in missing_critical][:4]

    return {
        "target_role": target_role,
        "match_score": weighted_score,
        "existing_skills": matched_skills,
        "other_skills": other_skills,
        "missing_skills": missing_required,
        "important_missing_skills": missing_critical,
        "recommended_skills": recommended_skills,
        "recommended_projects": benchmark.get("project_blueprints", [])
    }
