import re
import numpy as np
from transformers import pipeline

class ResumeAnalyzer:
    """Deep analysis of resume content using semantic understanding"""
    
    def __init__(self, config):
        self.config = config
        
        # Load zero-shot classifier for analysis
        self.classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=-1  # CPU
        )
        
        # Load sentiment analyzer for tone detection
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english"
        )

    def analyze_resume_semantic(self, text):
        """
        Complete semantic analysis of resume
        This method combines all other analysis methods
        """
        print("🔍 Performing semantic analysis on resume...")
        
        try:
            # Extract skills
            skills_data = self.extract_skills_semantic(text)
            
            # Analyze experience
            experience_data = self.analyze_experience(text)
            
            # Analyze education
            education_data = self.analyze_education_semantic(text)
            
            # Analyze projects
            projects_data = self.analyze_projects(text)
            
            # Generate summary
            analysis_results = {
                'skills': skills_data,
                'experience': experience_data,
                'education': education_data,
                'projects': projects_data
            }
            summary = self.generate_resume_summary(analysis_results)
            
            return {
                'full_text': text,
                'skills': skills_data,
                'experience': experience_data,
                'education': education_data,
                'projects': projects_data,
                'summary': summary,
                'sections': self._extract_sections_simple(text)
            }
        except Exception as e:
            print(f"⚠️ Error in semantic analysis: {e}")
            # Return basic data if analysis fails
            return {
                'full_text': text,
                'skills': {'skills': [], 'unique_skills': []},
                'experience': {'total_years': 0, 'roles': [], 'companies': []},
                'education': [],
                'projects': [],
                'summary': text[:200] + '...' if len(text) > 200 else text,
                'sections': {}
            }
    
    def extract_skills_semantic(self, text):
        """
        Extract skills using semantic understanding
        Not just keyword matching - understands context
        """
        # Split into sentences
        sentences = text.split('.')
        
        skills = []
        skill_contexts = []
        
        # Skill categories for classification
        skill_categories = [
            "programming language", "framework", "database", 
            "cloud platform", "devops tool", "soft skill",
            "data science", "machine learning", "web development",
            "mobile development", "project management", "design"
        ]
        
        for sentence in sentences:
            if len(sentence) < 20:
                continue
            
            # Check if sentence contains skill information
            result = self.classifier(
                sentence,
                candidate_labels=skill_categories + ["not a skill"],
                multi_label=False
            )
            
            if result['labels'][0] != "not a skill" and result['scores'][0] > 0.6:
                # Extract the skill from context
                extracted_skills = self._extract_skill_from_context(sentence)
                
                for skill in extracted_skills:
                    skill_level = self._detect_skill_level(sentence, skill)
                    
                    skills.append({
                        'skill': skill,
                        'category': result['labels'][0],
                        'confidence': result['scores'][0],
                        'level': skill_level,
                        'context': sentence
                    })
                    
                    skill_contexts.append({
                        'skill': skill,
                        'context': sentence
                    })
        
        return {
            'skills': skills,
            'unique_skills': list(set([s['skill'] for s in skills])),
            'skill_contexts': skill_contexts,
            'primary_skills': self._identify_primary_skills(skills)
        }
    
    def _extract_skill_from_context(self, sentence):
        """Extract actual skill name from context"""
        # Common skill patterns
        skill_patterns = [
            r'\b(python|java|javascript|typescript|ruby|php|go|rust|swift|kotlin)\b',
            r'\b(react|angular|vue|django|flask|spring|tensorflow|pytorch|keras)\b',
            r'\b(sql|mysql|postgresql|mongodb|redis|elasticsearch|cassandra)\b',
            r'\b(aws|azure|gcp|docker|kubernetes|jenkins|terraform|ansible)\b',
            r'\b(machine learning|deep learning|nlp|computer vision|data science)\b'
        ]
        
        found_skills = []
        sentence_lower = sentence.lower()
        
        for pattern in skill_patterns:
            matches = re.findall(pattern, sentence_lower)
            found_skills.extend(matches)
        
        return found_skills if found_skills else [sentence[:20]]  # Fallback
    
    def _detect_skill_level(self, sentence, skill):
        """Detect proficiency level from context"""
        sentence_lower = sentence.lower()
        
        # Level indicators
        expert_indicators = ['expert', 'advanced', 'senior', 'lead', 'principal', 'master']
        intermediate_indicators = ['intermediate', 'working knowledge', 'proficient', 'experienced']
        beginner_indicators = ['beginner', 'basic', 'learning', 'familiar', 'junior']
        
        if any(ind in sentence_lower for ind in expert_indicators):
            return 'expert'
        elif any(ind in sentence_lower for ind in intermediate_indicators):
            return 'intermediate'
        elif any(ind in sentence_lower for ind in beginner_indicators):
            return 'beginner'
        else:
            return 'not specified'
    
    def _identify_primary_skills(self, skills):
        """Identify primary skills based on frequency and context"""
        if not skills:
            return []
        
        # Count skill occurrences
        skill_counts = {}
        for s in skills:
            skill = s['skill']
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
        
        # Sort by frequency
        sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [skill for skill, count in sorted_skills[:5]]
    
    def analyze_experience(self, text):
        """Analyze experience using semantic understanding"""
        # Split into sections
        sections = text.split('\n\n')
        
        experience_data = {
            'total_years': 0,
            'roles': [],
            'companies': [],
            'achievements': [],
            'responsibilities': [],
            'experience_quality': 'unknown'
        }
        
        for section in sections:
            if 'experience' in section.lower() or 'work' in section.lower():
                # This is experience section
                lines = section.split('\n')
                
                for line in lines:
                    if len(line) < 20:
                        continue
                    
                    # Extract role
                    role = self._extract_role_semantic(line)
                    if role:
                        experience_data['roles'].append(role)
                    
                    # Extract company
                    company = self._extract_company_semantic(line)
                    if company:
                        experience_data['companies'].append(company)
                    
                    # Classify if line contains achievement
                    achievement_result = self.classifier(
                        line,
                        candidate_labels=["achievement", "responsibility", "description"],
                        multi_label=False
                    )
                    
                    if achievement_result['labels'][0] == "achievement" and achievement_result['scores'][0] > 0.7:
                        experience_data['achievements'].append(line.strip())
                    elif "responsible" in line.lower() or "duties" in line.lower():
                        experience_data['responsibilities'].append(line.strip())
        
        # Calculate years
        experience_data['total_years'] = self._calculate_years_semantic(text)
        
        # Assess quality
        experience_data['experience_quality'] = self._assess_experience_quality(experience_data)
        
        return experience_data
    
    def _extract_role_semantic(self, text):
        """Extract role using semantic understanding"""
        role_keywords = ['engineer', 'developer', 'manager', 'analyst', 'consultant',
                        'specialist', 'architect', 'lead', 'head', 'director', 'scientist']
        
        text_lower = text.lower()
        for keyword in role_keywords:
            if keyword in text_lower:
                # Extract the phrase
                words = text.split()
                for i, word in enumerate(words):
                    if keyword in word.lower():
                        start = max(0, i-2)
                        end = min(len(words), i+3)
                        return ' '.join(words[start:end])
        
        return None
    
    def _extract_company_semantic(self, text):
        """Extract company name"""
        # Look for proper nouns that might be companies
        words = text.split()
        company_parts = []
        
        for i, word in enumerate(words):
            if word[0].isupper() and len(word) > 2:
                # Check if it's likely a company name
                context = text[max(0, i-5):min(len(text), i+10)]
                
                # Classify if this is a company
                result = self.classifier(
                    context,
                    candidate_labels=["company name", "job title", "location", "other"],
                    multi_label=False
                )
                
                if result['labels'][0] == "company name" and result['scores'][0] > 0.6:
                    company_parts.append(word)
        
        return ' '.join(company_parts) if company_parts else None
    
    def _calculate_years_semantic(self, text):
        """Calculate years of experience using semantic understanding"""
        # Look for explicit statements
        year_patterns = [
            r'(\d+)[\+]?\s*years? of experience',
            r'experience of (\d+)[\+]?\s*years?',
            r'(\d+)[\+]?\s*yr s? exp',
            r'(\d+)[\+]?\s*years? in'
        ]
        
        for pattern in year_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1))
        
        # Look for date ranges
        date_pattern = r'(\d{4})\s*[-–]\s*(\d{4}|present|current)'
        matches = re.findall(date_pattern, text, re.IGNORECASE)
        
        if matches:
            total = 0
            for start, end in matches:
                try:
                    start_year = int(start)
                    if end.lower() in ['present', 'current']:
                        import datetime
                        end_year = datetime.datetime.now().year
                    else:
                        end_year = int(end)
                    total += (end_year - start_year)
                except:
                    continue
            return total
        
        return 0
    
    def _assess_experience_quality(self, exp_data):
        """Assess the quality of experience"""
        score = 0
        
        # More achievements = better
        if len(exp_data['achievements']) >= 3:
            score += 3
        elif len(exp_data['achievements']) >= 1:
            score += 1
        
        # Multiple roles = growth
        if len(exp_data['roles']) >= 3:
            score += 2
        elif len(exp_data['roles']) >= 2:
            score += 1
        
        # Multiple companies = diversity
        if len(exp_data['companies']) >= 3:
            score += 2
        elif len(exp_data['companies']) >= 2:
            score += 1
        
        if score >= 5:
            return 'excellent'
        elif score >= 3:
            return 'good'
        elif score >= 1:
            return 'average'
        else:
            return 'basic'
    
    def analyze_education_semantic(self, text):
        """Analyze education background"""
        education = []
        
        # Look for education section
        if 'education' in text.lower():
            sections = text.split('\n\n')
            for section in sections:
                if 'education' in section.lower():
                    lines = section.split('\n')[1:]
                    
                    for line in lines:
                        if len(line) < 15:
                            continue
                        
                        # Classify education type
                        result = self.classifier(
                            line,
                            candidate_labels=["bachelor", "master", "phd", "diploma", "certification"],
                            multi_label=False
                        )
                        
                        education.append({
                            'text': line.strip(),
                            'type': result['labels'][0],
                            'confidence': result['scores'][0],
                            'institution': self._extract_institution_semantic(line),
                            'year': self._extract_year(line)
                        })
        
        return education
    
    def _extract_institution_semantic(self, text):
        """Extract institution name"""
        inst_patterns = [
            r'university of [\w\s]+',
            r'[\w\s]+ university',
            r'[\w\s]+ college',
            r'[\w\s]+ institute',
            r'iit [\w\s]+',
            r'nit [\w\s]+'
        ]
        
        text_lower = text.lower()
        for pattern in inst_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return match.group()
        
        return None
    
    def analyze_projects(self, text):
        """Analyze projects"""
        projects = []
        
        if 'project' in text.lower():
            sections = text.split('\n\n')
            for section in sections:
                if 'project' in section.lower():
                    lines = section.split('\n')[1:]
                    
                    for line in lines:
                        if line.strip() and len(line) > 20:
                            # Determine project type
                            result = self.classifier(
                                line,
                                candidate_labels=["web", "mobile", "data science", "ml", "cloud", "other"],
                                multi_label=False
                            )
                            
                            projects.append({
                                'description': line.strip(),
                                'type': result['labels'][0],
                                'confidence': result['scores'][0]
                            })
        
        return projects
    
    def generate_resume_summary(self, analysis_results):
        """Generate a semantic summary of the resume"""
        summary_parts = []
        
        # Experience summary
        exp = analysis_results.get('experience', {})
        if exp.get('total_years'):
            summary_parts.append(f"{exp['total_years']} years of experience")
        
        if exp.get('experience_quality'):
            summary_parts.append(f"Quality: {exp['experience_quality']}")
        
        # Skills summary
        skills = analysis_results.get('skills', {})
        if skills.get('primary_skills'):
            primary = ', '.join(skills['primary_skills'][:3])
            summary_parts.append(f"Primary skills: {primary}")
        
        # Achievements
        if exp.get('achievements'):
            summary_parts.append(f"{len(exp['achievements'])} key achievements")
        
        return ' | '.join(summary_parts)