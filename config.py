# import os

# class Config:
#     # Base directory
#     BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
#     # Secret key
#     SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
#     # Upload folders
#     UPLOAD_FOLDER = os.path.join(BASE_DIR, 'resume_store', 'uploads')
#     PROCESSED_FOLDER = os.path.join(BASE_DIR, 'resume_store', 'processed')
#     RESULTS_FOLDER = os.path.join(BASE_DIR, 'resume_store', 'results')
    
#     # Create directories if they don't exist
#     os.makedirs(UPLOAD_FOLDER, exist_ok=True)
#     os.makedirs(PROCESSED_FOLDER, exist_ok=True)
#     os.makedirs(RESULTS_FOLDER, exist_ok=True)
    
#     # File upload settings
#     ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}
#     MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
#     # Model paths
#     MODELS_FOLDER = os.path.join(BASE_DIR, 'models')
#     FINE_TUNED_MODEL_PATH = os.path.join(MODELS_FOLDER, 'fine_tuned_model')
#     SKILL_EXTRACTOR_PATH = os.path.join(MODELS_FOLDER, 'skill_extractor_model')
    
#     # Scoring weights
#     SCORE_WEIGHTS = {
#         'semantic': 0.4,
#         'skills': 0.3,
#         'experience': 0.2,
#         'education': 0.1
#     }
    
#     # Decision thresholds
#     THRESHOLDS = {
#         'shortlist': 80,
#         'interview': 70,
#         'reject': 60
#     }
    
#     # Processing limits
#     MAX_RESUME_LENGTH = 10000  # Max characters to process
#     MAX_SENTENCES_FOR_ANALYSIS = 50

import os

class Config:
    # Base directory
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Secret key
    SECRET_KEY = 'dev-secret-key'
    
    # Upload folders
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'resume_store', 'uploads')
    PROCESSED_FOLDER = os.path.join(BASE_DIR, 'resume_store', 'processed')
    RESULTS_FOLDER = os.path.join(BASE_DIR, 'resume_store', 'results')
    
    # Create directories
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(PROCESSED_FOLDER, exist_ok=True)
    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    
    # File upload settings
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}
    MAX_FILE_SIZE = 5 * 1024 * 1024
    
    # Model paths (use pre-trained for now)
    MODEL_NAME = 'bert-base-uncased'  # Use this instead of fine-tuned path
    
    # Scoring weights
    SCORE_WEIGHTS = {
        'semantic': 0.4,
        'skills': 0.3,
        'experience': 0.2,
        'education': 0.1
    }
    
    # Decision thresholds
    THRESHOLDS = {
        'shortlist': 80,
        'interview': 70,
        'reject': 60
    }