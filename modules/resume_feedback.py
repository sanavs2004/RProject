import json
from datetime import datetime

class ResumeFeedbackGenerator:
    """Generates personalized feedback for candidates"""
    
    def __init__(self, config):
        self.config = config
    
    def generate_rejection_feedback(self, skills_data, job_requirements, scores):
        """
        Generate constructive feedback for rejected candidates
        """
        # Identify skill gaps
        skill_gaps = self._identify_skill_gaps(
            skills_data.get('skills', []),
            job_requirements.get('required_skills', [])
        )
        
        # Generate learning recommendations
        learning_path = self._generate_learning_path(skill_gaps)
        
        feedback = {
            'summary': self._generate_summary(scores),
            'skill_gaps': skill_gaps,
            'learning_recommendations': learning_path,
            'encouragement': self._generate_encouragement(),
            'reapplication_info': {
                'can_reapply': True,
                'recommended_time': '3-6 months',
                'process': 'Complete the learning path and upload your updated resume'
            }
        }
        
        return feedback
    
    def _identify_skill_gaps(self, candidate_skills, required_skills):
        """Identify missing skills"""
        if not candidate_skills:
            return [{'skill': skill, 'priority': 'high'} for skill in required_skills]
        
        candidate_skill_names = set()
        for s in candidate_skills:
            if isinstance(s, dict):
                candidate_skill_names.add(s.get('skill', '').lower())
            else:
                candidate_skill_names.add(str(s).lower())
        
        gaps = []
        for skill in required_skills:
            if skill.lower() not in candidate_skill_names:
                # Determine priority
                if skill in required_skills[:3]:  # First 3 skills are high priority
                    priority = 'high'
                else:
                    priority = 'medium'
                
                gaps.append({
                    'skill': skill,
                    'priority': priority,
                    'resources': self._get_learning_resources(skill)
                })
        
        return gaps
    
    def _get_learning_resources(self, skill):
        """Get learning resources for a skill"""
        resources = {
            'python': [
                {'type': 'course', 'name': 'Python for Beginners', 'platform': 'Coursera', 'url': '#'},
                {'type': 'book', 'name': 'Automate the Boring Stuff with Python', 'url': '#'}
            ],
            'java': [
                {'type': 'course', 'name': 'Java Programming Masterclass', 'platform': 'Udemy', 'url': '#'}
            ],
            'javascript': [
                {'type': 'course', 'name': 'The Complete JavaScript Course', 'platform': 'Udemy', 'url': '#'}
            ],
            'react': [
                {'type': 'course', 'name': 'React - The Complete Guide', 'platform': 'Udemy', 'url': '#'}
            ],
            'sql': [
                {'type': 'course', 'name': 'SQL for Data Science', 'platform': 'Coursera', 'url': '#'}
            ],
            'aws': [
                {'type': 'certification', 'name': 'AWS Certified Cloud Practitioner', 'platform': 'AWS', 'url': '#'}
            ],
            'docker': [
                {'type': 'course', 'name': 'Docker Mastery', 'platform': 'Udemy', 'url': '#'}
            ],
            'machine learning': [
                {'type': 'course', 'name': 'Machine Learning by Andrew Ng', 'platform': 'Coursera', 'url': '#'}
            ]
        }
        
        return resources.get(skill.lower(), [
            {'type': 'search', 'name': f'Learn {skill}', 'platform': 'Google', 'url': '#'}
        ])
    
    def _generate_learning_path(self, skill_gaps):
        """Generate personalized learning path"""
        if not skill_gaps:
            return None
        
        # Sort by priority
        high_priority = [g for g in skill_gaps if g['priority'] == 'high']
        medium_priority = [g for g in skill_gaps if g['priority'] == 'medium']
        
        learning_path = {
            'estimated_duration': self._calculate_duration(skill_gaps),
            'phases': []
        }
        
        # Phase 1: High priority skills
        if high_priority:
            phase1 = {
                'name': 'Core Skills',
                'duration': f"{len(high_priority) * 2} weeks",
                'skills': high_priority,
                'resources': []
            }
            for gap in high_priority[:3]:  # Limit resources
                phase1['resources'].extend(gap.get('resources', [])[:2])
            learning_path['phases'].append(phase1)
        
        # Phase 2: Medium priority skills
        if medium_priority:
            phase2 = {
                'name': 'Supplementary Skills',
                'duration': f"{len(medium_priority) * 1} weeks",
                'skills': medium_priority,
                'resources': []
            }
            for gap in medium_priority[:3]:
                phase2['resources'].extend(gap.get('resources', [])[:1])
            learning_path['phases'].append(phase2)
        
        return learning_path
    
    def _calculate_duration(self, skill_gaps):
        """Calculate estimated learning duration"""
        high_count = len([g for g in skill_gaps if g['priority'] == 'high'])
        medium_count = len([g for g in skill_gaps if g['priority'] == 'medium'])
        
        total_weeks = (high_count * 2) + (medium_count * 1)
        
        if total_weeks <= 4:
            return "1 month"
        elif total_weeks <= 8:
            return "2 months"
        elif total_weeks <= 12:
            return "3 months"
        else:
            return "3-4 months"
    
    def _generate_summary(self, scores):
        """Generate summary feedback"""
        overall = scores.get('overall', 0)
        
        if overall >= 80:
            return "Strong application! Very close to meeting our requirements."
        elif overall >= 70:
            return "Good application with some areas for improvement."
        elif overall >= 60:
            return "Decent application. Focus on addressing skill gaps."
        elif overall >= 50:
            return "Your application shows potential. Work on key requirements."
        else:
            return "Thank you for your interest. Focus on building core skills."
    
    def _generate_encouragement(self):
        """Generate encouraging message"""
        encouragements = [
            "Every expert was once a beginner. Keep learning and growing!",
            "Your next opportunity is waiting. Stay focused on your goals!",
            "Rejection is just redirection. Use this feedback to come back stronger!",
            "Skills can be learned. Dedication and persistence matter most!",
            "This is not a 'no', it's a 'not yet'. Keep building!"
        ]
        
        import random
        return random.choice(encouragements)
    
    def generate_positive_feedback(self, scores):
        """Generate feedback for shortlisted candidates"""
        overall = scores.get('overall', 0)
        
        feedback = {
            'summary': f"Congratulations! Your profile shows a {overall:.1f}% match with the role.",
            'strengths': [
                f"Semantic match: {scores.get('semantic', 0):.1f}%",
                f"Skill alignment: {scores.get('skill', 0):.1f}%",
                f"Experience score: {scores.get('experience', 0):.1f}%"
            ],
            'next_steps': [
                "You will be contacted for an interview shortly",
                "Prepare to discuss your experience in detail",
                "Review the job description before the interview"
            ],
            'interview_tips': [
                "Research our company culture and values",
                "Prepare specific examples of your achievements",
                "Think of questions you'd like to ask us"
            ]
        }
        
        return feedback
    
    def generate_interview_invitation(self, candidate_name, job_title, scores):
        """Generate interview invitation email"""
        email = f"""
        Dear {candidate_name},
        
        We were impressed by your application for the {job_title} position!
        
        Based on our AI-powered screening, your profile shows a strong match 
        (score: {scores.get('overall', 0):.1f}%) with our requirements.
        
        We would like to invite you for an interview to discuss your application further.
        
        Please let us know your availability for next week.
        
        Best regards,
        RecruitAI Team
        """
        
        return email
    
    def generate_rejection_email(self, candidate_name, job_title, feedback):
        """Generate rejection email with constructive feedback"""
        email = f"""
        Dear {candidate_name},
        
        Thank you for applying for the {job_title} position at our company.
        
        After careful review of your application, we have decided to move forward 
        with other candidates whose profiles more closely match our current requirements.
        
        However, we believe in providing value even when we can't move forward. 
        Based on our analysis, here are some suggestions for your skill development:
        
        {self._format_skill_gaps_for_email(feedback.get('skill_gaps', []))}
        
        We've created a personalized learning path that you can follow to strengthen 
        your profile. You can reapply after completing these recommendations.
        
        {feedback.get('encouragement', '')}
        
        We wish you the best in your job search!
        
        Best regards,
        RecruitAI Team
        """
        
        return email
    
    def _format_skill_gaps_for_email(self, skill_gaps):
        """Format skill gaps for email"""
        if not skill_gaps:
            return "No specific skill gaps identified."
        
        formatted = "\n"
        for gap in skill_gaps:
            formatted += f"• {gap['skill']} ({gap['priority']} priority)\n"
        
        return formatted