# 🎓 AI-Powered Personalized Learning Platform — Implementation Guide

## 📋 Overview

This guide explains the complete system redesign for your Final Year Project. The platform now features:

✅ **Category-Based Onboarding** - 6 educational tiers with conditional flows  
✅ **Modern Dashboard** - YouTube-style recommendation UI  
✅ **AI-Powered Notes** - Auto-generated from video transcripts  
✅ **AI-Powered Quizzes** - Adaptive MCQ generation and grading  
✅ **Weak Topic Detection** - Identifies problem areas after quizzes  
✅ **Adaptive Recommendations** - Personalized learning paths  

---

## 🚀 Phase 1: Database Setup

### Step 1: Run Database Migrations

```bash
# Connect to MySQL
mysql -h localhost -u root -p ai_learning_platform < database/schema_updates.sql
```

**What gets created:**
- `educational_categories` - Primary, Secondary, Matriculation, Intermediate, University, Professional
- `student_classes` - Class 1-10, streams, departments
- `university_departments` - 10 major departments
- `university_fields_of_study` - Specific fields per department
- `recommendation_history` - Tracks what was recommended
- `quiz_attempts` - Records quiz submissions

### Step 2: Verify Tables

```sql
-- Run in MySQL:
SELECT * FROM educational_categories;
SELECT * FROM student_classes;
SELECT * FROM university_departments;
```

---

## 🎨 Phase 2: Frontend Updates

### Step 1: Update Application Initialization

**File:** `app/__init__.py`

Add these imports and blueprint registrations:

```python
from app.routes.onboarding_category import onboarding_bp

app.register_blueprint(onboarding_bp, url_prefix='/onboarding')
```

### Step 2: Update Routes

**Modify:** `app/routes/dashboard.py`

```python
from flask import render_template, session, redirect
from app.ai.recommendation_engine import get_user_recommendations
from app.utils.db import fetch_query

@dashboard_bp.route('/dashboard')
@login_required
def index():
    user_id = session['user_id']
    
    # Fetch user profile
    user = fetch_query(
        """SELECT u.*, ec.name as category_name, sc.class_label
           FROM users u
           LEFT JOIN educational_categories ec ON u.educational_category_id = ec.id
           LEFT JOIN student_classes sc ON u.student_class_id = sc.id
           WHERE u.id = %s""",
        (user_id,)
    )[0]
    
    # Get recommendations
    recommendations = get_user_recommendations(user_id, num=12)
    
    return render_template('dashboard_modern.html',
        user_name=user['full_name'],
        user_avatar=user['profile_pic'],
        category_name=user.get('category_name', 'General'),
        class_name=user.get('class_label', ''),
        learning_level=user['learning_level'],
        recommendations=recommendations,
        show_weak_topics=True  # Only after quizzes
    )
```

### Step 3: Update Onboarding Route

**File:** `app/routes/auth.py`

After user registration:

```python
# After successful registration:
return redirect(url_for('onboarding.preferences'))
```

---

## 🧠 Phase 3: AI Systems Integration

### Step 1: Install AI Libraries

```bash
pip install google-generativeai groq python-youtube-transcript
```

### Step 2: Set Environment Variables

**File:** `.env`

```
GOOGLE_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

### Step 3: Initialize AI Systems

**Create:** `app/ai/config.py`

```python
import os
import google.generativeai as genai
from groq import Groq

# Initialize Gemini
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# Initialize Groq
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
groq_client = Groq(api_key=GROQ_API_KEY)
```

---

## 📚 Phase 4: Notes & Quiz Generation

### Step 1: Extract Video Transcript

**Create:** `app/utils/youtube_helper.py`

```python
from youtube_transcript_api import YouTubeTranscriptFetcher

def get_video_transcript(video_id: str) -> str:
    """Extract transcript from YouTube video"""
    try:
        transcript = YouTubeTranscriptFetcher.fetch_transcript(video_id)
        return ' '.join([item['text'] for item in transcript])
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return None
```

### Step 2: Generate Notes from Video

**File:** `app/routes/video.py`

```python
from app.ai.notes_generator import generate_notes_sync
from app.utils.youtube_helper import get_video_transcript

@video_bp.route('/video/<video_id>/notes', methods=['GET'])
@login_required
def generate_notes(video_id):
    user_id = session['user_id']
    
    # Get transcript
    transcript = get_video_transcript(video_id)
    
    if not transcript:
        return jsonify({'error': 'Could not extract transcript'}), 400
    
    # Generate notes
    result = generate_notes_sync(
        video_id=video_id,
        transcript=transcript,
        topic='Video Topic',
        level=session.get('learning_level', 'Beginner')
    )
    
    if result['success']:
        # Save notes
        execute_query(
            """INSERT INTO video_notes (user_id, video_id, notes)
               VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE notes = VALUES(notes)""",
            (user_id, video_id, json.dumps(result['notes']))
        )
        return jsonify({'success': True, 'notes': result['notes']})
    
    return jsonify({'error': result.get('error')}), 500
```

### Step 3: Generate Quiz from Video

**File:** `app/routes/quiz.py`

```python
from app.ai.quiz_generator import generate_quiz_sync

@quiz_bp.route('/quiz/generate/<video_id>', methods=['POST'])
@login_required
def create_quiz(video_id):
    user_id = session['user_id']
    
    # Get transcript
    transcript = get_video_transcript(video_id)
    
    if not transcript:
        return jsonify({'error': 'Could not extract transcript'}), 400
    
    # Generate quiz
    result = generate_quiz_sync(
        video_id=video_id,
        transcript=transcript,
        topic='Video Topic',
        num_questions=10,
        difficulty=session.get('learning_level', 'Medium')
    )
    
    if result['success']:
        # Save quiz
        quiz_id = execute_query(
            """INSERT INTO video_quizzes 
               (user_id, video_id, topic, questions)
               VALUES (%s, %s, %s, %s)""",
            (user_id, video_id, 'Topic', json.dumps(result['quiz']['questions']))
        )
        return jsonify({'success': True, 'quiz_id': quiz_id, 'quiz': result['quiz']})
    
    return jsonify({'error': result.get('error')}), 500
```

---

## 🎯 Phase 5: Adaptive Recommendations

### Recommendation Strategy

**For New Users (No Quizzes):**
```
Category-based → Class-based → Topic-based suggestions
```

**For Returning Users (With Quiz History):**
```
Weak Topics (Easy) → Related Topics (Medium) → Progression Topics (Advanced)
```

**Implementation:** `app/ai/recommendation_engine.py`

```python
def get_recommendations(user_id: int, num_recommendations: int = 12) -> List[Dict]:
    """Main recommendation function"""
    # Check if user has weak topics
    # If yes: recommend easy videos on weak topics
    # If no: recommend based on category/class
```

### Recording Recommendations

```python
# When showing recommendation to user
engine.record_recommendation(
    user_id=user_id,
    video_id=video_id,
    reason='Based on weak topics'
)
```

---

## 📊 Phase 6: Weak Topic Detection & Tracking

### Automatic Weak Topic Detection

When quiz score < 60%:
1. Extract incorrect concepts from quiz
2. Record in `weak_topics` table
3. Increment `fail_count`
4. Trigger adaptive recommendations

**Implementation in `quiz_generator.py`:**

```python
def grade_quiz(self, user_id: int, quiz_id: int, answers: Dict):
    # Grade answers
    # If score < 60:
    #   For each incorrect concept:
    #     INSERT INTO weak_topics (user_id, topic, fail_count)
    #     VALUES (..., 1)
    #     ON DUPLICATE KEY UPDATE fail_count = fail_count + 1
```

### Displaying Weak Topics on Dashboard

```html
{% if show_weak_topics and weak_topics %}
<section class="dashboard-section">
    <h2>⚠️ Topics to Review</h2>
    <!-- List weak topics with action buttons -->
</section>
{% endif %}
```

---

## 🔄 Complete User Flow

### 1️⃣ New User Registration
```
Register → Onboarding (Category Selection) → Class Selection → Learning Level → Dashboard
```

### 2️⃣ Dashboard Initial Load
```
Fetch User Profile → Get Category-Based Recommendations → Display Recommendations
```

### 3️⃣ Watch Video & Generate Content
```
User Clicks Video → Extract Transcript → Generate Notes & Quiz → Display to User
```

### 4️⃣ Take Quiz & Get Feedback
```
Submit Answers → Grade Quiz → Detect Weak Topics → Update Dashboard → Show Recommendations
```

### 5️⃣ Adaptive Loop
```
Next Visit → Check Weak Topics → Recommend Easy Videos on Weak Topics → Track Progress
```

---

## 📝 Database Query Reference

### Get User Profile with Full Info
```sql
SELECT u.*, 
       ec.name as category_name,
       sc.class_label,
       ud.name as department_name,
       ufs.field_name
FROM users u
LEFT JOIN educational_categories ec ON u.educational_category_id = ec.id
LEFT JOIN student_classes sc ON u.student_class_id = sc.id
LEFT JOIN university_departments ud ON u.university_department_id = ud.id
LEFT JOIN university_fields_of_study ufs ON u.university_field_id = ufs.id
WHERE u.id = ?;
```

### Get User's Weak Topics
```sql
SELECT topic, fail_count, last_detected
FROM weak_topics
WHERE user_id = ?
ORDER BY fail_count DESC, last_detected DESC;
```

### Get Quiz Performance Analytics
```sql
SELECT 
    quiz_id,
    COUNT(*) as attempts,
    AVG(percentage) as avg_score,
    MAX(percentage) as best_score
FROM quiz_attempts
WHERE user_id = ?
GROUP BY quiz_id;
```

---

## 🔧 Configuration & Settings

### Onboarding Flow Duration
Each user progresses through:
- **Step 1:** Category selection (25%)
- **Step 2:** Class/Stream selection (50%)
- **Step 3:** Department/Field selection (75%) [University only]
- **Step 4:** Learning level (100%)

### Recommendation Weighting
```
- Weak Topics: 50% (highest priority)
- Progression Topics: 30%
- Diverse Topics: 20%
```

### Difficulty Adaptation Algorithm
```
Score >= 85%  → Increase difficulty
Score 60-84%  → Keep same difficulty
Score < 60%   → Decrease difficulty
```

---

## 🧪 Testing Checklist

- [ ] Database migrations run successfully
- [ ] Onboarding flow works for all 6 categories
- [ ] Category-conditional logic displays correct classes
- [ ] Dashboard loads with recommendations
- [ ] Notes generation works (requires API key)
- [ ] Quiz generation works (requires API key)
- [ ] Quiz grading detects weak topics
- [ ] Weak topics appear on dashboard
- [ ] Adaptive recommendations change after quiz
- [ ] Responsive design works on mobile

---

## 📖 File Structure Summary

```
ai_learning_platform/
├── app/
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── notes_generator.py      ✨ NEW
│   │   ├── quiz_generator.py       ✨ NEW
│   │   ├── recommendation_engine.py ✨ NEW
│   │   └── config.py               ✨ NEW
│   ├── routes/
│   │   ├── onboarding_category.py  ✨ NEW
│   │   ├── quiz.py                 ⚡ UPDATED
│   │   ├── video.py                ⚡ UPDATED
│   │   └── dashboard.py            ⚡ UPDATED
│   └── utils/
│       └── youtube_helper.py       ✨ NEW
├── database/
│   ├── schema_updates.sql          ✨ NEW
│   └── schema.sql                  (existing)
├── static/
│   ├── CSS/
│   │   └── dashboard_modern.css    ✨ NEW
│   └── JS/
│       └── dashboard_modern.js     ✨ NEW
├── templates/
│   ├── onboarding_new.html         ✨ NEW
│   ├── dashboard_modern.html       ✨ NEW
│   └── (other templates)
└── requirements.txt                ⚡ UPDATED
```

---

## 🚀 Quick Start Commands

```bash
# 1. Update dependencies
pip install -r requirements.txt

# 2. Run database migrations
mysql -u root -p < database/schema_updates.sql

# 3. Set environment variables
export GOOGLE_API_KEY="your_key_here"
export GROQ_API_KEY="your_key_here"

# 4. Start development server
python run.py
```

---

## 📞 Key Functions Quick Reference

### Onboarding
```python
from app.routes.onboarding_category import save_category
# Saves user's category, class, level
```

### Recommendations
```python
from app.ai.recommendation_engine import get_user_recommendations
recs = get_user_recommendations(user_id, num=12)
```

### Notes Generation
```python
from app.ai.notes_generator import generate_notes_sync
notes = generate_notes_sync(video_id, transcript, topic, level)
```

### Quiz Generation
```python
from app.ai.quiz_generator import generate_quiz_sync, grade_quiz_sync
quiz = generate_quiz_sync(video_id, transcript, topic, num=10)
result = grade_quiz_sync(user_id, quiz_id, answers)
```

---

## 🎯 Next Steps

1. **Deploy Database** - Run schema_updates.sql
2. **Update App Init** - Register blueprints
3. **Add API Keys** - Set Gemini & Groq keys
4. **Test Onboarding** - Create test user and go through flow
5. **Test Dashboard** - Verify recommendations display
6. **Test AI Systems** - Generate notes/quizzes from sample video
7. **Test Adaptive Flow** - Submit quiz and check weak topics

---

## 💡 Pro Tips

- **Weak Topic Threshold:** Scores below 60% trigger weak topic tracking
- **Recommendation Refresh:** Recommendations update after every quiz attempt
- **Difficulty Progression:** Users auto-progress through difficulty levels based on performance
- **Category Lock:** Once a user selects category, it cannot be changed without admin intervention
- **Quiz Cache:** Cache recently generated quizzes to avoid regeneration

---

## 📚 Documentation

Full API documentation is in `FEATURE_DOCUMENTATION.md`

---

**Last Updated:** May 27, 2026  
**Project Status:** Development Phase  
**Version:** 2.0 (Redesigned with Category-Based Onboarding & AI Systems)
