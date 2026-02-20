import numpy as np
from datetime import datetime

class ResumeRanker:
    """Ranks candidates based on comprehensive scoring"""
    
    def __init__(self, config):
        self.config = config
        self.weights = config.SCORE_WEIGHTS
        self.thresholds = config.THRESHOLDS
    
    def calculate_comprehensive_score(self, semantic_match, skill_relevance, experience_data, job_requirements):
        """
        Calculate comprehensive score combining multiple factors
        """
        scores = {}
        
        # 1. Semantic match score
        scores['semantic'] = semantic_match['overall_similarity']
        
        # 2. Skill relevance score
        scores['skill'] = skill_relevance['overall_relevance']
        
        # 3. Experience score
        scores['experience'] = self._calculate_experience_score(
            experience_data, 
            job_requirements.get('experience_level', '')
        )
        
        # 4. Education score
        scores['education'] = self._calculate_education_score(
            experience_data.get('education', []),
            job_requirements
        )
        
        # 5. Achievement score (bonus)
        scores['achievements'] = self._calculate_achievement_score(experience_data)
        
        # Calculate weighted overall score
        overall = (
            self.weights['semantic'] * scores['semantic'] +
            self.weights['skills'] * scores['skill'] +
            self.weights['experience'] * scores['experience'] +
            self.weights['education'] * scores['education']
        )
        
        # Add achievement bonus (capped)
        overall = min(overall + scores['achievements'], 100)
        
        scores['overall'] = overall
        
        return scores
    
    def _calculate_experience_score(self, experience_data, required_level):
        """Calculate experience score"""
        years = experience_data.get('total_years', 0)
        
        # Map required level to years
        level_years = {
            'entry': 2,
            'junior': 3,
            'mid': 5,
            'senior': 8,
            'lead': 10,
            'manager': 12
        }
        
        required_years = level_years.get(required_level.lower(), 5)
        
        # Calculate score based on years
        if years >= required_years:
            base_score = 100
        else:
            base_score = (years / required_years) * 100
        
        # Quality multiplier
        quality_multiplier = {
            'excellent': 1.1,
            'good': 1.0,
            'average': 0.9,
            'basic': 0.8
        }.get(experience_data.get('experience_quality', 'good'), 1.0)
        
        return min(base_score * quality_multiplier, 100)
    
    def _calculate_education_score(self, education, job_requirements):
        """Calculate education score"""
        if not education:
            return 50  # Default score if no education info
        
        # Check for required degrees
        required_degrees = job_requirements.get('required_education', [])
        if not required_degrees:
            return 80  # No specific requirement
        
        score = 0
        for edu in education:
            edu_type = edu.get('type', '').lower()
            if any(req.lower() in edu_type for req in required_degrees):
                score = 100
                break
        
        return score if score else 60
    
    def _calculate_achievement_score(self, experience_data):
        """Calculate achievement bonus score"""
        achievements = experience_data.get('achievements', [])
        
        if len(achievements) >= 5:
            return 15
        elif len(achievements) >= 3:
            return 10
        elif len(achievements) >= 1:
            return 5
        else:
            return 0
    
    def rank_candidate(self, scores, job):
        """
        Rank candidate and make decision
        """
        overall = scores['overall']
        
        # Determine decision
        if overall >= self.thresholds['shortlist']:
            decision = 'shortlist'
        elif overall >= self.thresholds['interview']:
            decision = 'interview'
        else:
            decision = 'reject'
        
        # Determine rank
        if overall >= 90:
            rank = 'A+'
        elif overall >= 85:
            rank = 'A'
        elif overall >= 80:
            rank = 'A-'
        elif overall >= 75:
            rank = 'B+'
        elif overall >= 70:
            rank = 'B'
        elif overall >= 65:
            rank = 'B-'
        elif overall >= 60:
            rank = 'C+'
        elif overall >= 55:
            rank = 'C'
        elif overall >= 50:
            rank = 'C-'
        else:
            rank = 'D'
        
        # Generate recommendations
        recommendations = self._generate_recommendations(scores, job)
        
        return {
            'overall_score': overall,
            'decision': decision,
            'rank': rank,
            'percentile': self._calculate_percentile(scores),
            'strengths': self._identify_strengths(scores),
            'weaknesses': self._identify_weaknesses(scores),
            'recommendations': recommendations,
            'next_steps': self._determine_next_steps(decision)
        }
    
    def _calculate_percentile(self, scores):
        """Calculate approximate percentile"""
        # Simplified - in production would compare with other candidates
        overall = scores['overall']
        
        if overall >= 95:
            return 99
        elif overall >= 90:
            return 95
        elif overall >= 85:
            return 90
        elif overall >= 80:
            return 80
        elif overall >= 75:
            return 70
        elif overall >= 70:
            return 60
        elif overall >= 65:
            return 50
        elif overall >= 60:
            return 40
        elif overall >= 55:
            return 30
        elif overall >= 50:
            return 20
        else:
            return 10
    
    def _identify_strengths(self, scores):
        """Identify candidate strengths"""
        strengths = []
        
        if scores['semantic'] >= 80:
            strengths.append("Excellent overall match with job requirements")
        if scores['skill'] >= 80:
            strengths.append("Strong skill alignment")
        if scores['experience'] >= 80:
            strengths.append("Relevant experience level")
        if scores['education'] >= 80:
            strengths.append("Meets education requirements")
        if scores['achievements'] >= 10:
            strengths.append("Strong achievement record")
        
        return strengths
    
    def _identify_weaknesses(self, scores):
        """Identify candidate weaknesses"""
        weaknesses = []
        
        if scores['semantic'] < 60:
            weaknesses.append("Weak semantic match with job description")
        if scores['skill'] < 60:
            weaknesses.append("Skill gaps identified")
        if scores['experience'] < 50:
            weaknesses.append("Limited relevant experience")
        if scores['education'] < 50:
            weaknesses.append("Does not meet education requirements")
        
        return weaknesses
    
    def _generate_recommendations(self, scores, job):
        """Generate recommendations based on scores"""
        recommendations = []
        
        if scores['skill'] < 70:
            missing = job.get('required_skills', [])
            if missing:
                recommendations.append(f"Consider upskilling in: {', '.join(missing[:3])}")
        
        if scores['experience'] < 60:
            recommendations.append("Gain more experience through internships or projects")
        
        if scores['education'] < 60 and job.get('required_education'):
            recommendations.append("Consider pursuing relevant certifications")
        
        return recommendations
    
    def _determine_next_steps(self, decision):
        """Determine next steps based on decision"""
        if decision == 'shortlist':
            return {
                'action': 'Schedule technical interview',
                'timeline': 'Within 2 days',
                'priority': 'High'
            }
        elif decision == 'interview':
            return {
                'action': 'Schedule initial screening call',
                'timeline': 'Within 3 days',
                'priority': 'Medium'
            }
        else:
            return {
                'action': 'Send feedback and learning path',
                'timeline': 'Within 1 day',
                'priority': 'Low'
            }
    
    def rank_multiple_candidates(self, candidate_scores):
        """Rank multiple candidates"""
        # Sort by overall score
        ranked = sorted(candidate_scores, key=lambda x: x['overall_score'], reverse=True)
        
        # Add rank
        for i, candidate in enumerate(ranked, 1):
            candidate['rank'] = i
        
        return ranked