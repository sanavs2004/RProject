# import torch
# import numpy as np
# from transformers import AutoTokenizer, AutoModel, pipeline
# from sklearn.metrics.pairwise import cosine_similarity
# import os
# import json

# class ResumeMatcher:
#     """BERT-based semantic matching between resume and job description"""
    
#     def __init__(self, config):
#         self.config = config
#         self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
#         # Use a standard pre-trained model instead of a custom fine-tuned one
#         self.model_name = 'bert-base-uncased'
        
#         print(f"🔄 Loading pre-trained BERT model: {self.model_name}")
#         self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
#         self.model = AutoModel.from_pretrained(self.model_name)
        
#         self.model.to(self.device)
#         self.model.eval()
#         # self.config = config
#         # self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
#         # # Load BERT model
#         # self.model_name = 'bert-base-uncased'
#         # self.model_path = os.path.join(config.BASE_DIR, 'models', 'fine_tuned_model')

#         # # Use pre-trained model since fine-tuned one doesn't exist yet
#         # self.model_name = 'bert-base-uncased'
        
#         # print(f"Loading pre-trained BERT model: {self.model_name}")
#         # self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
#         # self.model = AutoModel.from_pretrained(self.model_name)
        
#         # self.model.to(self.device)
#         # self.model.eval()
        
#         # Check if fine-tuned model exists
#         if os.path.exists(self.model_path):
#             print(f"Loading fine-tuned BERT model from {self.model_path}")
#             self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
#             self.model = AutoModel.from_pretrained(self.model_path)
#         else:
#             print(f"Loading pre-trained BERT model: {self.model_name}")
#             self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
#             self.model = AutoModel.from_pretrained(self.model_name)
        
#         self.model.to(self.device)
#         self.model.eval()
        
#         # Load zero-shot classifier for skill matching
#         self.classifier = pipeline(
#             "zero-shot-classification",
#             model="facebook/bart-large-mnli",
#             device=0 if torch.cuda.is_available() else -1
#         )
        
#         # Skill categories for zero-shot
#         self.skill_categories = [
#             "programming language", "framework", "database", 
#             "cloud platform", "devops tool", "soft skill", 
#             "project management", "data science", "machine learning"
#         ]
    
#     def compute_semantic_similarity(self, resume_text, job_description):
#         """
#         Compute semantic similarity between resume and job description using BERT
#         This is NOT keyword matching - it understands context and meaning
#         """
#         # Truncate if too long
#         resume_text = resume_text[:10000]
#         job_description = job_description[:10000]
        
#         # Get embeddings
#         resume_embedding = self._get_embedding(resume_text)
#         job_embedding = self._get_embedding(job_description)
        
#         # Calculate cosine similarity
#         similarity = cosine_similarity(
#             resume_embedding.reshape(1, -1),
#             job_embedding.reshape(1, -1)
#         )[0][0]
        
#         # Convert to percentage
#         similarity_score = float(similarity * 100)
        
#         # Get detailed semantic match
#         detailed_match = self._get_semantic_match_details(resume_text, job_description)
        
#         return {
#             'overall_similarity': similarity_score,
#             'detailed_matches': detailed_match,
#             'embedding_similarity': similarity_score,
#             'explanation': self._generate_match_explanation(similarity_score, detailed_match)
#         }
    
#     def _get_embedding(self, text):
#         """Get BERT embedding for text"""
#         # Tokenize
#         inputs = self.tokenizer(
#             text,
#             truncation=True,
#             padding='max_length',
#             max_length=512,
#             return_tensors='pt'
#         )
        
#         # Move to device
#         inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
#         # Get embeddings
#         with torch.no_grad():
#             outputs = self.model(**inputs)
#             # Use [CLS] token embedding
#             embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()
        
#         return embedding[0]
    
#     def _get_semantic_match_details(self, resume_text, job_description):
#         """
#         Get detailed semantic matches between resume and job description
#         Uses BERT to understand meaning, not just words
#         """
#         # Split into sentences
#         resume_sentences = [s.strip() for s in resume_text.split('.') if len(s.strip()) > 20]
#         job_sentences = [s.strip() for s in job_description.split('.') if len(s.strip()) > 20]
        
#         matches = []
        
#         # For each job requirement, find semantically similar resume sentences
#         for job_sent in job_sentences[:10]:  # Limit for performance
#             if len(job_sent) < 20:
#                 continue
            
#             job_embedding = self._get_embedding(job_sent)
#             best_match = None
#             best_score = 0
            
#             for resume_sent in resume_sentences:
#                 resume_embedding = self._get_embedding(resume_sent)
                
#                 similarity = cosine_similarity(
#                     resume_embedding.reshape(1, -1),
#                     job_embedding.reshape(1, -1)
#                 )[0][0]
                
#                 if similarity > best_score and similarity > 0.6:  # Threshold
#                     best_score = similarity
#                     best_match = resume_sent
            
#             if best_match:
#                 matches.append({
#                     'job_requirement': job_sent,
#                     'resume_match': best_match,
#                     'similarity': float(best_score * 100),
#                     'match_type': self._classify_match_type(job_sent, best_match)
#                 })
        
#         return matches
    
#     def _classify_match_type(self, job_text, resume_text):
#         """Classify the type of match"""
#         categories = ['skill', 'experience', 'education', 'responsibility', 'achievement']
        
#         result = self.classifier(
#             resume_text,
#             candidate_labels=categories,
#             multi_label=False
#         )
        
#         return result['labels'][0]
    
#     def _generate_match_explanation(self, similarity_score, detailed_matches):
#         """Generate human-readable explanation of the match"""
#         if similarity_score >= 80:
#             level = "Excellent"
#         elif similarity_score >= 70:
#             level = "Good"
#         elif similarity_score >= 60:
#             level = "Moderate"
#         else:
#             level = "Low"
        
#         explanation = f"{level} match ({similarity_score:.1f}%). "
        
#         if detailed_matches:
#             explanation += f"Found {len(detailed_matches)} strong semantic matches. "
#             top_matches = detailed_matches[:3]
#             if top_matches:
#                 explanation += "Top matches: " + ", ".join([m['match_type'] for m in top_matches])
        
#         return explanation
    
#     def compute_skill_relevance(self, candidate_skills, required_skills):
#         """
#         Compute skill relevance using semantic understanding
#         Understands that "ML" means "Machine Learning", "Py" means "Python", etc.
#         """
#         if not required_skills:
#             return 0
        
#         # Convert skills to strings
#         if isinstance(candidate_skills, list):
#             if candidate_skills and isinstance(candidate_skills[0], dict):
#                 candidate_skill_text = ', '.join([s['skill'] for s in candidate_skills])
#             else:
#                 candidate_skill_text = ', '.join(candidate_skills)
#         else:
#             candidate_skill_text = str(candidate_skills)
        
#         # For each required skill, check semantic relevance
#         relevance_scores = []
#         relevance_details = []
        
#         for required_skill in required_skills:
#             # Use zero-shot to check if candidate has this skill
#             result = self.classifier(
#                 candidate_skill_text,
#                 candidate_labels=[required_skill],
#                 multi_label=True,
#                 hypothesis_template="This person has experience with {}."
#             )
            
#             relevance = result['scores'][0]
#             relevance_scores.append(relevance)
            
#             if relevance > 0.5:
#                 relevance_details.append({
#                     'skill': required_skill,
#                     'relevance': float(relevance * 100),
#                     'confidence': 'high' if relevance > 0.8 else 'medium'
#                 })
        
#         # Calculate overall relevance
#         if relevance_scores:
#             overall_relevance = np.mean(relevance_scores) * 100
#         else:
#             overall_relevance = 0
        
#         return {
#             'overall_relevance': float(overall_relevance),
#             'matched_skills': relevance_details,
#             'missing_skills': [
#                 skill for i, skill in enumerate(required_skills) 
#                 if relevance_scores[i] < 0.5
#             ] if relevance_scores else required_skills
#         }
    
#     def compute_contextual_match(self, resume_text, job_description, required_skills):
#         """
#         Compute contextual match with emphasis on skills
#         Combines semantic similarity with skill relevance
#         """
#         # Get semantic similarity
#         semantic = self.compute_semantic_similarity(resume_text, job_description)
        
#         # Get skill relevance
#         # Extract skills from resume (simplified)
#         skill_text = self._extract_skill_text(resume_text)
#         skill_relevance = self.compute_skill_relevance(skill_text, required_skills)
        
#         # Weighted combination
#         semantic_weight = 0.6
#         skill_weight = 0.4
        
#         combined_score = (
#             semantic_weight * semantic['overall_similarity'] +
#             skill_weight * skill_relevance['overall_relevance']
#         )
        
#         return {
#             'combined_score': combined_score,
#             'semantic_component': semantic,
#             'skill_component': skill_relevance,
#             'weights': {
#                 'semantic': semantic_weight,
#                 'skill': skill_weight
#             }
#         }
    
#     def _extract_skill_text(self, text):
#         """Extract skill-related text for analysis"""
#         # Look for skill sections
#         skill_section = ""
        
#         # Find skills section
#         lines = text.split('\n')
#         in_skills = False
        
#         for line in lines:
#             if 'skill' in line.lower():
#                 in_skills = True
#                 continue
#             if in_skills and line.strip() and not any(x in line.lower() for x in ['experience', 'education', 'project']):
#                 skill_section += line + " "
#             elif in_skills and any(x in line.lower() for x in ['experience', 'education']):
#                 break
        
#         return skill_section if skill_section else text[:1000]  # Fallback to first 1000 chars
    
#     def batch_compute_similarities(self, resumes, job_description):
#         """
#         Compute similarities for multiple resumes in batch
#         """
#         # Get job embedding once
#         job_embedding = self._get_embedding(job_description)
        
#         similarities = []
#         for resume in resumes:
#             resume_embedding = self._get_embedding(resume)
#             similarity = cosine_similarity(
#                 resume_embedding.reshape(1, -1),
#                 job_embedding.reshape(1, -1)
#             )[0][0]
#             similarities.append(float(similarity * 100))
        
#         return similarities
    
#     def get_explainable_scores(self, resume_text, job_description, required_skills):
#         """
#         Get detailed explainable scores for transparency
#         """
#         # Get embeddings
#         resume_emb = self._get_embedding(resume_text)
#         job_emb = self._get_embedding(job_description)
        
#         # Base similarity
#         base_similarity = cosine_similarity(
#             resume_emb.reshape(1, -1),
#             job_emb.reshape(1, -1)
#         )[0][0] * 100
        
#         # Get semantic matches
#         semantic_matches = self._get_semantic_match_details(resume_text, job_description)
        
#         # Get skill relevance
#         skill_relevance = self.compute_skill_relevance(resume_text, required_skills)
        
#         # Generate explanations
#         explanations = {
#             'overall_score': base_similarity,
#             'score_components': {
#                 'semantic_similarity': {
#                     'score': base_similarity,
#                     'weight': 0.6,
#                     'description': 'How well the overall resume content matches the job description semantically'
#                 },
#                 'skill_relevance': {
#                     'score': skill_relevance['overall_relevance'],
#                     'weight': 0.4,
#                     'description': 'Relevance of candidate skills to job requirements'
#                 }
#             },
#             'key_matches': semantic_matches[:5],  # Top 5 matches
#             'skill_analysis': {
#                 'matched': skill_relevance.get('matched_skills', []),
#                 'missing': skill_relevance.get('missing_skills', [])
#             },
#             'interpretation': self._interpret_score(base_similarity)
#         }
        
#         return explanations
    
#     def _interpret_score(self, score):
#         """Provide human-readable interpretation of score"""
#         if score >= 85:
#             return "Excellent match - candidate is highly suitable"
#         elif score >= 75:
#             return "Strong match - candidate meets most requirements"
#         elif score >= 65:
#             return "Good match - candidate meets key requirements"
#         elif score >= 55:
#             return "Moderate match - candidate meets some requirements"
#         elif score >= 45:
#             return "Fair match - candidate meets basic requirements"
#         else:
#             return "Low match - candidate may not be suitable"


import torch
import numpy as np
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline
import os

class ResumeMatcher:
    """Semantic matching using Sentence-BERT (optimized for similarity)"""
    
    def __init__(self, config):
        self.config = config
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Use Sentence-BERT model (optimized for similarity tasks)
        self.model_name = 'sentence-transformers/all-MiniLM-L6-v2'
        
        print(f"🔄 Loading Sentence-BERT model: {self.model_name}")
        print(f"📊 Model is optimized for semantic similarity matching")
        
        # Load the model
        self.model = SentenceTransformer(self.model_name)
        self.model.to(self.device)
        
        # Keep zero-shot classifier for skill matching (optional)
        self.classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=0 if torch.cuda.is_available() else -1
        )
        
        print("✅ ResumeMatcher initialized successfully")
    
    def compute_semantic_similarity(self, resume_text, job_description):
        """
        Compute semantic similarity using Sentence-BERT embeddings
        This is MUCH better for similarity tasks than regular BERT
        """
        # Truncate if too long
        resume_text = resume_text[:10000]
        job_description = job_description[:10000]
        
        # Encode texts to embeddings
        resume_embedding = self.model.encode(resume_text, convert_to_tensor=True)
        job_embedding = self.model.encode(job_description, convert_to_tensor=True)
        
        # Calculate cosine similarity
        similarity = util.pytorch_cos_sim(resume_embedding, job_embedding).item()
        
        # Convert to percentage
        similarity_score = float(similarity * 100)
        
        return {
            'overall_similarity': similarity_score,
            'embedding_similarity': similarity_score,
            'explanation': f'Resume matches job description with {similarity_score:.1f}% semantic similarity'
        }
    
    def compute_skill_relevance(self, candidate_skills, required_skills):
        """
        Compute skill relevance using semantic understanding
        """
        if not required_skills:
            return {
                'overall_relevance': 0,
                'matched_skills': [],
                'missing_skills': []
            }
        
        # Convert skills to text
        if isinstance(candidate_skills, list):
            if candidate_skills and isinstance(candidate_skills[0], dict):
                candidate_text = ' '.join([s.get('skill', '') for s in candidate_skills])
            else:
                candidate_text = ' '.join([str(s) for s in candidate_skills])
        else:
            candidate_text = str(candidate_skills)
        
        matched = []
        missing = []
        
        # For each required skill, check if it's semantically present
        for skill in required_skills:
            # Encode skill and candidate text
            skill_emb = self.model.encode(skill, convert_to_tensor=True)
            
            # For long candidate text, we need a different approach
            # Let's check if skill appears in the text semantically
            words = candidate_text.lower().split()
            found = False
            
            for word in words[:100]:  # Check first 100 words
                word_emb = self.model.encode(word, convert_to_tensor=True)
                similarity = util.pytorch_cos_sim(word_emb, skill_emb).item()
                if similarity > 0.7:  # Threshold for semantic match
                    found = True
                    break
            
            if found:
                matched.append({
                    'skill': skill,
                    'relevance': 85.0,
                    'confidence': 'high'
                })
            else:
                missing.append(skill)
        
        # Calculate overall relevance
        overall = (len(matched) / len(required_skills)) * 100 if required_skills else 0
        
        return {
            'overall_relevance': overall,
            'matched_skills': matched,
            'missing_skills': missing
        }
    
    def batch_compute_similarities(self, resumes, job_description):
        """
        Compute similarities for multiple resumes efficiently
        """
        # Encode all resumes at once
        resume_embeddings = self.model.encode(resumes, convert_to_tensor=True)
        job_embedding = self.model.encode(job_description, convert_to_tensor=True)
        
        # Compute all similarities
        similarities = util.pytorch_cos_sim(resume_embeddings, job_embedding)
        
        return [float(sim * 100) for sim in similarities]