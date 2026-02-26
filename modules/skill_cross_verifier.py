class SkillCrossVerifier:
    """
    Cross-verifies skills claimed in resume against GitHub evidence
    and skill test results
    """
    
    def __init__(self):
        self.skill_synonyms = {
            'python': ['python', 'python3', 'py', 'django', 'flask'],
            'javascript': ['javascript', 'js', 'node', 'nodejs', 'react', 'vue', 'angular'],
            'java': ['java', 'spring', 'jvm'],
            'c++': ['c++', 'cpp', 'cplusplus'],
            'sql': ['sql', 'mysql', 'postgresql', 'database'],
            'aws': ['aws', 'ec2', 's3', 'lambda', 'cloudformation'],
            'docker': ['docker', 'container', 'kubernetes', 'k8s'],
            'git': ['git', 'github', 'version control']
        }
    
    def verify_skills(self, claimed_skills, github_data=None, skill_test_results=None):
        """
        Verify claimed skills against available evidence
        
        Args:
            claimed_skills: list of skills from resume
            github_data: GitHub verification result
            skill_test_results: skill test scores per skill
        
        Returns:
            dict: verification results
        """
        verification = {
            'verified': [],
            'partial': [],
            'unverified': [],
            'confidence_bonus': 0
        }
        
        if not claimed_skills:
            return verification
        
        # Check each claimed skill
        for skill in claimed_skills:
            evidence_score = 0
            
            # GitHub evidence
            if github_data:
                evidence_score += self._check_github_evidence(skill, github_data)
            
            # Skill test evidence
            if skill_test_results and skill in skill_test_results:
                evidence_score += skill_test_results[skill] / 100 * 2
            
            # Classify based on evidence score
            if evidence_score >= 3:
                verification['verified'].append(skill)
            elif evidence_score >= 1:
                verification['partial'].append(skill)
            else:
                verification['unverified'].append(skill)
        
        # Calculate confidence bonus based on verification ratio
        total_claimed = len(claimed_skills)
        if total_claimed > 0:
            verified_count = len(verification['verified'])
            partial_count = len(verification['partial'])
            
            # Bonus formula: (verified * 1.0 + partial * 0.5) / total
            bonus_ratio = (verified_count + (partial_count * 0.5)) / total_claimed
            verification['confidence_bonus'] = round(bonus_ratio * 15, 2)  # Max 15% bonus
        
        return verification
    
    def _check_github_evidence(self, skill, github_data):
        """Check if skill appears in GitHub data"""
        if not github_data or not github_data.get('languages_used'):
            return 0
        
        skill_lower = skill.lower()
        github_langs = [lang.lower() for lang in github_data['languages_used'].keys()]
        
        # Direct match
        if skill_lower in github_langs:
            return 3
        
        # Synonym match
        for lang in github_langs:
            if skill_lower in lang or lang in skill_lower:
                return 2
        
        # Check for synonyms
        for key, synonyms in self.skill_synonyms.items():
            if skill_lower == key or skill_lower in synonyms:
                for lang in github_langs:
                    if any(syn in lang for syn in synonyms):
                        return 2
        
        return 0