import re
import PyPDF2
import docx2txt
from datetime import datetime

class SemanticParser:
    """Parse resumes with semantic understanding"""
    
    def __init__(self):
        # Try to import sentence_transformers for similarity
        try:
            from sentence_transformers import SentenceTransformer, util
            self.util = util
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.semantic_support = True
        except ImportError:
            self.semantic_support = False
            print("⚠️ sentence-transformers not installed. Using basic matching.")
    
    def parse_resume_semantic(self, file_path):
        """Extract and understand resume content semantically"""
        # Extract raw text
        text = self._extract_text(file_path)
        
        # Clean text
        text = self._clean_text(text)
        
        # Extract semantic sections
        sections = self._extract_sections_semantic(text)
        
        # Extract key points (important sentences)
        key_points = self._extract_key_points(text)
        
        return {
            'text': text,
            'sections': sections,
            'key_points': key_points,
            'word_count': len(text.split()),
            'char_count': len(text)
        }
    
    # ========== ADD THE FUNCTION HERE (inside the class) ==========
    def calculate_similarity(self, embedding1, embedding2):
        """Calculate similarity with proper type handling"""
        try:
            if not self.semantic_support:
                return 50.0
            
            # Convert both to same dtype (float32)
            if embedding1.dtype != embedding2.dtype:
                embedding1 = embedding1.astype('float32')
                embedding2 = embedding2.astype('float32')
            
            # Now calculate similarity
            similarity = self.util.cos_sim(embedding1, embedding2).item() * 100
            return similarity
        except Exception as e:
            print(f"Error calculating similarity: {e}")
            return 50.0
    
    def _extract_text(self, file_path):
        """Extract text from file"""
        ext = file_path.lower().split('.')[-1]
        
        try:
            if ext == 'txt':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            elif ext == 'pdf':
                text = ""
                with open(file_path, 'rb') as f:
                    pdf = PyPDF2.PdfReader(f)
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                return text
            elif ext == 'docx':
                return docx2txt.process(file_path)
            else:
                return ""
        except:
            return ""
    
    def _clean_text(self, text):
        """Clean text while preserving meaning"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep sentence structure
        text = re.sub(r'[^\w\s\.\,\-\/\+\#\@\(\)]', '', text)
        
        return text.strip()
    
    def _extract_sections_semantic(self, text):
        """Extract sections using semantic understanding"""
        sections = {
            'summary': '',
            'experience': '',
            'education': '',
            'skills': '',
            'projects': '',
            'certifications': ''
        }
        
        lines = text.split('\n')
        current_section = 'general'
        section_text = []
        
        section_indicators = {
            'summary': ['summary', 'profile', 'about', 'objective'],
            'experience': ['experience', 'work', 'employment', 'job'],
            'education': ['education', 'academic', 'degree', 'university', 'college'],
            'skills': ['skills', 'technologies', 'competencies', 'expertise'],
            'projects': ['projects', 'personal projects', 'academic projects'],
            'certifications': ['certifications', 'certificates', 'licenses']
        }
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check if this line starts a new section
            for section, indicators in section_indicators.items():
                if any(ind in line_lower for ind in indicators) and len(line) < 50:
                    if current_section != 'general' and section_text:
                        sections[current_section] = ' '.join(section_text)
                    current_section = section
                    section_text = []
                    break
            else:
                if line.strip():
                    section_text.append(line)
        
        # Save last section
        if current_section != 'general' and section_text:
            sections[current_section] = ' '.join(section_text)
        
        return sections
    
    def _extract_key_points(self, text):
        """Extract key points from resume"""
        sentences = text.split('.')
        key_points = []
        
        # Indicators of important sentences
        importance_indicators = [
            'led', 'managed', 'created', 'developed', 'designed',
            'achieved', 'increased', 'decreased', 'improved',
            'responsible', 'spearheaded', 'architected', 'built',
            'patent', 'published', 'award', 'recognition'
        ]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue
            
            # Check if sentence contains important indicators
            sentence_lower = sentence.lower()
            for indicator in importance_indicators:
                if indicator in sentence_lower:
                    key_points.append(sentence)
                    break
        
        return key_points[:10]  # Return top 10 key points
    
    def extract_experience_semantic(self, text):
        """Extract experience with semantic understanding"""
        # Find experience section
        sections = self._extract_sections_semantic(text)
        exp_text = sections.get('experience', '')
        
        # Extract years
        years = self._extract_years(text)
        
        # Extract descriptions
        descriptions = []
        sentences = exp_text.split('.')
        for sent in sentences:
            if len(sent.strip()) > 30:
                descriptions.append(sent.strip())
        
        # Determine quality
        if len(descriptions) > 5:
            quality = 'excellent'
        elif len(descriptions) > 3:
            quality = 'good'
        elif len(descriptions) > 1:
            quality = 'average'
        else:
            quality = 'basic'
        
        return {
            'years': years,
            'descriptions': descriptions[:5],
            'quality': quality
        }
    
    def _extract_years(self, text):
        """Extract years of experience"""
        # Look for explicit statements
        patterns = [
            r'(\d+)[\+]?\s*years? of experience',
            r'experience of (\d+)[\+]?\s*years?',
            r'(\d+)[\+]?\s*yr\s*exp',
            r'(\d+)[\+]?\s*years? in'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except:
                    pass
        
        # Calculate from dates
        date_pattern = r'(\d{4})\s*[-–]\s*(\d{4}|present|current)'
        matches = re.findall(date_pattern, text, re.IGNORECASE)
        
        total = 0
        current_year = datetime.now().year
        
        for start, end in matches:
            try:
                start_year = int(start)
                if end.lower() in ['present', 'current']:
                    end_year = current_year
                else:
                    end_year = int(end)
                total += (end_year - start_year)
            except:
                continue
        
        return total
    
    def extract_education_semantic(self, text):
        """Extract education with semantic understanding"""
        sections = self._extract_sections_semantic(text)
        edu_text = sections.get('education', '')
        
        education = []
        
        # Look for degrees
        degree_patterns = [
            (r'(bachelor|b\.?tech|b\.?e|b\.?sc)', 'bachelor'),
            (r'(master|m\.?tech|m\.?e|m\.?sc|mba)', 'master'),
            (r'(ph\.?d|doctorate)', 'phd'),
            (r'(diploma|certificate)', 'diploma')
        ]
        
        sentences = edu_text.split('.')
        for sentence in sentences:
            sentence_lower = sentence.lower()
            for pattern, degree_type in degree_patterns:
                if re.search(pattern, sentence_lower):
                    education.append({
                        'degree': degree_type,
                        'description': sentence.strip()
                    })
                    break
        
        return education