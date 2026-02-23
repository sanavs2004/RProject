import os
import uuid
import json
import numpy as np
from datetime import datetime
from werkzeug.utils import secure_filename
from sentence_transformers import SentenceTransformer, util

# Import your JD module
from jd_module import get_all_jds

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
        print("✅ Semantic models loaded successfully")
        
        # Create directories
        os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(config.RESULTS_FOLDER, exist_ok=True)
    
    def safe_cosine_similarity(self, emb1, emb2):
        """Safe cosine similarity with dtype handling"""
        try:
            import torch
            
            # Convert to tensors if needed
            if not isinstance(emb1, torch.Tensor):
                emb1 = torch.tensor(emb1)
            if not isinstance(emb2, torch.Tensor):
                emb2 = torch.tensor(emb2)
            
            # Ensure both are float32
            emb1 = emb1.float()
            emb2 = emb2.float()
            
            # Reshape if needed for cosine_similarity
            if len(emb1.shape) == 1:
                emb1 = emb1.unsqueeze(0)
            if len(emb2.shape) == 1:
                emb2 = emb2.unsqueeze(0)
            
            # Calculate similarity
            similarity = torch.nn.functional.cosine_similarity(emb1, emb2)
            return float(similarity.mean().item() * 100)
            
        except Exception as e:
            print(f"⚠️ Similarity error: {e}")
            return 50.0
    
    def screen_resumes(self, jd_text, resume_files, job_title="Custom Job"):
        """
        Screen multiple resumes against a job description using semantic understanding
        
        Args:
            jd_text: Job description text
            resume_files: List of uploaded file objects
            job_title: Title of the job
            
        Returns:
            screening_id: Unique ID for this screening session
        """
        screening_id = str(uuid.uuid4())
        
        # Create job object with semantic understanding
        job = {
            'id': screening_id,
            'title': job_title,
            'description': jd_text,
            'embedding': self.embedder.encode(jd_text).tolist(),
            'semantic_keywords': self._extract_semantic_keywords(jd_text),
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
        
        # Save results
        output = {
            'screening_id': screening_id,
            'job': job,
            'candidates': ranked_results,
            'total': len(ranked_results),
            'created_at': datetime.now().isoformat()
        }
        
        # Save to file
        result_path = os.path.join(self.config.RESULTS_FOLDER, f"{screening_id}.json")
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
        
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
            
            # Calculate semantic similarity - USING SAFE FUNCTION
            semantic_similarity = self.safe_cosine_similarity(resume_embedding, job_embedding)
            
            # Extract skills semantically
            skills = self.skill_extractor.extract_semantic(parsed_data['text'])
            
            # Calculate skill relevance - USING SAFE FUNCTION
            skill_relevance = self._calculate_semantic_skill_relevance(
                skills, 
                job['semantic_keywords']
            )
            
            # Extract experience with semantic understanding
            experience = self.parser.extract_experience_semantic(parsed_data['text'])
            
            # Calculate experience relevance - USING SAFE FUNCTION
            exp_relevance = self._calculate_experience_relevance(
                experience,
                job['description']
            )
            
            # Calculate education relevance - USING SAFE FUNCTION
            education = self.parser.extract_education_semantic(parsed_data['text'])
            edu_relevance = self._calculate_education_relevance(
                education,
                job['description']
            )
            
            # Calculate weighted overall score
            overall_score = (
                semantic_similarity * 0.5 +
                skill_relevance * 0.3 +
                exp_relevance * 0.15 +
                edu_relevance * 0.05
            )
            
            # Clean up
            os.remove(file_path)
            
            return {
                'candidate_id': candidate_id,
                'filename': filename,
                'semantic_score': round(semantic_similarity, 1),
                'skill_relevance': round(skill_relevance, 1),
                'experience_relevance': round(exp_relevance, 1),
                'education_relevance': round(edu_relevance, 1),
                'overall_score': round(overall_score, 1),
                'extracted_skills': skills[:10],
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
            return 50  # Neutral score
        
        skill_text = ' '.join([s['skill'] for s in candidate_skills])
        keyword_text = ' '.join(jd_keywords)
        
        if not skill_text or not keyword_text:
            return 50
        
        skill_emb = self.embedder.encode(skill_text)
        keyword_emb = self.embedder.encode(keyword_text)
        
        # USING SAFE FUNCTION
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
        
        # USING SAFE FUNCTION
        similarity = self.safe_cosine_similarity(exp_emb, jd_emb)
        
        # Bonus for high experience
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
        
        # USING SAFE FUNCTION
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
            
            # USING SAFE FUNCTION
            similarity = self.safe_cosine_similarity(point_emb, jd_emb)
            
            if similarity > 70:
                matches.append({
                    'point': point,
                    'similarity': round(similarity, 1)
                })
        
        return matches
    
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
                        'created_at': data['created_at']
                    })
        
        screenings.sort(key=lambda x: x['created_at'], reverse=True)
        return screenings