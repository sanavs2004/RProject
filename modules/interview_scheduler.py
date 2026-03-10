import os
import uuid
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from jinja2 import Template
import re

class InterviewScheduler:
    """
    Manages interview scheduling for shortlisted candidates
    Handles slot creation, invitations, booking, and confirmations
    """
    
    def __init__(self, config):
        self.config = config
        self.slots_folder = os.path.join(config.BASE_DIR, 'interviews', 'slots')
        self.invitations_folder = os.path.join(config.BASE_DIR, 'interviews', 'invitations')
        self.confirmations_folder = os.path.join(config.BASE_DIR, 'interviews', 'confirmations')
        
        # Create directories
        os.makedirs(self.slots_folder, exist_ok=True)
        os.makedirs(self.invitations_folder, exist_ok=True)
        os.makedirs(self.confirmations_folder, exist_ok=True)
        
        # Email configuration (from environment variables)
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        self.smtp_username = os.environ.get('SMTP_USERNAME', '')
        self.smtp_password = os.environ.get('SMTP_PASSWORD', '')
        self.from_email = os.environ.get('FROM_EMAIL', 'noreply@recruitai.com')
        
        print("✅ Interview Scheduler initialized")
    
    def create_slots(self, recruiter_email, slots_data):
        """
        Recruiter creates available interview slots
        
        Args:
            recruiter_email: Recruiter's email for notifications
            slots_data: List of slot objects with date, time, duration, mode
        
        Returns:
            slot_group_id: Unique ID for this group of slots
        """
        slot_group_id = str(uuid.uuid4())
        
        slots = []
        for slot in slots_data:
            slot_id = str(uuid.uuid4())
            slot_obj = {
                'id': slot_id,
                'group_id': slot_group_id,
                'date': slot['date'],
                'start_time': slot['start_time'],
                'end_time': slot['end_time'],
                'duration': slot.get('duration', 60),  # minutes
                'mode': slot.get('mode', 'video'),  # video, phone, in-person
                'location': slot.get('location', 'Google Meet'),
                'recruiter_email': recruiter_email,
                'status': 'available',  # available, booked, cancelled
                'created_at': datetime.now().isoformat(),
                'booked_by': None,
                'booking_time': None
            }
            slots.append(slot_obj)
            
            # Save individual slot
            slot_path = os.path.join(self.slots_folder, f"{slot_id}.json")
            with open(slot_path, 'w') as f:
                json.dump(slot_obj, f, indent=2)
        
        # Save slot group
        group_path = os.path.join(self.slots_folder, f"group_{slot_group_id}.json")
        with open(group_path, 'w') as f:
            json.dump({
                'group_id': slot_group_id,
                'recruiter_email': recruiter_email,
                'slots': slots,
                'created_at': datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"✅ Created {len(slots)} interview slots (Group ID: {slot_group_id})")
        return slot_group_id
    
    def send_interview_invites(self, candidate_emails, candidate_names, job_title, slot_group_id, base_url):
        """
        Send interview invitations to shortlisted candidates
        """
        invitations = []
        
        print(f"\n📧 SCHEDULER - Received emails: {candidate_emails}")
        print(f"📧 SCHEDULER - Received names: {candidate_names}")
        
        for i, email in enumerate(candidate_emails):
            name = candidate_names[i] if i < len(candidate_names) else "Candidate"
            
            print(f"  → Processing: {name} at {email}")
            
            # Generate unique token for this invitation
            token = str(uuid.uuid4())
            selection_link = f"{base_url}/select-slot/{token}"
            
            # Create invitation record
            invitation = {
                'id': str(uuid.uuid4()),
                'token': token,
                'candidate_email': email,
                'candidate_name': name,
                'job_title': job_title,
                'slot_group_id': slot_group_id,
                'status': 'sent',
                'sent_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=7)).isoformat(),
                'selection_link': selection_link
            }
            
            # Save invitation
            inv_path = os.path.join(self.invitations_folder, f"{token}.json")
            with open(inv_path, 'w') as f:
                json.dump(invitation, f, indent=2)
            
            invitations.append(invitation)
            
            # Send email
            self._send_invitation_email(invitation, selection_link)
            print(f"  ✅ Invitation sent to {email}")
        
        return invitations
    
    def _send_invitation_email(self, invitation, selection_link):
        """Send interview invitation email"""
        try:
            # Load email template with UTF-8 encoding
            template_path = os.path.join(
                self.config.BASE_DIR, 
                'templates', 
                'email_templates', 
                'interview_invite.html'
            )
            
            # Read with explicit UTF-8 encoding
            with open(template_path, 'r', encoding='utf-8') as f:
                template_str = f.read()
            
            template = Template(template_str)
            html_content = template.render(
                candidate_name=invitation['candidate_name'],
                job_title=invitation['job_title'],
                selection_link=selection_link,
                expires_at=invitation['expires_at'][:10]
            )
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Interview Invitation: {invitation['job_title']} position"
            msg['From'] = self.from_email
            msg['To'] = invitation['candidate_email']
            
            # Attach HTML content with UTF-8 encoding
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # Send email
            if self.smtp_username and self.smtp_password:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
                server.quit()
                print(f"  ✅ Invitation sent to {invitation['candidate_email']}")
            else:
                # Development mode - save to file with UTF-8
                email_dir = os.path.join(self.config.BASE_DIR, 'interviews', 'emails')
                os.makedirs(email_dir, exist_ok=True)
                email_path = os.path.join(email_dir, f"{invitation['id']}.html")
                
                with open(email_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"  📧 Email saved to {email_path} (SMTP not configured)")
                
        except Exception as e:
            print(f"❌ Failed to send email to {invitation['candidate_email']}: {e}")
            # Don't re-raise - we still want to mark as sent
            # The invitation will be saved even if email fails
    
    def get_available_slots(self, slot_group_id):
        """Get all available slots for a group"""
        available_slots = []
        
        group_path = os.path.join(self.slots_folder, f"group_{slot_group_id}.json")
        if os.path.exists(group_path):
            with open(group_path, 'r') as f:
                group = json.load(f)
                
            for slot in group['slots']:
                if slot['status'] == 'available':
                    # Check if slot is still in the future
                    slot_datetime = datetime.fromisoformat(f"{slot['date']}T{slot['start_time']}")
                    if slot_datetime > datetime.now():
                        available_slots.append(slot)
        
        return available_slots
    
    def book_slot(self, token, slot_id, candidate_email, candidate_name):
        """
        Candidate books an interview slot
        
        Returns:
            dict: Booking confirmation details
        """
        # Verify invitation
        inv_path = os.path.join(self.invitations_folder, f"{token}.json")
        if not os.path.exists(inv_path):
            return {'success': False, 'error': 'Invalid invitation token'}
        
        with open(inv_path, 'r') as f:
            invitation = json.load(f)
        
        # Check if invitation is expired
        expires_at = datetime.fromisoformat(invitation['expires_at'])
        if datetime.now() > expires_at:
            return {'success': False, 'error': 'Invitation has expired'}
        
        # Check if already booked
        if invitation['status'] == 'booked':
            return {'success': False, 'error': 'You have already booked a slot'}
        
        # Verify slot
        slot_path = os.path.join(self.slots_folder, f"{slot_id}.json")
        if not os.path.exists(slot_path):
            return {'success': False, 'error': 'Selected slot not found'}
        
        with open(slot_path, 'r') as f:
            slot = json.load(f)
        
        # Check if slot is available
        if slot['status'] != 'available':
            return {'success': False, 'error': 'Slot is no longer available'}
        
        # Check if slot is still in the future
        slot_datetime = datetime.fromisoformat(f"{slot['date']}T{slot['start_time']}")
        if slot_datetime <= datetime.now():
            return {'success': False, 'error': 'Cannot book past slots'}
        
        # Book the slot
        slot['status'] = 'booked'
        slot['booked_by'] = candidate_email
        slot['booking_time'] = datetime.now().isoformat()
        
        # Update slot file
        with open(slot_path, 'w') as f:
            json.dump(slot, f, indent=2)
        
        # Update group file
        group_path = os.path.join(self.slots_folder, f"group_{slot['group_id']}.json")
        if os.path.exists(group_path):
            with open(group_path, 'r') as f:
                group = json.load(f)
            
            for s in group['slots']:
                if s['id'] == slot_id:
                    s.update(slot)
                    break
            
            with open(group_path, 'w') as f:
                json.dump(group, f, indent=2)
        
        # Update invitation
        invitation['status'] = 'booked'
        invitation['booked_slot_id'] = slot_id
        invitation['booked_at'] = datetime.now().isoformat()
        
        with open(inv_path, 'w') as f:
            json.dump(invitation, f, indent=2)
        
        # Create confirmation
        confirmation = self._create_confirmation(invitation, slot)
        
        # Send confirmation emails
        self._send_confirmation_emails(confirmation, invitation, slot)
        
        return {
            'success': True,
            'confirmation': confirmation,
            'slot': slot
        }
    
    def _create_confirmation(self, invitation, slot):
        """Create confirmation record"""
        confirmation_id = str(uuid.uuid4())
        
        # Generate video link if mode is video
        video_link = None
        if slot['mode'] == 'video':
            video_link = f"https://meet.google.com/{uuid.uuid4().hex[:12]}"
        
        confirmation = {
            'id': confirmation_id,
            'invitation_id': invitation['id'],
            'candidate_email': invitation['candidate_email'],
            'candidate_name': invitation['candidate_name'],
            'recruiter_email': slot['recruiter_email'],
            'job_title': invitation['job_title'],
            'slot': slot,
            'video_link': video_link,
            'confirmed_at': datetime.now().isoformat(),
            'status': 'confirmed'
        }
        
        # Save confirmation
        conf_path = os.path.join(self.confirmations_folder, f"{confirmation_id}.json")
        with open(conf_path, 'w') as f:
            json.dump(confirmation, f, indent=2)
        
        return confirmation
    
    def _send_confirmation_emails(self, confirmation, invitation, slot):
        """Send confirmation emails to candidate and recruiter"""
        try:
            # Load email template
            template_path = os.path.join(
                self.config.BASE_DIR, 
                'templates', 
                'email_templates', 
                'confirmation_email.html'
            )
            
            with open(template_path, 'r') as f:
                template_str = f.read()
            
            template = Template(template_str)
            
            # Format datetime for display
            slot_datetime = datetime.fromisoformat(f"{slot['date']}T{slot['start_time']}")
            formatted_date = slot_datetime.strftime("%A, %B %d, %Y")
            formatted_time = slot_datetime.strftime("%I:%M %p")
            formatted_end = datetime.fromisoformat(f"{slot['date']}T{slot['end_time']}").strftime("%I:%M %p")
            
            # Create calendar invite (ICS file)
            ics_content = self._create_ics_file(confirmation, slot, formatted_date)
            
            # Send to candidate
            candidate_html = template.render(
                recipient_type='candidate',
                name=invitation['candidate_name'],
                job_title=invitation['job_title'],
                date=formatted_date,
                start_time=formatted_time,
                end_time=formatted_end,
                mode=slot['mode'],
                location=slot.get('location', 'To be provided'),
                video_link=confirmation.get('video_link', ''),
                recruiter_email=slot['recruiter_email']
            )
            
            self._send_email(
                to_email=invitation['candidate_email'],
                subject=f"Interview Confirmed: {invitation['job_title']} on {formatted_date}",
                html_content=candidate_html,
                ics_content=ics_content
            )
            
            # Send to recruiter
            recruiter_html = template.render(
                recipient_type='recruiter',
                name="Recruiter",
                candidate_name=invitation['candidate_name'],
                candidate_email=invitation['candidate_email'],
                job_title=invitation['job_title'],
                date=formatted_date,
                start_time=formatted_time,
                end_time=formatted_end,
                mode=slot['mode'],
                location=slot.get('location', 'To be provided'),
                video_link=confirmation.get('video_link', '')
            )
            
            self._send_email(
                to_email=slot['recruiter_email'],
                subject=f"Interview Scheduled: {invitation['candidate_name']} for {invitation['job_title']}",
                html_content=recruiter_html,
                ics_content=ics_content
            )
            
            print(f"✅ Confirmation emails sent for {invitation['candidate_email']}")
            
        except Exception as e:
            print(f"❌ Failed to send confirmation emails: {e}")
    
    def _create_ics_file(self, confirmation, slot, formatted_date):
        """Create calendar invite (ICS file)"""
        start_dt = datetime.fromisoformat(f"{slot['date']}T{slot['start_time']}")
        end_dt = datetime.fromisoformat(f"{slot['date']}T{slot['end_time']}")
        
        ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//RecruitAI//Interview Scheduler//EN
BEGIN:VEVENT
UID:{confirmation['id']}@recruitai.com
DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%S')}Z
DTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}Z
DTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}Z
SUMMARY:Interview: {confirmation['job_title']}
DESCRIPTION:Interview for {confirmation['job_title']} position
LOCATION:{slot.get('location', 'Video Call')}
STATUS:CONFIRMED
BEGIN:VALARM
TRIGGER:-PT15M
ACTION:DISPLAY
DESCRIPTION:Reminder: Interview in 15 minutes
END:VALARM
END:VEVENT
END:VCALENDAR"""
        
        return ics_content
    
    def _send_email(self, to_email, subject, html_content, ics_content=None):
        """Generic email sending function"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            msg.attach(MIMEText(html_content, 'html'))
            
            # Attach calendar invite if provided
            if ics_content:
                attachment = MIMEText(ics_content, 'calendar')
                attachment.add_header('Content-Type', 'text/calendar; method=REQUEST')
                attachment.add_header('Content-Disposition', 'attachment; filename="invite.ics"')
                msg.attach(attachment)
            
            if self.smtp_username and self.smtp_password:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
                server.quit()
            else:
                # Development mode
                email_dir = os.path.join(self.config.BASE_DIR, 'interviews', 'emails')
                os.makedirs(email_dir, exist_ok=True)
                email_path = os.path.join(email_dir, f"{uuid.uuid4().hex}.html")
                with open(email_path, 'w') as f:
                    f.write(html_content)
                print(f"📧 Email saved to {email_path}")
                
        except Exception as e:
            print(f"❌ Email error: {e}")
    
    def get_scheduled_interviews(self, recruiter_email=None):
        """Get all scheduled interviews"""
        interviews = []
        
        for file in os.listdir(self.confirmations_folder):
            if file.endswith('.json'):
                path = os.path.join(self.confirmations_folder, file)
                with open(path, 'r') as f:
                    conf = json.load(f)
                
                if recruiter_email and conf['recruiter_email'] != recruiter_email:
                    continue
                
                interviews.append(conf)
        
        # Sort by date
        interviews.sort(key=lambda x: x['slot']['date'] + x['slot']['start_time'])
        return interviews
    
    def get_invitation_by_token(self, token):
        """Get invitation details by token"""
        inv_path = os.path.join(self.invitations_folder, f"{token}.json")
        if os.path.exists(inv_path):
            with open(inv_path, 'r') as f:
                return json.load(f)
        return None
    
    def extract_email_from_resume(self, parsed_data):
        """Extract email from parsed resume data"""
        text = parsed_data.get('text', '')
        # Simple email regex
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return emails[0] if emails else None