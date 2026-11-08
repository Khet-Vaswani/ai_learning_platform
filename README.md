# StudyWise — AI-Powered Personalized Learning Platform

StudyWise turns educational YouTube videos into a personalized learning experience. It recommends videos for each student's field and level, writes study notes and quizzes **strictly from what is said in each video**, adapts quiz difficulty to the student's own scores, tracks weak topics, and includes an AI assistant that knows the student's progress and can answer questions about the videos they watched.

**Live demo:** <https://ai-learning-platform-ndjy.vercel.app>

Built with **Flask**, **MySQL / MariaDB**, **Groq** and **Google Gemini**, with a **Mixture-of-Experts (MoE)** recommendation engine.

> Final Year Project. Architecture and flow diagrams: [`fyp_system_architecture.svg`](fyp_system_architecture.svg), [`fyp_flowchart_architecture.svg`](fyp_flowchart_architecture.svg).

---

## Contents

- [Features](#features)
- [How it works](#how-it-works)
- [Tech stack](#tech-stack)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Deploying to Vercel](#deploying-to-vercel)
- [Performance](#performance)
- [Project structure](#project-structure)
- [Testing](#testing)
- [Security](#security)
- [Roadmap](#roadmap)

---

## Features

### For students

| Feature | What it does |
|---|---|
| **Personalized onboarding** | School class, college stream, university department and field, or competitive exam (CSS, MDCAT, IELTS…) sets up the first recommendations. Any other field can be typed in Settings. |
| **Video recommendations** | A Mixture-of-Experts engine balances weak topics, progression and variety. Students mark videos *helpful*, *already know it* or *not for me* to tune results. |
| **Transcript-grounded study notes** | Structured notes in English, written only from the video's transcript, never from its title or description. |
| **Transcript-grounded quizzes** | Multiple-choice questions, each backed by a quote from the transcript that is checked automatically. Questions with unverifiable quotes are discarded. |
| **Mixed-level quizzes** | Every quiz mixes Easy, Medium and Hard questions, ordered easy to hard. The student's recent scores decide the mix, and results show the score at each level. |
| **Weak topic tracking** | Topics scored under 50% are flagged and prioritized in recommendations. |
| **AI learning assistant** | Answers general questions, reads uploaded files (PDF, Word, text, code and images) and knows the student's own scores, weak topics and study plan. Chats are saved to the student's account. |
| **Ask about a video** | Answers what the teacher said in a watched video, with quotes from the transcript, and keeps any general explanation clearly labelled as not from the video. |
| **Progress analytics** | Score trends, topic mastery, quiz history, learning curves, study time and a study planner. |
| **Accounts** | Email and password (at least 8 characters with a letter, a number and a symbol), password reset by email, or sign-in with Google, GitHub and LinkedIn. |

### For administrators

- Dashboard with platform statistics
- Student management and per-student progress
- Educational category, department and field management
- Reports and recommendation-engine evaluation (precision, recall, NDCG, hit rate)

---

## How it works

### Transcript pipeline

Notes, quizzes and video answers are only produced from a real transcript. Sources are tried in this order:

1. Transcript already saved in the database
2. YouTube captions: English manual, English auto-generated, then YouTube's English translation of the original captions
3. Subtitles through `yt-dlp`
4. **Gemini speech-to-text from the YouTube link.** Google fetches the video itself, so this also works when YouTube blocks the server and for videos without captions.
5. Speech-to-text from downloaded audio (Groq Whisper, then local Whisper)

If none works, the student sees a clear message, including when YouTube blocked the request. The platform never falls back to the title, description or general topic.

### Grounding checks

- **Quizzes:** every question carries an evidence quote. A question whose quote doesn't match the transcript is discarded.
- **Video answers:** the "From the video" part is only shown when its supporting quotes match the transcript. Otherwise the assistant says the teacher didn't explain it and gives a separately labelled general answer.

### Quiz levels

Each quiz mixes all three levels. The mix leans towards the level the student's recent scores point to (last 3 quizzes on the topic, then the last 5 overall, then the profile setting):

| Recent average | Easy | Medium | Hard (per 10 questions) |
|---|---|---|---|
| Under 50% | 5 | 3 | 2 |
| 50% to 79% | 3 | 4 | 3 |
| 80% or more | 2 | 3 | 5 |

Easy questions test recall, Medium questions test understanding (why and how), and Hard questions apply ideas in short scenarios.

### Recommendations

The MoE engine combines experts for weak topics, the student's field, their history and variety, weighted by an attention-based router. Fields the built-in lists don't cover get their core subjects from the AI once, saved for reuse. YouTube searches are cached for 24 hours and run in parallel.

### AI providers

Groq (`openai/gpt-oss-120b`, `qwen/qwen3.8-27b`, `openai/gpt-oss-20b`) is the primary provider for notes, quizzes and the assistant. Google Gemini is the fallback, and also reads images and scanned PDFs and transcribes videos.

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
| Auth | bcrypt password hashing, OAuth 2.0 (Google, GitHub, LinkedIn), SMTP email |
| Hosting | Vercel (app), Aiven (MySQL) |

---

## Getting started

### Prerequisites

- Python 3.11
- MySQL or MariaDB running locally (XAMPP works)
- API keys: [Groq](https://console.groq.com/keys), [Google Gemini](https://aistudio.google.com/apikey), [YouTube Data API v3](https://console.cloud.google.com/apis/library/youtube.googleapis.com)
- Optional: [FFmpeg](https://ffmpeg.org) on your `PATH`, for local speech-to-text

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

Start MySQL, for example with **Start** next to MySQL in the XAMPP Control Panel. Nothing needs importing by hand: on startup the app creates the database and applies `database/schema.sql`, `schema_updates.sql` and `seed_data.sql`. Later starts skip this unless those files change.

### 5. Create an admin account

```bash
python create_admin.py admin@example.com "Strong#Pass123" "Administrator"
```

Always pass a password: without one the script uses a default that is public in the code.

### 6. Run the app

```bash
python run.py
```

Open <http://localhost:5000>. The admin panel is at <http://localhost:5000/admin/login>.

---

## Configuration

All settings live in `.env` (copy `.env.example`). Never commit `.env`.

| Variable | Required | Purpose |
|---|---|---|
| `SECRET_KEY` | Yes | Signs login sessions. Use a long random string: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Yes | Database connection |
| `DB_POOL_SIZE` | No | Connections each server copy keeps open (default 10; use 2 on a free hosted database) |
| `GROQ_API_KEY` | Yes | Notes, quizzes, assistant, Whisper speech-to-text |
| `GEMINI_API_KEY` | Recommended | AI fallback, images and scanned PDFs, video transcription |
| `YOUTUBE_API_KEY` | Yes | Video search and details |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Optional | Sign in with Google |
| `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` | Optional | Sign in with GitHub |
| `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET` | Optional | Sign in with LinkedIn |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM` | Optional | Emails password-reset links (Gmail: `smtp.gmail.com`, port 587, an App password). Without them, links only appear in the server log. |
| `YT_PROXY_URL` | Optional | Proxy for YouTube captions and audio, for hosts YouTube blocks |
| `OAUTHLIB_INSECURE_TRANSPORT` | Local only | `1` allows OAuth over plain HTTP on localhost. Never set it on the live site. |

### OAuth redirect URLs

Register these in each provider's console, both for local development and for the live site:

| Provider | Local | Live |
|---|---|---|
| Google | `http://localhost:5000/auth/google/callback` | `https://<your-site>/auth/google/callback` |
| GitHub | `http://localhost:5000/auth/github/callback` | `https://<your-site>/auth/github/callback` (GitHub allows one callback per app, so use a second OAuth App for the live site) |
| LinkedIn | `http://localhost:5000/auth/linkedin/callback` | `https://<your-site>/auth/linkedin/callback` (enable *Sign In with LinkedIn using OpenID Connect*) |

---

## Deploying to Vercel

The repository is ready for Vercel: `pyproject.toml` sets the entrypoint `run:app`. Every push to `main` redeploys.

1. **Database.** Vercel doesn't host MySQL. Create a free MySQL service on [Aiven](https://aiven.io) or any MySQL 8 host. Free Aiven services can be powered off when idle: power it on again in the Aiven console if the site reports a database connection error.
2. **Import** the GitHub repository in Vercel with the **Flask** preset.
3. **Environment variables** (Settings → Environment Variables), from `.env.example`:
   - Required: `SECRET_KEY`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `GROQ_API_KEY`, `YOUTUBE_API_KEY`
   - Recommended: `GEMINI_API_KEY`, `DB_POOL_SIZE=2`, the `SMTP_` settings
   - Optional: OAuth client IDs and secrets, `YT_PROXY_URL`
   - The app refuses to start on Vercel without `SECRET_KEY`.
4. **Deploy.** The first request creates the tables.
5. **Admin account:** run `create_admin.py` with the hosted database's `DB_` values set in your terminal.
6. **OAuth:** add the live callback URLs from the table above.

**YouTube API key:** set *Application restrictions* to **None** (the app calls YouTube from the server, so a *Websites* restriction blocks it) and *API restrictions* to **YouTube Data API v3**.

**Transcripts on Vercel:** YouTube often blocks caption requests from cloud servers. The Gemini step transcribes those videos automatically. To fill transcripts in advance, run `python sync_transcripts.py` on your own computer with the hosted database's `DB_` values set; it saves transcripts for the videos the site has shown. `YT_PROXY_URL` is another option.

**Limits on Vercel:** no local speech-to-text (no FFmpeg), and chat uploads up to 3 MB.

**Troubleshooting:** the deployment's **Logs** show `[ERROR]` lines for database problems, `[OAuth]` lines naming the reason a sign-in failed, and `[YouTube Search]` lines for API key problems.

---

## Performance

- **One database round trip per query:** pooled connections use autocommit, with no per-query connection check or session reset. Dropped connections reconnect only when a query fails.
- **Fast cold starts:** the Groq and Gemini libraries load on first use. Database setup runs only when the SQL files change.
- **Recommendations:** saved searches are fetched in one query and missing YouTube searches run in parallel. Results are cached per student and preferences.
- **Static files:** links carry a content fingerprint and are cached by the browser for a year. Chart.js loads only on pages with charts.
- **Speed tip:** put the database in the same region as the app, for example Vercel's Washington, D.C. (`iad1`) region with a US East database.

---

## Project structure

```
ai_learning_platform/
├── app/
│   ├── ai/                           # AI and learning logic
│   │   ├── __init__.py                 # App factory (config, static caching, blueprints)
│   │   ├── transcript_extractor.py     # Captions → yt-dlp → Gemini → Whisper pipeline
│   │   ├── quiz_generator.py           # Grounded, mixed-level quizzes and level selection
│   │   ├── notes_generator.py          # Transcript-only study notes
│   │   ├── video_qa.py                 # Assistant answers from a video's transcript
│   │   ├── moe_engine.py               # Mixture-of-Experts recommender and field topics
│   │   ├── evaluator.py                # Precision, recall, NDCG, hit rate
│   │   ├── learning_curve.py           # Learning curve tracking
│   │   └── speech_to_text.py, audio_extractor.py, weak_topic_analyzer.py, ...
│   ├── routes/                       # Flask blueprints
│   │   ├── auth.py, social_auth.py     # Login, registration, password reset, OAuth
│   │   ├── dashboard.py                # Student pages, settings, study planner
│   │   ├── gemini.py                   # Notes, quizzes, assistant and chat history APIs
│   │   ├── recommend.py, youtube.py    # Recommendations and video APIs
│   │   ├── onboarding.py
│   │   └── admin.py
│   ├── utils/                        # Database pool, auth helpers, notifications, mailer
│   └── config.py
├── database/
│   ├── schema.sql                    # Core tables
│   ├── schema_updates.sql            # Incremental changes (MariaDB and MySQL 8)
│   └── seed_data.sql                 # Educational categories and starter data
├── static/                           # css/ (shared design system in ui.css), js/
├── templates/                        # Jinja2 pages, partials and admin templates
├── tests/                            # Unit tests (no database, network or API keys)
├── migrate_schema.py                 # Applies the SQL files (runs automatically on startup)
├── create_admin.py                   # Creates an admin account or resets its password
├── sync_transcripts.py               # Saves transcripts into a database from your own computer
├── run.py                            # Entry point (local server and Vercel)
├── pyproject.toml                    # Vercel entrypoint and dependencies
├── requirements.txt
└── .env.example                      # Settings template
```

---

## Testing

The unit tests replace the database and AI calls with fakes, so they need no database, network or API keys:

```bash
python -m unittest discover tests -v
```

They cover transcript validation, quiz grounding, scoring and levels, adaptive difficulty, learning curves, the MoE gate and experts, topic mapping, evaluation metrics and password hashing.

---

## Security

- Keep `.env` out of version control, and replace any key that has ever been committed.
- Passwords are hashed with bcrypt and must contain a letter, a number and a symbol. Login errors don't reveal whether an email is registered.
- Password-reset links work once and expire after 30 minutes.
- Sign-in with OAuth uses a `state` check, and only verified provider emails are linked to accounts.
- On the live site, session cookies are HTTPS-only, and the app refuses to start without its own `SECRET_KEY`.
- Text from YouTube and from other students is escaped everywhere it's shown, so it can't inject scripts.
- Students only ever see their own quizzes, chats, plans and progress. The assistant reads only the logged-in student's data and watched videos.
- `python run.py` starts Flask's development server with debug mode on. Use it only on your own machine.

---

## Roadmap

- Video timestamps in answers and quiz explanations
- Spaced repetition for missed questions
- Learning paths and certificates
- Free and Premium plans

---

## Author

**Khet Vaswani** — Final Year Project

## License

No license has been chosen yet, so all rights are reserved by default. Add a `LICENSE` file (for example MIT) before others reuse the code.
