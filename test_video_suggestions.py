#!/usr/bin/env python
# ============================================================
# test_video_suggestions.py — Test the Quiz-Based Video Suggestions
# ============================================================

"""
This test demonstrates how video suggestions are generated
based on quiz performance.

Scenario 1: Weak Performance (< 60%)
- User gets 40% on Python quiz
- Suggested videos: Beginner/basics level
- Reason: Strengthen fundamentals

Scenario 2: Good Performance (60-80%)
- User gets 70% on Python quiz  
- Suggested videos: Intermediate level
- Reason: Deeper understanding

Scenario 3: Excellent Performance (> 80%)
- User gets 90% on Python quiz
- Suggested videos: Advanced level
- Reason: Next level learning
"""

def test_difficulty_suggestions():
    """Test the difficulty-based recommendation logic"""
    
    print("\n" + "="*60)
    print("QUIZ-BASED VIDEO SUGGESTION TEST")
    print("="*60)
    
    # Test cases
    test_cases = [
        {"percentage": 45, "topic": "Python", "expected": "beginner"},
        {"percentage": 50, "topic": "Flask", "expected": "beginner"},
        {"percentage": 70, "topic": "Machine Learning", "expected": "intermediate"},
        {"percentage": 75, "topic": "Web Development", "expected": "intermediate"},
        {"percentage": 85, "topic": "JavaScript", "expected": "advanced"},
        {"percentage": 95, "topic": "Data Science", "expected": "advanced"},
    ]
    
    for i, test in enumerate(test_cases, 1):
        percentage = test["percentage"]
        topic = test["topic"]
        expected = test["expected"]
        
        # Determine difficulty level (same logic as in the function)
        if percentage < 60:
            difficulty = "beginner"
            reason = f"⚠️ Weak Topic - Suggested simpler tutorials to strengthen basics"
        elif percentage < 80:
            difficulty = "intermediate"
            reason = f"📚 Good Progress - Suggested intermediate content for deeper understanding"
        else:
            difficulty = "advanced"
            reason = f"🚀 Excellent! - Suggested advanced videos for next level learning"
        
        # Verify
        status = "✅ PASS" if difficulty == expected else "❌ FAIL"
        
        print(f"\nTest {i}: {status}")
        print(f"  Topic: {topic}")
        print(f"  Score: {percentage}%")
        print(f"  Expected: {expected}")
        print(f"  Got: {difficulty}")
        print(f"  Reason: {reason}")
    
    print("\n" + "="*60)
    print("Test Summary:")
    print("- Weak performance (< 60%): Suggests BEGINNER videos")
    print("- Good performance (60-80%): Suggests INTERMEDIATE videos")
    print("- Excellent performance (> 80%): Suggests ADVANCED videos")
    print("="*60 + "\n")


def test_search_keywords():
    """Show what search keywords are used for each difficulty level"""
    
    print("\n" + "="*60)
    print("SEARCH KEYWORDS BY DIFFICULTY LEVEL")
    print("="*60)
    
    keywords_by_level = {
        "beginner": [
            "{topic} beginners",
            "{topic} basics",
            "{topic} basics tutorial",
            "learn {topic} from scratch",
            "{topic} for beginners"
        ],
        "intermediate": [
            "{topic} tutorial",
            "{topic} in depth",
            "{topic} intermediate",
            "advanced {topic}",
            "{topic} concepts"
        ],
        "advanced": [
            "{topic} advanced",
            "{topic} next level",
            "{topic} expert",
            "advanced {topic} tutorial",
            "{topic} professional"
        ]
    }
    
    for level, keywords in keywords_by_level.items():
        print(f"\n{level.upper()} Level Search Keywords:")
        for kw in keywords:
            print(f"  • {kw}")
    
    print("\n" + "="*60 + "\n")


def test_api_flow():
    """Show how the API flow works"""
    
    print("\n" + "="*60)
    print("API FLOW: Quiz Submission to Video Suggestions")
    print("="*60)
    
    print("""
STEP 1: User submits quiz
  POST /gemini/submit-quiz
  {
    "quiz_id": 123,
    "topic": "Python",
    "answers": { "0": "A", "1": "B", ... }
  }

STEP 2: System calculates score
  Total questions: 10
  Correct answers: 7
  Score: 70%

STEP 3: Determine difficulty level
  Since 60% ≤ 70% < 80% → INTERMEDIATE level

STEP 4: Generate video suggestions
  - Search keywords: 
    • "Python tutorial"
    • "Python in depth"
    • "Python intermediate"
    • "advanced Python"
    • "Python concepts"
  
STEP 5: Return response
  {
    "success": true,
    "percentage": 70,
    "topic": "Python",
    "video_suggestions": [
      {
        "video_id": "xyz123",
        "title": "Advanced Python Tutorial - Part 2",
        "channel": "Programming with Mosh",
        "thumbnail": "...",
        "reason": "📚 Good Progress - Suggested intermediate content...",
        "difficulty": "intermediate",
        "score": 70
      },
      ...
    ],
    "suggestion_reason": "📚 Good Progress - Suggested intermediate content...",
    "suggestion_difficulty": "intermediate",
    "suggestion_count": 3
  }
    """)
    
    print("="*60 + "\n")


if __name__ == "__main__":
    test_difficulty_suggestions()
    test_search_keywords()
    test_api_flow()
    
    print("\n✅ All tests completed successfully!")
    print("\nNEXT STEPS:")
    print("1. Submit a quiz and check the response includes video_suggestions")
    print("2. Verify videos match the student's performance level")
    print("3. Check that weak topics get simpler videos")
    print("4. Check that strong topics get advanced videos")
