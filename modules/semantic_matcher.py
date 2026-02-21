import numpy as np
from sentence_transformers import SentenceTransformer, util

class SemanticMatcher:
    """Match resumes and jobs using semantic understanding"""
    
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def calculate_semantic_similarity(self, resume_text, jd_text):
        """Calculate semantic similarity between resume and JD"""
        # Get embeddings
        resume_emb = self.model.encode(resume_text[:2000])
        jd_emb = self.model.encode(jd_text[:2000])
        
        # Calculate cosine similarity
        similarity = util.cos_sim(resume_emb, jd_emb).item() * 100
        return similarity
    
    def find_matching_sentences(self, resume_text, jd_text, threshold=70):
        """Find semantically matching sentences"""
        resume_sentences = [s.strip() for s in resume_text.split('.') if len(s) > 30]
        jd_sentences = [s.strip() for s in jd_text.split('.') if len(s) > 30]
        
        matches = []
        
        # Get embeddings for all sentences
        resume_embs = self.model.encode(resume_sentences[:20])
        jd_embs = self.model.encode(jd_sentences[:20])
        
        for i, jd_sent in enumerate(jd_sentences[:10]):
            for j, res_sent in enumerate(resume_sentences[:10]):
                similarity = util.cos_sim(jd_embs[i], resume_embs[j]).item() * 100
                if similarity > threshold:
                    matches.append({
                        'job_sentence': jd_sent,
                        'resume_sentence': res_sent,
                        'similarity': round(similarity, 1)
                    })
        
        return matches[:5]  # Return top 5 matches
    
    def calculate_skill_semantic_score(self, candidate_skills, job_skills):
        """Calculate skill match using semantic understanding"""
        if not job_skills or not candidate_skills:
            return 50
        
        # Create skill embeddings
        candidate_text = ' '.join([s.get('skill', '') for s in candidate_skills])
        job_text = ' '.join(job_skills)
        
        if not candidate_text or not job_text:
            return 50
        
        candidate_emb = self.model.encode(candidate_text)
        job_emb = self.model.encode(job_text)
        
        similarity = util.cos_sim(candidate_emb, job_emb).item() * 100
        return similarity