# 📚 Quiz-Based Video Recommendations Feature

## Overview
After a user completes a quiz, the system intelligently suggests videos based on their performance:
- **Weak Performance (< 60%)**: Suggests simpler/beginner-level videos
- **Good Performance (60-80%)**: Suggests intermediate videos for deeper learning
- **Excellent Performance (> 80%)**: Suggests advanced/next-level videos

---

## How It Works

### 1. **Quiz Submission Flow**
```
User takes quiz → Submits answers → System evaluates performance
→ Analyzes score → Determines difficulty level → Searches for videos
→ Returns 3 video suggestions with reasons
```

### 2. **Performance-Based Difficulty Levels**

| Score Range | Difficulty Level | Suggested Videos | Reason |
|------------|------------------|------------------|--------|
| **< 60%** | 🔴 Beginner | Basics, Introduction | ⚠️ Weak Topic - Strengthen fundamentals |
| **60-80%** | 🟡 Intermediate | Tutorials, In-depth | 📚 Good Progress - Deepen understanding |
| **> 80%** | 🟢 Advanced | Next-level, Expert | 🚀 Excellent - Challenge yourself |

### 3. **Search Keywords by Difficulty**

#### Beginner Level
```python
- "{topic} beginners"
- "{topic} basics"
- "{topic} basics tutorial"
- "learn {topic} from scratch"
- "{topic} for beginners"
```

#### Intermediate Level
```python
- "{topic} tutorial"
- "{topic} in depth"
- "{topic} intermediate"
- "advanced {topic}"
- "{topic} concepts"
```

#### Advanced Level
```python
- "{topic} advanced"
- "{topic} next level"
- "{topic} expert"
- "advanced {topic} tutorial"
- "{topic} professional"
```

---

## API Response Format

### Quiz Submission Endpoint
**POST** `/gemini/submit-quiz`

### Response (New Fields)
```json
{
  "success": true,
  "score": 7,
  "total": 10,
  "percentage": 70,
  "topic": "Python",
  "results": [...],
  
  "video_suggestions": [
    {
      "video_id": "abc123def456",
      "title": "Advanced Python - Working with Classes",
      "thumbnail": "https://img.youtube.com/vi/abc123/mqdefault.jpg",
      "channel": "Programming with Mosh",
      "topic": "Python",
      "difficulty": "intermediate",
      "score": 70,
      "reason": "📚 Good Progress - Suggested intermediate content for deeper understanding",
      "expert": "Quiz Performance Expert"
    },
    {
      "video_id": "xyz789uvw123",
      "title": "Python Intermediate Tutorial",
      "thumbnail": "https://img.youtube.com/vi/xyz789/mqdefault.jpg",
      "channel": "Tech With Tim",
      "topic": "Python",
      "difficulty": "intermediate",
      "score": 70,
      "reason": "📚 Good Progress - Suggested intermediate content for deeper understanding",
      "expert": "Quiz Performance Expert"
    },
    ...
  ],
  "suggestion_reason": "📚 Good Progress - Suggested intermediate content for deeper understanding",
  "suggestion_difficulty": "intermediate",
  "suggestion_count": 3,
  
  "curve_stage": "Accelerating",
  "predicted_next": 78,
  "mastery_eta": "5 days",
  "learning_rate": 2.5
}
```

---

## Implementation Details

### Files Modified

1. **[app/routes/recommend.py](app/routes/recommend.py)** (NEW FUNCTION)
   - Added `get_difficulty_based_recommendations()` function
   - Generates videos based on quiz performance
   - Handles YouTube API calls with caching
   - Returns fallback videos on quota exceeded

2. **[app/routes/gemini.py](app/routes/gemini.py)** (MODIFIED)
   - Imported `get_difficulty_based_recommendations`
   - Calls the function after learning curve update
   - Includes video suggestions in response

### Key Features

✅ **Smart Difficulty Detection**
- Automatically determines appropriate difficulty level
- Adapts to student's performance

✅ **YouTube Integration**
- Searches YouTube with relevant keywords
- Implements caching to reduce API calls
- Falls back to hardcoded videos on quota exceeded

✅ **Personalization**
- Excludes already watched videos
- Filters based on quiz topic
- Returns only top 3 suggestions

✅ **Error Handling**
- Gracefully handles API failures
- Returns empty suggestions instead of crashing
- Logs errors for debugging

---

## Example Scenarios

### Scenario 1: Weak Performance
```
User takes "Python Basics" quiz
Scores: 45% (4 out of 10 questions correct)

Response includes:
- Difficulty: "beginner"
- Reason: "⚠️ Weak Topic - Suggested simpler tutorials to strengthen basics"
- Videos: "Python for Beginners", "Learn Python Basics", "Introduction to Python"
```

### Scenario 2: Good Performance
```
User takes "Flask Development" quiz
Scores: 72% (7.2 out of 10)

Response includes:
- Difficulty: "intermediate"
- Reason: "📚 Good Progress - Suggested intermediate content for deeper understanding"
- Videos: "Flask Tutorial In-Depth", "Building Advanced APIs with Flask"
```

### Scenario 3: Excellent Performance
```
User takes "Advanced JavaScript" quiz
Scores: 92% (9.2 out of 10)

Response includes:
- Difficulty: "advanced"
- Reason: "🚀 Excellent! - Suggested advanced videos for next level learning"
- Videos: "Expert JavaScript Patterns", "Advanced JavaScript Concepts", "JavaScript Professional Tips"
```

---

## Frontend Integration

The frontend should:
1. Extract `video_suggestions` from the quiz response
2. Display videos in a card layout with:
   - Video thumbnail
   - Title and channel
   - Difficulty badge (🔴/🟡/🟢)
   - Reason/explanation
3. Add "Watch Video" button linking to YouTube
4. Show suggestion count

### Example HTML
```html
<div class="video-suggestions">
  <h3>{{ suggestion_reason }}</h3>
  <div class="difficulty-badge">{{ suggestion_difficulty }}</div>
  
  {% for video in video_suggestions %}
  <div class="video-card">
    <img src="{{ video.thumbnail }}" alt="{{ video.title }}">
    <h4>{{ video.title }}</h4>
    <p>{{ video.channel }}</p>
    <p class="reason">{{ video.reason }}</p>
    <a href="https://youtube.com/watch?v={{ video.video_id }}" 
       class="btn-watch" target="_blank">Watch Video</a>
  </div>
  {% endfor %}
</div>
```

---

## Database Schema

No new tables required. Uses existing tables:
- `video_quizzes` - Quiz scores and topics
- `weak_topics` - Already tracks weak topics
- `watched_videos` - Excludes already watched videos
- `search_cache` - Caches YouTube search results

---

## Performance Considerations

- **Caching**: Results cached for 15 minutes (CACHE_EXPIRY = 900)
- **API Limits**: YouTube API quota managed with fallback videos
- **Database Queries**: Optimized to avoid N+1 queries
- **Response Time**: < 2 seconds typically

---

## Testing

Run the test script:
```bash
python test_video_suggestions.py
```

Test cases cover:
- ✅ Beginner level detection (< 60%)
- ✅ Intermediate level detection (60-80%)
- ✅ Advanced level detection (> 80%)
- ✅ Search keyword generation
- ✅ API flow documentation

---

## Future Enhancements

1. **Multi-Language Support**
   - Translate search keywords to student's language
   
2. **Platform Integration**
   - Support YouTube, Udemy, Coursera, etc.
   
3. **AI-Powered Descriptions**
   - Generate personalized learning paths
   - Suggest topics to learn next
   
4. **Analytics**
   - Track which suggestions students watch
   - Measure learning improvement
   - A/B test difficulty levels

5. **Ranking Algorithm**
   - ML-based video ranking
   - Collaborative filtering
   - User preference learning

---

## FAQ

**Q: What if YouTube API quota is exceeded?**
A: Falls back to hardcoded videos matching the topic

**Q: Can suggestions exclude watched videos?**
A: Yes, queries `watched_videos` table before suggesting

**Q: How often are suggestions cached?**
A: 15 minutes by default, configurable in code

**Q: What if no videos are found?**
A: Returns empty suggestions gracefully, doesn't crash

**Q: Can difficulty levels be customized?**
A: Yes, modify thresholds in `get_difficulty_based_recommendations()`

---

## Support

For issues or questions, check:
1. Error logs: `print()` statements show debug info
2. API status: Monitor YouTube API quota usage
3. Network: Check internet connectivity
4. Database: Verify watched_videos table exists

---

**Created**: March 2026  
**Version**: 1.0  
**Status**: Production Ready ✅
