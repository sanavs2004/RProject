class ScoringEngine:
    """Scoring engine for candidate evaluation"""
    
    def __init__(self, config):
        from .resume_ranker import ResumeRanker
        self.ranker = ResumeRanker(config)
    
    def calculate_scores(self, data):
        """Calculate comprehensive scores"""
        return self.ranker.calculate_comprehensive_score(
            data.get('semantic_match', {}),
            data.get('skill_relevance', {}),
            data.get('experience_data', {}),
            data.get('job_requirements', {})
        )