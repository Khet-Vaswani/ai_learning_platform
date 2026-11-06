# LearnAI — AI-Powered Personalized Learning Platform

LearnAI is an adaptive e-learning web application. It recommends educational YouTube videos to each student, builds notes and quizzes **strictly from what is said in each video**, adjusts quiz difficulty to the student's own scores, tracks weak topics, and includes an AI assistant that knows the student's progress and can answer questions about the videos they watched.

Built with **Flask**, **MySQL/MariaDB**, **Groq** and **Google Gemini**, with a **Mixture-of-Experts (MoE)** recommendation engine.

> Final Year Project. See [`fyp_system_architecture.svg`](fyp_system_architecture.svg) and [`fyp_flowchart_architecture.svg`](fyp_flowchart_architecture.svg) for the architecture and flow diagrams.

---

## Contents

- [Features](#features)
- [How it works](#how-it-works)
- [Tech stack](#tech-stack)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Project structure](#project-structure)
- [Testing](#testing)
- [Security notes](#security-notes)
- [Roadmap](#roadmap)

---

## Features

### For students

| Feature | What it does |
|---|---|
| **Personalized onboarding** | Education level (school, college, university, professional), department and field of interest set up the first recommendations. |
| **Video recommendations** | A Mixture-of-Experts engine balances weak topics, progression and variety. Students can mark a video *helpful*, *already know it* or *not for me* to tune results. |
| **Transcript-grounded notes** | Study notes in English, generated only from the video's transcript, never from its title or description. |
| **Transcript-grounded quizzes** | Multiple-choice questions where every question carries a quote from the transcript that is checked automatically before the quiz is shown. |
| **Adaptive quiz levels** | Each quiz has one level (Easy, Medium or Hard) chosen from the student's recent scores on that topic. |
| **Weak topic tracking** | Topics scored under 50% are flagged and prioritized in recommendations. |
| **AI learning assistant** | Answers general questions, reads uploaded files (PDF, Word, text, code, images) and knows the student's own scores, weak topics and study plan. |
| **Ask about a video** | Answers what the teacher said in a watched video, with quotes from the transcript, and keeps any general explanation clearly separate. |
| **Progress analytics** | Score trends, topic mastery, quiz history, learning curves and study time. |
| **Social sign-in** | Email and password, or Google, GitHub and LinkedIn (OAuth 2.0). |

### For administrators

- Dashboard with platform statistics
- Student management and per-student progress
- Educational category management
- Reports and MoE recommendation-engine evaluation (precision, recall, NDCG, hit rate)

---

## How it works

### Transcript pipeline

Notes, quizzes and video answers are only produced from a real transcript. Sources are tried in this order:

1. Cached transcript in the database
2. YouTube captions: English manual, English auto-generated, then YouTube's English translation of the original captions
3. Subtitles through `yt-dlp`
4. Speech-to-text from the audio (Groq Whisper, then local Whisper)

If none works, the student sees a clear message. The platform never falls back to the title, description or general topic.

### Grounding checks

- **Quizzes:** each question includes an evidence quote. Questions whose quote does not match the transcript are discarded.
- **Video answers:** the "From the video" part is only shown when its supporting quotes match the transcript. Otherwise the assistant says the teacher did not explain it and gives a separately labelled general answer.

### Quiz levels

| Recent average on the topic | Next quiz |
|---|---|
| 80% or more | Hard (apply and analyse) |
| 50% to 79% | Medium (understand and compare) |
| Under 50% | Easy (recall facts and definitions) |

The level comes from the last 3 quizzes on the topic, then the last 5 quizzes overall, then the student's profile level.

### AI providers

Groq (`openai/gpt-oss-120b`, `qwen/qwen3.8-27b`, `openai/gpt-oss-20b`) is the primary provider, with Google Gemini as the fallback and for image and scanned-PDF understanding.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, Flask (blueprints) |
| Database | MySQL 8 or MariaDB 10.4+ (`mysql-connector-python`, connection pool) |
| AI | Groq API, Google Gemini (`google-genai`), Whisper |
| Video data | YouTube Data API v3, `youtube-transcript-api`, `yt-dlp` |
| Recommendations | Custom Mixture-of-Experts engine with an attention-based router |
| Frontend | Jinja2 templates, Bootstrap 5, custom CSS design system, vanilla JavaScript, Chart.js |
| Auth | bcrypt password hashing, OAuth 2.0 (Google, GitHub, LinkedIn) |

---

## Getting started

### Prerequisites

- Python 3.11
- MySQL or MariaDB running locally (XAMPP works)
- API keys: [Groq](https://console.groq.com), [Google Gemini](https://aistudio.google.com), [YouTube Data API v3](https://console.cloud.google.com)
- Optional: [FFmpeg](https://ffmpeg.org) on your `PATH`, needed for speech-to-text on videos without captions

### 1. Clone the repository

```bash
git clone https://github.com/Khet-Vaswani/ai_learning_platform.git
cd ai_learning_platform
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Or on macOS and Linux:

```bash
source venv/bin/activate
```

Then install the packages:

```bash
pip install -r requirements.txt
```

Optional, for local speech-to-text (large download):

```bash
pip install openai-whisper torch
```

### 3. Configure the environment

Copy the example file and fill in your own values (see [Configuration](#configuration)):

```bash
cp .env.example .env
```

### 4. Start the database

Start MySQL (for example, click **Start** next to MySQL in the XAMPP Control Panel). You don't need to import anything by hand: on startup the app creates the database and applies `database/schema.sql`, `schema_updates.sql` and `seed_data.sql`.

### 5. Create an admin account

```bash
python create_admin.py admin@example.com "Choose-A-Strong-Password" "Administrator"
```

### 6. Run the app

```bash
python run.py
```

Open <http://localhost:5000>. The admin panel is at <http://localhost:5000/admin/login>.

---

## Configuration

All settings live in `.env`. Never commit this file.

| Variable | Required | Purpose |
|---|---|---|
| `SECRET_KEY` | Yes | Flask session signing. Use a long random string. |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Yes | Database connection |
| `GROQ_API_KEY` | Yes | Primary AI provider and Whisper speech-to-text |
| `GEMINI_API_KEY` | Recommended | AI fallback, image and scanned-PDF analysis |
| `YOUTUBE_API_KEY` | Yes | Video search and details |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Optional | Sign in with Google |
| `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` | Optional | Sign in with GitHub |
| `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET` | Optional | Sign in with LinkedIn |
| `OAUTHLIB_INSECURE_TRANSPORT` | Local only | Set to `1` to allow OAuth over plain HTTP on localhost |

### OAuth redirect URLs

Register these in each provider's developer console (add both `localhost` and `127.0.0.1` for local development):

| Provider | Redirect URL |
|---|---|
| Google | `http://localhost:5000/auth/google/callback` |
| GitHub | `http://localhost:5000/auth/github/callback` |
| LinkedIn | `http://localhost:5000/auth/linkedin/callback` (also enable *Sign In with LinkedIn using OpenID Connect*) |

---

## Project structure

```
ai_learning_platform/
├── app/
│   ├── ai/                        # AI and learning logic
│   │   ├── transcript_extractor.py   # Captions → yt-dlp → Whisper pipeline
│   │   ├── quiz_generator.py         # Grounded quizzes and level selection
│   │   ├── notes_generator.py        # Transcript-only study notes
│   │   ├── video_qa.py               # Chatbot answers from a video's transcript
│   │   ├── moe_engine.py             # Mixture-of-Experts recommender
│   │   ├── recommendation_engine.py  # Recommendation helpers
│   │   ├── evaluator.py              # Precision, recall, NDCG, hit rate
│   │   ├── learning_curve.py         # Learning curve tracking
│   │   ├── weak_topic_analyzer.py    # Weak topic detection
│   │   └── speech_to_text.py, audio_extractor.py
│   ├── routes/                    # Flask blueprints
│   │   ├── auth.py, social_auth.py   # Login, registration, password reset, OAuth
│   │   ├── dashboard.py              # Student pages
│   │   ├── gemini.py                 # Notes, quizzes and chatbot APIs
│   │   ├── recommend.py, youtube.py  # Recommendations and video APIs
│   │   ├── onboarding.py
│   │   └── admin.py
│   └── utils/                     # Database pool, auth helpers, notifications
├── database/
│   ├── schema.sql                 # Core tables
│   ├── schema_updates.sql         # Incremental changes (safe to re-run)
│   └── seed_data.sql              # Educational categories and starter data
├── static/                        # CSS (shared design system in ui.css) and JavaScript
├── templates/                     # Jinja2 pages, partials and admin templates
├── tests/                         # Unit tests (no database, network or API keys)
├── migrate_schema.py              # Applies the SQL files (runs automatically on startup)
├── create_admin.py                # Creates or resets an admin account
├── run.py                         # Entry point
└── requirements.txt
```

---

## Testing

The unit tests replace the database and AI calls with fakes, so they need no database, network or API keys:

```bash
python -m unittest discover tests -v
```

They cover transcript validation, quiz grounding, scoring and levels, adaptive difficulty, learning curves, the MoE gate and experts, topic mapping, evaluation metrics and password hashing.

---

## Deploying to Vercel

The repository is ready for Vercel (`pyproject.toml` sets the entrypoint `run:app`). Every push to `main` redeploys.

1. **Database:** Vercel does not host MySQL. Create a free MySQL service on [Aiven](https://aiven.io) (or any MySQL 8 host).
2. **Import** the GitHub repository in Vercel with the **Flask** preset.
3. **Environment variables** (Settings → Environment Variables), using the values from `.env.example`:
   - Required: `SECRET_KEY`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `GROQ_API_KEY`, `YOUTUBE_API_KEY`
   - Recommended: `GEMINI_API_KEY`, `DB_POOL_SIZE=2`
   - Optional: OAuth client IDs and secrets, `YT_PROXY_URL`
   - Do not set `OAUTHLIB_INSECURE_TRANSPORT` on the live site.
4. **Deploy.** The first request creates the tables (later starts skip this unless the SQL files change).
5. **Admin account:** run `python create_admin.py <email> <password> "<name>"` with the hosted database's `DB_*` values set in your terminal.
6. **OAuth:** add `https://<your-site>.vercel.app/auth/<google|github|linkedin>/callback` in each provider's console.

**YouTube API key:** set *Application restrictions* to **None** (the app calls YouTube from the server, so a *Websites* restriction blocks it) and *API restrictions* to **YouTube Data API v3**.

**Transcripts on Vercel:** YouTube often blocks caption requests from cloud servers. Two fixes:
- Free: run `python sync_transcripts.py` on your own computer with the hosted database's `DB_*` values set in the terminal. It fetches transcripts for the videos the site shows and saves them in the database, which the live site uses first.
- Automatic: set `YT_PROXY_URL` to a residential proxy.

**Other limits on Vercel:** Speech-to-text for videos without captions is not available (no FFmpeg). Chat uploads are limited to 3 MB.

---

## Security notes

- Keep `.env` out of version control, and rotate any key that has been committed.
- `python run.py` starts Flask's development server with debug mode on. Use it only on your own machine. For deployment, turn debug off and run behind a production server (for example Waitress or Gunicorn) with HTTPS.
- Passwords are hashed with bcrypt. OAuth uses a `state` check, and only verified provider emails are linked to accounts.
- The assistant only reads the logged-in student's own data and their own watched videos.

---

## Roadmap

- Video timestamps in answers and quiz explanations
- Spaced repetition for missed questions
- Learning paths and certificates
- Chat history saved to the account
- Free and Premium plans

---

## Author

**Khet Vaswani** — Final Year Project

## License

No license has been chosen yet, so all rights are reserved by default. Add a `LICENSE` file (for example MIT) before others reuse the code.
