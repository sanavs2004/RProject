from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import json
from config import Config
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
import threading
from jd_module import generate_job_description, get_all_jds
# Import modules
from modules.resume_upload_handler import ResumeUploadHandler
from modules.resume_processor import ResumeProcessor
from modules.resume_matcher import ResumeMatcher
from modules.resume_analyzer import ResumeAnalyzer
from modules.resume_ranker import ResumeRanker
from modules.resume_feedback import ResumeFeedbackGenerator
# from config import RESUME_FOLDER, JD_FOLDER
# from modules.parser_module import extract_text
# from modules.bias_module import remove_bias
# from modules.skill_module import extract_skills, skill_score
# from modules.semantic_module import semantic_score
# from modules.scoring_module import calculate_final_score
from config import Config

# Add this simple JD Manager class
class JobDescriptionManager:
    def __init__(self, config):
        self.config = config
        self.jobs = [
            {
                'id': 'job1',
                'title': 'Python Developer',
                'department': 'Engineering',
                'raw_description': 'Looking for Python developer',
                'required_skills': ['Python', 'Django']
            }
        ]
    
    def get_all_jobs(self):
        return self.jobs
    
    def get_job_by_id(self, job_id):
        for job in self.jobs:
            if job['id'] == job_id:
                return job
        return None


app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY
CORS(app)

# Use the correct folder names from your config
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.PROCESSED_FOLDER, exist_ok=True)
os.makedirs(Config.RESULTS_FOLDER, exist_ok=True)
# os.makedirs(RESUME_FOLDER, exist_ok=True)
# os.makedirs(JD_FOLDER, exist_ok=True)

# Initialize modules
# Initialize modules - use UNDERSCORES, not spaces!
upload_handler = ResumeUploadHandler(Config)
resume_processor = ResumeProcessor(Config)  # ✅ Correct - with underscore
resume_matcher = ResumeMatcher(Config)      # ✅ Correct - with underscore
resume_analyzer = ResumeAnalyzer(Config)    # ✅ Correct - with underscore
resume_ranker = ResumeRanker(Config)        # ✅ Correct - with underscore
feedback_generator = ResumeFeedbackGenerator(Config)  # ✅ Correct - with underscore
# upload_handler = ResumeUploadHandler(Config)
# resume_processor = ResumeProcessor(Config)
# resume_matcher = ResumeMatcher(Config)
# resume_analyzer = ResumeAnalyzer(Config)
# resume_ranker = ResumeRanker(Config)
# feedback_generator = ResumeFeedbackGenerator(Config)




# Store processing status (in production, use Redis)
processing_status = {}

@app.route('/')
def index():
    return render_template('index.html')


# ==============================
# Generate JD
# ==============================
@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()

        role = data.get('role')
        skills = data.get('skills', '').split(',')
        skills = [s.strip() for s in skills if s.strip()]
        experience = data.get('experience')

        if not role or not skills or not experience:
            return jsonify(success=False, error="Please fill all fields"), 400

        jd_text = generate_job_description(role, skills, experience)

        return jsonify(success=True, jd_text=jd_text)

    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# ==============================
# JD History
# ==============================
@app.route('/history')
def history():
    return jsonify(success=True, jds=get_all_jds())


# ==============================
# Download JD
# ==============================
@app.route('/download/<filename>')
def download(filename):
    path = os.path.join("jd_store", filename)
    if not os.path.exists(path):
        return "File not found", 404
    return send_file(path, as_attachment=True)


@app.route('/resume')
def resume_page():
    """Resume upload page"""
    jobs = jd_manager.get_all_jobs()
    return render_template('resume.html', jobs=jobs)

@app.route('/upload-resume', methods=['POST'])
def upload_resume():
    """Handle resume upload and start processing"""
    try:
        # Generate unique application ID
        application_id = str(uuid.uuid4())
        
        # Get form datacd 
        job_id = request.form.get('job_id')
        candidate_name = request.form.get('candidate_name')
        candidate_email = request.form.get('candidate_email')
        
        if 'resume' not in request.files:
            return jsonify({'error': 'No resume file uploaded'}), 400
        
        file = request.files['resume']
        
        # Validate and save file
        file_path, error = upload_handler.validate_and_save(file, application_id)
        if error:
            return jsonify({'error': error}), 400
        
        # Get job details
        job = jd_manager.get_job_by_id(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        # Initialize status
        processing_status[application_id] = {
            'status': 'uploaded',
            'progress': 10,
            'message': 'Resume uploaded successfully',
            'application_id': application_id
        }
        
        # Start processing in background thread
        thread = threading.Thread(
            target=process_resume_background,
            args=(application_id, file_path, job, candidate_name, candidate_email)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'application_id': application_id,
            'message': 'Resume upload successful. Processing started.'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_resume_background(application_id, file_path, job, candidate_name, candidate_email):
    """Background processing of resume"""
    try:
        # Update status
        processing_status[application_id]['status'] = 'processing'
        processing_status[application_id]['progress'] = 20
        processing_status[application_id]['message'] = 'Parsing resume...'
        
        # Step 1: Parse resume
        parsed_data = resume_processor.parse_resume(file_path)
        
        processing_status[application_id]['progress'] = 40
        processing_status[application_id]['message'] = 'Extracting skills semantically...'
        
        # Step 2: Extract skills using semantic understanding
        skills_data = resume_analyzer.extract_skills_semantic(parsed_data['full_text'])
        
        processing_status[application_id]['progress'] = 50
        processing_status[application_id]['message'] = 'Analyzing experience...'
        
        # Step 3: Analyze experience
        experience_data = resume_analyzer.analyze_experience(parsed_data['full_text'])
        
        processing_status[application_id]['progress'] = 60
        processing_status[application_id]['message'] = 'Performing BERT semantic matching...'
        
        # Step 4: BERT-based semantic matching
        semantic_match = resume_matcher.compute_semantic_similarity(
            parsed_data['full_text'],
            job['raw_description']
        )
        
        processing_status[application_id]['progress'] = 70
        processing_status[application_id]['message'] = 'Calculating skill relevance...'
        
        # Step 5: Calculate skill relevance
        skill_relevance = resume_matcher.compute_skill_relevance(
            skills_data['skills'],
            job['required_skills']
        )
        
        processing_status[application_id]['progress'] = 80
        processing_status[application_id]['message'] = 'Generating scores and ranking...'
        
        # Step 6: Generate comprehensive scores
        scores = resume_ranker.calculate_comprehensive_score(
            semantic_match=semantic_match,
            skill_relevance=skill_relevance,
            experience_data=experience_data,
            job_requirements=job
        )
        
        # Step 7: Rank and generate feedback
        ranking = resume_ranker.rank_candidate(scores, job)
        
        processing_status[application_id]['progress'] = 90
        processing_status[application_id]['message'] = 'Generating feedback...'
        
        # Step 8: Generate feedback
        if ranking['decision'] == 'reject':
            feedback = feedback_generator.generate_rejection_feedback(
                skills_data=skills_data,
                job_requirements=job,
                scores=scores
            )
        else:
            feedback = feedback_generator.generate_positive_feedback(scores)
        
        # Step 9: Save results
        results = {
            'application_id': application_id,
            'candidate_name': candidate_name,
            'candidate_email': candidate_email,
            'job_title': job['title'],
            'job_id': job['id'],
            'parsed_data': parsed_data,
            'skills_data': skills_data,
            'experience_data': experience_data,
            'semantic_match': semantic_match,
            'skill_relevance': skill_relevance,
            'scores': scores,
            'ranking': ranking,
            'feedback': feedback,
            'processed_at': datetime.now().isoformat()
        }
        
        # Save to file
        results_path = os.path.join(Config.RESULTS_FOLDER, f"{application_id}.json")
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Update status
        processing_status[application_id].update({
            'status': 'completed',
            'progress': 100,
            'message': 'Processing complete',
            'results': {
                'overall_score': scores['overall'],
                'decision': ranking['decision'],
                'summary': feedback['summary']
            }
        })
        
    except Exception as e:
        processing_status[application_id].update({
            'status': 'failed',
            'progress': 0,
            'message': f'Processing failed: {str(e)}',
            'error': str(e)
        })
        print(f"Error processing resume {application_id}: {str(e)}")

@app.route('/resume-status/<application_id>')
def resume_status(application_id):
    """Get processing status"""
    status = processing_status.get(application_id, {
        'status': 'not_found',
        'message': 'Application not found'
    })
    return jsonify(status)

@app.route('/resume-results/<application_id>')
def resume_results(application_id):
    """Show detailed results"""
    results_path = os.path.join(Config.RESULTS_FOLDER, f"{application_id}.json")
    
    if not os.path.exists(results_path):
        return render_template('error.html', message='Results not found'), 404
    
    with open(results_path, 'r') as f:
        results = json.load(f)
    
    return render_template('resume_results.html', results=results)

@app.route('/api/candidate-ranking/<job_id>')
def candidate_ranking(job_id):
    """Get ranked candidates for a job"""
    # Load all results for this job
    rankings = []
    
    for filename in os.listdir(Config.RESULTS_FOLDER):
        if filename.endswith('.json'):
            with open(os.path.join(Config.RESULTS_FOLDER, filename), 'r') as f:
                result = json.load(f)
                if result['job_id'] == job_id:
                    rankings.append({
                        'application_id': result['application_id'],
                        'candidate_name': result['candidate_name'],
                        'overall_score': result['scores']['overall'],
                        'decision': result['ranking']['decision'],
                        'processed_at': result['processed_at']
                    })
    
    # Sort by score descending
    rankings.sort(key=lambda x: x['overall_score'], reverse=True)
    
    return jsonify(rankings)



# -------- Upload JD --------
# @app.route("/upload_jd", methods=["POST"])
# def upload_jd():
#     file = request.files["jd"]
#     path = os.path.join(JD_FOLDER, file.filename)
#     file.save(path)
#     return jsonify({"message": "JD uploaded"})


# # -------- Upload & Process Resumes --------
# @app.route("/process_resumes", methods=["POST"])
# def process_resumes():
#     jd_file = request.form["jd_name"]
#     jd_path = os.path.join(JD_FOLDER, jd_file)

#     jd_text = extract_text(jd_path)
#     jd_skills = extract_skills(jd_text)

#     results = []

#     files = request.files.getlist("resumes")

#     for file in files:
#         resume_path = os.path.join(RESUME_FOLDER, file.filename)
#         file.save(resume_path)

#         resume_text = extract_text(resume_path)
#         clean_text = remove_bias(resume_text)

#         resume_skills = extract_skills(clean_text)

#         sem_score = semantic_score(jd_text, clean_text)
#         skill_sc, missing = skill_score(jd_skills, resume_skills)

#         final = calculate_final_score(sem_score, skill_sc)

#         results.append({
#             "name": file.filename,
#             "semantic_score": sem_score,
#             "skill_score": skill_sc,
#             "final_score": final,
#             "missing_skills": missing
#         })

#     # Rank
#     results = sorted(results, key=lambda x: x["final_score"], reverse=True)

#     return jsonify(results)


if __name__ == '__main__':
    os.makedirs("jd_store", exist_ok=True)
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(Config.PROCESSED_FOLDER, exist_ok=True)
    os.makedirs(Config.RESULTS_FOLDER, exist_ok=True)

    
    app.run(debug=True, use_reloader=False, port=5000)
