# 🎓 AI-Powered Personalized Learning Platform (FYP)

An intelligent, adaptive e-learning web application built to customize the educational journey of students. It analyzes student performance in real-time, extracts YouTube video transcripts, generates smart quizzes and notes using Gemini AI, detects academic weaknesses, and refines video recommendation weights dynamically.

---

## 🌟 Core Features

### 🧠 1. Intelligent Onboarding Flow
A progressive 4-step user onboarding process that tailors initial platform settings based on the student's age, category, stream, and current confidence:
- **Categories:** Primary, Secondary, Matriculation, Intermediate (ICS, Pre-Med, Pre-Eng, Arts, Commerce), University (by Department & Field), and Professional.
- **Seeded Topics:** Instantly initializes recommendations based on choices.

### 📱 2. Modern YouTube-Style Dashboard
- Real-time recommended videos based on selected field and skill level.
- Carousel of active videos in the **Continue Learning** list.
- Dynamic **Recently Watched** history log.
- Displays **Weak Topics** cards only when the student encounters difficulty in quizzes.

### 📝 3. AI-Powered Notes Generator
- Automatically extracts YouTube video transcripts using `youtube-transcript-api`.
- Summarizes content into three distinct levels: **Beginner**, **Intermediate**, and **Advanced**.
- Formats notes with headings, core definitions, code snippets, equations, and practice questions.

### 🎯 4. AI-Powered Quiz Generation & Adaptive Grading
- Generates 10 contextual MCQs directly from video transcripts.
- Evaluates student answers and alters difficulty levels dynamically:
  - **Score ≥ 85%:** Promotes the user to the next difficulty level.
  - **Score 60-84%:** Retains current difficulty level.
  - **Score < 60%:** Lowers difficulty and flags the subject under **Weak Topics**.

### 🚀 5. Adaptive Recommendation Engine
Evolves dynamically using weighted priorities:
- **Weak Topics:** 50% priority (restores confidence first).
- **Progression Topics:** 30% priority (steps up difficulty).
- **Diverse Topics:** 20% priority (broadens knowledge base).

### 📈 6. Progress Analytics
- Live score trends and learning velocity charts.
- Topic mastery tracking and performance recommendations.

### 🛠️ 7. Sleek Admin Control Panel
A fully modernized, interactive dashboard for administrators to monitor student progress, modify categories, manage MoE systems, and evaluate database state.
- **Theme Switcher:** Includes a modern Light/Dark theme toggle with persisted local state.
- **Responsive Layout:** Repositioned into a fixed vertical sidebar.

---

## 🛠️ Tech Stack

- **Backend:** Flask (Python)
- **Database:** MySQL
- **AI Integrations:** Google Gemini Pro API (GenAI), Groq API
- **Frontend:** HTML5, CSS3 (Custom Variables, CSS Transitions, Responsive Grid), JavaScript (ES6+)
- **Libraries:** `bcrypt`, `mysql-connector-python`, `youtube-transcript-api`, `python-dotenv`

---

## 📁 File Structure

```
ai_learning_platform/
├── app/
│   ├── ai/
│   │   ├── notes_generator.py       # Summarizes transcripts using Gemini API
│   │   ├── quiz_generator.py        # Generates MCQs from transcript text
│   │   ├── recommendation_engine.py  # Weights and ranks video recommendations
│   │   └── weak_topic_analyzer.py   # Flags and manages user struggle areas
│   │
│   ├── routes/
│   │   ├── admin.py                 # Admin Panel views, layout & theme toggle
│   │   ├── auth.py                  # Student login, registration & rate limiters
│   │   ├── dashboard.py             # User home feed and search operations
│   │   └── onboarding.py            # Category-based preference setup
│   │
│   └── utils/
│       ├── auth_helpers.py          # Session utilities and bcrypt hashing
│       └── db.py                    # MySQL pool and query runner
│
├── database/
│   ├── schema.sql                   # Full schema definitions
│   └── seed_data.sql                # Starter educational tables
│
├── static/
│   ├── css/                         # Custom style grids & UI themes
│   └── js/                          # Dashboard & video players
│
├── templates/                       # Jinja2 HTML templates
├── .env                             # Environment configuration keys
├── migrate_schema.py                # Database migrations runner
├── run.py                           # App entry point
└── requirements.txt                 # Python project dependencies
```

---

## 🚀 Quick Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/ai_learning_platform.git
cd ai_learning_platform
```

### 2. Set Up Virtual Environment & Dependencies
```bash
# Create virtual environment
python -m venv venv
# Activate it (Windows)
venv\Scripts\activate
# Activate it (Mac/Linux)
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Database Migration
1. Ensure your MySQL server is running.
2. Create a database named `ai_learning_platform`.
3. Import the main schema:
   ```bash
   mysql -u root -p ai_learning_platform < database/schema.sql
   ```
4. Run the schema migrations python script to populate educational lists and classes:
   ```bash
   python migrate_schema.py
   ```

### 4. Environment Configuration
Create a `.env` file at the root directory and define your credentials:
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=ai_learning_platform

SECRET_KEY=your_flask_secret_key
GOOGLE_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
```

### 5. Running the Application
```bash
python run.py
```
Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 🔒 Default Admin Credentials
* **Email:** `admin@ailearn.com`
* **Password:** `admin123`
* **URL:** `/admin/login`

---

## 📜 License
This project is licensed under the MIT License - see the LICENSE file for details.
