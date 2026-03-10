"""
Learning Path Email Sender for RecruitAI
Sends personalized learning path emails to rejected/hold candidates
using the same Gmail SMTP setup as InterviewScheduler.
"""

import os
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


# ── HTML email template ──────────────────────────────────────────────────────
EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Your Personalised Learning Path</title>
</head>
<body style="margin:0;padding:0;background:#0d0d14;font-family:'Segoe UI',Arial,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:#0d0d14;padding:40px 0;">
  <tr><td align="center">
  <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

    <!-- Header -->
    <tr>
      <td style="background:linear-gradient(135deg,#1a1a2e,#16213e);border-radius:16px 16px 0 0;padding:40px 40px 32px;text-align:center;border-bottom:1px solid #2a2a3d;">
        <div style="display:inline-block;background:rgba(124,106,255,.15);border:1px solid rgba(124,106,255,.3);border-radius:20px;padding:6px 18px;font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#a89bff;margin-bottom:20px;">
          RecruitAI · Learning Path
        </div>
        <h1 style="margin:0;font-size:26px;font-weight:800;color:#e8e8f0;line-height:1.3;">
          Your Personal Roadmap to<br>
          <span style="color:#7c6aff;">{{ job_title }}</span>
        </h1>
        <p style="margin:16px 0 0;color:#8888aa;font-size:15px;">Hi {{ candidate_name }}, here's exactly how to get there. 🚀</p>
      </td>
    </tr>

    <!-- Body -->
    <tr>
      <td style="background:#12121a;padding:32px 40px;border-left:1px solid #2a2a3d;border-right:1px solid #2a2a3d;">

        <!-- Score + Stats row -->
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
          <tr>
            <td width="33%" style="text-align:center;background:#1a1a26;border:1px solid #2a2a3d;border-radius:12px;padding:16px 8px;">
              <div style="font-size:24px;font-weight:800;color:#7c6aff;">{{ current_score }}%</div>
              <div style="font-size:11px;color:#8888aa;margin-top:4px;text-transform:uppercase;letter-spacing:.07em;">Your Score</div>
            </td>
            <td width="4%"></td>
            <td width="33%" style="text-align:center;background:#1a1a26;border:1px solid #2a2a3d;border-radius:12px;padding:16px 8px;">
              <div style="font-size:24px;font-weight:800;color:#ff6a9b;">{{ skills_count }}</div>
              <div style="font-size:11px;color:#8888aa;margin-top:4px;text-transform:uppercase;letter-spacing:.07em;">Skills to Learn</div>
            </td>
            <td width="4%"></td>
            <td width="33%" style="text-align:center;background:#1a1a26;border:1px solid #2a2a3d;border-radius:12px;padding:16px 8px;">
              <div style="font-size:24px;font-weight:800;color:#6affce;">{{ total_weeks }}w</div>
              <div style="font-size:11px;color:#8888aa;margin-top:4px;text-transform:uppercase;letter-spacing:.07em;">Est. Duration</div>
            </td>
          </tr>
        </table>

        <!-- Motivation -->
        <div style="background:linear-gradient(135deg,rgba(124,106,255,.08),rgba(255,106,155,.05));border:1px solid rgba(124,106,255,.2);border-radius:12px;padding:20px 24px;margin-bottom:28px;">
          <p style="margin:0;font-size:15px;color:#c8c8e0;line-height:1.7;">
            💡 <strong style="color:#e8e8f0;">{{ motivation }}</strong>
          </p>
        </div>

        <!-- Skills to learn -->
        {% if modules %}
        <h2 style="margin:0 0 16px;font-size:16px;font-weight:700;color:#e8e8f0;text-transform:uppercase;letter-spacing:.08em;">
          📚 Your Learning Modules
        </h2>

        {% for module in modules %}
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:14px;background:#1a1a26;border:1px solid #2a2a3d;border-radius:12px;overflow:hidden;">
          <tr>
            <!-- Priority stripe -->
            <td width="4" style="background:{{ module.color }};border-radius:12px 0 0 12px;">&nbsp;</td>
            <td style="padding:16px 20px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <span style="font-size:15px;font-weight:700;color:#e8e8f0;text-transform:capitalize;">{{ module.skill }}</span>
                    <span style="margin-left:10px;font-size:11px;font-weight:600;padding:2px 10px;border-radius:20px;background:{{ module.badge_bg }};color:{{ module.badge_color }};">
                      {{ module.priority_label }}
                    </span>
                  </td>
                  <td align="right" style="font-size:12px;color:#8888aa;white-space:nowrap;">~{{ module.estimated_weeks }} weeks</td>
                </tr>
                {% if module.tip %}
                <tr>
                  <td colspan="2" style="padding-top:8px;">
                    <p style="margin:0;font-size:13px;color:#9999bb;line-height:1.6;font-style:italic;">{{ module.tip }}</p>
                  </td>
                </tr>
                {% endif %}
                <!-- Top course -->
                {% if module.courses %}
                <tr>
                  <td colspan="2" style="padding-top:10px;">
                    <a href="{{ module.courses[0].url }}" style="display:inline-block;font-size:12px;color:#7c6aff;text-decoration:none;border:1px solid rgba(124,106,255,.25);border-radius:6px;padding:5px 12px;">
                      🎓 {{ module.courses[0].title }} — {{ module.courses[0].platform }}
                    </a>
                  </td>
                </tr>
                {% endif %}
              </table>
            </td>
          </tr>
        </table>
        {% endfor %}
        {% endif %}

        <!-- CTA button -->
        <div style="text-align:center;margin:32px 0 8px;">
          <a href="{{ learning_path_url }}"
             style="display:inline-block;background:linear-gradient(135deg,#7c6aff,#ff6a9b);color:#fff;font-size:15px;font-weight:700;text-decoration:none;padding:14px 36px;border-radius:10px;letter-spacing:.03em;">
            View Full Learning Path →
          </a>
          <p style="margin:12px 0 0;font-size:12px;color:#8888aa;">Opens your interactive roadmap with all courses, practice links & timeline.</p>
        </div>

      </td>
    </tr>

    <!-- Footer -->
    <tr>
      <td style="background:#0a0a0f;border-radius:0 0 16px 16px;padding:24px 40px;text-align:center;border:1px solid #2a2a3d;border-top:none;">
        <p style="margin:0;font-size:12px;color:#555570;line-height:1.7;">
          This email was sent by <strong style="color:#7c6aff;">RecruitAI</strong> on behalf of the hiring team.<br>
          Keep working hard — the right opportunity is ahead. 💪
        </p>
      </td>
    </tr>

  </table>
  </td></tr>
</table>
</body>
</html>
"""


def _priority_color(priority: str):
    """Return color, badge_bg, badge_color for a priority level."""
    if priority == 'high':
        return '#ef4444', 'rgba(239,68,68,.15)', '#ef4444'
    if priority == 'medium':
        return '#f59e0b', 'rgba(245,158,11,.15)', '#f59e0b'
    return '#10b981', 'rgba(16,185,129,.15)', '#10b981'


def _render_template(template_str: str, context: dict) -> str:
    """Simple Jinja2-style renderer using string replace + loop logic via Jinja2."""
    try:
        from jinja2 import Template
        return Template(template_str).render(**context)
    except ImportError:
        # Fallback: basic str.format if jinja2 somehow missing
        return template_str


def send_learning_path_email(candidate: dict, job: dict, learning_path: dict, config) -> bool:
    """
    Send the personalised learning path email to a rejected/hold candidate.

    Args:
        candidate   : candidate dict from screening result
        job         : job dict from screening result
        learning_path: learning path dict from LearningPathGenerator.generate()
        config      : Flask Config object (needs SMTP_* env vars or defaults)

    Returns:
        True if sent (or saved in dev mode), False on failure.
    """
    # ── SMTP settings — same env vars as InterviewScheduler ─────────────────
    smtp_server   = os.environ.get('SMTP_SERVER',   'smtp.gmail.com')
    smtp_port     = int(os.environ.get('SMTP_PORT', 587))
    smtp_username = os.environ.get('SMTP_USERNAME', '')
    smtp_password = os.environ.get('SMTP_PASSWORD', '')
    from_email    = os.environ.get('FROM_EMAIL',    'noreply@recruitai.com')

    to_email = candidate.get('email')
    if not to_email or '@' not in to_email:
        print(f"⚠️  No valid email for candidate {candidate.get('filename')} — skipping learning path email.")
        return False

    # ── Build learning path URL ──────────────────────────────────────────────
    base_url = os.environ.get('BASE_URL', 'http://localhost:5002')
    candidate_id = candidate.get('candidate_id', 'unknown')
    learning_path_url = f"{base_url}/learning-path/{candidate_id}"

    # ── Enrich modules with color info for email ─────────────────────────────
    modules = learning_path.get('modules', [])
    for m in modules:
        color, badge_bg, badge_color = _priority_color(m.get('priority', 'medium'))
        m['color']       = color
        m['badge_bg']    = badge_bg
        m['badge_color'] = badge_color

    # ── Render HTML ──────────────────────────────────────────────────────────
    context = {
        'candidate_name'   : learning_path.get('candidate_name', 'Candidate'),
        'job_title'        : job.get('title', 'the role'),
        'current_score'    : f"{candidate.get('overall_score', 0):.0f}",
        'skills_count'     : len(modules),
        'total_weeks'      : learning_path.get('total_estimated_weeks', 0),
        'motivation'       : learning_path.get('motivation', 'Keep going — every skill you learn brings you closer!'),
        'modules'          : modules[:5],          # cap at 5 in email, full list on web page
        'learning_path_url': learning_path_url,
    }
    html_content = _render_template(EMAIL_TEMPLATE, context)

    # ── Build MIME message ───────────────────────────────────────────────────
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Your Learning Path for {job.get('title', 'the role')} — RecruitAI"
    msg['From']    = from_email
    msg['To']      = to_email
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    # ── Send or save (dev mode) ──────────────────────────────────────────────
    try:
        if smtp_username and smtp_password:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            server.quit()
            print(f"✅ Learning path email sent → {to_email}")
        else:
            # Dev mode: save HTML to disk
            email_dir = os.path.join(getattr(config, 'BASE_DIR', '.'), 'interviews', 'emails')
            os.makedirs(email_dir, exist_ok=True)
            filename = f"learning_path_{candidate_id}.html"
            path = os.path.join(email_dir, filename)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"📧 SMTP not configured — learning path email saved to {path}")

        # ── Log the send ─────────────────────────────────────────────────────
        log_dir = os.path.join(getattr(config, 'BASE_DIR', '.'), 'interviews', 'learning_path_emails')
        os.makedirs(log_dir, exist_ok=True)
        log = {
            'candidate_id'  : candidate_id,
            'candidate_email': to_email,
            'job_title'     : job.get('title'),
            'sent_at'       : datetime.now().isoformat(),
            'learning_path_url': learning_path_url,
        }
        with open(os.path.join(log_dir, f"{candidate_id}.json"), 'w') as f:
            json.dump(log, f, indent=2)

        return True

    except Exception as e:
        print(f"❌ Failed to send learning path email to {to_email}: {e}")
        return False