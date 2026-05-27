# 🚀 Localhost Testing Guide

## 1️⃣ START THE APPLICATION

```bash
# Activate virtual environment first
& .\venv\Scripts\Activate.ps1

# Run the Flask app
python run.py
```

**Expected output:**
```
* Running on http://127.0.0.1:5000
* WARNING in app.run_commands (from os.environ) read config environment variables...
Press CTRL+C to quit
```

---

## 2️⃣ TEST IN BROWSER

### **Home Page**
```
http://localhost:5000
```
✅ Should see: Login page or Dashboard (if logged in)

### **Register New User**
```
http://localhost:5000/register
```
- Enter username, email, password
- Select field (e.g., "Computer Science")
- Select skill level (e.g., "Beginner")
- Click Register

### **Login**
```
http://localhost:5000/login
```
- Use credentials just created
- Click Login

### **Dashboard**
```
http://localhost:5000/dashboard
```
✅ Should see:
- Welcome message
- Progress stats
- Video recommendations section
- Quiz history

---

## 3️⃣ TEST RECOMMENDATION SYSTEM

### **View Recommendations**
```
http://localhost:5000/dashboard
```
Scroll to **"Recommended Videos"** section
- Should display videos with:
  - Video thumbnail
  - Title & channel
  - Expert badge (⚠️ Weak Topic, 📊 Performance, 📺 New Topic)
  - Score/match percentage

### **Via API (Test Endpoint)**
```bash
# In PowerShell, or use Postman/curl
Invoke-WebRequest -Uri "http://localhost:5000/recommend/videos" -Headers @{"Cookie"="session=YOUR_SESSION"} | ConvertTo-Json
```

Or use **Postman**:
- URL: `http://localhost:5000/recommend/videos`
- Method: GET
- Add Cookie header with session ID

**Expected Response:**
```json
{
  "success": true,
  "recommendations": [
    {
      "video_id": "xyz123",
      "title": "Python Tutorial",
      "channel": "Programming with Mosh",
      "thumbnail": "https://...",
      "reason": "⚠️ Weak topic: Python (failed 2x)",
      "expert": "weak_topic",
      "final_score": 0.3715,
      "priority": "high",
      "weight_used": 0.371
    }
  ],
  "total": 5,
  "weights": {
    "weak_topic": 0.371,
    "performance": 0.285,
    "history": 0.344
  }
}
```

---

## 4️⃣ TEST QUIZ SYSTEM

### **Take a Quiz**
```
http://localhost:5000/quiz_page?topic=Python
```
- Answer quiz questions
- Submit quiz

### **Check Results**
```
http://localhost:5000/evaluation
```
- View score percentage
- View video suggestions based on performance
- Check if recommendations match your score level:
  - < 60%: Should suggest **BEGINNER** videos
  - 60-80%: Should suggest **INTERMEDIATE** videos
  - > 80%: Should suggest **ADVANCED** videos

---

## 5️⃣ TEST MOE ANALYSIS ENDPOINT

### **View MoE Analysis**
```
http://localhost:5000/recommend/moe-analysis
```

**Expected Response:**
```json
{
  "success": true,
  "analysis": {
    "weights": {
      "weak_topic": 0.371,
      "performance": 0.285,
      "history": 0.344
    },
    "context": {
      "weak_count": 3,
      "quiz_count": 4,
      "watch_count": 24,
      "avg_score": 34.4
    },
    "experts": {
      "weak_topic": {
        "name": "Weak Topic Expert",
        "icon": "⚠️",
        "weight": 0.371,
        "data": 3
      },
      "performance": {
        "name": "Performance Expert",
        "icon": "📊",
        "weight": 0.285,
        "data": 4
      },
      "history": {
        "name": "History Expert",
        "icon": "📺",
        "weight": 0.344,
        "data": 24
      }
    }
  }
}
```

---

## 6️⃣ CHECKLIST - WHAT TO VERIFY

### ✅ **Registration & Login**
- [ ] Can register with username/email
- [ ] Can login with credentials
- [ ] Field of interest saves correctly
- [ ] Skill level saves correctly

### ✅ **Dashboard**
- [ ] Shows user profile
- [ ] Displays progress stats
- [ ] Shows "Recommended Videos" section
- [ ] Recommendations load without errors

### ✅ **Recommendation System (MoE)**
- [ ] Videos display with thumbnails
- [ ] Expert badges show (⚠️📊📺)
- [ ] Final scores are between 0 and 1
- [ ] Videos sorted by score (highest first)
- [ ] No duplicate videos

### ✅ **Quiz & Evaluation**
- [ ] Can take quiz
- [ ] Score calculation correct
- [ ] Video suggestions appear after quiz
- [ ] Suggestions match performance level:
  - Low score (< 60%) → Beginner videos
  - Medium score (60-80%) → Intermediate videos
  - High score (> 80%) → Advanced videos

### ✅ **Database**
- [ ] Quiz history saves
- [ ] Weak topics tracked
- [ ] Watched videos recorded
- [ ] Learning curves updated

### ✅ **API Endpoints**
- [ ] `/recommend/videos` returns proper JSON
- [ ] `/recommend/moe-analysis` shows weights
- [ ] `/recommend/weak-topics` lists weak topics
- [ ] All responses have `"success": true`

---

## 7️⃣ CHECK BROWSER CONSOLE (F12)

Press **F12** → **Console tab**

✅ **Should see NO errors** like:
- `Uncaught SyntaxError`
- `TypeError: Cannot read property`
- `404 Not Found`

✅ **Should see success messages**:
- "MoE Response: {success: true, ...}"
- "Loaded 5 recommendations"

---

## 8️⃣ CHECK SERVER LOGS (Terminal)

Look for messages like:

```
🤖 TransformerMoE initialized for user 1
   Context: weak=3, quizzes=4, watched=24, avg=34.4%
   Dynamic Weights: weak=0.371, perf=0.285, hist=0.344

📊 Expert Outputs:
   Expert 1 (Weak Topics) : 3 queries
   Expert 2 (Performance) : 4 queries
   Expert 3 (History)     : 5 queries
   Total                  : 12 queries

🎯 Top Recommendations:
   [performance ] score=0.2847 w=0.285 — 📉 Very low score 30%
   [weak_topic  ] score=0.2786 w=0.371 — ⚠️ Weak topic: OS

✅ Final: 11 recommendations
   Attention Weights Used:
   weak=0.371 perf=0.285 hist=0.344
```

✅ **No errors** about:
- `ImportError`
- `IndentationError`
- `KeyError`

---

## 9️⃣ QUICK TEST SCRIPT

Run this to verify MoE system:
```bash
python test_moe_system.py
```

Should show:
```
✅ ALL 5 TESTS PASSED!
🎉 Recommendation system is working correctly
```

---

## 🔟 TROUBLESHOOTING

### **Issue: "No recommendations showing"**
- ✅ Take a quiz first
- ✅ Wait for database to process
- ✅ Check browser console (F12)
- ✅ Check server logs for errors

### **Issue: "All videos are same"**
- ✅ Check `/recommend/moe-analysis` weights
- ✅ Verify watched_videos table
- ✅ Run deduplication: `final.sort(key=lambda x: x['final_score'], reverse=True)`

### **Issue: "Wrong difficulty level"**
- ✅ Verify quiz score calculation
- ✅ Check `get_difficulty_based_recommendations()` function
- ✅ Score < 60% should be "beginner"
- ✅ Score 60-80% should be "intermediate"
- ✅ Score > 80% should be "advanced"

### **Issue: "YouTube API quota exceeded"**
- ✅ Fallback videos will show instead
- ✅ Check fallback list in `recommend.py`
- ✅ Wait 24 hours for quota reset

---

## 📊 EXPECTED BEHAVIOR

### **New User (No Quiz History)**
- ✅ Should show recommended topics from field
- ✅ MoE weights: high history expert weight
- ✅ Videos from preferred field topics

### **Student with Past Quizzes**
- ✅ Should show weak topics first
- ✅ Should show performance-based difficulty
- ✅ MoE weights: balanced across all experts

### **Student with Many Videos Watched**
- ✅ Should show unexplored topics
- ✅ Should not repeat already watched
- ✅ MoE weights: adjusted based on context

---

## 🎯 FINAL VERIFICATION

✅ All of these should work:

1. Register → Login → Dashboard
2. See recommendations without errors
3. Take quiz → Get evaluation
4. Video suggestions match your score
5. API endpoints return proper JSON
6. No console errors (F12)
7. No server errors (terminal logs)
8. Tests pass (python test_moe_system.py)

If all ✅, **YOUR SYSTEM IS WORKING PERFECTLY!** 🚀
