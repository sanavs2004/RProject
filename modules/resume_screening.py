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
        
        # Initialize GitHub modules
        try:
            from modules.github_verification import GitHubVerifier
            from modules.adaptive_scoring import AdaptiveScorer
            from modules.skill_cross_verifier import SkillCrossVerifier
            from modules.role_config_manager import RoleConfigManager
            
            self.github_verifier = GitHubVerifier(config)
            self.adaptive_scorer = AdaptiveScorer(config)
            self.skill_verifier = SkillCrossVerifier()
            self.role_config = RoleConfigManager(
                os.path.join(config.BASE_DIR, 'config', 'role_weights.json')
            )
            self.github_enabled = True
            print("✅ GitHub verification modules loaded")
        except Exception as e:
            print(f"⚠️ GitHub modules not loaded: {e}")
            self.github_enabled = False
        
        # Load embedding model
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # LLM availability (for advanced analysis)
        try:
            import requests
            self.llm_available = True  # Add this line
            self.ollama_url = "http://localhost:11434/api/generate"
            self.llm_model = "phi3"
            print("✅ LLM available for advanced analysis")
        except:
            self.llm_available = False  # Add this line
            print("⚠️ LLM not available, using basic analysis")
        
        print("✅ Semantic models loaded successfully")
        
        # Create directories
        os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(config.RESULTS_FOLDER, exist_ok=True)
        os.makedirs(config.ANALYTICS_FOLDER, exist_ok=True)
        os.makedirs(config.LEARNING_PATHS_FOLDER, exist_ok=True)


    def _extract_skills_with_llm(self, jd_text):
        """Extract required skills using LLM (fallback if not available)"""
        if not self.llm_available:
            return self._extract_skills_basic(jd_text)
        
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
                skills = [s.strip() for s in skills_text.split(',') if s.strip()]
                return skills[:10]
        except:
            pass
        
        return self._extract_skills_basic(jd_text)

# def _extract_skills_basic(self, jd_text):
#     """Basic skill extraction as fallback"""
#     common_skills = [
#         'python', 'java', 'javascript', 'react', 'angular', 'vue',
#         'django', 'flask', 'spring', 'sql', 'mongodb', 'postgresql',
#         'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'tensorflow',
#         'pytorch', 'machine learning', 'data science', 'nlp',
#         'html', 'css', 'node.js', 'express', 'php', 'ruby', 'c++',
#         'c#', 'go', 'rust', 'swift', 'kotlin', 'android', 'ios'
#     ]
    
#     found = []
#     text_lower = jd_text.lower()
#     for skill in common_skills:
#         if skill in text_lower:
#             found.append(skill)
    
#     return found[:10]
    
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
        Screen multiple resumes against a job description
        """
        # Limit to max_resumes
        if len(resume_files) > max_resumes:
            print(f"⚠️ Limiting to {max_resumes} resumes (received {len(resume_files)})")
            resume_files = resume_files[:max_resumes]
        
        screening_id = str(uuid.uuid4())
        
        # Extract required skills (check if llm_available exists)
        if hasattr(self, 'llm_available') and self.llm_available:
            required_skills = self._extract_skills_with_llm(jd_text)
        else:
            required_skills = self._extract_skills_basic(jd_text)
        
        # Create job object
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
        
        # Rank candidates
        ranked_results = self.ranker.rank_candidates_semantic(results, job)
        
        # Apply decision rules
        for candidate in ranked_results:
            candidate['decision'] = self._apply_decision_rules(candidate)
        
        # Skill gap analysis
        if hasattr(self, 'llm_available') and self.llm_available:
            skill_gap_analysis = self._analyze_skill_gaps_advanced(ranked_results, job)
        else:
            skill_gap_analysis = self._analyze_skill_gaps_basic(ranked_results, job)
        
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
        
        # Save to analytics
        self._save_to_analytics(output)
        
        return screening_id, output
    
    # def screen_resumes(self, jd_text, resume_files, job_title="Custom Job", max_resumes=10):
    #     """
    #     Screen multiple resumes against a job description using semantic understanding
    #     Now supports up to 10 resumes
    #     """
    #     # Limit to max_resumes (default 10)
    #     if len(resume_files) > max_resumes:
    #         print(f"⚠️ Limiting to {max_resumes} resumes (received {len(resume_files)})")
    #         resume_files = resume_files[:max_resumes]
        
    #     screening_id = str(uuid.uuid4())
        
    #     # Extract required skills using LLM if available
    #     required_skills = self._extract_skills_with_llm(jd_text) if self.llm_available else self._extract_skills_basic(jd_text)
        
    #     # Create job object with semantic understanding
    #     job = {
    #         'id': screening_id,
    #         'title': job_title,
    #         'description': jd_text,
    #         'embedding': self.embedder.encode(jd_text).tolist(),
    #         'semantic_keywords': self._extract_semantic_keywords(jd_text),
    #         'required_skills': required_skills,
    #         'created_at': datetime.now().isoformat()
    #     }
        
    #     # Process each resume
    #     results = []
    #     for file in resume_files:
    #         if file and file.filename:
    #             result = self._process_single_resume_semantic(file, job)
    #             if result:
    #                 results.append(result)
        
    #     # Rank candidates semantically
    #     ranked_results = self.ranker.rank_candidates_semantic(results, job)
        
    #     # Apply decision rules based on thresholds
    #     for candidate in ranked_results:
    #         candidate['decision'] = self._apply_decision_rules(candidate)
        
    #     # Perform advanced skill gap analysis with LLM
    #     skill_gap_analysis = self._analyze_skill_gaps_advanced(ranked_results, job) if self.llm_available else self._analyze_skill_gaps_basic(ranked_results, job)
        
    #     # Save results
    #     output = {
    #         'screening_id': screening_id,
    #         'job': job,
    #         'candidates': ranked_results,
    #         'total': len(ranked_results),
    #         'created_at': datetime.now().isoformat(),
    #         'skill_gap_analysis': skill_gap_analysis,
    #         'recommendations': self._generate_recommendations(ranked_results, job)
    #     }
        
    #     # Save to file
    #     result_path = os.path.join(self.config.RESULTS_FOLDER, f"{screening_id}.json")
    #     with open(result_path, 'w', encoding='utf-8') as f:
    #         json.dump(output, f, indent=2)
        
    #     # Also save to analytics database
    #     self._save_to_analytics(output)
        
    #     return screening_id, output
    
    
        

    def _process_single_resume_semantic(self, file, job):
        """Process a single resume with full semantic understanding and GitHub verification"""
        try:
            # Save file temporarily
            filename = secure_filename(file.filename)
            candidate_id = str(uuid.uuid4())
            file_path = os.path.join(self.config.UPLOAD_FOLDER, f"{candidate_id}_{filename}")
            file.save(file_path)
            
            # Parse resume with semantic understanding
            parsed_data = self.parser.parse_resume_semantic(file_path)
            
            # Extract GitHub username (AUTOMATIC!)
            github_username = parsed_data.get('github_username')
            
            # Initialize GitHub verification result
            github_result = None
            if github_username and hasattr(self, 'github_verifier'):
                print(f"🔍 Verifying GitHub: {github_username}")
                github_result = self.github_verifier.verify_github(
                    github_username,
                    [s['skill'] for s in self.skill_extractor.extract_semantic(parsed_data['text'])]
                )
            
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
            
            # Calculate base overall score with adjusted weights
            base_score = (
                semantic_similarity * 0.25 +      # Semantic match (25%)
                skill_relevance * 0.40 +           # Skills match (40%)
                exp_relevance * 0.25 +              # Experience match (25%)
                edu_relevance * 0.10                 # Education match (10%)
            )
            
            # ===== SCORE BOOSTING FORMULA =====
            # Transform scores: 37.7% → 67.7% (adds ~30 points)
            # Formula: boosted_score = 40 + (original_score * 0.75)
            boosted_score = 40 + (base_score * 0.75)
            
            # Cap at 100
            boosted_score = min(boosted_score, 100)
            
            # Ensure minimum score of 50 (threshold)
            min_threshold = 50
            if boosted_score < min_threshold:
                boosted_score = min_threshold
                
            # Identify missing skills using LLM if available
            if hasattr(self, 'llm_available') and self.llm_available:
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
            
            # Calculate confidence bonus from GitHub verification
            confidence_bonus = 0
            signals_used = ['resume']
            
            if github_result and github_result.get('github_score'):
                signals_used.append('github')
                
                # Add GitHub bonus (15% of GitHub score)
                github_bonus = github_result.get('github_score', 0) * 0.15
                confidence_bonus += github_bonus
                
                # Cross-verify skills for additional bonus
                if hasattr(self, 'skill_verifier'):
                    skill_verification = self.skill_verifier.verify_skills(
                        [s['skill'] for s in skills],
                        github_result
                    )
                    confidence_bonus += skill_verification.get('confidence_bonus', 0)
            
            # Calculate final score with adaptive weights
            if hasattr(self, 'adaptive_scorer') and signals_used != ['resume']:
                final_score_result = self.adaptive_scorer.calculate_final_score(
                    scores={
                        'resume': boosted_score,
                        'github': github_result.get('github_score', 0) if github_result else 0
                    },
                    signals_present=signals_used,
                    role=job['title'].lower().replace(' ', '_')
                )
                final_score = final_score_result['final_score'] + confidence_bonus
            else:
                final_score = boosted_score + confidence_bonus
            
            # Final cap at 100
            final_score = min(final_score, 100)
            
            # Clean up
            os.remove(file_path)
            
            # Return ALL required fields
            return {
                'candidate_id': candidate_id,
                'filename': filename,
                'semantic_score': round(semantic_similarity, 1),
                'verification_score': round(skill_relevance, 1),
                'skill_relevance': round(skill_relevance, 1),
                'experience_relevance': round(exp_relevance, 1),
                'education_relevance': round(edu_relevance, 1),
                'overall_score': round(boosted_score, 1),  # Boosted score for display
                'base_score': round(base_score, 1),        # Original raw score
                'boosted_score': round(boosted_score, 1),   # After boosting
                'final_score': round(final_score, 1),       # After GitHub bonus
                'confidence_bonus': round(confidence_bonus, 1),
                'signals_used': signals_used,
                'extracted_skills': [s['skill'] for s in skills[:10]],
                'missing_skills': missing_skills,
                'experience_years': experience['years'],
                'experience_quality': experience['quality'],
                'education': education[:3],
                'key_matches': self._find_semantic_matches(
                    parsed_data['key_points'],
                    job['description']
                ),
                'github_username': github_username,
                'github_verification': github_result,
                'has_github': github_username is not None
            }
            
        except Exception as e:
            print(f"Error processing {file.filename}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
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
            return 60  # Increased from 50
        
        skill_text = ' '.join([s['skill'] for s in candidate_skills])
        keyword_text = ' '.join(jd_keywords)
        
        if not skill_text or not keyword_text:
            return 60  # Increased from 50
        
        skill_emb = self.embedder.encode(skill_text)
        keyword_emb = self.embedder.encode(keyword_text)
        
        similarity = self.safe_cosine_similarity(skill_emb, keyword_emb)
        
        # Boost the score (add 15 points)
        boosted_similarity = min(similarity + 15, 100)
        return boosted_similarity
    
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
        SHORTLIST_THRESHOLD = 75   # Keep this for top candidates
        INTERVIEW_THRESHOLD = 50    # Changed from 60 to 50
        
        score = candidate['overall_score']
        
        if score >= SHORTLIST_THRESHOLD:
            return {
                'action': 'shortlist',
                'message': 'Candidate meets criteria for shortlisting',
                'next_step': 'interview_invite'
            }
        elif score >= INTERVIEW_THRESHOLD:
            return {
                'action': 'interview',     # This will now show for scores 50-74
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
        # Parse resume with semantic understanding   ← ❌ THIS IS OUTSIDE ANY METHOD!
        parsed_data = self.parser.parse_resume_semantic(file_path)

        # Debug: print what was found
        print(f"📄 Parsed resume: {filename}")
        print(f"   GitHub username found: {parsed_data.get('github_username')}")
        print(f"   Has GitHub: {parsed_data.get('has_github')}")
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
    

