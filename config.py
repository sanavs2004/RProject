import os

class Config:
    # Base directory
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Secret key
    SECRET_KEY = 'dev-secret-key-change-in-production'
    
    # Upload folders
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'resume_store', 'uploads')
    RESULTS_FOLDER = os.path.join(BASE_DIR, 'resume_store', 'results')
    JD_STORE_FOLDER = os.path.join(BASE_DIR, 'jd_store')
    
    # Create directories if they don't exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    os.makedirs(JD_STORE_FOLDER, exist_ok=True)
    
    # File upload settings
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size