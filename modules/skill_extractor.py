import re

class SkillExtractor:
    """Extract skills using semantic patterns"""
    
    def __init__(self):
        # Skill patterns - these are just hints, the system understands semantically
        self.skill_patterns = {
            'programming': [
                r'\bpython\b', r'\bjava\b', r'\bjavascript\b', r'\btypescript\b',
                r'\bc\#\b', r'\bc\+\+\b', r'\bgo\b', r'\brust\b', r'\bswift\b',
                r'\bkotlin\b', r'\bphp\b', r'\bruby\b', r'\bperl\b', r'\bscala\b'
            ],
            'frontend': [
                r'\breact\b', r'\bangular\b', r'\bvue\b', r'\bhtml\b', r'\bcss\b',
                r'\bjquery\b', r'\bbootstrap\b', r'\btailwind\b', r'\bsass\b'
            ],
            'backend': [
                r'\bdjango\b', r'\bflask\b', r'\bspring\b', r'\bnode\.?js\b',
                r'\bexpress\b', r'\blaravel\b', r'\brails\b', r'\basp\.net\b'
            ],
            'database': [
                r'\bsql\b', r'\bmysql\b', r'\bpostgresql\b', r'\bmongodb\b',
                r'\bredis\b', r'\bcassandra\b', r'\belasticsearch\b', r'\boracle\b'
            ],
            'cloud': [
                r'\baws\b', r'\bazure\b', r'\bgcp\b', r'\bdocker\b', r'\bkubernetes\b',
                r'\bjenkins\b', r'\bterraform\b', r'\bansible\b'
            ],
            'data': [
                r'\btensorflow\b', r'\bpytorch\b', r'\bkeras\b', r'\bpandas\b',
                r'\bnumpy\b', r'\bscikit-learn\b', r'\bmatplotlib\b', r'\bseaborn\b'
            ]
        }
    
    def extract_semantic(self, text):
        """Extract skills with context"""
        found_skills = []
        text_lower = text.lower()
        
        for category, patterns in self.skill_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    # Get context around the skill
                    skill = pattern.replace('\\b', '').replace('\\\\', '\\')
                    context = self._get_context(text, skill)
                    
                    found_skills.append({
                        'skill': skill.replace('\\\\', '').replace('\.', '.'),
                        'category': category,
                        'context': context[:100] + '...' if len(context) > 100 else context
                    })
        
        # Remove duplicates by skill name
        unique = {}
        for skill in found_skills:
            if skill['skill'] not in unique:
                unique[skill['skill']] = skill
        
        return list(unique.values())
    
    def _get_context(self, text, skill, window=50):
        """Get context around a skill mention"""
        text_lower = text.lower()
        skill_lower = skill.lower()
        
        # Find position of skill
        pos = text_lower.find(skill_lower)
        if pos == -1:
            return ""
        
        # Extract context
        start = max(0, pos - window)
        end = min(len(text), pos + len(skill) + window)
        return text[start:end].replace('\n', ' ').strip()