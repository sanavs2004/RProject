# RecruitAI - AI-Powered Recruitment Automation Platform

**RecruitAI** is an intelligent end-to-end recruitment automation platform designed to transform the talent acquisition lifecycle through AI-driven workflows. The system leverages transformer-based language models for semantic understanding and implements a unique **"test-before-shortlist"** approach to ensure only verified, high-quality candidates reach recruiters.

---

# Problem Statement

Traditional recruitment processes suffer from inefficiencies including manual resume screening, subjective candidate evaluation, and delayed decision-making. Existing Applicant Tracking Systems (ATS) rely on keyword-based matching that fails to capture semantic context, leading to false positives and missed qualified candidates.

This project aims to develop an **AI-powered recruitment platform** that automates the hiring lifecycle with objective skill validation, semantic matching, and meaningful feedback for all candidates.

---

# Key Features

- **Semantic Resume Parsing** - Transformer-based LLMs (BERT/RoBERTa) for contextual understanding beyond keyword matching
- **Test-Before-Shortlist** - Automated skill assessments immediately after resume submission
- **ML-Based Fit Prediction** - Combines semantic scores and verification scores to forecast candidate success (89% accuracy)
- **Decision Rule Engine** - Configurable thresholds for transparent, data-driven shortlisting
- **Learning Path Generator** - Personalized upskilling recommendations for rejected candidates
- **Bias Detection** - Automatic removal of sensitive attributes for fair evaluation
- **Interview Scheduling** - Automated calendar integration with self-scheduling for candidates
- **Analytics Dashboard** - Real-time hiring metrics and skill gap analysis
- **Explainable AI** - Transparent scoring mechanisms to reduce bias and build trust

---

# System Architecture

The system consists of three main layers:

### 1. Frontend Layer (HTML,CSS,JS)
- Recruiter dashboard for job posting and candidate review
- Candidate portal for resume upload and assessment completion
- Analytics dashboard with interactive visualizations

### 2. Backend Layer (Flask)
- RESTful API endpoints for all modules
- JWT-based authentication and role-based access control
- Celery for asynchronous task processing

### 3. AI Processing Layer
- Resume parsing and semantic matching using Hugging Face Transformers
- Skill verification engine with automated assessments
- ML-based fit prediction using XGBoost and SVM models
- Learning path generation with skill gap analysis

---

# Technologies Used

- **Backend**: Python, Flask, Flask-RESTful
- **AI/ML**: Hugging Face Transformers, TensorFlow/PyTorch, scikit-learn, spaCy, NLTK
- **Frontend**: HTML,CSS,JavaScript,Bootstrap


---
