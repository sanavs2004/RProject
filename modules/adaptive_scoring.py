import json
import os
from modules.role_config_manager import RoleConfigManager  # Add this import

class AdaptiveScorer:
    """
    Dynamically redistributes weights when signals are missing
    Never penalizes candidates for missing optional channels
    """
    
    def __init__(self, config):
        self.config = config
        # Initialize the role config manager
        config_file = os.path.join(config.BASE_DIR, 'config', 'role_weights.json')
        self.role_config_manager = RoleConfigManager(config_file)
    
    def calculate_final_score(self, scores, signals_present, role='default'):
        """
        Calculate weighted score with adaptive redistribution
        
        Args:
            scores: dict of scores {'resume': 85, 'github': 70, 'skill_test': 90}
            signals_present: list of present signals ['resume', 'skill_test']
            role: job role for role-specific weights
        
        Returns:
            dict: final score and detailed breakdown
        """
        # Get role-specific weights from config file
        role_config = self.role_config_manager.get_role_config(role)
        weights = role_config.get('weights', {
            'resume': 0.35,
            'skill_test': 0.40,
            'github': 0.15,
            'other': 0.10
        })
        
        # Filter to present signals
        present_weights = {k: v for k, v in weights.items() if k in signals_present}
        present_scores = {k: scores.get(k, 0) for k in present_weights.keys()}
        
        # Calculate total weight of present signals
        total_weight = sum(present_weights.values())
        
        # If no signals present (should never happen - resume is always present)
        if total_weight == 0:
            return {
                'final_score': 0,
                'weights_applied': {},
                'signals_used': [],
                'warning': 'No valid signals available'
            }
        
        # Redistribute weights proportionally
        redistributed_weights = {}
        for signal, weight in present_weights.items():
            redistributed_weights[signal] = weight / total_weight
        
        # Calculate weighted score
        final_score = 0
        score_components = {}
        
        for signal, weight in redistributed_weights.items():
            signal_score = present_scores.get(signal, 0)
            contribution = signal_score * weight
            final_score += contribution
            score_components[signal] = {
                'raw_score': signal_score,
                'weight': round(weight, 3),
                'contribution': round(contribution, 2)
            }
        
        return {
            'final_score': round(final_score, 2),
            'weights_applied': redistributed_weights,
            'original_weights': weights,
            'score_components': score_components,
            'signals_used': signals_present
        }
    
    def get_fairness_flag(self, signals_present, role):
        """Check if candidate is at a disadvantage"""
        role_config = self.role_config_manager.get_role_config(role)
        weights = role_config.get('weights', {})
        
        # If candidate has no optional channels and those channels have high weight
        optional_channels = ['github', 'other']
        optional_weight = sum(weights.get(ch, 0) for ch in optional_channels)
        
        if optional_weight > 0.2 and len(signals_present) <= 2:
            return {
                'flag': True,
                'message': f'Candidate missing {optional_weight*100:.0f}% of signal weight',
                'missing': [ch for ch in optional_channels if ch not in signals_present]
            }
        
        return {'flag': False, 'message': 'Fair assessment'}