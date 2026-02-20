import os
import re
from werkzeug.utils import secure_filename
from datetime import datetime

class ResumeUploadHandler:
    """Handles resume file upload, validation, and storage"""
    
    def __init__(self, config):
        self.config = config
        self.upload_folder = config.UPLOAD_FOLDER
        self.allowed_extensions = config.ALLOWED_EXTENSIONS
        self.max_file_size = config.MAX_FILE_SIZE
        
    def validate_and_save(self, file, application_id):
        """
        Validate and save uploaded resume file
        Returns: (file_path, error_message)
        """
        # Check if file exists
        if not file:
            return None, "No file provided"
        
        # Check filename
        if file.filename == '':
            return None, "No file selected"
        
        # Check file extension
        if not self._allowed_file(file.filename):
            return None, f"File type not allowed. Allowed: {', '.join(self.allowed_extensions)}"
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > self.max_file_size:
            return None, f"File too large. Max size: {self.max_file_size // (1024*1024)}MB"
        
        # Secure filename and save
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower()
        
        # Create unique filename with application_id
        new_filename = f"{application_id}.{ext}"
        file_path = os.path.join(self.upload_folder, new_filename)
        
        # Save file
        file.save(file_path)
        
        return file_path, None
    
    def _allowed_file(self, filename):
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def extract_text_from_file(self, file_path):
        """Extract text content from file based on extension"""
        ext = file_path.rsplit('.', 1)[1].lower()
        
        if ext == 'txt':
            return self._extract_from_txt(file_path)
        elif ext == 'pdf':
            return self._extract_from_pdf(file_path)
        elif ext == 'docx':
            return self._extract_from_docx(file_path)
        else:
            return None
    
    def _extract_from_txt(self, file_path):
        """Extract text from TXT file"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    def _extract_from_pdf(self, file_path):
        """Extract text from PDF file"""
        try:
            import PyPDF2
            text = ""
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text += page.extract_text() or ""
            return text
        except ImportError:
            return "PDF extraction requires PyPDF2. Install with: pip install PyPDF2"
        except Exception as e:
            return f"Error extracting PDF: {str(e)}"
    
    def _extract_from_docx(self, file_path):
        """Extract text from DOCX file"""
        try:
            import docx2txt
            return docx2txt.process(file_path)
        except ImportError:
            return "DOCX extraction requires docx2txt. Install with: pip install docx2txt"
        except Exception as e:
            return f"Error extracting DOCX: {str(e)}"