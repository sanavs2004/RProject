"""
Learning Path Generator Module for RecruitAI
Generates personalized upskilling paths for rejected/hold candidates
based on their missing skills and the job requirements.
"""

import os
import json
import requests
from datetime import datetime


# ─── Static resource map ────────────────────────────────────────────────────
SKILL_RESOURCES = {
    # Programming languages
    "python": {
        "courses": [
            {"title": "Python for Everybody", "platform": "Coursera", "url": "https://www.coursera.org/specializations/python", "level": "Beginner", "duration": "4 months"},
            {"title": "Complete Python Bootcamp", "platform": "Udemy", "url": "https://www.udemy.com/course/complete-python-bootcamp/", "level": "Beginner", "duration": "22 hours"},
        ],
        "practice": [
            {"title": "LeetCode Python Problems", "url": "https://leetcode.com/problemset/all/?difficulty=EASY&listId=wpwgkgt", "type": "Practice"},
            {"title": "HackerRank Python", "url": "https://www.hackerrank.com/domains/python", "type": "Practice"},
        ],
        "docs": "https://docs.python.org/3/tutorial/",
        "estimated_weeks": 8
    },
    "javascript": {
        "courses": [
            {"title": "JavaScript Algorithms and Data Structures", "platform": "freeCodeCamp", "url": "https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures/", "level": "Beginner", "duration": "300 hours"},
            {"title": "The Complete JavaScript Course", "platform": "Udemy", "url": "https://www.udemy.com/course/the-complete-javascript-course/", "level": "Beginner", "duration": "69 hours"},
        ],
        "practice": [
            {"title": "JavaScript30", "url": "https://javascript30.com/", "type": "Project"},
        ],
        "docs": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide",
        "estimated_weeks": 10
    },
    "react": {
        "courses": [
            {"title": "React - The Complete Guide", "platform": "Udemy", "url": "https://www.udemy.com/course/react-the-complete-guide-incl-redux/", "level": "Intermediate", "duration": "48 hours"},
            {"title": "Full Stack Open - React", "platform": "University of Helsinki", "url": "https://fullstackopen.com/en/", "level": "Intermediate", "duration": "Self-paced"},
        ],
        "practice": [
            {"title": "Build 25 React Projects", "url": "https://www.youtube.com/watch?v=5ZdHfJVAY-s", "type": "Project"},
        ],
        "docs": "https://react.dev/learn",
        "estimated_weeks": 8
    },
    "machine learning": {
        "courses": [
            {"title": "Machine Learning Specialization", "platform": "Coursera (Andrew Ng)", "url": "https://www.coursera.org/specializations/machine-learning-introduction", "level": "Intermediate", "duration": "3 months"},
            {"title": "Fast.ai Practical Deep Learning", "platform": "fast.ai", "url": "https://course.fast.ai/", "level": "Intermediate", "duration": "Self-paced"},
        ],
        "practice": [
            {"title": "Kaggle Learn ML", "url": "https://www.kaggle.com/learn/machine-learning", "type": "Practice"},
        ],
        "docs": "https://scikit-learn.org/stable/user_guide.html",
        "estimated_weeks": 16
    },
    "deep learning": {
        "courses": [
            {"title": "Deep Learning Specialization", "platform": "Coursera (Andrew Ng)", "url": "https://www.coursera.org/specializations/deep-learning", "level": "Advanced", "duration": "5 months"},
        ],
        "practice": [
            {"title": "Kaggle Deep Learning", "url": "https://www.kaggle.com/learn/deep-learning", "type": "Practice"},
        ],
        "docs": "https://pytorch.org/tutorials/",
        "estimated_weeks": 20
    },
    "nlp": {
        "courses": [
            {"title": "NLP with Hugging Face", "platform": "Hugging Face", "url": "https://huggingface.co/learn/nlp-course/", "level": "Intermediate", "duration": "Self-paced"},
            {"title": "Natural Language Processing Specialization", "platform": "Coursera (DeepLearning.AI)", "url": "https://www.coursera.org/specializations/natural-language-processing", "level": "Advanced", "duration": "4 months"},
        ],
        "practice": [
            {"title": "NLP Projects on Kaggle", "url": "https://www.kaggle.com/competitions?search=nlp", "type": "Project"},
        ],
        "docs": "https://www.nltk.org/book/",
        "estimated_weeks": 12
    },
    "sql": {
        "courses": [
            {"title": "SQL for Data Science", "platform": "Coursera", "url": "https://www.coursera.org/learn/sql-for-data-science", "level": "Beginner", "duration": "4 weeks"},
            {"title": "The Complete SQL Bootcamp", "platform": "Udemy", "url": "https://www.udemy.com/course/the-complete-sql-bootcamp/", "level": "Beginner", "duration": "9 hours"},
        ],
        "practice": [
            {"title": "SQLZoo", "url": "https://sqlzoo.net/", "type": "Practice"},
            {"title": "LeetCode SQL", "url": "https://leetcode.com/problemset/database/", "type": "Practice"},
        ],
        "docs": "https://www.postgresql.org/docs/current/tutorial.html",
        "estimated_weeks": 4
    },
    "docker": {
        "courses": [
            {"title": "Docker & Kubernetes: The Practical Guide", "platform": "Udemy", "url": "https://www.udemy.com/course/docker-kubernetes-the-practical-guide/", "level": "Intermediate", "duration": "23 hours"},
        ],
        "practice": [
            {"title": "Play with Docker", "url": "https://labs.play-with-docker.com/", "type": "Practice"},
        ],
        "docs": "https://docs.docker.com/get-started/",
        "estimated_weeks": 3
    },
    "aws": {
        "courses": [
            {"title": "AWS Cloud Practitioner Essentials", "platform": "AWS Training", "url": "https://aws.amazon.com/training/digital/aws-cloud-practitioner-essentials/", "level": "Beginner", "duration": "6 hours"},
            {"title": "Ultimate AWS Certified Developer", "platform": "Udemy", "url": "https://www.udemy.com/course/aws-certified-developer-associate-dva-c01/", "level": "Intermediate", "duration": "32 hours"},
        ],
        "practice": [
            {"title": "AWS Free Tier Projects", "url": "https://aws.amazon.com/free/", "type": "Project"},
        ],
        "docs": "https://docs.aws.amazon.com/",
        "estimated_weeks": 8
    },
    "java": {
        "courses": [
            {"title": "Java Programming Masterclass", "platform": "Udemy", "url": "https://www.udemy.com/course/java-the-complete-java-developer-course/", "level": "Beginner", "duration": "80 hours"},
        ],
        "practice": [
            {"title": "Exercism Java Track", "url": "https://exercism.org/tracks/java", "type": "Practice"},
        ],
        "docs": "https://docs.oracle.com/javase/tutorial/",
        "estimated_weeks": 12
    },
    "data science": {
        "courses": [
            {"title": "IBM Data Science Professional Certificate", "platform": "Coursera", "url": "https://www.coursera.org/professional-certificates/ibm-data-science", "level": "Beginner", "duration": "3 months"},
        ],
        "practice": [
            {"title": "Kaggle Data Science Competitions", "url": "https://www.kaggle.com/competitions", "type": "Project"},
        ],
        "docs": "https://pandas.pydata.org/docs/user_guide/index.html",
        "estimated_weeks": 16
    },
    "flask": {
        "courses": [
            {"title": "Python and Flask Bootcamp", "platform": "Udemy", "url": "https://www.udemy.com/course/python-and-flask-bootcamp-create-websites-using-flask/", "level": "Intermediate", "duration": "20 hours"},
        ],
        "practice": [
            {"title": "Flask Mega-Tutorial", "url": "https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world", "type": "Tutorial"},
        ],
        "docs": "https://flask.palletsprojects.com/en/3.0.x/tutorial/",
        "estimated_weeks": 4
    },
    "django": {
        "courses": [
            {"title": "Django for Everybody", "platform": "Coursera", "url": "https://www.coursera.org/specializations/django", "level": "Intermediate", "duration": "4 months"},
        ],
        "practice": [
            {"title": "Django Girls Tutorial", "url": "https://tutorial.djangogirls.org/", "type": "Tutorial"},
        ],
        "docs": "https://docs.djangoproject.com/en/stable/intro/tutorial01/",
        "estimated_weeks": 6
    },
    "tensorflow": {
        "courses": [
            {"title": "TensorFlow Developer Certificate", "platform": "Coursera (DeepLearning.AI)", "url": "https://www.coursera.org/professional-certificates/tensorflow-in-practice", "level": "Intermediate", "duration": "4 months"},
        ],
        "practice": [
            {"title": "TensorFlow Tutorials", "url": "https://www.tensorflow.org/tutorials", "type": "Tutorial"},
        ],
        "docs": "https://www.tensorflow.org/guide",
        "estimated_weeks": 10
    },
    "pytorch": {
        "courses": [
            {"title": "PyTorch for Deep Learning & Machine Learning", "platform": "Udemy", "url": "https://www.udemy.com/course/pytorch-for-deep-learning/", "level": "Intermediate", "duration": "43 hours"},
        ],
        "practice": [
            {"title": "PyTorch Tutorials", "url": "https://pytorch.org/tutorials/beginner/basics/intro.html", "type": "Tutorial"},
        ],
        "docs": "https://pytorch.org/docs/stable/index.html",
        "estimated_weeks": 10
    },
    "kubernetes": {
        "courses": [
            {"title": "Kubernetes for the Absolute Beginners", "platform": "Udemy", "url": "https://www.udemy.com/course/learn-kubernetes/", "level": "Beginner", "duration": "6 hours"},
        ],
        "practice": [
            {"title": "Kubernetes Play Ground", "url": "https://labs.play-with-k8s.com/", "type": "Practice"},
        ],
        "docs": "https://kubernetes.io/docs/tutorials/",
        "estimated_weeks": 6
    },
    "git": {
        "courses": [
            {"title": "Git & GitHub Crash Course", "platform": "freeCodeCamp", "url": "https://www.youtube.com/watch?v=RGOj5yH7evk", "level": "Beginner", "duration": "1 hour"},
        ],
        "practice": [
            {"title": "Learn Git Branching", "url": "https://learngitbranching.js.org/", "type": "Interactive"},
        ],
        "docs": "https://git-scm.com/book/en/v2",
        "estimated_weeks": 1
    },
}

# Default fallback for unknown skills
DEFAULT_RESOURCE = {
    "courses": [
        {"title": "Search on Coursera", "platform": "Coursera", "url": "https://www.coursera.org/search?query={skill}", "level": "Varies", "duration": "Varies"},
        {"title": "Search on Udemy", "platform": "Udemy", "url": "https://www.udemy.com/courses/search/?q={skill}", "level": "Varies", "duration": "Varies"},
    ],
    "practice": [
        {"title": "Search on YouTube", "url": "https://www.youtube.com/results?search_query=learn+{skill}+tutorial", "type": "Video"},
    ],
    "docs": "https://www.google.com/search?q={skill}+documentation",
    "estimated_weeks": 6
}


class LearningPathGenerator:
    """
    Generates a personalized learning path for a candidate
    based on their missing skills and job requirements.
    """

    def __init__(self, config=None):
        self.config = config
        self.ollama_url = getattr(config, 'OLLAMA_URL', 'http://localhost:11434/api/generate')
        self.ollama_model = getattr(config, 'OLLAMA_MODEL', 'phi3')
        self.learning_paths_folder = getattr(config, 'LEARNING_PATHS_FOLDER', 'learning_paths')
        os.makedirs(self.learning_paths_folder, exist_ok=True)

    # ── LLM helper ──────────────────────────────────────────────────────────
    def _ask_llm(self, prompt, timeout=30):
        """Try Ollama; return None on failure."""
        try:
            resp = requests.post(
                self.ollama_url,
                json={"model": self.ollama_model, "prompt": prompt, "stream": False},
                timeout=timeout
            )
            if resp.status_code == 200:
                return resp.json().get('response', '').strip()
        except Exception:
            pass
        return None

    # ── Resource lookup ─────────────────────────────────────────────────────
    def _get_resources_for_skill(self, skill: str) -> dict:
        """Return resource dict for a skill (case-insensitive, partial match)."""
        skill_lower = skill.lower().strip()
        # Exact match
        if skill_lower in SKILL_RESOURCES:
            return SKILL_RESOURCES[skill_lower]
        # Partial match
        for key in SKILL_RESOURCES:
            if key in skill_lower or skill_lower in key:
                return SKILL_RESOURCES[key]
        # Fallback — fill {skill} placeholders
        fallback = json.loads(
            json.dumps(DEFAULT_RESOURCE).replace('{skill}', skill.replace(' ', '+'))
        )
        return fallback

    # ── Priority label ───────────────────────────────────────────────────────
    def _priority_label(self, priority: str) -> str:
        mapping = {'high': '🔴 High', 'medium': '🟡 Medium', 'low': '🟢 Low'}
        return mapping.get(priority.lower(), '🟡 Medium')

    # ── Core generator ───────────────────────────────────────────────────────
    def generate(self, candidate: dict, job: dict) -> dict:
        """
        Generate a full learning path for a candidate.

        Args:
            candidate: dict with keys like 'filename', 'missing_skills',
                       'extracted_skills', 'overall_score', 'decision'
            job:       dict with keys like 'title', 'description',
                       'required_skills'

        Returns:
            learning_path dict (also saved to disk)
        """
        missing_skills = candidate.get('missing_skills', [])
        extracted_skills = candidate.get('extracted_skills', [])
        job_title = job.get('title', 'the role')
        score = candidate.get('overall_score', 0)

        # ── Build per-skill modules ──────────────────────────────────────────
        modules = []
        total_weeks = 0

        for item in missing_skills:
            skill = item.get('skill', '') if isinstance(item, dict) else str(item)
            priority = item.get('priority', 'medium') if isinstance(item, dict) else 'medium'
            if not skill:
                continue

            resources = self._get_resources_for_skill(skill)
            weeks = resources.get('estimated_weeks', 6)
            total_weeks += weeks

            # Optional LLM tip
            tip = self._ask_llm(
                f"Give one concise, practical tip (max 2 sentences) for a software developer "
                f"learning '{skill}' to qualify for a '{job_title}' position."
            )

            modules.append({
                'skill': skill,
                'priority': priority,
                'priority_label': self._priority_label(priority),
                'estimated_weeks': weeks,
                'courses': resources.get('courses', []),
                'practice': resources.get('practice', []),
                'docs': resources.get('docs', ''),
                'tip': tip or f"Focus on hands-on projects with {skill} to build real experience.",
            })

        # Sort by priority: high → medium → low
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        modules.sort(key=lambda m: priority_order.get(m['priority'], 1))

        # ── Overall motivation message (LLM or fallback) ────────────────────
        motivation = self._ask_llm(
            f"Write a short, encouraging 2-sentence message for a candidate who scored "
            f"{score:.0f}% in a screening for '{job_title}'. "
            f"They need to improve: {', '.join([m['skill'] for m in modules[:3]])}. "
            f"Be positive and actionable."
        ) or (
            f"You scored {score:.0f}% — you're on the right track! "
            f"Focus on the skills below and you'll be a strong candidate next time."
        )

        # ── Timeline phases ─────────────────────────────────────────────────
        timeline = self._build_timeline(modules)

        # ── Assemble result ─────────────────────────────────────────────────
        learning_path = {
            'candidate_id': candidate.get('candidate_id', 'unknown'),
            'candidate_name': candidate.get('filename', 'Candidate').replace('.pdf', '').replace('.docx', ''),
            'job_title': job_title,
            'current_score': score,
            'current_skills': extracted_skills,
            'modules': modules,
            'timeline': timeline,
            'total_estimated_weeks': total_weeks,
            'motivation': motivation,
            'generated_at': datetime.now().isoformat(),
        }

        # ── Save to disk ─────────────────────────────────────────────────────
        candidate_id = candidate.get('candidate_id', 'unknown')
        path = os.path.join(self.learning_paths_folder, f"{candidate_id}_learning_path.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(learning_path, f, indent=2)

        return learning_path

    # ── Timeline builder ─────────────────────────────────────────────────────
    def _build_timeline(self, modules: list) -> list:
        """Split modules into 3 phases: Foundation → Intermediate → Advanced."""
        high   = [m for m in modules if m['priority'] == 'high']
        medium = [m for m in modules if m['priority'] == 'medium']
        low    = [m for m in modules if m['priority'] == 'low']

        phases = []
        if high:
            phases.append({
                'phase': 1,
                'label': 'Phase 1 — Foundation',
                'description': 'Master the most critical missing skills first.',
                'skills': [m['skill'] for m in high],
                'weeks': sum(m['estimated_weeks'] for m in high),
                'color': '#ef4444',
            })
        if medium:
            phases.append({
                'phase': 2,
                'label': 'Phase 2 — Intermediate',
                'description': 'Build on your foundation with supporting skills.',
                'skills': [m['skill'] for m in medium],
                'weeks': sum(m['estimated_weeks'] for m in medium),
                'color': '#f59e0b',
            })
        if low:
            phases.append({
                'phase': 3,
                'label': 'Phase 3 — Advanced',
                'description': 'Polish your profile with complementary skills.',
                'skills': [m['skill'] for m in low],
                'weeks': sum(m['estimated_weeks'] for m in low),
                'color': '#10b981',
            })
        return phases

    # ── Retrieve saved path ──────────────────────────────────────────────────
    def get_learning_path(self, candidate_id: str) -> dict | None:
        path = os.path.join(self.learning_paths_folder, f"{candidate_id}_learning_path.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None