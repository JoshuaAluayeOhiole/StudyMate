# StudyMate: AI-Powered Study Assistant

**StudyMate** is a web based AI-powered study assistant designed for high school students, university students, and self learners. It was built as a final year Computer Science project at the Global Wealth University, Benin City Study Centre, Nigeria
*(Global Wealth University -Headquartered in Lome, Togo)*.

Live demo: [studymate.jaotechgworld.com](https://studymate.jaotechgworld.com)

---

## Features

### AI Study Assistant
Ask any academic or educational question and receive an intelligent, clear response instantly. The AI adapts its explanations to the user's level and remembers conversation history across sessions so users can always continue where they left off. Chat history can be downloaded as a PDF.

### Study Plan Generator
Users select their subjects, choose the exact days and times they are available to study, set a study priority (balanced, focus on weak subjects, or exam mode), and add optional notes. The AI generates a detailed personalised weekly timetable that fits the user's real schedule. The timetable can be downloaded as a PDF with a StudyMate watermark and the user's name.

### AI Quiz Generator
Users can test their knowledge on any topic. The quiz setup adapts to the user's level:
- **High School**: Subject and Topic fields
- **University**: Department, Course Code, and optional Area of Concentration
- **Self-Learner**: Open fields for independent learning topics

The AI generates multiple choice questions (5 to 30), scores the user instantly, provides explanations for every answer, and allows the quiz summary to be downloaded as a PDF.

### Performance Tracker
Tracks total questions asked, study plans generated, quizzes taken, average quiz score, active study days, and study plan history. Includes a bar chart of daily study activity and a doughnut chart of study engagement breakdown.

### User Profile
Users can update their name, email address, and password from the profile page.

### Progressive Web App (PWA)
StudyMate is installable on Android and iOS as a home screen app. It functions like a native mobile application without requiring an app store download.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Database | SQLite |
| AI / LLM | Groq API (Llama 3.3 70B) |
| Frontend | HTML, CSS, JavaScript |
| PDF Generation | jsPDF |
| Markdown Rendering | Python-Markdown |
| Hosting | cPanel shared hosting with Phusion Passenger |

---

## Project Structure

```
studymate/
├── app.py                  # Main Flask application
├── passenger_wsgi.py       # Phusion Passenger entry point
├── requirements.txt        # Python dependencies
├── static/
│   ├── css/
│   │   └── style.css       # Main stylesheet
│   ├── img/
│   │   ├── favicon.ico
│   │   ├── favicon-192.png
│   │   └── favicon-512.png
│   ├── manifest.json       # PWA manifest
│   └── service_worker.js   # PWA service worker
└── templates/
    ├── base.html           # Base layout template
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── chat.html           # AI Study Assistant
    ├── study_plan.html     # Study Plan Generator
    ├── performance.html    # Performance Tracker
    ├── quiz.html           # AI Quiz Generator
    ├── profile.html        # User Profile
    ├── 404.html
    └── 500.html
```

---

## Setup and Installation

### Requirements
- Python 3.10 or higher
- pip

### Steps

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/studymate.git
cd studymate

# Install dependencies
pip install -r requirements.txt

# Set your Groq API key as an environment variable
export GROQ_API_KEY=your_groq_api_key_here

# Run the application
python app.py
```

The app will be available at `http://localhost:5000`

> **Note:** You can get a free Groq API key at [console.groq.com](https://console.groq.com)

---

## Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Your Groq API key for AI functionality |
| `SECRET_KEY` | Flask session secret key (optional, defaults to a development key) |

---

## Database

StudyMate uses SQLite. The database file `studymate.db` is created automatically on first run. It is excluded from this repository via `.gitignore` to protect user data.

---

## Screenshots


![alt text](<registration page.png>) ![alt text](<login page.png>) ![alt text](<dashboard page.png>) ![alt text](<ai chats page.png>) ![alt text](<study plan page.png>) ![alt text](<quiz page.png>) ![alt text](<performance page.png>) ![alt text](< profile page.png>)
---

## Author

**Joshua Aluaye Ohiole**
Final Year Computer Science Student
Global Wealth University, Benin City Study Centre, Nigeria
*(Global Wealth University — Headquartered in Lome, Togo)*

- X (Twitter): [@GoRighteous](https://x.com/GoRighteous)

---

## License

This project was developed as an academic final year project. All rights reserved.

---

## Acknowledgements

- [Groq](https://groq.com) for the fast AI inference API
- [Flask](https://flask.palletsprojects.com) for the web framework
- [jsPDF](https://github.com/parallax/jsPDF) for client-side PDF generation



## Feedback & Contributions

Feel free to:
- Open issues
- Suggest improvements
- Contribute to the project

Your feedback is welcome.
