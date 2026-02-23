from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import uuid
from datetime import datetime
from config import Config

# Import JD module
from jd_module import generate_job_description, get_all_jds

# Import Resume Screening modules
from modules.resume_screening import ResumeScreeningEngine
from modules.semantic_parser import SemanticParser
from modules.semantic_matcher import SemanticMatcher
from modules.semantic_ranker import SemanticRanker
from modules.skill_extractor import SkillExtractor

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# Initialize modules
screening_engine = ResumeScreeningEngine(Config)
semantic_parser = SemanticParser()
semantic_matcher = SemanticMatcher()
semantic_ranker = SemanticRanker()
skill_extractor = SkillExtractor()

# Store processing status (optional - can be removed if not needed)
processing_status = {}

# Ensure directories exist
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.RESULTS_FOLDER, exist_ok=True)
os.makedirs(Config.JD_STORE_FOLDER, exist_ok=True)


# ======================
# HOME ROUTE
# ======================
@app.route('/')
def index():
    """Recruiter Dashboard"""
    recent_screenings = screening_engine.get_all_screenings()[:5]
    recent_jds = get_all_jds()[:5]
    
    return render_template('recruiter_dashboard.html', 
                         recent_screenings=recent_screenings,
                         recent_jds=recent_jds)


# ======================
# JD MODULE ROUTES
# ======================
@app.route('/generate-jd', methods=['GET', 'POST'])
def generate_jd():
    """Generate job description using JD module"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        role = data.get('role')
        skills_input = data.get('skills', '')
        experience = data.get('experience')
        
        # Parse skills (handle both string and list)
        if isinstance(skills_input, str):
            skills = [s.strip() for s in skills_input.split(',') if s.strip()]
        else:
            skills = skills_input
        
        if not role or not skills or not experience:
            return jsonify({
                'success': False, 
                'error': 'Please fill all fields'
            }), 400
        
        try:
            # Generate JD using your module
            jd_text = generate_job_description(role, skills, experience)
            
            return jsonify({
                'success': True, 
                'jd_text': jd_text,
                'message': 'Job description generated successfully'
            })
            
        except Exception as e:
            return jsonify({
                'success': False, 
                'error': str(e)
            }), 500
    
    # GET request - show form
    return render_template('jd.html')


@app.route('/jd-history')
def jd_history():
    """View all generated job descriptions"""
    jds = get_all_jds()
    return render_template('jd_history.html', jds=jds)


@app.route('/jd/<filename>')
def view_jd(filename):
    """View a specific job description"""
    import os
    filepath = os.path.join(Config.JD_STORE_FOLDER, filename)
    
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return render_template('view_jd.html', filename=filename, content=content)
    
    return render_template('error.html', message='JD not found'), 404
@app.route('/api/jd/<filename>')
def get_jd_content(filename):
    """Get JD content for preview - handles both text and binary files"""
    import os
    filepath = os.path.join(Config.JD_STORE_FOLDER, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        # Try to read as text first
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'content': content})
    except UnicodeDecodeError:
        # If it's a binary file, return a message
        return jsonify({'content': f'[Binary file: {filename}. Preview not available.]'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    


# ======================
# RESUME SCREENING ROUTES
# ======================
@app.route('/screen-candidates', methods=['GET', 'POST'])
def screen_candidates():
    """Screen candidates using semantic understanding"""
    if request.method == 'POST':
        try:
            # Get form data
            jd_option = request.form.get('jd_option', 'new')
            job_title = request.form.get('job_title', 'Custom Job')
            jd_text = ""
            
            # Handle JD input
            if jd_option == 'existing':
                # Get from existing JD file
                jd_file = request.files.get('jd_file')
                if jd_file and jd_file.filename:
                    jd_text = jd_file.read().decode('utf-8')
                    # Get job title from filename if not provided
                    if not job_title or job_title == 'Custom Job':
                        job_title = os.path.splitext(jd_file.filename)[0]
            else:
                # Use textarea input
                jd_text = request.form.get('jd_text', '').strip()
            
            if not jd_text:
                return jsonify({
                    'success': False, 
                    'error': 'Job description is required'
                }), 400
            
            # Get resume files
            resume_files = request.files.getlist('resumes')
            
            # Filter out empty files
            resume_files = [f for f in resume_files if f and f.filename]
            
            if not resume_files:
                return jsonify({
                    'success': False, 
                    'error': 'Please upload at least one resume'
                }), 400
            
            # Run semantic screening
            screening_id, results = screening_engine.screen_resumes(
                jd_text=jd_text,
                resume_files=resume_files,
                job_title=job_title
            )
            
            return jsonify({
                'success': True,
                'screening_id': screening_id,
                'redirect': f'/ranking-results/{screening_id}',
                'message': f'✅ Processed {len(results["candidates"])} resumes with semantic understanding',
                'candidates_count': len(results["candidates"])
            })
            
        except Exception as e:
            print(f"Error in screening: {e}")
            return jsonify({
                'success': False, 
                'error': str(e)
            }), 500
    
    # GET request - show screening form
    recent_jds = get_all_jds()[:10]
    return render_template('screen_candidates.html', recent_jds=recent_jds)


@app.route('/ranking-results/<screening_id>')
def ranking_results(screening_id):
    """Show semantic ranking results"""
    result = screening_engine.get_screening_result(screening_id)
    
    if not result:
        return render_template('error.html', message='Screening results not found'), 404
    
    return render_template('ranking_results.html',
                         results=result,
                         job=result['job'],
                         candidates=result['candidates'])


@app.route('/screening-history')
def screening_history():
    """View all screenings"""
    screenings = screening_engine.get_all_screenings()
    return render_template('screening_history.html', screenings=screenings)


@app.route('/screening-status/<screening_id>')
def screening_status(screening_id):
    """Get screening status (for AJAX polling)"""
    # Check if results exist
    result = screening_engine.get_screening_result(screening_id)
    
    if result:
        return jsonify({
            'status': 'completed',
            'progress': 100,
            'redirect': f'/ranking-results/{screening_id}'
        })
    
    # Check if still processing
    status = processing_status.get(screening_id, {
        'status': 'processing',
        'progress': 50,
        'message': 'Processing resumes...'
    })
    
    return jsonify(status)


@app.route('/api/screening/<screening_id>')
def api_screening(screening_id):
    """API endpoint to get screening results as JSON"""
    result = screening_engine.get_screening_result(screening_id)
    
    if result:
        return jsonify(result)
    
    return jsonify({'error': 'Not found'}), 404


@app.route('/api/jds')
def api_jds():
    """API endpoint to get all JDs"""
    jds = get_all_jds()
    return jsonify(jds)


# ======================
# CANDIDATE DETAILS (Optional)
# ======================
@app.route('/candidate/<candidate_id>')
def candidate_details(candidate_id):
    """View candidate details (placeholder)"""
    # Find candidate in any screening result
    screenings = screening_engine.get_all_screenings()
    
    for screening in screenings:
        result = screening_engine.get_screening_result(screening['id'])
        if result:
            for candidate in result.get('candidates', []):
                if candidate.get('candidate_id') == candidate_id:
                    return render_template('candidate_detail.html', 
                                         candidate=candidate,
                                         job=result['job'])
    
    return render_template('error.html', message='Candidate not found'), 404


# ======================
# ERROR HANDLERS
# ======================
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', message='Page not found'), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', message='Internal server error'), 500


# ======================
# MAIN ENTRY POINT
# ======================
if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 RecruitAI - AI-Powered Recruitment Platform")
    print("="*60)
    print(f"📋 JD Module: Connected to Ollama (phi3)")
    print(f"🧠 Semantic Module: Using Sentence Transformers")
    print(f"📍 Upload folder: {Config.UPLOAD_FOLDER}")
    print(f"📍 Results folder: {Config.RESULTS_FOLDER}")
    print(f"📍 JD Store: {Config.JD_STORE_FOLDER}")
    print("\n🌐 Access the application:")
    print("   http://localhost:5001")
    print("\n📌 Recruiter Workflow:")
    print("   1. Generate JD → /generate-jd")
    print("   2. Screen Candidates → /screen-candidates")
    print("   3. View Rankings → /ranking-results/<id>")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5001)