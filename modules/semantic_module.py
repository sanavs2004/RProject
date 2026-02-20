class SemanticMatcher:
    """Semantic matching using BERT"""
    
    def __init__(self, config):
        from .resume_matcher import ResumeMatcher
        self.matcher = ResumeMatcher(config)
    
    def compute_similarity(self, text1, text2):
        """Compute semantic similarity"""
        return self.matcher.compute_semantic_similarity(text1, text2)