"""
Tailor - tailor your resume + cover letter to a specific job, using AI.

Flow:
  1. Paste your current resume and the job description.
  2. Pick a cover-letter tone.
  3. The app sends both to Google's Gemini model and gets back:
       - a match score
       - keywords the job wants that your resume is missing
       - rewritten, tailored resume bullets
       - a drafted cover letter
  4. The page shows it all, with copy buttons.

Runs on Google's FREE Gemini tier. Get a key at https://aistudio.google.com
Run with:  python app.py     (or double-click run.bat on Windows)
"""

import os
import re
import json
import threading
import webbrowser

import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Stable, free-tier Gemini model. (gemini-2.0-flash was retired June 2026.)
# You can change this to a newer model later if you like.
MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

# Keep inputs sane
MAX_CHARS = 12000

app = Flask(__name__)


def build_prompt(resume, job, tone):
    return f"""You are an expert resume writer and career coach.

A candidate wants to tailor their resume to a specific job posting.

THEIR CURRENT RESUME:
\"\"\"
{resume[:MAX_CHARS]}
\"\"\"

THE JOB DESCRIPTION:
\"\"\"
{job[:MAX_CHARS]}
\"\"\"

Return ONLY a JSON object with exactly these keys:
{{
  "match_score": <integer 0-100: how well the current resume matches this job>,
  "summary": "<one sentence on how strong the match is and the biggest gap>",
  "missing_keywords": [<up to 8 important skills/terms in the job description that are NOT in the resume>],
  "present_keywords": [<up to 8 important skills/terms the resume ALREADY shows that match the job>],
  "tailored_bullets": [<5-7 rewritten resume bullet points tailored to THIS job, strong action verbs, results-oriented>],
  "cover_letter": "<a {tone} cover letter, 150-220 words, tailored to this job>"
}}

Rules:
- Be honest. Do NOT invent jobs, employers, skills, degrees, certifications, or numbers the candidate did not provide.
- Only use the job's terminology where the candidate genuinely has that experience.
- Keep bullets concise and concrete.
- The cover letter must read naturally and be faithful to the candidate's real background."""


def parse_json_loosely(s):
    s = (s or "").strip()
    s = re.sub(r"^```(?:json)?", "", s).strip()
    s = re.sub(r"```$", "", s).strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(s[start:end + 1])
        except Exception:
            return None
    return None


def call_gemini(resume, job, tone):
    if not GEMINI_API_KEY:
        raise ValueError(
            "No Gemini API key found. Add it to the .env file "
            "(GEMINI_API_KEY=...) and restart. Get a free key at "
            "https://aistudio.google.com"
        )

    body = {
        "contents": [{"parts": [{"text": build_prompt(resume, job, tone)}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048,
            # ask Gemini to return strict JSON so it parses cleanly
            "responseMimeType": "application/json",
        },
    }

    resp = requests.post(
        GEMINI_URL,
        headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
        json=body,
        timeout=60,
    )

    if resp.status_code in (400, 403) and "API_KEY" in resp.text.upper():
        raise ValueError("Your Gemini API key was rejected. Check it in the .env file.")
    if resp.status_code == 429:
        raise ValueError("Hit the free-tier rate limit. Wait a minute and try again.")
    if resp.status_code != 200:
        raise ValueError(f"The AI service returned an error (HTTP {resp.status_code}).")

    data = resp.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise ValueError("The AI didn't return a result. Try shortening your inputs.")

    parts = candidates[0].get("content", {}).get("parts", [])
    text = parts[0].get("text", "") if parts else ""

    parsed = parse_json_loosely(text)
    if not parsed:
        return {"raw": text.strip()}
    return parsed


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/tailor", methods=["POST"])
def tailor():
    payload = request.get_json(silent=True) or {}
    resume = (payload.get("resume") or "").strip()
    job = (payload.get("job") or "").strip()
    tone = (payload.get("tone") or "professional").strip()

    if len(resume) < 30:
        return jsonify({"error": "Please paste your resume (a bit more detail needed)."}), 400
    if len(job) < 30:
        return jsonify({"error": "Please paste the job description."}), 400

    try:
        result = call_gemini(resume, job, tone)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Something went wrong: {e}"}), 500


def open_browser():
    if not os.getenv("NO_BROWSER"):
        webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    threading.Timer(1.2, open_browser).start()
    print("\n  Tailor is running!  Open http://127.0.0.1:5000 in your browser.\n")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
