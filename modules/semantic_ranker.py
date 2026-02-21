import numpy as np

class SemanticRanker:
    """Rank candidates based on semantic understanding"""
    
    def rank_candidates_semantic(self, candidates, job):
        """Rank candidates using semantic scores"""
        if not candidates:
            return []
        
        # Filter out None candidates
        valid = [c for c in candidates if c is not None]
        
        # Sort by overall score
        valid.sort(key=lambda x: x['overall_score'], reverse=True)
        
        # Add rank and insights
        for i, candidate in enumerate(valid, 1):
            candidate['rank'] = i
            candidate['badge'] = self._get_badge(i)
            candidate['recommendation'] = self._get_recommendation(candidate)
        
        return valid
    
    def _get_badge(self, rank):
        """Get badge for rank"""
        if rank == 1:
            return '🏆 TOP CANDIDATE'
        elif rank == 2:
            return '🥈 Strong Match'
        elif rank == 3:
            return '🥉 Good Match'
        else:
            return f'#{rank}'
    
    def _get_recommendation(self, candidate):
        """Get recommendation based on scores"""
        score = candidate['overall_score']
        
        if score >= 85:
            return "Excellent match - Strongly recommend for interview"
        elif score >= 75:
            return "Very good match - Recommend for interview"
        elif score >= 65:
            return "Good match - Consider for interview"
        elif score >= 55:
            return "Moderate match - May be considered"
        else:
            return "Below threshold - Not recommended at this time"
    
    def get_shortlist(self, candidates, threshold=70):
        """Get candidates above threshold"""
        return [c for c in candidates if c and c.get('overall_score', 0) >= threshold]