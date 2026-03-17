from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
import uuid
import json
from datetime import datetime, timedelta
from config import Config
# Import JD module
from jd_module import generate_job_description, get_all_jds
from modules.interview_scheduler import InterviewScheduler
from flask import send_file, abort
import os
import glob

# Import Resume Screening modules
from modules.resume_screening import ResumeScreeningEngine
from modules.semantic_parser import SemanticParser
from modules.semantic_matcher import SemanticMatcher
from modules.semantic_ranker import SemanticRanker
from modules.skill_extractor import SkillExtractor
from modules.learning_path_generator import LearningPathGenerator
from modules.learning_path_emailer import send_learning_path_email
from modules.fit_predictor import FitPredictor
from apscheduler.schedulers.background import BackgroundScheduler
from auto_screener import auto_screener
from analytics_engine import analytics_engine

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# Initialize modules
screening_engine = ResumeScreeningEngine(Config)
semantic_parser = SemanticParser()
semantic_matcher = SemanticMatcher()
semantic_ranker = SemanticRanker()
skill_extractor = SkillExtractor()
interview_scheduler = InterviewScheduler(Config)  # Moved here
learning_path_gen = LearningPathGenerator(Config)
fit_predictor = FitPredictor(os.path.join(Config.BASE_DIR, 'models'))
scheduler = BackgroundScheduler()

# Store processing status
processing_status = {}

# Ensure directories exist
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.RESULTS_FOLDER, exist_ok=True)
os.makedirs(Config.JD_STORE_FOLDER, exist_ok=True)


 
# Run every hour
scheduler.add_job(
    func    = auto_screener.check_and_process_deadlines,
    trigger = 'interval',
    hours   = 1,
    id      = 'auto_screener',
    name    = 'Auto Screen after Deadline',
    replace_existing = True
)
 
# Also run once at startup (after 10 seconds) to catch any missed deadlines
scheduler.add_job(
    func    = auto_screener.check_and_process_deadlines,
    trigger = 'date',
    run_date = datetime.now() + timedelta(seconds=10),
    id       = 'startup_check',
    name     = 'Startup deadline check'
)
 
scheduler.start()
print("✅ AutoScreener scheduler started — checking deadlines every hour.")
 
 


# ======================
# HOME ROUTE
# ======================
@app.route('/')
def index():
    """Recruiter Dashboard with interview data"""
    try:
        # Get recent screenings
        recent_screenings = screening_engine.get_all_screenings()[:5]
        
        # Get scheduled interviews
        all_interviews = interview_scheduler.get_scheduled_interviews()
        
        # Calculate stats
        total_screenings = len(screening_engine.get_all_screenings())
        
        # Count shortlisted candidates (score >= 65)
        shortlisted_count = 0
        screenings = screening_engine.get_all_screenings()[:10]
        for s in screenings:
            try:
                result = screening_engine.get_screening_result(s['id'])
                if result and result.get('candidates'):
                    shortlisted = [c for c in result['candidates'] if c.get('overall_score', 0) >= 65]
                    shortlisted_count += len(shortlisted)
            except:
                pass
        
        # Count pending invites
        pending_invites = 0
        invitations_folder = os.path.join(Config.BASE_DIR, 'interviews', 'invitations')
        if os.path.exists(invitations_folder):
            for file in os.listdir(invitations_folder):
                if file.endswith('.json'):
                    try:
                        with open(os.path.join(invitations_folder, file), 'r') as f:
                            inv = json.load(f)
                            if inv.get('status') == 'sent':
                                pending_invites += 1
                    except:
                        pass
        
        # Today's date calculations
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        # Filter today's and tomorrow's interviews
        today_interviews = []
        tomorrow_interviews = []
        
        for interview in all_interviews:
            try:
                interview_date = datetime.fromisoformat(interview['slot']['date']).date()
                if interview_date == today:
                    today_interviews.append(interview)
                elif interview_date == tomorrow:
                    tomorrow_interviews.append(interview)
            except:
                pass
        
        # Sort interviews by time
        today_interviews.sort(key=lambda x: x['slot']['start_time'])
        tomorrow_interviews.sort(key=lambda x: x['slot']['start_time'])
        
        return render_template('recruiter_dashboard.html',
                             total_screenings=total_screenings,
                             shortlisted_count=shortlisted_count,
                             scheduled_interviews=len(all_interviews),
                             pending_invites=pending_invites,
                             recent_screenings=recent_screenings,
                             today_interviews=today_interviews,
                             tomorrow_interviews=tomorrow_interviews)
    
    except Exception as e:
        print(f"Dashboard error: {e}")
        return render_template('recruiter_dashboard.html',
                             total_screenings=0,
                             shortlisted_count=0,
                             scheduled_interviews=0,
                             pending_invites=0,
                             recent_screenings=[],
                             today_interviews=[],
                             tomorrow_interviews=[])


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
        
        if isinstance(skills_input, str):
            skills = [s.strip() for s in skills_input.split(',') if s.strip()]
        else:
            skills = skills_input
        
        if not role or not skills or not experience:
            return jsonify({'success': False, 'error': 'Please fill all fields'}), 400
        
        try:
            jd_text = generate_job_description(role, skills, experience)
            return jsonify({'success': True, 'jd_text': jd_text, 'message': 'Job description generated successfully'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return render_template('jd.html')


@app.route('/jd-history')
def jd_history():
    """View all generated job descriptions"""
    jds = get_all_jds()
    return render_template('jd_history.html', jds=jds)


@app.route('/jd/<filename>')
def view_jd(filename):
    """View a specific job description"""
    filepath = os.path.join(Config.JD_STORE_FOLDER, filename)
    
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return render_template('view_jd.html', filename=filename, content=content)
    
    return render_template('error.html', message='JD not found'), 404


@app.route('/api/recent-jds')
def api_recent_jds():
    """API endpoint to get recent JDs with display names"""
    from jd_module import STORE_FOLDER
    
    jds = []
    if os.path.exists(STORE_FOLDER):
        for file in os.listdir(STORE_FOLDER):
            if file.endswith('.txt'):
                filepath = os.path.join(STORE_FOLDER, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if file == "latest_jd.txt":
                        display_name = "Latest JD"
                    else:
                        name_part = file.replace('jd_', '').replace('.txt', '')
                        parts = name_part.split('_')
                        
                        if len(parts) > 1 and parts[-1].isdigit() and len(parts[-1]) == 14:
                            display_name = ' '.join(parts[:-1])
                        else:
                            display_name = ' '.join(parts)
                    
                    jds.append({
                        'filename': file,
                        'display_name': display_name,
                        'content': content[:200] + '...'
                    })
                except Exception as e:
                    print(f"Error reading {file}: {e}")
        
        jds.sort(key=lambda x: x['filename'], reverse=True)
    
    return jsonify(jds)


@app.route('/api/jd/<filename>')
def api_jd_content(filename):
    """Get full JD content for preview"""
    from jd_module import STORE_FOLDER
    
    filepath = os.path.join(STORE_FOLDER, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'content': content})
    return jsonify({'error': 'File not found'}), 404


# ======================
# RESUME SCREENING ROUTES
# ======================
@app.route('/screen-candidates', methods=['GET', 'POST'])
def screen_candidates():
    """Screen candidates using semantic understanding"""
    if request.method == 'POST':
        try:
            jd_option = request.form.get('jd_option', 'new')
            job_title = request.form.get('job_title', 'Custom Job')
            jd_text = ""
            
            if jd_option == 'existing':
                recent_jd = request.form.get('recent_jd')
                if recent_jd:
                    jd_path = os.path.join(Config.JD_STORE_FOLDER, recent_jd)
                    if os.path.exists(jd_path):
                        with open(jd_path, 'r', encoding='utf-8') as f:
                            jd_text = f.read()
                        job_title = recent_jd.replace('jd_', '').replace('.txt', '')
                        if '_' in job_title:
                            parts = job_title.split('_')
                            if len(parts) > 1 and parts[-1].isdigit():
                                job_title = ' '.join(parts[:-1])
                            else:
                                job_title = ' '.join(parts)
                
                jd_file = request.files.get('jd_file')
                if jd_file and jd_file.filename:
                    jd_text = jd_file.read().decode('utf-8')
                    if not job_title or job_title == 'Custom Job':
                        job_title = os.path.splitext(jd_file.filename)[0]
            else:
                jd_text = request.form.get('jd_text', '').strip()
                job_title = request.form.get('job_title', 'Custom Job')
            
            if not jd_text:
                return jsonify({'success': False, 'error': 'Job description is required'}), 400
            
            resume_files = request.files.getlist('resumes')
            resume_files = [f for f in resume_files if f and f.filename]
            
            if not resume_files:
                return jsonify({'success': False, 'error': 'Please upload at least one resume'}), 400
            
            screening_id, results = screening_engine.screen_resumes(
                jd_text=jd_text,
                resume_files=resume_files,
                job_title=job_title
            )
            
            return jsonify({
                'success': True,
                'screening_id': screening_id,
                'redirect': f'/ranking-results/{screening_id}',
                'message': f'✅ Processed {len(results["candidates"])} resumes'
            })
            
        except Exception as e:
            print(f"Error in screening: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    recent_jds = screening_engine.get_recent_jds() if hasattr(screening_engine, 'get_recent_jds') else []
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
    result = screening_engine.get_screening_result(screening_id)
    
    if result:
        return jsonify({
            'status': 'completed',
            'progress': 100,
            'redirect': f'/ranking-results/{screening_id}'
        })
    
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

@app.route('/learning-path/<candidate_id>')
def learning_path(candidate_id):
    """
    Show the personalised learning path PAGE for a candidate.
    Linked from the ranking results page via the 📚 button.
    """
    # Try to load an already-generated path first (saved from screening)
    existing = learning_path_gen.get_learning_path(candidate_id)
    if existing:
        return render_template('learning_path.html', learning_path=existing)

    # Not generated yet — find candidate and generate now
    screenings = screening_engine.get_all_screenings()
    for screening in screenings:
        result = screening_engine.get_screening_result(screening['id'])
        if result:
            for candidate in result.get('candidates', []):
                if candidate.get('candidate_id') == candidate_id:
                    lp = learning_path_gen.generate(candidate, result['job'])
                    return render_template('learning_path.html', learning_path=lp)

    return render_template('error.html', message='Candidate not found'), 404


@app.route('/api/resend-learning-path/<candidate_id>', methods=['POST'])
def resend_learning_path(candidate_id):
    """
    Recruiter manually re-sends the learning path email for a candidate.
    Called from the ranking results page via a button.
    """
    screenings = screening_engine.get_all_screenings()
    for screening in screenings:
        result = screening_engine.get_screening_result(screening['id'])
        if result:
            for candidate in result.get('candidates', []):
                if candidate.get('candidate_id') == candidate_id:
                    # Get or generate learning path
                    lp = learning_path_gen.get_learning_path(candidate_id)
                    if not lp:
                        lp = learning_path_gen.generate(candidate, result['job'])

                    # Send email
                    sent = send_learning_path_email(candidate, result['job'], lp, Config)
                    return jsonify({
                        'success': sent,
                        'message': f"Learning path emailed to {candidate.get('email')}" if sent
                                   else 'Failed to send — check SMTP settings or candidate has no email'
                    })

    return jsonify({'success': False, 'error': 'Candidate not found'}), 404


@app.route('/api/learning-path/<candidate_id>')
def api_get_learning_path(candidate_id):
    """
    Returns the learning path JSON for a candidate.
    Useful for debugging or future frontend use.
    """
    lp = learning_path_gen.get_learning_path(candidate_id)
    if lp:
        return jsonify(lp)
    return jsonify({'error': 'Learning path not found'}), 404

@app.route('/api/ml-model-info')
def api_ml_model_info():
    """Returns ML model metadata — accuracy, training info etc."""
    return jsonify(fit_predictor.get_model_info())


@app.route('/api/retrain-model', methods=['POST'])
def api_retrain_model():
    """Force retrain the XGBoost+SVM model with fresh synthetic data."""
    try:
        info = fit_predictor.retrain()
        return jsonify({
            'success': True,
            'message': f"Model retrained! Accuracy: {info.get('ensemble_accuracy')}%",
            'info': info
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    


# ════════════════════════════════════════════════════════════════
#  FEATURE 1 PATCH — Add these routes to app.py
#  Paste BEFORE the error handlers section
# ════════════════════════════════════════════════════════════════

@app.route('/jd-share/<filename>')
def jd_share(filename):
    """Public shareable JD page — anyone with the link can view and apply."""
    filepath = os.path.join(Config.JD_STORE_FOLDER, filename)

    if not os.path.exists(filepath):
        return render_template('error.html', message='Job posting not found'), 404

    with open(filepath, 'r', encoding='utf-8') as f:
        jd_content = f.read()

    # Build a clean job title from filename
    name_part = filename.replace('jd_', '').replace('.txt', '')
    parts = name_part.split('_')
    if len(parts) > 1 and parts[-1].isdigit() and len(parts[-1]) == 14:
        job_title = ' '.join(parts[:-1]).title()
    else:
        job_title = ' '.join(parts).title()

    # Get file creation time as posted date
    created_ts = os.path.getctime(filepath)
    posted_date = datetime.fromtimestamp(created_ts).strftime('%d %b %Y')

    # Check for deadline stored in meta file
    meta_path = filepath.replace('.txt', '_meta.json')
    deadline = None
    deadline_passed = False
    if os.path.exists(meta_path):
        with open(meta_path, 'r') as f:
            meta = json.load(f)
        deadline = meta.get('deadline')
        if deadline:
            try:
                dl_date = datetime.strptime(deadline, '%Y-%m-%d').date()
                deadline_passed = dl_date < datetime.now().date()
                deadline = dl_date.strftime('%d %b %Y')
            except:
                pass

    return render_template('jd_share.html',
                           filename=filename,
                           job_title=job_title,
                           jd_content=jd_content,
                           posted_date=posted_date,
                           deadline=deadline,
                           deadline_passed=deadline_passed)


@app.route('/apply/<filename>')
def apply_portal(filename):
    """Candidate self-upload portal for a specific JD."""
    filepath = os.path.join(Config.JD_STORE_FOLDER, filename)

    if not os.path.exists(filepath):
        return render_template('error.html', message='Job posting not found'), 404

    # Check deadline
    meta_path = filepath.replace('.txt', '_meta.json')
    deadline_passed = False
    if os.path.exists(meta_path):
        with open(meta_path, 'r') as f:
            meta = json.load(f)
        deadline = meta.get('deadline')
        if deadline:
            try:
                dl_date = datetime.strptime(deadline, '%Y-%m-%d').date()
                deadline_passed = dl_date < datetime.now().date()
            except:
                pass

    if deadline_passed:
        return render_template('error.html', message='Applications for this position are closed.'), 403

    # Build job title
    name_part = filename.replace('jd_', '').replace('.txt', '')
    parts = name_part.split('_')
    if len(parts) > 1 and parts[-1].isdigit() and len(parts[-1]) == 14:
        job_title = ' '.join(parts[:-1]).title()
    else:
        job_title = ' '.join(parts).title()

    return render_template('apply.html',
                           filename=filename,
                           job_title=job_title)


@app.route('/api/candidate-apply', methods=['POST'])
def api_candidate_apply():
    """
    Handles candidate self-application.
    Saves resume to uploads folder with candidate name + email injected.
    """
    try:
        candidate_name  = request.form.get('candidate_name', '').strip()
        candidate_email = request.form.get('candidate_email', '').strip()
        jd_filename     = request.form.get('jd_filename', '').strip()
        resume_file     = request.files.get('resume')

        # Validate
        if not candidate_name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        if not candidate_email or '@' not in candidate_email:
            return jsonify({'success': False, 'error': 'Valid email is required'}), 400
        if not resume_file or not resume_file.filename:
            return jsonify({'success': False, 'error': 'Resume file is required'}), 400

        ext = os.path.splitext(resume_file.filename)[1].lower()
        if ext not in ['.pdf', '.docx']:
            return jsonify({'success': False, 'error': 'Only PDF or DOCX files are accepted'}), 400

        # Check deadline
        jd_path = os.path.join(Config.JD_STORE_FOLDER, jd_filename)
        meta_path = jd_path.replace('.txt', '_meta.json')
        if os.path.exists(meta_path):
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            deadline = meta.get('deadline')
            if deadline:
                try:
                    dl_date = datetime.strptime(deadline, '%Y-%m-%d').date()
                    if dl_date < datetime.now().date():
                        return jsonify({'success': False, 'error': 'Application deadline has passed'}), 403
                except:
                    pass

        # Save resume with candidate_id prefix
        candidate_id = str(uuid.uuid4())[:8]
        safe_name    = candidate_name.lower().replace(' ', '_')
        save_name    = f"{candidate_id}_{safe_name}{ext}"
        save_path    = os.path.join(Config.UPLOAD_FOLDER, save_name)
        resume_file.save(save_path)

        # Save application metadata so recruiter can see who applied
        applications_folder = os.path.join(Config.BASE_DIR, 'applications')
        os.makedirs(applications_folder, exist_ok=True)

        application = {
            'candidate_id'   : candidate_id,
            'candidate_name' : candidate_name,
            'candidate_email': candidate_email,
            'jd_filename'    : jd_filename,
            'resume_path'    : save_path,
            'resume_filename': save_name,
            'applied_at'     : datetime.now().isoformat(),
            'status'         : 'pending'
        }

        app_file = os.path.join(applications_folder, f"{candidate_id}.json")
        with open(app_file, 'w') as f:
            json.dump(application, f, indent=2)

        print(f"✅ New application: {candidate_name} <{candidate_email}> for {jd_filename}")

        return jsonify({
            'success'      : True,
            'candidate_id' : candidate_id,
            'message'      : 'Application submitted successfully!'
        })

    except Exception as e:
        print(f"Application error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# @app.route('/api/set-deadline', methods=['POST'])
# def api_set_deadline():
#     """Set or update application deadline for a JD."""
#     data     = request.get_json()
#     filename = data.get('filename')
#     deadline = data.get('deadline')   # format: YYYY-MM-DD

#     if not filename or not deadline:
#         return jsonify({'success': False, 'error': 'Missing filename or deadline'}), 400

#     jd_path   = os.path.join(Config.JD_STORE_FOLDER, filename)
#     meta_path = jd_path.replace('.txt', '_meta.json')

#     if not os.path.exists(jd_path):
#         return jsonify({'success': False, 'error': 'JD not found'}), 404

#     # Load existing meta or create new
#     meta = {}
#     if os.path.exists(meta_path):
#         with open(meta_path, 'r') as f:
#             meta = json.load(f)

#     meta['deadline']   = deadline
#     meta['updated_at'] = datetime.now().isoformat()

#     with open(meta_path, 'w') as f:
#         json.dump(meta, f, indent=2)

#     return jsonify({'success': True, 'message': f'Deadline set to {deadline}'})


@app.route('/applications')
def view_applications():
    """Recruiter view — all candidate self-applications."""
    applications_folder = os.path.join(Config.BASE_DIR, 'applications')
    apps = []

    if os.path.exists(applications_folder):
        for file in sorted(os.listdir(applications_folder), reverse=True):
            if file.endswith('.json'):
                try:
                    with open(os.path.join(applications_folder, file)) as f:
                        apps.append(json.load(f))
                except:
                    pass

    return render_template('applications.html', applications=apps)


# ======================
# CANDIDATE DETAILS
# ======================
@app.route('/candidate/<candidate_id>')
def candidate_details(candidate_id):
    """View candidate details"""
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


@app.route('/api/candidate/<candidate_id>')
def get_candidate_details(candidate_id):
    """Get detailed candidate information"""
    screenings = screening_engine.get_all_screenings()
    
    for screening in screenings:
        result = screening_engine.get_screening_result(screening['id'])
        if result:
            for candidate in result.get('candidates', []):
                if candidate.get('candidate_id') == candidate_id:
                    return jsonify(candidate)
    
    return jsonify({'error': 'Candidate not found'}), 404


@app.route('/debug-candidate/<screening_id>')
def debug_candidate(screening_id):
    """Debug endpoint to see raw candidate data"""
    result = screening_engine.get_screening_result(screening_id)
    
    if not result:
        return jsonify({'error': 'Screening not found'}), 404
    
    candidates = result.get('candidates', [])
    debug_data = []
    
    for c in candidates:
        debug_data.append({
            'filename': c.get('filename'),
            'semantic_score': c.get('semantic_score'),
            'skill_match_score': c.get('skill_match_score'),
            'experience_score': c.get('experience_score'),
            'education_score': c.get('education_score'),
            'github_score': c.get('github_score'),
            'confidence_bonus': c.get('confidence_bonus'),
            'overall_score': c.get('overall_score'),
            'final_score': c.get('final_score'),
            'extracted_skills': c.get('extracted_skills', [])[:5],
            'missing_skills': c.get('missing_skills', [])[:3]
        })
    
    return jsonify({
        'screening_id': screening_id,
        'job_title': result.get('job', {}).get('title'),
        'total_candidates': len(candidates),
        'candidates': debug_data
    })


# ======================
# INTERVIEW SCHEDULING ROUTES (ONLY ONCE!)
# ======================

@app.route('/schedule-interviews/<screening_id>')
def schedule_interviews(screening_id):
    """Page to schedule interviews for shortlisted candidates"""
    result = screening_engine.get_screening_result(screening_id)
    
    if not result:
        return render_template('error.html', message='Screening not found'), 404
    
    shortlisted = [c for c in result['candidates'] if c.get('overall_score', 0) >= 65]
    
    return render_template('schedule_interviews.html', 
                         screening=result,
                         candidates=shortlisted,
                         job=result['job'])


@app.route('/create-slots', methods=['GET', 'POST'])
def create_slots():
    """Page for recruiters to create interview slots"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        recruiter_email = data.get('recruiter_email', session.get('recruiter_email', 'recruiter@company.com'))
        slots_data = data.get('slots', [])
        
        if not slots_data:
            return jsonify({'success': False, 'error': 'No slots provided'}), 400
        
        slot_group_id = interview_scheduler.create_slots(recruiter_email, slots_data)
        
        return jsonify({
            'success': True,
            'slot_group_id': slot_group_id,
            'message': f'Created {len(slots_data)} slots successfully'
        })
    
    # Pass current date to template
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('create_slots.html', today=today)

@app.route('/debug-email/<screening_id>')
def debug_email(screening_id):
    """Debug endpoint to check stored emails"""
    result = screening_engine.get_screening_result(screening_id)
    
    if not result:
        return jsonify({'error': 'Screening not found'}), 404
    
    debug_info = []
    for candidate in result.get('candidates', []):
        debug_info.append({
            'filename': candidate.get('filename'),
            'email': candidate.get('email'),
            'has_github': candidate.get('has_github'),
            'github_username': candidate.get('github_username'),
            'score': candidate.get('overall_score')
        })
    
    return jsonify({
        'screening_id': screening_id,
        'job_title': result['job']['title'],
        'candidates': debug_info
    })


@app.route('/send-invites', methods=['GET', 'POST'])
def send_invites():
    """Page to send interview invites to shortlisted candidates"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        screening_id = data.get('screening_id')
        slot_group_id = data.get('slot_group_id')
        
        if not screening_id or not slot_group_id:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Get screening results
        result = screening_engine.get_screening_result(screening_id)
        
        if not result:
            return jsonify({'success': False, 'error': 'Screening not found'}), 404
        
        # Extract candidate emails and names from shortlisted candidates
        candidate_emails = []
        candidate_names = []
        
        print(f"\n📧 Processing screening: {screening_id}")
        print(f"Job Title: {result['job']['title']}")
        print(f"Total candidates: {len(result['candidates'])}")
        
        for candidate in result['candidates']:
            score = candidate.get('overall_score', 0)
            filename = candidate.get('filename', 'Unknown')
            
            print(f"\n  Candidate: {filename}")
            print(f"  Score: {score}")
            print(f"  Email from candidate: {candidate.get('email')}")
            
            if score >= 60:  # Shortlisted only
                email = candidate.get('email')
                
                if email and '@' in email and '.' in email:
                    print(f"  ✅ VALID EMAIL: {email}")
                    candidate_emails.append(email)
                    candidate_names.append(filename.replace('.pdf', '').replace('.', ' '))
                else:
                    print(f"  ❌ No valid email for shortlisted candidate: {filename}")
        
        print(f"\n📧 Final emails to send: {candidate_emails}")
        print(f"📧 Final names: {candidate_names}")
        
        if not candidate_emails:
            return jsonify({
                'success': False, 
                'error': 'No shortlisted candidates with valid emails found'
            }), 400
        
        base_url = request.host_url.rstrip('/')
        
        # Call the scheduler with the correct emails
        invitations = interview_scheduler.send_interview_invites(
            candidate_emails=candidate_emails,
            candidate_names=candidate_names,
            job_title=result['job']['title'],
            slot_group_id=slot_group_id,
            base_url=base_url
        )
        
        return jsonify({
            'success': True,
            'invitations': invitations,
            'message': f'Sent {len(invitations)} invitations'
        })
    
    # GET request - show form with recent screenings
    screenings = screening_engine.get_all_screenings()[:10]
    return render_template('send_invites.html', screenings=screenings)

# @app.route('/send-invites', methods=['GET', 'POST'])
# def send_invites():
#     """Page to send interview invites to shortlisted candidates"""
#     if request.method == 'POST':
#         data = request.get_json() if request.is_json else request.form
        
#         screening_id = data.get('screening_id')
#         slot_group_id = data.get('slot_group_id')
        
#         if not screening_id or not slot_group_id:
#             return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
#         result = screening_engine.get_screening_result(screening_id)
        
#         if not result:
#             return jsonify({'success': False, 'error': 'Screening not found'}), 404
        
#         candidate_emails = []
#         candidate_names = []
        
#         for candidate in result['candidates']:
#             if candidate.get('overall_score', 0) >= 65:
#                 email = candidate.get('email')
#                 if not email:
#                     name_part = candidate['filename'].replace('.pdf', '').replace('.', ' ')
#                     email = f"{name_part.lower().replace(' ', '.')}@example.com"
                
#                 candidate_emails.append(email)
#                 candidate_names.append(candidate['filename'].replace('.pdf', '').replace('.', ' '))
        
#         base_url = request.host_url.rstrip('/')
        
#         invitations = interview_scheduler.send_interview_invites(
#             candidate_emails=candidate_emails,
#             candidate_names=candidate_names,
#             job_title=result['job']['title'],
#             slot_group_id=slot_group_id,
#             base_url=base_url
#         )
        
#         return jsonify({
#             'success': True,
#             'invitations': invitations,
#             'message': f'Sent {len(invitations)} invitations'
#         })
    
#     screenings = screening_engine.get_all_screenings()[:10]
#     return render_template('send_invites.html', screenings=screenings)


@app.route('/scheduled-interviews')
def scheduled_interviews():
    """View all scheduled interviews"""
    interviews = interview_scheduler.get_scheduled_interviews()
    
    # Get today's date for template
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Group interviews by date
    grouped = {}
    for interview in interviews:
        date = interview['slot']['date']
        if date not in grouped:
            grouped[date] = []
        grouped[date].append(interview)
    
    # Sort dates
    sorted_grouped = dict(sorted(grouped.items()))
    
    return render_template('scheduled_interviews.html', 
                         interviews=interviews,
                         grouped=sorted_grouped,
                         today=today)  # ← Pass today to template

@app.route('/select-slot/<token>')
def select_slot(token):
    """Page for candidates to select interview slot"""
    invitation = interview_scheduler.get_invitation_by_token(token)
    
    if not invitation:
        return render_template('error.html', message='Invalid or expired invitation link'), 404
    
    if invitation['status'] == 'booked':
        return render_template('error.html', message='This invitation has already been used'), 400
    
    return render_template('slot_selection.html', token=token)

@app.route('/analytics')
def analytics():
    """Full recruitment analytics dashboard."""
    data = analytics_engine.get_dashboard_data()
    return render_template('analytics.html', data=data)
 
 
@app.route('/api/analytics')
def api_analytics():
    """Analytics data as JSON — for future use."""
    data = analytics_engine.get_dashboard_data()
    return jsonify(data)

@app.route('/api/slot-groups')
def api_slot_groups():
    groups = interview_scheduler.get_all_slot_groups()
    return jsonify({'groups': groups})

@app.route('/model-report')
def model_report():
    """Show ML model training report with confusion matrix."""
    import json
    report_path = os.path.join(Config.BASE_DIR, 'models', 'training_report.json')
    matrix_path = os.path.join(Config.BASE_DIR, 'models', 'confusion_matrix.png')
 
    report = None
    if os.path.exists(report_path):
        with open(report_path) as f:
            report = json.load(f)
 
    has_matrix = os.path.exists(matrix_path)
    return render_template('model_report.html', report=report, has_matrix=has_matrix)
 
 
@app.route('/models/confusion_matrix.png')
def serve_confusion_matrix():
    """Serve confusion matrix image."""
    matrix_path = os.path.join(Config.BASE_DIR, 'models', 'confusion_matrix.png')
    if os.path.exists(matrix_path):
        return send_file(matrix_path, mimetype='image/png')
    return '', 404


@app.route('/api/create-interview-slots', methods=['POST'])
def api_create_interview_slots():
    """API endpoint for recruiters to create interview slots"""
    data = request.get_json()
    
    recruiter_email = data.get('recruiter_email')
    slots = data.get('slots', [])
    
    if not recruiter_email or not slots:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    slot_group_id = interview_scheduler.create_slots(recruiter_email, slots)
    
    return jsonify({
        'success': True,
        'slot_group_id': slot_group_id
    })


@app.route('/api/send-interview-invites', methods=['POST'])
def api_send_interview_invites():
    """Send interview invites to shortlisted candidates"""
    data = request.get_json()
    
    screening_id = data.get('screening_id')
    slot_group_id = data.get('slot_group_id')
    
    if not screening_id or not slot_group_id:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    result = screening_engine.get_screening_result(screening_id)
    
    if not result:
        return jsonify({'success': False, 'error': 'Screening not found'}), 404
    
    candidate_emails = []
    candidate_names = []
    
    print(f"\n🔍 API send-interview-invites called for screening: {screening_id}")
    
    for candidate in result['candidates']:
        if candidate.get('overall_score', 0) >= 60:
            email = candidate.get('email')
            filename = candidate.get('filename')
            
            print(f"  Candidate: {filename} -> Email: {email}")
            
            if email and '@' in email:
                candidate_emails.append(email)
                candidate_names.append(filename.replace('.pdf', '').replace('.', ' '))
            else:
                # Fallback - use filename to generate email
                fallback = filename.replace('.pdf', '').lower().replace(' ', '.') + '@example.com'
                print(f"  ⚠️ No valid email, using fallback: {fallback}")
                candidate_emails.append(fallback)
                candidate_names.append(filename.replace('.pdf', '').replace('.', ' '))
    
    base_url = request.host_url.rstrip('/')
    
    invitations = interview_scheduler.send_interview_invites(
        candidate_emails=candidate_emails,
        candidate_names=candidate_names,
        job_title=result['job']['title'],
        slot_group_id=slot_group_id,
        base_url=base_url
    )
    
    return jsonify({
        'success': True,
        'invitations': invitations
    })



@app.route('/view-resume/<candidate_id>')
def view_resume(candidate_id):
    """Serve the actual resume PDF file"""
    # Search through all screenings to find the candidate
    screenings = screening_engine.get_all_screenings()
    
    for screening in screenings:
        result = screening_engine.get_screening_result(screening['id'])
        if result and result.get('candidates'):
            for candidate in result['candidates']:
                if candidate.get('candidate_id') == candidate_id:
                    
                    # Method 1: Check if resume_path is stored
                    resume_path = candidate.get('resume_path')
                    if resume_path and os.path.exists(resume_path):
                        return send_file(resume_path, as_attachment=False)
                    
                    # Method 2: Try to find by candidate_id in upload folder
                    upload_folder = Config.UPLOAD_FOLDER
                    pattern = os.path.join(upload_folder, f"{candidate_id}_*")
                    files = glob.glob(pattern)
                    
                    if files:
                        return send_file(files[0], as_attachment=False)
                    
                    # Method 3: Try to find by filename
                    filename = candidate.get('filename')
                    if filename:
                        file_path = os.path.join(upload_folder, filename)
                        if os.path.exists(file_path):
                            return send_file(file_path, as_attachment=False)
                    
                    # Method 4: Look in all subfolders
                    for root, dirs, files in os.walk(upload_folder):
                        for file in files:
                            if candidate_id in file or filename in file:
                                return send_file(os.path.join(root, file), as_attachment=False)
    
    # If we get here, file not found
    return render_template('error.html', message='Resume file not found'), 404

@app.route('/api/interview-slots/<token>')
def api_interview_slots(token):
    """Get available slots for a token"""
    invitation = interview_scheduler.get_invitation_by_token(token)
    
    if not invitation:
        return jsonify({'success': False, 'error': 'Invalid token'}), 404
    
    if invitation['status'] == 'booked':
        return jsonify({'success': False, 'error': 'You have already booked a slot'}), 400
    
    slots = interview_scheduler.get_available_slots(invitation['slot_group_id'])
    
    return jsonify({
        'success': True,
        'invitation': invitation,
        'slots': slots
    })


@app.route('/api/book-slot', methods=['POST'])
def api_book_slot():
    """Book an interview slot"""
    data = request.get_json()
    
    token = data.get('token')
    slot_id = data.get('slot_id')
    
    if not token or not slot_id:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    invitation = interview_scheduler.get_invitation_by_token(token)
    
    if not invitation:
        return jsonify({'success': False, 'error': 'Invalid token'}), 404
    
    result = interview_scheduler.book_slot(
        token=token,
        slot_id=slot_id,
        candidate_email=invitation['candidate_email'],
        candidate_name=invitation['candidate_name']
    )
    
    return jsonify(result)


@app.route('/api/recent-screenings')
def api_recent_screenings():
    """API endpoint to get recent screenings for dropdown"""
    screenings = screening_engine.get_all_screenings()[:10]
    result = []
    for s in screenings:
        result.append({
            'id': s['id'],
            'job_title': s['job_title'],
            'total': s['total'],
            'top_score': s['top_score']
        })
    return jsonify(result)

@app.route('/api/screening-candidates/<screening_id>')
def api_screening_candidates(screening_id):
    """Get shortlisted candidates for a screening"""
    result = screening_engine.get_screening_result(screening_id)
    
    if not result:
        return jsonify({'success': False, 'error': 'Screening not found'}), 404
    
    shortlisted = []
    print(f"\n🔍 API screening-candidates called for: {screening_id}")
    
    for c in result['candidates']:
        score = c.get('overall_score', 0)
        if score >= 60:
            email = c.get('email')
            filename = c.get('filename')
            
            print(f"  Candidate: {filename}")
            print(f"    Score: {score}")
            print(f"    Email from data: {email}")
            
            shortlisted.append({
                'name': filename.replace('.pdf', '').replace('.', ' '),
                'email': email,
                'score': score
            })
    
    print(f"  Returning {len(shortlisted)} shortlisted candidates")
    
    return jsonify({
        'success': True,
        'job_title': result['job']['title'],
        'candidates': shortlisted
    })

@app.route('/debug-results/<screening_id>')
def debug_results(screening_id):
    """Check what's actually saved in the results file"""
    result = screening_engine.get_screening_result(screening_id)
    
    if not result:
        return jsonify({'error': 'Not found'}), 404
    
    debug = []
    for c in result.get('candidates', []):
        debug.append({
            'filename': c.get('filename'),
            'saved_email': c.get('email'),
            'has_email_field': 'email' in c,
            'all_keys': list(c.keys())
        })
    
    return jsonify({
        'screening_id': screening_id,
        'candidates': debug
    })


@app.route('/api/set-deadline', methods=['POST'])
def api_set_deadline():
    """Set deadline + optional slot_group_id for a JD."""
    data     = request.get_json()
    filename = data.get('filename')
    deadline = data.get('deadline')        # YYYY-MM-DD
    slot_group_id = data.get('slot_group_id', None)
 
    if not filename or not deadline:
        return jsonify({'success': False, 'error': 'Missing filename or deadline'}), 400
 
    jd_path   = os.path.join(Config.JD_STORE_FOLDER, filename)
    meta_path = jd_path.replace('.txt', '_meta.json')
 
    if not os.path.exists(jd_path):
        return jsonify({'success': False, 'error': 'JD not found'}), 404
 
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, 'r') as f:
            meta = json.load(f)
 
    meta['deadline']      = deadline
    meta['status']        = 'open'
    meta['updated_at']    = datetime.now().isoformat()
    if slot_group_id:
        meta['slot_group_id'] = slot_group_id
 
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)
 
    return jsonify({
        'success' : True,
        'message' : f'Deadline set to {deadline}. Auto screening will trigger after deadline.'
    })
 
 
@app.route('/api/trigger-auto-screen', methods=['POST'])
def api_trigger_auto_screen():
    """
    Manually trigger auto screening — useful for testing
    without waiting for the scheduler.
    """
    try:
        auto_screener.check_and_process_deadlines()
        return jsonify({'success': True, 'message': 'Auto screening triggered.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
 
 
@app.route('/api/jd-status/<filename>')
def api_jd_status(filename):
    """Get current status of a JD — open, processed, or no deadline."""
    meta_path = os.path.join(Config.JD_STORE_FOLDER, filename.replace('.txt', '_meta.json'))
 
    if not os.path.exists(meta_path):
        return jsonify({'status': 'no_deadline', 'deadline': None})
 
    with open(meta_path, 'r') as f:
        meta = json.load(f)
 
    return jsonify({
        'status'       : meta.get('status', 'open'),
        'deadline'     : meta.get('deadline'),
        'processed_at' : meta.get('processed_at'),
        'screening_id' : meta.get('screening_id'),
    })
 
 
@app.route('/auto-screen-logs')
def auto_screen_logs():
    """View all auto screening logs."""
    log_folder = os.path.join(Config.BASE_DIR, 'auto_screen_logs')
    logs = []
 
    if os.path.exists(log_folder):
        for file in sorted(os.listdir(log_folder), reverse=True):
            if file.endswith('.json'):
                try:
                    with open(os.path.join(log_folder, file)) as f:
                        logs.append(json.load(f))
                except:
                    pass
 
    return render_template('auto_screen_logs.html', logs=logs)


# ======================
# LEARNING PATH ROUTES
# ======================

from modules.learning_path_generator import LearningPathGenerator

# Initialize learning path generator
learning_path_gen = LearningPathGenerator(Config)

@app.route('/generate-learning-paths/<screening_id>')
def generate_learning_paths(screening_id):
    """Generate learning paths for all rejected candidates in a screening"""
    # Get screening results
    result = screening_engine.get_screening_result(screening_id)
    
    if not result:
        return render_template('error.html', message='Screening not found'), 404
    
    # Find rejected candidates (score < 50)
    rejected = [c for c in result['candidates'] if c.get('overall_score', 0) < 50]
    
    if not rejected:
        return render_template('error.html', message='No rejected candidates found'), 404
    
    generated_paths = []
    for candidate in rejected:
        learning_path = learning_path_gen.generate_learning_path(candidate, result['job'])
        generated_paths.append(learning_path)
        
        # Send email if candidate has email
        if candidate.get('email'):
            base_url = request.host_url.rstrip('/')
            learning_path_gen.send_learning_path_email(candidate['email'], learning_path, base_url)
    
    return render_template('learning_paths_generated.html', 
                         paths=generated_paths,
                         count=len(generated_paths),
                         screening_id=screening_id)

@app.route('/learning-path/<candidate_id>')
def view_learning_path(candidate_id):
    """View learning path for a candidate"""
    learning_path = learning_path_gen.get_learning_path(candidate_id)
    
    if not learning_path:
        return render_template('error.html', message='Learning path not found'), 404
    
    return render_template('learning_path.html', path=learning_path)

@app.route('/api/generate-learning-path/<candidate_id>', methods=['POST'])
def api_generate_learning_path(candidate_id):
    """API endpoint to generate learning path for a specific candidate"""
    data = request.get_json()
    
    # Find candidate in screenings
    screenings = screening_engine.get_all_screenings()
    candidate_data = None
    job_data = None
    
    for screening in screenings:
        result = screening_engine.get_screening_result(screening['id'])
        if result and result.get('candidates'):
            for c in result['candidates']:
                if c.get('candidate_id') == candidate_id:
                    candidate_data = c
                    job_data = result['job']
                    break
        if candidate_data:
            break
    
    if not candidate_data:
        return jsonify({'success': False, 'error': 'Candidate not found'}), 404
    
    # Generate learning path
    learning_path = learning_path_gen.generate_learning_path(candidate_data, job_data)
    
    return jsonify({
        'success': True,
        'learning_path': learning_path,
        'view_url': f"/learning-path/{candidate_id}"
    })


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
    
    app.run(debug=True, port=5002)