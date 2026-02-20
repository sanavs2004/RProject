class SkillExtractor:
    """Skill extraction using semantic understanding"""
    
    def __init__(self):
        from .resume_analyzer import ResumeAnalyzer
        self.analyzer = ResumeAnalyzer(None)
    
    def extract_skills(self, text):
        """Extract skills semantically"""
        if hasattr(self.analyzer, 'extract_skills_semantic'):
            return self.analyzer.extract_skills_semantic(text)
        return {'skills': []}