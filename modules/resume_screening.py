import os
import uuid
import json
import numpy as np
from datetime import datetime
from werkzeug.utils import secure_filename
from sentence_transformers import SentenceTransformer, util

# Import your JD module
from jd_module import get_all_jds, STORE_FOLDER as JD_STORE

# Import submodules
from modules.semantic_parser import SemanticParser
from modules.semantic_matcher import SemanticMatcher
from modules.semantic_ranker import SemanticRanker
from modules.skill_extractor import SkillExtractor

class ResumeScreeningEngine:
    """Main orchestration class for semantic resume screening"""
    
    def __init__(self, config):
        self.config = config
        
        # Initialize semantic modules
        print("🧠 Loading semantic models...")
        self.parser = SemanticParser()
        self.matcher = SemanticMatcher()
        self.ranker = SemanticRanker()
        self.skill_extractor = SkillExtractor()
        
        # Load embedding model
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Try to load LLM for advanced analysis
        try:
            import requests
            self.llm_available = True
            self.ollama_url = "http://localhost:11434/api/generate"
            self.llm_model = "phi3"
            print("✅ LLM available for advanced analysis")
        except:
            self.llm_available = False
            print("⚠️ LLM not available, using basic analysis")
        
        print("✅ Semantic models loaded successfully")
        
        # Create directories
        os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(config.RESULTS_FOLDER, exist_ok=True)
        os.makedirs(config.ANALYTICS_FOLDER, exist_ok=True)
        os.makedirs(config.LEARNING_PATHS_FOLDER, exist_ok=True)
    
    def safe_cosine_similarity(self, emb1, emb2):
        """Safe cosine similarity with dtype handling"""
        try:
            import torch
            
            if not isinstance(emb1, torch.Tensor):
                emb1 = torch.tensor(emb1)
            if not isinstance(emb2, torch.Tensor):
                emb2 = torch.tensor(emb2)
            
            emb1 = emb1.float()
            emb2 = emb2.float()
            
            if len(emb1.shape) == 1:
                emb1 = emb1.unsqueeze(0)
            if len(emb2.shape) == 1:
                emb2 = emb2.unsqueeze(0)
            
            similarity = torch.nn.functional.cosine_similarity(emb1, emb2)
            return float(similarity.mean().item() * 100)
            
        except Exception as e:
            print(f"⚠️ Similarity error: {e}")
            return 50.0
    
    def get_recent_jds(self):
        """Get all JDs from JD store with job role as filename"""
        jds = []
        if os.path.exists(JD_STORE):
            for file in os.listdir(JD_STORE):
                if file.endswith('.txt'):
                    filepath = os.path.join(JD_STORE, file)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Extract job role from filename (remove jd_ prefix and timestamp)
                    display_name = file.replace('jd_', '').replace('.txt', '')
                    if '_' in display_name:
                        # Try to extract just the role name
                        parts = display_name.split('_')
                        if len(parts) > 1:
                            # Remove timestamp part (usually at end)
                            if parts[-1].isdigit() or len(parts[-1]) == 14:  # timestamp pattern
                                display_name = ' '.join(parts[:-1])
                            else:
                                display_name = ' '.join(parts)
                    
                    jds.append({
                        'filename': file,
                        'display_name': display_name,
                        'content': content,
                        'path': filepath
                    })
            
            # Sort by filename (newest first)
            jds.sort(key=lambda x: x['filename'], reverse=True)
        
        return jds
    
    def screen_resumes(self, jd_text, resume_files, job_title="Custom Job", max_resumes=10):
        """
        Screen multiple resumes against a job description using semantic understanding
        Now supports up to 10 resumes
        """
        # Limit to max_resumes (default 10)
        if len(resume_files) > max_resumes:
            print(f"⚠️ Limiting to {max_resumes} resumes (received {len(resume_files)})")
            resume_files = resume_files[:max_resumes]
        
        screening_id = str(uuid.uuid4())
        
        # Extract required skills using LLM if available
        required_skills = self._extract_skills_with_llm(jd_text) if self.llm_available else self._extract_skills_basic(jd_text)
        
        # Create job object with semantic understanding
        job = {
            'id': screening_id,
            'title': job_title,
            'description': jd_text,
            'embedding': self.embedder.encode(jd_text).tolist(),
            'semantic_keywords': self._extract_semantic_keywords(jd_text),
            'required_skills': required_skills,
            'created_at': datetime.now().isoformat()
        }
        
        # Process each resume
        results = []
        for file in resume_files:
            if file and file.filename:
                result = self._process_single_resume_semantic(file, job)
                if result:
                    results.append(result)
        
        # Rank candidates semantically
        ranked_results = self.ranker.rank_candidates_semantic(results, job)
        
        # Apply decision rules based on thresholds
        for candidate in ranked_results:
            candidate['decision'] = self._apply_decision_rules(candidate)
        
        # Perform advanced skill gap analysis with LLM
        skill_gap_analysis = self._analyze_skill_gaps_advanced(ranked_results, job) if self.llm_available else self._analyze_skill_gaps_basic(ranked_results, job)
        
        # Save results
        output = {
            'screening_id': screening_id,
            'job': job,
            'candidates': ranked_results,
            'total': len(ranked_results),
            'created_at': datetime.now().isoformat(),
            'skill_gap_analysis': skill_gap_analysis,
            'recommendations': self._generate_recommendations(ranked_results, job)
        }
        
        # Save to file
        result_path = os.path.join(self.config.RESULTS_FOLDER, f"{screening_id}.json")
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
        
        # Also save to analytics database
        self._save_to_analytics(output)
        
        return screening_id, output
    
    def _process_single_resume_semantic(self, file, job):
        """Process a single resume with full semantic understanding"""
        try:
            # Save file temporarily
            filename = secure_filename(file.filename)
            candidate_id = str(uuid.uuid4())
            file_path = os.path.join(self.config.UPLOAD_FOLDER, f"{candidate_id}_{filename}")
            file.save(file_path)
            
            # Parse resume with semantic understanding
            parsed_data = self.parser.parse_resume_semantic(file_path)
            
            # Generate resume embedding
            resume_embedding = self.embedder.encode(parsed_data['text'])
            job_embedding = np.array(job['embedding'])
            
            # Calculate semantic similarity
            semantic_similarity = self.safe_cosine_similarity(resume_embedding, job_embedding)
            
            # Extract skills semantically
            skills = self.skill_extractor.extract_semantic(parsed_data['text'])
            
            # Calculate skill relevance
            skill_relevance = self._calculate_semantic_skill_relevance(
                skills, 
                job['semantic_keywords']
            )
            
            # Extract experience
            experience = self.parser.extract_experience_semantic(parsed_data['text'])
            
            # Calculate experience relevance
            exp_relevance = self._calculate_experience_relevance(
                experience,
                job['description']
            )
            
            # Calculate education relevance
            education = self.parser.extract_education_semantic(parsed_data['text'])
            edu_relevance = self._calculate_education_relevance(
                education,
                job['description']
            )
            
            # Calculate weighted overall score
            overall_score = (
                semantic_similarity * 0.4 +      # Semantic Score
                skill_relevance * 0.3 +           # Verification Score
                exp_relevance * 0.2 +              # Experience Score
                edu_relevance * 0.1                 # Education Score
            )
            
            # Identify missing skills using LLM if available
            if self.llm_available:
                missing_skills = self._identify_missing_skills_llm(
                    [s['skill'] for s in skills],
                    job.get('required_skills', []),
                    parsed_data['text'][:1000],
                    job['description'][:1000]
                )
            else:
                missing_skills = self._identify_missing_skills_basic(
                    [s['skill'] for s in skills],
                    job.get('required_skills', [])
                )
            
            # Clean up
            os.remove(file_path)
            
            return {
                'candidate_id': candidate_id,
                'filename': filename,
                'semantic_score': round(semantic_similarity, 1),
                'verification_score': round(skill_relevance, 1),
                'skill_relevance': round(skill_relevance, 1),
                'experience_relevance': round(exp_relevance, 1),
                'education_relevance': round(edu_relevance, 1),
                'overall_score': round(overall_score, 1),
                'extracted_skills': [s['skill'] for s in skills[:10]],
                'missing_skills': missing_skills,
                'experience_years': experience['years'],
                'experience_quality': experience['quality'],
                'education': education[:3],
                'key_matches': self._find_semantic_matches(
                    parsed_data['key_points'],
                    job['description']
                )
            }
            
        except Exception as e:
            print(f"Error processing {file.filename}: {e}")
            return None
    
    def _extract_skills_with_llm(self, jd_text):
        """Extract required skills using LLM"""
        try:
            prompt = f"""
            Extract the key technical skills required for this job description.
            Return ONLY a comma-separated list of skills, nothing else.
            
            Job Description:
            {jd_text[:1000]}
            """
            
            import requests
            response = requests.post(
                self.ollama_url,
                json={"model": self.llm_model, "prompt": prompt, "stream": False},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                skills_text = result.get('response', '')
                # Parse comma-separated list
                skills = [s.strip() for s in skills_text.split(',') if s.strip()]
                return skills[:10]  # Limit to 10 skills
        except:
            pass
        
        # Fallback to basic extraction
        return self._extract_skills_basic(jd_text)
    
    def _extract_skills_basic(self, jd_text):
        """Basic skill extraction as fallback"""
        common_skills = [
            'python', 'java', 'javascript', 'react', 'angular', 'vue',
            'django', 'flask', 'spring', 'sql', 'mongodb', 'postgresql',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'tensorflow',
            'pytorch', 'machine learning', 'data science', 'nlp',
            'html', 'css', 'node.js', 'express', 'php', 'ruby', 'c++',
            'c#', 'go', 'rust', 'swift', 'kotlin', 'android', 'ios'
        ]
        
        found = []
        text_lower = jd_text.lower()
        for skill in common_skills:
            if skill in text_lower:
                found.append(skill)
        
        return found[:10]
    
    def _identify_missing_skills_llm(self, candidate_skills, required_skills, resume_text, jd_text):
        """Identify missing skills using LLM for deeper understanding"""
        try:
            prompt = f"""
            Analyze this candidate's resume against the job requirements.
            
            Job Requirements: {', '.join(required_skills[:5])}
            Candidate Skills Found: {', '.join(candidate_skills[:5])}
            
            Resume Excerpt: {resume_text[:500]}
            Job Description: {jd_text[:500]}
            
            Identify the TOP 3 most important skills the candidate is missing.
            Return ONLY a comma-separated list of skills, nothing else.
            If no skills are missing, return "None".
            """
            
            import requests
            response = requests.post(
                self.ollama_url,
                json={"model": self.llm_model, "prompt": prompt, "stream": False},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                skills_text = result.get('response', '')
                if skills_text.lower() == 'none':
                    return []
                
                # Parse comma-separated list
                missing = []
                for s in skills_text.split(','):
                    skill = s.strip()
                    if skill and skill.lower() != 'none':
                        missing.append({
                            'skill': skill,
                            'priority': 'high' if len(missing) < 2 else 'medium',
                            'context': 'Identified by LLM analysis'
                        })
                return missing[:3]
        except:
            pass
        
        # Fallback to basic identification
        return self._identify_missing_skills_basic(candidate_skills, required_skills)
    
    def _identify_missing_skills_basic(self, candidate_skills, required_skills):
        """Basic missing skills identification as fallback"""
        if not required_skills:
            return []
        
        candidate_lower = [s.lower() for s in candidate_skills]
        missing = []
        
        for i, skill in enumerate(required_skills):
            skill_lower = skill.lower()
            if not any(skill_lower in cs or cs in skill_lower for cs in candidate_lower):
                missing.append({
                    'skill': skill,
                    'priority': 'high' if i < 3 else 'medium',
                    'context': 'Keyword-based detection'
                })
        
        return missing[:5]
    
    def _analyze_skill_gaps_advanced(self, candidates, job):
        """Advanced skill gap analysis using LLM"""
        skill_gap_analysis = {
            'most_missing_skills': {},
            'average_scores': {},
            'trends': [],
            'recommendations': [],
            'detailed_analysis': ''
        }
        
        # Basic counts first
        all_missing = []
        for candidate in candidates:
            all_missing.extend([m['skill'] for m in candidate.get('missing_skills', [])])
        
        from collections import Counter
        missing_counts = Counter(all_missing)
        skill_gap_analysis['most_missing_skills'] = dict(missing_counts.most_common(5))
        
        # Calculate averages
        if candidates:
            skill_gap_analysis['average_scores'] = {
                'semantic': round(sum(c['semantic_score'] for c in candidates) / len(candidates), 1),
                'verification': round(sum(c['verification_score'] for c in candidates) / len(candidates), 1),
                'overall': round(sum(c['overall_score'] for c in candidates) / len(candidates), 1)
            }
        
        # Use LLM for deeper analysis if available
        if self.llm_available and candidates:
            try:
                # Prepare summary for LLM
                candidates_summary = []
                for c in candidates[:3]:  # Top 3 candidates
                    candidates_summary.append({
                        'score': c['overall_score'],
                        'skills': c['extracted_skills'][:3],
                        'missing': [m['skill'] for m in c.get('missing_skills', [])][:2]
                    })
                
                prompt = f"""
                Analyze the skill gaps for this recruitment drive.
                
                Job Title: {job['title']}
                Total Candidates: {len(candidates)}
                Average Score: {skill_gap_analysis['average_scores']['overall']}
                
                Top Missing Skills: {', '.join(list(skill_gap_analysis['most_missing_skills'].keys())[:3])}
                
                Candidate Summary: {json.dumps(candidates_summary)}
                
                Provide 3-4 bullet points about:
                1. Key skill gaps across candidates
                2. Recommendations for future hiring
                3. Training needs if hiring internally
                
                Keep each bullet point concise.
                """
                
                response = requests.post(
                    self.ollama_url,
                    json={"model": self.llm_model, "prompt": prompt, "stream": False},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    analysis = result.get('response', '')
                    skill_gap_analysis['detailed_analysis'] = analysis
                    
                    # Extract recommendations
                    lines = analysis.split('\n')
                    recommendations = [l.strip('-• ') for l in lines if l.strip() and (l.startswith('-') or l.startswith('•'))]
                    skill_gap_analysis['recommendations'] = recommendations[:3]
            except:
                pass
        
        return skill_gap_analysis
    
    def _analyze_skill_gaps_basic(self, candidates, job):
        """Basic skill gap analysis as fallback"""
        skill_gap_analysis = {
            'most_missing_skills': {},
            'average_scores': {},
            'recommendations': []
        }
        
        all_missing = []
        for candidate in candidates:
            all_missing.extend([m['skill'] for m in candidate.get('missing_skills', [])])
        
        from collections import Counter
        missing_counts = Counter(all_missing)
        skill_gap_analysis['most_missing_skills'] = dict(missing_counts.most_common(5))
        
        if candidates:
            skill_gap_analysis['average_scores'] = {
                'semantic': round(sum(c['semantic_score'] for c in candidates) / len(candidates), 1),
                'verification': round(sum(c['verification_score'] for c in candidates) / len(candidates), 1),
                'overall': round(sum(c['overall_score'] for c in candidates) / len(candidates), 1)
            }
            
            # Generate basic recommendations
            if skill_gap_analysis['most_missing_skills']:
                top_gap = list(skill_gap_analysis['most_missing_skills'].keys())[0]
                skill_gap_analysis['recommendations'].append(
                    f"Candidates commonly missing {top_gap} skills. Consider training programs."
                )
        
        return skill_gap_analysis
    
    def _extract_semantic_keywords(self, text):
        """Extract semantically important keywords from JD"""
        words = text.lower().split()
        word_freq = {}
        for word in words:
            if len(word) > 3:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [w[0] for w in sorted_words[:20]]
    
    def _calculate_semantic_skill_relevance(self, candidate_skills, jd_keywords):
        """Calculate skill relevance using semantic understanding"""
        if not jd_keywords or not candidate_skills:
            return 50
        
        skill_text = ' '.join([s['skill'] for s in candidate_skills])
        keyword_text = ' '.join(jd_keywords)
        
        if not skill_text or not keyword_text:
            return 50
        
        skill_emb = self.embedder.encode(skill_text)
        keyword_emb = self.embedder.encode(keyword_text)
        
        similarity = self.safe_cosine_similarity(skill_emb, keyword_emb)
        return similarity
    
    def _calculate_experience_relevance(self, experience, jd_text):
        """Calculate experience relevance"""
        exp_text = f"{experience['years']} years of experience. "
        exp_text += ' '.join(experience['descriptions'])
        
        if not exp_text:
            return 50
        
        exp_emb = self.embedder.encode(exp_text[:500])
        jd_emb = self.embedder.encode(jd_text[:500])
        
        similarity = self.safe_cosine_similarity(exp_emb, jd_emb)
        
        if experience['years'] > 5:
            similarity = min(similarity + 10, 100)
        
        return similarity
    
    def _calculate_education_relevance(self, education, jd_text):
        """Calculate education relevance"""
        if not education:
            return 50
        
        edu_text = ' '.join([e.get('degree', '') for e in education])
        if not edu_text:
            return 50
        
        edu_emb = self.embedder.encode(edu_text)
        jd_emb = self.embedder.encode(jd_text[:500])
        
        similarity = self.safe_cosine_similarity(edu_emb, jd_emb)
        return similarity
    
    def _find_semantic_matches(self, resume_points, jd_text):
        """Find semantic matches between resume and JD"""
        matches = []
        
        for point in resume_points[:5]:
            if not point:
                continue
            
            point_emb = self.embedder.encode(point)
            jd_emb = self.embedder.encode(jd_text[:1000])
            
            similarity = self.safe_cosine_similarity(point_emb, jd_emb)
            
            if similarity > 70:
                matches.append({
                    'point': point,
                    'similarity': round(similarity, 1)
                })
        
        return matches
    
    def _apply_decision_rules(self, candidate):
        """Apply decision rules based on thresholds"""
        SHORTLIST_THRESHOLD = 75
        INTERVIEW_THRESHOLD = 60
        
        score = candidate['overall_score']
        
        if score >= SHORTLIST_THRESHOLD:
            return {
                'action': 'shortlist',
                'message': 'Candidate meets all criteria for shortlisting',
                'next_step': 'interview_invite'
            }
        elif score >= INTERVIEW_THRESHOLD:
            return {
                'action': 'interview',
                'message': 'Candidate shows potential, schedule interview',
                'next_step': 'interview_scheduling'
            }
        else:
            return {
                'action': 'reject',
                'message': 'Candidate does not meet minimum requirements',
                'next_step': 'learning_path',
                'missing_skills': candidate.get('missing_skills', [])
            }
    
    def _generate_recommendations(self, candidates, job):
        """Generate recommendations based on screening results"""
        recommendations = {
            'hiring_recommendation': None,
            'top_candidates': [],
            'skill_development': []
        }
        
        # Get top 3 candidates
        top_candidates = sorted(candidates, key=lambda x: x['overall_score'], reverse=True)[:3]
        recommendations['top_candidates'] = [
            {
                'filename': c['filename'],
                'score': c['overall_score'],
                'decision': c['decision']['action']
            }
            for c in top_candidates
        ]
        
        # Generate hiring recommendation
        if candidates and candidates[0]['overall_score'] >= 75:
            recommendations['hiring_recommendation'] = 'Proceed with top candidate'
        elif candidates and candidates[0]['overall_score'] >= 60:
            recommendations['hiring_recommendation'] = 'Schedule interviews with top 2-3 candidates'
        else:
            recommendations['hiring_recommendation'] = 'No strong candidates, consider reposting job'
        
        return recommendations
    
    def _save_to_analytics(self, data):
        """Save screening data to analytics for future reference"""
        analytics_file = os.path.join(self.config.ANALYTICS_FOLDER, 'all_screenings.json')
        
        if os.path.exists(analytics_file):
            with open(analytics_file, 'r') as f:
                analytics = json.load(f)
        else:
            analytics = {'screenings': []}
        
        # Calculate average score
        avg_score = 0
        if data['candidates']:
            avg_score = sum(c['overall_score'] for c in data['candidates']) / len(data['candidates'])
        
        # Add this screening
        analytics['screenings'].append({
            'screening_id': data['screening_id'],
            'job_title': data['job']['title'],
            'date': data['created_at'],
            'total_candidates': data['total'],
            'average_score': round(avg_score, 1),
            'top_score': data['candidates'][0]['overall_score'] if data['candidates'] else 0,
            'skill_gaps': data['skill_gap_analysis']['most_missing_skills']
        })
        
        # Keep only last 50 screenings
        if len(analytics['screenings']) > 50:
            analytics['screenings'] = analytics['screenings'][-50:]
        
        with open(analytics_file, 'w') as f:
            json.dump(analytics, f, indent=2)
    
    def generate_learning_path(self, candidate_data, job):
        """Generate personalized learning path for rejected candidates"""
        learning_path = {
            'candidate': candidate_data['filename'],
            'missing_skills': candidate_data.get('missing_skills', []),
            'recommended_courses': [],
            'estimated_time': '',
            'reapply_date': ''
        }
        
        # Generate course recommendations for each missing skill
        for missing in candidate_data.get('missing_skills', []):
            skill = missing['skill']
            learning_path['recommended_courses'].append({
                'skill': skill,
                'course': f"Complete {skill} certification",
                'platform': 'Coursera/Udemy',
                'duration': '4-6 weeks'
            })
        
        # Calculate estimated time
        total_weeks = len(learning_path['recommended_courses']) * 4
        learning_path['estimated_time'] = f"{total_weeks} weeks"
        
        # Set reapply date
        from datetime import timedelta
        reapply = datetime.now() + timedelta(weeks=total_weeks)
        learning_path['reapply_date'] = reapply.strftime('%Y-%m-%d')
        
        # Save learning path
        path_id = str(uuid.uuid4())
        path_file = os.path.join(self.config.LEARNING_PATHS_FOLDER, f"{path_id}.json")
        with open(path_file, 'w') as f:
            json.dump(learning_path, f, indent=2)
        
        return learning_path
    
    def get_screening_result(self, screening_id):
        """Retrieve saved screening result"""
        result_path = os.path.join(self.config.RESULTS_FOLDER, f"{screening_id}.json")
        if os.path.exists(result_path):
            with open(result_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def get_all_screenings(self):
        """Get list of all screenings"""
        if not os.path.exists(self.config.RESULTS_FOLDER):
            return []
        
        screenings = []
        for file in os.listdir(self.config.RESULTS_FOLDER):
            if file.endswith('.json'):
                path = os.path.join(self.config.RESULTS_FOLDER, file)
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    screenings.append({
                        'id': data['screening_id'],
                        'job_title': data['job']['title'],
                        'total': data['total'],
                        'created_at': data['created_at'],
                        'top_score': data['candidates'][0]['overall_score'] if data['candidates'] else 0,
                        'skill_gaps': data.get('skill_gap_analysis', {}).get('most_missing_skills', {})
                    })
        
        screenings.sort(key=lambda x: x['created_at'], reverse=True)
        return screenings
    
    def get_analytics_summary(self):
        """Get analytics summary for dashboard"""
        analytics_file = os.path.join(self.config.ANALYTICS_FOLDER, 'all_screenings.json')
        if not os.path.exists(analytics_file):
            return {
                'total_screenings': 0,
                'total_candidates': 0,
                'average_score': 0,
                'common_skill_gaps': {}
            }
        
        with open(analytics_file, 'r') as f:
            analytics = json.load(f)
        
        total_candidates = sum(s['total_candidates'] for s in analytics['screenings'])
        avg_score = sum(s['average_score'] for s in analytics['screenings']) / len(analytics['screenings']) if analytics['screenings'] else 0
        
        all_gaps = {}
        for s in analytics['screenings']:
            for skill, count in s.get('skill_gaps', {}).items():
                all_gaps[skill] = all_gaps.get(skill, 0) + count
        
        return {
            'total_screenings': len(analytics['screenings']),
            'total_candidates': total_candidates,
            'average_score': round(avg_score, 1),
            'common_skill_gaps': dict(sorted(all_gaps.items(), key=lambda x: x[1], reverse=True)[:5])
        }