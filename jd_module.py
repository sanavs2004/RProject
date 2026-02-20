import requests
import re
import os
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/api/generate"
STORE_FOLDER = "jd_store"
MODEL_NAME = "phi3"


# ==============================
# Generate Job Description
# ==============================
def generate_job_description(role, skills, experience):
    """
    Generate a job description using Phi-3 via Ollama.
    Saves both latest and timestamped copies.
    Returns the cleaned JD text.
    Raises exception on failure.
    """

    prompt = f"""
You are an HR professional.

Write a formal Job Description using EXACT formatting below.

Role Summary:
<2–3 lines>

Key Responsibilities:
- point
- point
- point
- point

Required Qualifications:
- point
- point
- point
- point

Rules:
- Leave one blank line between sections.
- Use hyphen bullets only.
- Do not use markdown or symbols.
- Keep sentences concise.

Job Title: {role}
Experience Required: {experience} years
Key Skills: {', '.join(skills)}
"""

    # 🔥 Increased timeout for model cold start
    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
        timeout=180
    )

    response.raise_for_status()
    result = response.json()

    raw_jd = result.get("response", "").strip()
    if not raw_jd:
        raise RuntimeError("Empty response from model")

    cleaned_jd = clean_jd_output(raw_jd)

    # Save files
    os.makedirs(STORE_FOLDER, exist_ok=True)

    # Save latest
    with open(os.path.join(STORE_FOLDER, "latest_jd.txt"), "w", encoding="utf-8") as f:
        f.write(cleaned_jd)

    # Save timestamped
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"jd_{timestamp}.txt"
    with open(os.path.join(STORE_FOLDER, filename), "w", encoding="utf-8") as f:
        f.write(cleaned_jd)

    return cleaned_jd


# ==============================
# Get JD History
# ==============================
def get_all_jds():
    if not os.path.exists(STORE_FOLDER):
        return []

    jds = []
    for file in os.listdir(STORE_FOLDER):
        if file.startswith("jd_") and file.endswith(".txt"):
            path = os.path.join(STORE_FOLDER, file)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            jds.append({
                "filename": file,
                "content": content
            })

    # newest first
    jds.sort(key=lambda x: x["filename"], reverse=True)
    return jds


# ==============================
# Clean JD Output
# ==============================
def clean_jd_output(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)

    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        line = line.replace('•', '-')
        if line.startswith(('-', '*', '•')):
            line = '- ' + line.lstrip('-*• ').strip()

        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)
