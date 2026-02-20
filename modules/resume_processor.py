# import re
# from datetime import datetime
# from .resume_upload_handler import ResumeUploadHandler  # If needed
# from .resume_analyzer import ResumeAnalyzer  # This has semantic analysis
# from .resume_matcher import ResumeMatcher 
# from .parser_module import ResumeParser
# from .bias_module import BiasDetector

# class ResumeProcessor:
#     """Main orchestration module for resume processing"""
    
#     def __init__(self, config):
#         self.config = config
#         self.parser = ResumeParser()  # Now works
#         self.bias_detector = BiasDetector()  # Now works
#         self.analyzer = ResumeAnalyzer(config)
#         self.matcher = ResumeMatcher(config)
#         # self.config = config
#         # self.analyzer = ResumeAnalyzer(config)
#         # self.parser = ResumeParser()
#         # self.bias_detector = BiasDetector()
        
# def parse_resume(self, file_path):
#     """
#     Parse resume and extract structured information
#     Uses semantic understanding, not just keywords
#     """
#     # Extract text from file
#     text = self._extract_text(file_path)
    
#     # Clean text
#     text = self._clean_text(text)
    
#     # Use the actual methods from ResumeAnalyzer
#     # Instead of calling analyze_resume_semantic, call individual methods
    
#     # Extract skills using semantic understanding
#     skills_data = self.analyzer.extract_skills_semantic(text)
    
#     # Analyze experience
#     experience_data = self.analyzer.analyze_experience(text)
    
#     # Analyze education
#     education_data = self.analyzer.analyze_education_semantic(text)
    
#     # Analyze projects
#     projects_data = self.analyzer.analyze_projects(text)
    
#     # Generate summary
#     analysis_results = {
#         'skills': skills_data,
#         'experience': experience_data,
#         'education': education_data,
#         'projects': projects_data
#     }
#     summary = self.analyzer.generate_resume_summary(analysis_results)
    
#     # Parse sections (you might need to add this method or use a simple split)
#     sections = self._extract_sections_simple(text)
    
#     # Extract contact info
#     contact_info = self._extract_contact_info(text)
    
#     parsed_data = {
#         'full_text': text,
#         'sections': sections,
#         'contact_info': contact_info,
#         'skills_data': skills_data,
#         'experience_data': experience_data,
#         'education_data': education_data,
#         'projects_data': projects_data,
#         'summary': summary,
#         'word_count': len(text.split()),
#         'character_count': len(text)
#     }
    
#     return parsed_data
    
#     def _extract_text(self, file_path):
#         """Extract text from file"""
#         ext = file_path.rsplit('.', 1)[1].lower()
        
#         if ext == 'txt':
#             with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
#                 return f.read()
#         elif ext == 'pdf':
#             import PyPDF2
#             text = ""
#             with open(file_path, 'rb') as f:
#                 pdf_reader = PyPDF2.PdfReader(f)
#                 for page in pdf_reader.pages:
#                     text += page.extract_text() or ""
#             return text
#         elif ext == 'docx':
#             import docx2txt
#             return docx2txt.process(file_path)
#         else:
#             raise ValueError(f"Unsupported file type: {ext}")
    
#     def _clean_text(self, text):
#         """Clean text while preserving semantic meaning"""
#         # Remove extra whitespace
#         text = re.sub(r'\s+', ' ', text)
        
#         # Remove special characters but keep sentence structure
#         text = re.sub(r'[^\w\s\.\,\-\/\+\#\@\(\)]', '', text)
        
#         return text.strip()
    
#     def _extract_contact_info(self, text):
#         """Extract contact information using patterns"""
#         contact = {
#             'email': None,
#             'phone': None,
#             'linkedin': None,
#             'github': None,
#             'location': None
#         }
        
#         # Email pattern
#         email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
#         emails = re.findall(email_pattern, text)
#         if emails:
#             contact['email'] = emails[0]
        
#         # Phone pattern (simple)
#         phone_pattern = r'\b[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}\b'
#         phones = re.findall(phone_pattern, text)
#         if phones:
#             contact['phone'] = phones[0]
        
#         return contact
    
#     def _extract_education(self, text):
#         """Extract education information"""
#         education = []
        
#         # Education keywords
#         edu_keywords = ['bachelor', 'master', 'phd', 'doctorate', 'b.tech', 'm.tech', 
#                        'b.e', 'm.e', 'b.sc', 'm.sc', 'b.a', 'm.a', 'mba', 'pgdm']
        
#         # Split into sentences
#         sentences = text.split('.')
        
#         for sentence in sentences:
#             sentence_lower = sentence.lower()
#             if any(keyword in sentence_lower for keyword in edu_keywords):
#                 education.append({
#                     'text': sentence.strip(),
#                     'degree': self._extract_degree_type(sentence),
#                     'institution': self._extract_institution(sentence),
#                     'year': self._extract_year(sentence)
#                 })
        
#         return education
    
#     def _extract_degree_type(self, text):
#         """Extract degree type from text"""
#         degree_patterns = {
#             'bachelor': ['bachelor', 'b.tech', 'b.e', 'b.sc', 'b.a'],
#             'master': ['master', 'm.tech', 'm.e', 'm.sc', 'm.a', 'mba'],
#             'doctorate': ['phd', 'doctorate', 'ph.d']
#         }
        
#         text_lower = text.lower()
#         for degree_type, patterns in degree_patterns.items():
#             if any(pattern in text_lower for pattern in patterns):
#                 return degree_type
#         return 'unknown'
    
#     def _extract_institution(self, text):
#         """Extract institution name"""
#         # Look for university/college names
#         inst_patterns = [
#             r'university of [\w\s]+',
#             r'[\w\s]+ university',
#             r'[\w\s]+ college',
#             r'[\w\s]+ institute',
#             r'iit [\w\s]+',
#             r'nit [\w\s]+'
#         ]
        
#         text_lower = text.lower()
#         for pattern in inst_patterns:
#             match = re.search(pattern, text_lower)
#             if match:
#                 return match.group()
        
#         return None
    
#     def _extract_year(self, text):
#         """Extract year from text"""
#         year_pattern = r'\b(19|20)\d{2}\b'
#         years = re.findall(year_pattern, text)
#         return years[0] if years else None
    
#     def _extract_experience(self, text):
#         """Extract experience information"""
#         experience = []
        
#         # Split into sections
#         sections = text.split('\n\n')
        
#         for section in sections:
#             if 'experience' in section.lower() or 'work' in section.lower():
#                 # This section likely contains experience
#                 lines = section.split('\n')
#                 for line in lines:
#                     if line.strip() and len(line) > 20:
#                         experience.append({
#                             'text': line.strip(),
#                             'duration': self._extract_duration(line),
#                             'company': self._extract_company(line),
#                             'role': self._extract_role(line)
#                         })
        
#         return experience
    
#     def _extract_duration(self, text):
#         """Extract duration from text"""
#         # Pattern for date ranges
#         date_pattern = r'(\b\w+\s\d{4})\s*[-–]\s*(\b\w+\s\d{4}|\bpresent\b)'
#         matches = re.findall(date_pattern, text, re.IGNORECASE)
        
#         if matches:
#             return {
#                 'from': matches[0][0],
#                 'to': matches[0][1]
#             }
#         return None
    
#     def _extract_company(self, text):
#         """Extract company name"""
#         # Look for company names (usually proper nouns)
#         words = text.split()
#         for i, word in enumerate(words):
#             if word[0].isupper() and len(word) > 2:
#                 # Potential company name
#                 if i < len(words) - 1 and words[i+1][0].isupper():
#                     return f"{word} {words[i+1]}"
#                 return word
#         return None
    
#     def _extract_role(self, text):
#         """Extract role/job title"""
#         role_keywords = ['engineer', 'developer', 'manager', 'analyst', 'consultant',
#                         'specialist', 'architect', 'lead', 'head', 'director']
        
#         text_lower = text.lower()
#         for keyword in role_keywords:
#             if keyword in text_lower:
#                 # Extract the phrase containing the role
#                 words = text.split()
#                 for i, word in enumerate(words):
#                     if keyword in word.lower():
#                         # Get context (3 words before and after)
#                         start = max(0, i-3)
#                         end = min(len(words), i+4)
#                         return ' '.join(words[start:end])
        
#         return None
    
#     def _extract_projects(self, text):
#         """Extract project information"""
#         projects = []
        
#         # Look for project section
#         if 'project' in text.lower():
#             sections = text.split('\n\n')
#             for section in sections:
#                 if 'project' in section.lower():
#                     lines = section.split('\n')[1:]  # Skip header
#                     for line in lines:
#                         if line.strip() and len(line) > 20:
#                             projects.append(line.strip())
        
#         return projects
    
#     def _extract_certifications(self, text):
#         """Extract certifications"""
#         certifications = []
        
#         cert_keywords = ['certified', 'certification', 'certificate', 'professional']
        
#         sentences = text.split('.')
#         for sentence in sentences:
#             if any(keyword in sentence.lower() for keyword in cert_keywords):
#                 certifications.append(sentence.strip())
        
#         return certifications
    
#     def _extract_languages(self, text):
#         """Extract languages known"""
#         languages = []
        
#         # Common languages
#         lang_list = ['english', 'hindi', 'spanish', 'french', 'german', 'japanese',
#                     'chinese', 'tamil', 'telugu', 'malayalam', 'kannada', 'bengali']
        
#         text_lower = text.lower()
#         for lang in lang_list:
#             if lang in text_lower:
#                 languages.append(lang)
        
#         return languages
    
#     def _extract_summary(self, text):
#         """Extract or generate summary"""
#         # Look for summary/profile section
#         if 'summary' in text.lower() or 'profile' in text.lower():
#             sections = text.split('\n\n')
#             for section in sections:
#                 if 'summary' in section.lower() or 'profile' in section.lower():
#                     return section.strip()
        
#         # If no summary section, use first few sentences
#         sentences = text.split('.')[:3]
#         return '. '.join(sentences)