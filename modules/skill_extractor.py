import re

class SkillExtractor:
    """Extract skills using semantic patterns"""
    
    def __init__(self):
        # Skill patterns - mapping of skill names to their regex patterns
        self.skill_patterns = {
            'programming': {
                'python': r'\bpython\b',
                'java': r'\bjava\b',
                'javascript': r'\bjavascript\b|\bjs\b',
                'typescript': r'\btypescript\b|\bts\b',
                'csharp': r'\bc#\b|\bcsharp\b',
                'cpp': r'\bc\+\+\b|\bcpp\b',
                'go': r'\bgo\b',
                'rust': r'\brust\b',
                'swift': r'\bswift\b',
                'kotlin': r'\bkotlin\b',
                'php': r'\bphp\b',
                'ruby': r'\bruby\b',
                'perl': r'\bperl\b',
                'scala': r'\bscala\b'
            },
            'frontend': {
                'react': r'\breact\b|\breact\.?js\b',
                'angular': r'\bangular\b',
                'vue': r'\bvue\b|\bvue\.?js\b',
                'html': r'\bhtml\b',
                'css': r'\bcss\b',
                'jquery': r'\bjquery\b',
                'bootstrap': r'\bbootstrap\b',
                'tailwind': r'\btailwind\b|\btailwindcss\b',
                'sass': r'\bsass\b|\bscss\b'
            },
            'backend': {
                'django': r'\bdjango\b',
                'flask': r'\bflask\b',
                'spring': r'\bspring\b|\bspringboot\b',
                'nodejs': r'\bnode\.?js\b|\bnode\b',
                'express': r'\bexpress\b|\bexpress\.?js\b',
                'laravel': r'\blaravel\b',
                'rails': r'\brails\b',
                'aspnet': r'\basp\.?net\b'
            },
            'database': {
                'sql': r'\bsql\b',
                'mysql': r'\bmysql\b',
                'postgresql': r'\bpostgresql\b|\bpostgres\b',
                'mongodb': r'\bmongodb\b|\bmongo\b',
                'redis': r'\bredis\b',
                'cassandra': r'\bcassandra\b',
                'elasticsearch': r'\belasticsearch\b',
                'oracle': r'\boracle\b'
            },
            'cloud': {
                'aws': r'\baws\b',
                'azure': r'\bazure\b',
                'gcp': r'\bgcp\b|\bgoogle cloud\b',
                'docker': r'\bdocker\b',
                'kubernetes': r'\bkubernetes\b|\bk8s\b',
                'jenkins': r'\bjenkins\b',
                'terraform': r'\bterraform\b',
                'ansible': r'\bansible\b'
            },
            'data': {
                'tensorflow': r'\btensorflow\b',
                'pytorch': r'\bpytorch\b',
                'keras': r'\bkeras\b',
                'pandas': r'\bpandas\b',
                'numpy': r'\bnumpy\b',
                'scikit-learn': r'\bscikit-learn\b|\bsklearn\b',
                'matplotlib': r'\bmatplotlib\b',
                'seaborn': r'\bseaborn\b'
            },
            'tools': {
                'git': r'\bgit\b',
                'github': r'\bgithub\b',
                'gitlab': r'\bgitlab\b',
                'jira': r'\bjira\b',
                'confluence': r'\bconfluence\b',
                'vscode': r'\bvs\s?code\b|\bvisual studio code\b',
                'chrome_devtools': r'\bchrome\s?devtools?\b'
            }
        }
    
    def extract_semantic(self, text):
        """Extract skills with context"""
        print("\n🔍 DEBUG: Analyzing text for skills...")
        print(f"Text length: {len(text)} characters")
        
        found_skills = []
        text_lower = text.lower()
        
        for category, skills in self.skill_patterns.items():
            for skill_name, pattern in skills.items():
                try:
                    if re.search(pattern, text_lower, re.IGNORECASE):
                        # Get context around the skill
                        context = self._get_context(text, skill_name)
                        
                        found_skills.append({
                            'skill': skill_name,
                            'category': category,
                            'context': context[:100] + '...' if len(context) > 100 else context
                        })
                        print(f"   ✅ Found: {skill_name} in category {category}")
                except Exception as e:
                    print(f"   ⚠️ Error matching {skill_name}: {e}")
        
        # Remove duplicates by skill name
        unique = {}
        for skill in found_skills:
            if skill['skill'] not in unique:
                unique[skill['skill']] = skill
        
        result = list(unique.values())
        print(f"\n📊 Total unique skills found: {len(result)}")
        if result:
            print(f"   Skills: {[s['skill'] for s in result]}")
        
        return result
    
    def _get_context(self, text, skill, window=50):
        """Get context around a skill mention"""
        text_lower = text.lower()
        skill_lower = skill.lower()
        
        # Find position of skill
        pos = text_lower.find(skill_lower)
        if pos == -1:
            # Try to find by word boundary
            pattern = r'\b' + re.escape(skill_lower) + r'\b'
            match = re.search(pattern, text_lower)
            if match:
                pos = match.start()
            else:
                return ""
        
        # Extract context
        start = max(0, pos - window)
        end = min(len(text), pos + len(skill) + window)
        return text[start:end].replace('\n', ' ').strip()
    
    def extract_skills_from_resume(self, file_path):
        """Helper method to extract skills directly from a resume file"""
        try:
            # Try to read the file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            return self.extract_semantic(text)
        except Exception as e:
            print(f"Error reading file: {e}")
            return []