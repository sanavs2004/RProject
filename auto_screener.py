"""
AutoscreenerPipeline for RecruitAI
====================================
Runs automatically after JD deadline passes.

Flow:
  1. APScheduler calls check_and_process_deadlines() every hour
  2. Finds JDs whose deadline has passed and status = 'open'
  3. Loads all pending applications for that JD
  4. Runs resume screening on all applicants
  5. Sends interview invites to Strong Fit candidates
  6. Sends learning path emails to Hold/Reject candidates
  7. Marks JD as 'processed'
"""

import os
import json
import uuid
from datetime import datetime

from modules.resume_screening import ResumeScreeningEngine
from modules.learning_path_generator import LearningPathGenerator
from modules.learning_path_emailer import send_learning_path_email
from modules.interview_scheduler import InterviewScheduler
from config import Config


class AutoScreener:

    def __init__(self):
        self.screening_engine   = ResumeScreeningEngine(Config)
        self.learning_path_gen  = LearningPathGenerator(Config)
        self.interview_scheduler = InterviewScheduler(Config)

        self.jd_folder           = Config.JD_STORE_FOLDER
        self.applications_folder = os.path.join(Config.BASE_DIR, 'applications')
        self.log_folder          = os.path.join(Config.BASE_DIR, 'auto_screen_logs')
        os.makedirs(self.log_folder, exist_ok=True)

    # ──────────────────────────────────────────────────────────────────────────
    # MAIN ENTRY POINT — called by APScheduler every hour
    # ──────────────────────────────────────────────────────────────────────────
    def check_and_process_deadlines(self):
        """
        Check all JDs. If deadline has passed and status is open,
        trigger auto screening for that JD.
        """
        print(f"\n⏰ AutoScreener running at {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        if not os.path.exists(self.jd_folder):
            print("   No JD folder found.")
            return

        processed_count = 0

        for file in os.listdir(self.jd_folder):
            if not file.endswith('_meta.json'):
                continue

            meta_path = os.path.join(self.jd_folder, file)
            try:
                with open(meta_path, 'r') as f:
                    meta = json.load(f)

                # Skip if already processed or no deadline
                if meta.get('status') != 'open':
                    continue
                deadline = meta.get('deadline')
                if not deadline:
                    continue

                # Check if deadline has passed
                deadline_date = datetime.strptime(deadline, '%Y-%m-%d').date()
                if deadline_date >= datetime.now().date():
                    print(f"   ⏳ {file}: deadline {deadline} not yet passed.")
                    continue

                # Get the JD filename from meta filename
                jd_filename = file.replace('_meta.json', '.txt')
                jd_path     = os.path.join(self.jd_folder, jd_filename)

                if not os.path.exists(jd_path):
                    print(f"   ❌ JD file not found: {jd_filename}")
                    continue

                print(f"\n🚀 Deadline passed for: {jd_filename}")
                print(f"   Triggering auto screening...")

                # Run the full pipeline
                result = self._process_jd(jd_filename, jd_path, meta)

                # Mark as processed
                meta['status']       = 'processed'
                meta['processed_at'] = datetime.now().isoformat()
                meta['screening_id'] = result.get('screening_id')
                with open(meta_path, 'w') as f:
                    json.dump(meta, f, indent=2)

                processed_count += 1
                print(f"   ✅ Done! Screening ID: {result.get('screening_id')}")

            except Exception as e:
                print(f"   ❌ Error processing {file}: {e}")

        if processed_count == 0:
            print("   No JDs ready for auto screening.")
        else:
            print(f"\n✅ Auto screening complete. Processed {processed_count} JD(s).")

    # ──────────────────────────────────────────────────────────────────────────
    # PROCESS ONE JD
    # ──────────────────────────────────────────────────────────────────────────
    def _process_jd(self, jd_filename, jd_path, meta):
        """
        Full pipeline for one JD after deadline:
        Load applications → Screen → Email results
        """
        # Load JD text
        with open(jd_path, 'r', encoding='utf-8') as f:
            jd_text = f.read()

        # Build job title from filename
        name_part = jd_filename.replace('jd_', '').replace('.txt', '')
        parts     = name_part.split('_')
        if len(parts) > 1 and parts[-1].isdigit() and len(parts[-1]) >= 6:
            job_title = ' '.join(parts[:-1]).title()
        else:
            job_title = ' '.join(parts).title()

        # Load all pending applications for this JD
        applications = self._get_pending_applications(jd_filename)

        if not applications:
            print(f"   ⚠️ No pending applications found for {jd_filename}")
            return {'screening_id': None, 'total': 0}

        print(f"   📄 Found {len(applications)} application(s) to screen.")

        # Build fake file objects from saved resume paths
        resume_files = []
        valid_apps   = []

        for app in applications:
            resume_path = app.get('resume_path')
            if resume_path and os.path.exists(resume_path):
                resume_files.append(ResumeFileWrapper(resume_path, app))
                valid_apps.append(app)
            else:
                print(f"   ⚠️ Resume not found for {app.get('candidate_name')}")

        if not resume_files:
            print(f"   ❌ No valid resumes found.")
            return {'screening_id': None, 'total': 0}

        # Run screening
        screening_id, results = self.screening_engine.screen_resumes(
            jd_text      = jd_text,
            resume_files = resume_files,
            job_title    = job_title
        )

        print(f"   🧠 Screening complete. ID: {screening_id}")

        # Send emails to each candidate
        self._send_emails(results, jd_text, job_title, meta)

        # Save auto screen log
        self._save_log(jd_filename, screening_id, results, valid_apps)

        return {
            'screening_id': screening_id,
            'total'       : len(results.get('candidates', []))
        }

    # ──────────────────────────────────────────────────────────────────────────
    # SEND EMAILS BASED ON DECISION
    # ──────────────────────────────────────────────────────────────────────────
    def _send_emails(self, results, jd_text, job_title, meta):
        """
        Strong Fit  → Interview invite email
        Hold/Reject → Learning path email
        """
        candidates = results.get('candidates', [])
        job        = results.get('job', {})

        shortlisted = []
        others      = []

        for candidate in candidates:
            decision = candidate.get('decision', {})
            action   = decision.get('action', 'reject')

            if action == 'shortlist':
                shortlisted.append(candidate)
            else:
                others.append(candidate)

        print(f"   📊 Results: {len(shortlisted)} shortlisted, {len(others)} hold/rejected")

        # ── Send interview invites to shortlisted ─────────────────────────────
        if shortlisted:
            # Check if recruiter has created slots
            slot_group_id = meta.get('slot_group_id')

            if slot_group_id:
                candidate_emails = []
                candidate_names  = []
                for c in shortlisted:
                    email = c.get('email')
                    if email and '@' in email:
                        candidate_emails.append(email)
                        candidate_names.append(
                            c.get('filename', '').replace('.pdf', '').replace('_', ' ')
                        )

                if candidate_emails:
                    try:
                        self.interview_scheduler.send_interview_invites(
                            candidate_emails = candidate_emails,
                            candidate_names  = candidate_names,
                            job_title        = job_title,
                            slot_group_id    = slot_group_id,
                            base_url         = 'http://localhost:5002'
                        )
                        print(f"   📧 Interview invites sent to {len(candidate_emails)} candidate(s).")
                    except Exception as e:
                        print(f"   ❌ Interview invite error: {e}")
            else:
                print(f"   ⚠️ No slot_group_id set — interview invites skipped.")
                print(f"      Set slot_group_id in JD meta to enable auto interview invites.")

        # ── Send learning path emails to hold/rejected ────────────────────────
        for candidate in others:
            email = candidate.get('email')
            if not email or '@' not in email:
                continue
            try:
                lp = self.learning_path_gen.generate(candidate, job)
                sent = send_learning_path_email(candidate, job, lp, Config)
                status = '✅' if sent else '❌'
                print(f"   {status} Learning path email → {email}")
            except Exception as e:
                print(f"   ❌ Learning path error for {email}: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────────
    def _get_pending_applications(self, jd_filename):
        """Load all pending applications for a specific JD."""
        if not os.path.exists(self.applications_folder):
            return []

        apps = []
        for file in os.listdir(self.applications_folder):
            if not file.endswith('.json'):
                continue
            try:
                with open(os.path.join(self.applications_folder, file)) as f:
                    app = json.load(f)
                if app.get('jd_filename') == jd_filename and app.get('status') == 'pending':
                    apps.append(app)
            except:
                pass
        return apps

    def _save_log(self, jd_filename, screening_id, results, applications):
        """Save auto screening log for audit trail."""
        log = {
            'jd_filename'  : jd_filename,
            'screening_id' : screening_id,
            'processed_at' : datetime.now().isoformat(),
            'total'        : len(results.get('candidates', [])),
            'shortlisted'  : len([c for c in results.get('candidates', [])
                                  if c.get('decision', {}).get('action') == 'shortlist']),
            'rejected'     : len([c for c in results.get('candidates', [])
                                  if c.get('decision', {}).get('action') == 'reject']),
            'applicants'   : [a.get('candidate_name') for a in applications]
        }
        log_file = os.path.join(self.log_folder, f"{screening_id}.json")
        with open(log_file, 'w') as f:
            json.dump(log, f, indent=2)


# ──────────────────────────────────────────────────────────────────────────────
# RESUME FILE WRAPPER
# Wraps a saved resume path to look like a Flask file upload object
# so the existing screening engine can process it without changes
# ──────────────────────────────────────────────────────────────────────────────
class ResumeFileWrapper:
    """
    Makes a saved resume file look like a Flask FileStorage object.
    The screening engine calls .filename, .read(), and .save() on uploads —
    this wrapper provides all three from a local file path.
    """

    def __init__(self, path, app_data):
        self.path          = path
        self.filename      = os.path.basename(path)
        self._app_data     = app_data
        # Pre-inject candidate email and name so screening engine picks them up
        self._email        = app_data.get('candidate_email', '')
        self._name         = app_data.get('candidate_name', '')

    def read(self):
        with open(self.path, 'rb') as f:
            return f.read()

    def save(self, dest):
        import shutil
        shutil.copy2(self.path, dest)

    def seek(self, pos):
        pass  # no-op for compatibility


# ──────────────────────────────────────────────────────────────────────────────
# SINGLETON — one instance shared across app
# ──────────────────────────────────────────────────────────────────────────────
auto_screener = AutoScreener()