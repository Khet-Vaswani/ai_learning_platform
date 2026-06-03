# 🚀 Quick Start Guide — AI Learning Platform

## ⚡ 5-Minute Overview

Your platform now has:
- ✅ 4-step intelligent onboarding (category → class → level)
- ✅ Modern YouTube-style dashboard
- ✅ AI-powered notes generation from videos
- ✅ AI-powered quiz generation from videos
- ✅ Adaptive recommendations based on performance
- ✅ Automatic weak topic detection
- ✅ Personalized study plans

---

## 🔧 Quick Setup (Copy & Paste)

### Step 1: Database Migration
```bash
# SSH into your server and run:
mysql -h localhost -u root -p < /path/to/database/schema_updates.sql
```

### Step 2: Install Dependencies
```bash
cd /path/to/ai_learning_platform
pip install google-generativeai groq youtube-transcript-api
```

### Step 3: Set Environment Variables
```bash
# Create or update .env file:
export GOOGLE_API_KEY="your_gemini_api_key"
export GROQ_API_KEY="your_groq_api_key"
export DB_NAME="ai_learning_platform"
```

### Step 4: Update Flask App
**In app/__init__.py, add:**
```python
from app.routes.onboarding_category import onboarding_bp
app.register_blueprint(onboarding_bp, url_prefix='/onboarding')
```

### Step 5: Test
```bash
python run.py
# Visit http://localhost:5000/register
```

---

## 📊 User Flow Walkthrough

```
1. User signs up
   ↓
2. Redirected to /onboarding/preferences
   ↓
3. Step 1: Select category (Primary/Secondary/Matriculation/Intermediate/University/Professional)
   ↓
4. Step 2: Select class/stream (conditional based on category)
   ↓
5. Step 3: Select department/field (university only)
   ↓
6. Step 4: Select learning level (Beginner/Intermediate/Advanced)
   ↓
7. Dashboard loaded with personalized recommendations
   ↓
8. User watches video → Notes & Quiz auto-generated
   ↓
9. Quiz taken → Weak topics detected → Recommendations adapted
```

---

## 📁 Files to Review First

1. **IMPLEMENTATION_GUIDE.md** - Complete technical guide
2. **PROJECT_SUMMARY.md** - High-level overview (this directory)
3. **database/schema_updates.sql** - Database changes
4. **app/routes/onboarding_category.py** - New onboarding logic
5. **templates/onboarding_new.html** - New onboarding UI
6. **templates/dashboard_modern.html** - New dashboard UI

---

## 🔑 Key APIs Quick Reference

### Get Recommendations
```python
from app.ai.recommendation_engine import get_user_recommendations
recs = get_user_recommendations(user_id=1, num=12)
# Returns 12 personalized video recommendations
```

### Generate Notes
```python
from app.ai.notes_generator import generate_notes_sync
notes = generate_notes_sync(
    video_id="dQw4w9WgXcQ",
    transcript="Full video transcript text...",
    topic="Machine Learning",
    level="Beginner"
)
# Returns: { 'success': True, 'notes': {...} }
```

### Generate Quiz
```python
from app.ai.quiz_generator import generate_quiz_sync
quiz = generate_quiz_sync(
    video_id="dQw4w9WgXcQ",
    transcript="Full video transcript text...",
    topic="Machine Learning",
    num_questions=10,
    difficulty="Medium"
)
# Returns: { 'success': True, 'quiz': {...} }
```

### Analyze User Performance
```python
from app.ai.weak_topic_analyzer import analyze_user_performance
analysis = analyze_user_performance(user_id=1)
# Returns: { 'has_weak_topics': True, 'critical': [...], ... }
```

---

## 📋 Database Tables

### New Tables Created
```sql
-- View all new tables:
SELECT TABLE_NAME FROM information_schema.TABLES 
WHERE TABLE_SCHEMA='ai_learning_platform' 
AND TABLE_NAME IN (
    'educational_categories',
    'student_classes',
    'university_departments',
    'university_fields_of_study',
    'recommendation_history',
    'quiz_attempts'
);
```

### Updated Table (users)
```
Added columns:
- educational_category_id INT
- student_class_id INT
- university_department_id INT
- university_field_id INT
- learning_level ENUM('Beginner','Intermediate','Advanced')
```

---

## 🧪 Testing Checklist

- [ ] Can register new user
- [ ] Onboarding shows 6 categories
- [ ] Category selection shows correct classes
- [ ] Learning level selection works
- [ ] Dashboard loads with recommendations
- [ ] Can generate notes from sample video
- [ ] Can generate quiz from sample video
- [ ] Can submit quiz answers
- [ ] Weak topics appear after low quiz score
- [ ] Recommendations change based on performance

---

## 🔗 URL Routes

```
GET  /register                     → Registration page
POST /register                     → Create new user
GET  /onboarding/preferences       → New onboarding flow
POST /onboarding/save-category     → Save onboarding choices
POST /onboarding/skip              → Skip onboarding
GET  /dashboard                    → Main dashboard
POST /video/<id>/notes             → Generate notes
POST /quiz/generate/<id>           → Generate quiz
POST /quiz/<id>/submit             → Submit quiz answers
GET  /weak-topics                  → View weak topics
GET  /progress                     → View progress analytics
```

---

## 💾 Database Backup Before Deploying

```bash
# Backup current database
mysqldump -u root -p ai_learning_platform > backup_$(date +%Y%m%d).sql

# Run migrations
mysql -u root -p ai_learning_platform < database/schema_updates.sql

# If something goes wrong, restore:
mysql -u root -p ai_learning_platform < backup_YYYYMMDD.sql
```

---

## 🚨 Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| API key errors | Check .env file has GOOGLE_API_KEY and GROQ_API_KEY |
| Database connection fails | Verify MySQL is running and credentials are correct |
| Transcript extraction fails | Check youtube-transcript-api is installed |
| Dashboard not loading | Verify onboarding_bp is registered in app/__init__.py |
| Recommendations not appearing | Check user has completed onboarding (onboarding_done=1) |
| Quiz grading fails | Ensure quiz_attempts table exists in database |

---

## 📱 Responsive Design

Dashboard works on:
- ✅ Desktop (1920x1080 and larger)
- ✅ Tablet (768px to 1024px)
- ✅ Mobile (320px to 767px)

Test with browser dev tools:
```
Chrome → F12 → Toggle device toolbar (Ctrl+Shift+M)
```

---

## 📞 File Locations

| What | Where |
|------|-------|
| Database schema | `database/schema_updates.sql` |
| Onboarding backend | `app/routes/onboarding_category.py` |
| Onboarding frontend | `templates/onboarding_new.html` |
| Dashboard HTML | `templates/dashboard_modern.html` |
| Dashboard CSS | `static/CSS/dashboard_modern.css` |
| Dashboard JS | `static/JS/dashboard_modern.js` |
| Notes generator | `app/ai/notes_generator.py` |
| Quiz generator | `app/ai/quiz_generator.py` |
| Recommender | `app/ai/recommendation_engine.py` |
| Weak topic analyzer | `app/ai/weak_topic_analyzer.py` |

---

## 🎯 Performance Tips

1. **Cache recommendations** - Don't regenerate on every dashboard load
2. **Async processing** - Generate notes/quizzes in background
3. **Database indexes** - Already added in schema_updates.sql
4. **Pagination** - Limit recommendation queries to 12-20 items
5. **Lazy loading** - Load weak topics section only when needed

---

## 📊 Configuration

Edit these in the respective AI files:

**Notes Generator** (`app/ai/notes_generator.py`):
```python
# Chunk size for processing transcripts
chunk_size = 3000  # characters
```

**Quiz Generator** (`app/ai/quiz_generator.py`):
```python
# Default number of questions
num_questions = 10
# Passing score
passing_score = 70
```

**Weak Topic Analyzer** (`app/ai/weak_topic_analyzer.py`):
```python
WEAK_THRESHOLD = 60        # Score below this = weak
CRITICAL_THRESHOLD = 40    # Score below this = critical
FAIL_COUNT_CRITICAL = 3    # Failures to mark critical
```

**Recommendation Engine** (`app/ai/recommendation_engine.py`):
```python
# Recommendation weights
WEAK_TOPICS_WEIGHT = 50   # %
PROGRESSION_WEIGHT = 30   # %
DIVERSE_WEIGHT = 20       # %
```

---

## 🔄 Database Queries for Monitoring

```sql
-- Check user onboarding status
SELECT id, full_name, onboarding_done, educational_category_id, 
       learning_level FROM users;

-- View weak topics
SELECT user_id, topic, fail_count, last_detected FROM weak_topics 
ORDER BY fail_count DESC;

-- Check quiz performance
SELECT user_id, AVG(percentage) as avg_score, COUNT(*) as attempts
FROM quiz_attempts GROUP BY user_id;

-- See recommendations history
SELECT user_id, video_id, reason, recommended_at FROM recommendation_history
ORDER BY recommended_at DESC LIMIT 20;
```

---

## ✅ Deployment Checklist (2-3 Hours)

- [ ] 15 min - Database migration
- [ ] 15 min - Update app/__init__.py
- [ ] 15 min - Install dependencies
- [ ] 15 min - Set environment variables
- [ ] 30 min - Test onboarding flow
- [ ] 30 min - Test recommendations
- [ ] 15 min - Test notes & quiz generation
- [ ] 15 min - Test weak topic detection
- [ ] 15 min - Test responsive design
- [ ] 30 min - Troubleshoot any issues

---

## 📞 Need Help?

1. **Errors with database?** → Check `DATABASE_GUIDE.md`
2. **Errors with AI?** → Check API key setup in `.env`
3. **Errors with frontend?** → Check browser console (F12)
4. **Errors with backend?** → Check Flask logs
5. **General questions?** → Read `IMPLEMENTATION_GUIDE.md`

---

**Ready to deploy? Start with Step 1 above!** 🚀

---

Last Updated: May 27, 2026
