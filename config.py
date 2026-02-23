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
    
    # New folders for enhanced features
    ANALYTICS_FOLDER = os.path.join(BASE_DIR, 'analytics')
    LEARNING_PATHS_FOLDER = os.path.join(BASE_DIR, 'learning_paths')
    
    # Create all directories
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    os.makedirs(JD_STORE_FOLDER, exist_ok=True)
    os.makedirs(ANALYTICS_FOLDER, exist_ok=True)
    os.makedirs(LEARNING_PATHS_FOLDER, exist_ok=True)
    
    # File upload settings
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    MAX_RESUMES_PER_BATCH = 10  # Allow up to 10 resumes per screening
    
    # Ollama settings
    OLLAMA_URL = "http://localhost:11434/api/generate"
    OLLAMA_MODEL = "phi3"