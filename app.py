from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import hashlib
import os
from groq import Groq
from datetime import datetime
import markdown as md_lib

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "studymate_secret_key_2026")

# Register markdown filter for Jinja2 templates
@app.template_filter('markdown')
def markdown_filter(text):
    import markdown as md_lib
    return md_lib.markdown(text or "", extensions=['nl2br', 'fenced_code'])

# ─── DATABASE SETUP ────────────────────────────────────────────────────────

def get_db():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "studymate.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            has_seen_onboarding INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Add column to existing databases that don't have it yet
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN has_seen_onboarding INTEGER DEFAULT 0")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN has_seen_security_notice INTEGER DEFAULT 0")
    except:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            response TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subjects TEXT NOT NULL,
            hours_per_day INTEGER NOT NULL,
            plan_content TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            level TEXT NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()

# ─── HELPER FUNCTIONS ──────────────────────────────────────────────────────

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def render_markdown(text):
    """Convert markdown text to safe HTML."""
    return md_lib.markdown(text, extensions=['nl2br', 'fenced_code'])

def call_ai_api(messages):
    try:
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def save_session(user_id, question, response):
    conn = get_db()
    conn.execute(
        "INSERT INTO sessions (user_id, question, response) VALUES (?, ?, ?)",
        (user_id, question, response)
    )
    conn.commit()
    conn.close()

def get_chat_history(user_id, limit=20):
    """Load the last N messages for a user from the database."""
    conn = get_db()
    rows = conn.execute(
        "SELECT question, response FROM sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    # Reverse so oldest is first
    rows = list(reversed(rows))
    return [{"question": r["question"], "response": r["response"]} for r in rows]

def get_user_stats(user_id):
    conn = get_db()
    total_questions = conn.execute(
        "SELECT COUNT(*) as count FROM sessions WHERE user_id = ?", (user_id,)
    ).fetchone()["count"]

    total_plans = conn.execute(
        "SELECT COUNT(*) as count FROM study_plans WHERE user_id = ?", (user_id,)
    ).fetchone()["count"]

    recent_sessions = conn.execute(
        "SELECT DATE(created_at) as date, COUNT(*) as count FROM sessions WHERE user_id = ? GROUP BY DATE(created_at) ORDER BY date DESC LIMIT 7",
        (user_id,)
    ).fetchall()

    total_quizzes = conn.execute(
        "SELECT COUNT(*) as count FROM quiz_results WHERE user_id = ?", (user_id,)
    ).fetchone()["count"]

    avg_score_row = conn.execute(
        "SELECT AVG(CAST(score AS FLOAT) / total * 100) as avg FROM quiz_results WHERE user_id = ?", (user_id,)
    ).fetchone()["avg"]

    recent_quizzes = conn.execute(
        "SELECT topic, level, score, total, created_at FROM quiz_results WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
        (user_id,)
    ).fetchall()

    study_plan_history = conn.execute(
        "SELECT subjects, hours_per_day, plan_content, created_at FROM study_plans WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
        (user_id,)
    ).fetchall()

    conn.close()
    return {
        "total_questions": total_questions,
        "total_plans": total_plans,
        "recent_sessions": [{"date": s["date"], "count": s["count"]} for s in recent_sessions],
        "total_quizzes": total_quizzes,
        "avg_score": round(avg_score_row) if avg_score_row else 0,
        "recent_quizzes": [{"topic": q["topic"], "level": q["level"], "score": q["score"], "total": q["total"], "created_at": q["created_at"]} for q in recent_quizzes],
        "study_plan_history": [{"subjects": p["subjects"], "hours_per_day": p["hours_per_day"], "plan_content": p["plan_content"], "created_at": p["created_at"]} for p in study_plan_history]
    }

# ─── ROUTES ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not full_name or not email or not password:
            return render_template("register.html", error="All fields are required.")

        conn = get_db()
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            conn.close()
            return render_template("register.html", error="This email is already registered.")

        conn.execute(
            "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
            (full_name, email, hash_password(password))
        )
        conn.commit()
        conn.close()
        # Flag so login page knows this is a brand new user
        session["show_onboarding"] = True
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ? AND password_hash = ?",
            (email, hash_password(password))
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            # Show onboarding if new registration OR first ever login
            if session.get("show_onboarding") or not user["has_seen_onboarding"]:
                session["show_onboarding"] = True
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid email or password.")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    stats = get_user_stats(session["user_id"])
    show_onboarding = session.pop("show_onboarding", False)

    # Check if user has seen the security notice
    conn = get_db()
    user = conn.execute("SELECT has_seen_security_notice FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    conn.close()
    show_security_notice = not user["has_seen_security_notice"] if user else False

    return render_template("dashboard.html", user_name=session["user_name"], stats=stats, show_onboarding=show_onboarding, show_security_notice=show_security_notice)

@app.route("/dismiss-security-notice", methods=["POST"])
def dismiss_security_notice():
    if "user_id" in session:
        conn = get_db()
        conn.execute("UPDATE users SET has_seen_security_notice = 1 WHERE id = ?", (session["user_id"],))
        conn.commit()
        conn.close()
    return jsonify({"ok": True})

@app.route("/dismiss-onboarding", methods=["POST"])
def dismiss_onboarding():
    if "user_id" in session:
        conn = get_db()
        conn.execute("UPDATE users SET has_seen_onboarding = 1 WHERE id = ?", (session["user_id"],))
        conn.commit()
        conn.close()
    return jsonify({"ok": True})

@app.route("/chat")
def chat():
    if "user_id" not in session:
        return redirect(url_for("login"))
    # Load last 20 messages from the database
    history = get_chat_history(session["user_id"], limit=20)
    return render_template("chat.html", user_name=session["user_name"], history=history)

@app.route("/ask", methods=["POST"])
def ask():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    question = data.get("question", "").strip()
    # Frontend still sends its live session history (messages since page load)
    frontend_history = data.get("history", [])

    if not question:
        return jsonify({"error": "No question provided"}), 400

    messages = [
        {
            "role": "system",
            "content": "You are StudyMate, a helpful AI study assistant for undergraduate students. Answer academic questions clearly, simply, and helpfully. Keep responses concise and easy to understand. Always remember the context of the conversation."
        }
    ]

    # Load persistent DB history (last 20 messages) for AI context
    db_history = get_chat_history(session["user_id"], limit=20)

    # Add DB history first (older context)
    for entry in db_history:
        messages.append({"role": "user", "content": entry["question"]})
        messages.append({"role": "assistant", "content": entry["response"]})

    # Add any live messages from this session not yet saved
    for entry in frontend_history:
        # Avoid duplicating what's already in DB history
        if not any(d["question"] == entry["question"] for d in db_history):
            messages.append({"role": "user", "content": entry["question"]})
            messages.append({"role": "assistant", "content": entry["response"]})

    messages.append({"role": "user", "content": question})

    response = call_ai_api(messages)
    save_session(session["user_id"], question, response)
    response_html = render_markdown(response)
    return jsonify({"response": response, "response_html": response_html})

@app.route("/clear-chat", methods=["POST"])
def clear_chat():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE user_id = ?", (session["user_id"],))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/study-plan", methods=["GET", "POST"])
def study_plan():
    if "user_id" not in session:
        return redirect(url_for("login"))

    plan = None
    if request.method == "POST":
        subjects = request.form.get("subjects", "").strip()
        priority = request.form.get("priority", "balanced")
        notes = request.form.get("notes", "").strip()

        # Build schedule from selected days and times
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        schedule_lines = []
        total_hours = 0

        for day in days:
            if request.form.get(f"day_{day}"):
                start = request.form.get(f"start_{day}", "08:00")
                end = request.form.get(f"end_{day}", "10:00")
                # Calculate hours for this day
                try:
                    sh, sm = map(int, start.split(":"))
                    eh, em = map(int, end.split(":"))
                    duration = (eh * 60 + em - sh * 60 - sm) / 60
                    total_hours += duration
                    schedule_lines.append(f"  - {day}: {start} to {end} ({duration:.1f} hours)")
                except:
                    schedule_lines.append(f"  - {day}: {start} to {end}")

        if not schedule_lines:
            return render_template("study_plan.html", user_name=session["user_name"], plan=None,
                                   error="Please select at least one study day.")

        schedule_text = "\n".join(schedule_lines)

        priority_map = {
            "balanced": "Distribute time equally across all subjects.",
            "weak":     "Allocate more time to subjects the student finds difficult, spread them across more sessions.",
            "exam":     "Prioritise subjects with upcoming exams, giving them the most sessions this week."
        }
        priority_instruction = priority_map.get(priority, priority_map["balanced"])

        prompt = f"""Create a detailed personalised weekly study timetable for an undergraduate student.

SUBJECTS: {subjects}

AVAILABLE STUDY SCHEDULE (days and exact time windows the student is free):
{schedule_text}

STUDY PRIORITY: {priority_instruction}

{"ADDITIONAL NOTES: " + notes if notes else ""}

INSTRUCTIONS:
- Only schedule study sessions on the days and within the exact time windows listed above. Do not add sessions on other days or outside these times.
- Break each day's available time into focused study blocks (e.g. 45-60 minutes per subject with short breaks).
- Assign specific subjects to specific time slots — do not leave slots vague.
- Format the timetable clearly, day by day, showing the time, subject, and what to focus on.
- Always display times in 12-hour format with AM or PM (e.g. 6:00 PM, not 18:00).
- End with a short motivational tip for the student."""

        messages = [
            {
                "role": "system",
                "content": "You are StudyMate, a helpful AI study assistant for undergraduate students. Create clear, practical, and detailed study timetables that respect the student's exact available time windows."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        plan = call_ai_api(messages)

        conn = get_db()
        conn.execute(
            "INSERT INTO study_plans (user_id, subjects, hours_per_day, plan_content) VALUES (?, ?, ?, ?)",
            (session["user_id"], subjects, int(total_hours), plan)
        )
        conn.commit()
        conn.close()

    plan_html = render_markdown(plan) if plan else None
    return render_template("study_plan.html", user_name=session["user_name"], plan=plan, plan_html=plan_html)

@app.route("/performance")
def performance():
    if "user_id" not in session:
        return redirect(url_for("login"))
    stats = get_user_stats(session["user_id"])
    return render_template("performance.html", user_name=session["user_name"], stats=stats)

# ─── QUIZ ROUTES ───────────────────────────────────────────────────────────

@app.route("/quiz")
def quiz():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("quiz.html", user_name=session["user_name"])

@app.route("/generate-quiz", methods=["POST"])
def generate_quiz():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    topic = data.get("topic", "").strip()
    level = data.get("level", "High School")
    num_questions = int(data.get("num_questions", 5))

    if not topic:
        return jsonify({"error": "Please enter a topic"}), 400

    prompt = f"""Generate exactly {num_questions} multiple choice questions on the topic: "{topic}" for a {level} level student.

Return ONLY a valid JSON array with no extra text, no markdown, no explanation. Just the raw JSON array.

Format:
[
  {{
    "question": "Question text here?",
    "options": ["A. Option one", "B. Option two", "C. Option three", "D. Option four"],
    "answer": "A",
    "explanation": "Brief explanation of why A is correct."
  }}
]

Rules:
- Each question must have exactly 4 options labeled A, B, C, D
- The answer field must be just the letter: A, B, C, or D
- Questions must be relevant to {topic} at {level} level
- Make questions clear and unambiguous"""

    messages = [
        {
            "role": "system",
            "content": "You are a quiz generator. You must return only valid JSON arrays with no markdown formatting, no code blocks, no extra text. Just raw JSON."
        },
        {"role": "user", "content": prompt}
    ]

    try:
        import re, json
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        response = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        questions = json.loads(raw)
        return jsonify({"questions": questions, "topic": topic, "level": level})
    except Exception as e:
        return jsonify({"error": f"Failed to generate quiz: {str(e)}"}), 500

@app.route("/save-quiz-result", methods=["POST"])
def save_quiz_result():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    data = request.get_json()
    topic = data.get("topic", "Unknown")
    level = data.get("level", "High School")
    score = int(data.get("score", 0))
    total = int(data.get("total", 0))
    conn = get_db()
    conn.execute(
        "INSERT INTO quiz_results (user_id, topic, level, score, total) VALUES (?, ?, ?, ?, ?)",
        (session["user_id"], topic, level, score, total)
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

# ─── PWA ROUTES ────────────────────────────────────────────────────────────

@app.route("/manifest.json")
def manifest():
    return app.send_static_file("manifest.json")

@app.route("/service_worker.js")
def service_worker():
    from flask import Response
    sw_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "service_worker.js")
    with open(sw_path, 'r') as f:
        content = f.read()
    return Response(content, mimetype='application/javascript')

# ─── PROFILE ROUTES ────────────────────────────────────────────────────────

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    conn.close()

    success = None
    error = None

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_name":
            new_name = request.form.get("full_name", "").strip()
            if not new_name:
                error = "Name cannot be empty."
            else:
                conn = get_db()
                conn.execute("UPDATE users SET full_name = ? WHERE id = ?", (new_name, session["user_id"]))
                conn.commit()
                conn.close()
                session["user_name"] = new_name
                success = "Your name has been updated successfully."
                # Refresh user data
                conn = get_db()
                user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
                conn.close()

        elif action == "update_email":
            new_email = request.form.get("email", "").strip().lower()
            if not new_email:
                error = "Email cannot be empty."
            else:
                conn = get_db()
                existing = conn.execute(
                    "SELECT id FROM users WHERE email = ? AND id != ?",
                    (new_email, session["user_id"])
                ).fetchone()
                if existing:
                    conn.close()
                    error = "That email address is already used by another account."
                else:
                    conn.execute("UPDATE users SET email = ? WHERE id = ?", (new_email, session["user_id"]))
                    conn.commit()
                    conn.close()
                    success = "Your email has been updated successfully."
                    conn = get_db()
                    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
                    conn.close()

        elif action == "update_password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            if not current_password or not new_password or not confirm_password:
                error = "All password fields are required."
            elif new_password != confirm_password:
                error = "New password and confirmation do not match."
            elif len(new_password) < 6:
                error = "New password must be at least 6 characters."
            else:
                conn = get_db()
                valid = conn.execute(
                    "SELECT id FROM users WHERE id = ? AND password_hash = ?",
                    (session["user_id"], hash_password(current_password))
                ).fetchone()
                if not valid:
                    conn.close()
                    error = "Your current password is incorrect."
                else:
                    conn.execute(
                        "UPDATE users SET password_hash = ? WHERE id = ?",
                        (hash_password(new_password), session["user_id"])
                    )
                    conn.commit()
                    conn.close()
                    success = "Your password has been changed successfully."

    return render_template("profile.html", user=user, user_name=session["user_name"], success=success, error=error)

# ─── ERROR HANDLERS ────────────────────────────────────────────────────────

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500

# ─── RUN APP ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
