# ============================================================
# ai/recommendation_engine.py — Adaptive Recommendation System
# ============================================================

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json
from app.utils.db import execute_query, fetch_query

class RecommendationEngine:
    """
    Adaptive recommendation system that:
    1. Recommends based on user's educational category/class/field
    2. Adapts recommendations based on quiz performance
    3. Prioritizes weak topics for learning
    4. Suggests progressive difficulty levels
    """
    
    def __init__(self):
        pass
    
    def get_recommendations(self, user_id: int, num_recommendations: int = 12) -> List[Dict]:
        """
        Get personalized recommendations for a user.
        
        Strategy:
        1. Check if user has completed quizzes
        2. If yes, recommend based on weak topics (Easy level)
        3. If no, recommend based on category/class/field
        """
        
        # Fetch user profile
        user = fetch_query(
            """SELECT educational_category_id, student_class_id, 
                      university_department_id, university_field_id, 
                      learning_level
               FROM users WHERE id = %s""",
            (user_id,)
        )
        
        if not user:
            return []
        
        user_profile = user[0]
        
        # Check if user has weak topics
        weak_topics = fetch_query(
            "SELECT COUNT(*) as count FROM weak_topics WHERE user_id = %s",
            (user_id,)
        )
        
        has_weak_topics = weak_topics[0]['count'] > 0 if weak_topics else False
        
        if has_weak_topics:
            # Return adaptive recommendations for weak topics
            return self._get_adaptive_recommendations(user_id, user_profile, num_recommendations)
        else:
            # Return category-based recommendations for new users
            return self._get_category_based_recommendations(user_id, user_profile, num_recommendations)
    
    def _get_category_based_recommendations(self, user_id: int, user_profile: Dict, 
                                           num: int) -> List[Dict]:
        """
        Get recommendations for new users based on their educational profile.
        """
        
        category_id = user_profile.get('educational_category_id')
        class_id = user_profile.get('student_class_id')
        field_id = user_profile.get('university_field_id')
        learning_level = user_profile.get('learning_level', 'Beginner')
        
        # Build search queries based on category
        search_queries = self._build_search_queries(category_id, class_id, field_id, learning_level)
        
        recommendations = []
        
        # Note: In real implementation, these would query YouTube API
        # For now, returning placeholder structure
        for i, query in enumerate(search_queries[:num]):
            recommendation = {
                'id': f'rec_{user_id}_{i}',
                'title': f'Video on {query}',
                'channel': 'Educational Channel',
                'thumbnail': 'https://via.placeholder.com/320x180',
                'difficulty': learning_level,
                'topic': query,
                'reason': 'Based on your learning profile',
                'video_id': f'video_{i}',
                'estimated_duration': '12 mins'
            }
            recommendations.append(recommendation)
        
        return recommendations[:num]
    
    def _get_adaptive_recommendations(self, user_id: int, user_profile: Dict, 
                                     num: int) -> List[Dict]:
        """
        Get recommendations based on user's weak topics and quiz performance.
        """
        
        # Fetch weak topics
        weak_topics = fetch_query(
            """SELECT topic, fail_count FROM weak_topics 
               WHERE user_id = %s
               ORDER BY fail_count DESC, last_detected DESC
               LIMIT 3""",
            (user_id,)
        )
        
        recommendations = []
        
        for topic_data in weak_topics:
            topic = topic_data['topic']
            fail_count = topic_data['fail_count']
            
            # Determine difficulty for weak topics
            if fail_count >= 3:
                difficulty = 'Beginner'  # Very basic videos
                reason = '📚 Review Basics'
            elif fail_count == 2:
                difficulty = 'Beginner'
                reason = '🔄 Practice More'
            else:
                difficulty = 'Intermediate'
                reason = '⬆️ Level Up'
            
            # Create recommendation
            rec = {
                'id': f'weak_{user_id}_{topic}',
                'title': f'{topic} - Step by Step Guide',
                'channel': 'Educational Channel',
                'thumbnail': 'https://via.placeholder.com/320x180',
                'difficulty': difficulty,
                'topic': topic,
                'reason': reason,
                'video_id': f'video_{topic.replace(" ", "_")}',
                'estimated_duration': '15 mins',
                'priority': 'HIGH'
            }
            recommendations.append(rec)
        
        # Add progression recommendations (next level topics)
        progression_recs = self._get_progression_recommendations(user_id, user_profile)
        recommendations.extend(progression_recs)
        
        # Add diverse topic recommendations
        diverse_recs = self._get_diverse_recommendations(user_id, user_profile)
        recommendations.extend(diverse_recs)
        
        return recommendations[:num]
    
    def _build_search_queries(self, category_id: int, class_id: int, 
                             field_id: Optional[int], level: str) -> List[str]:
        """
        Build YouTube search queries based on user's educational profile.
        """
        
        queries = []
        
        # Fetch category name and class label
        if category_id:
            category = fetch_query(
                "SELECT name FROM educational_categories WHERE id = %s",
                (category_id,)
            )
            category_name = category[0]['name'] if category else 'General'
        
        if class_id:
            class_info = fetch_query(
                "SELECT class_label FROM student_classes WHERE id = %s",
                (class_id,)
            )
            class_label = class_info[0]['class_label'] if class_info else ''
        
        # Build relevant queries
        level_suffix = {
            'Beginner': 'for beginners',
            'Intermediate': 'intermediate tutorial',
            'Advanced': 'advanced concepts'
        }
        suffix = level_suffix.get(level, 'for beginners')
        
        # Topic-specific queries based on class
        topics_by_class = {
            'Class 1': ['Basic Numbers', 'English Reading', 'Science Basics'],
            'Class 2': ['Arithmetic Basics', 'Grammar Fundamentals', 'Nature Science'],
            'Class 3': ['Number Operations', 'Writing Skills', 'Physics Concepts'],
            'Class 4': ['Fractions', 'Essay Writing', 'Biology Basics'],
            'Class 5': ['Percentages', 'Literature', 'Earth Science'],
            'Class 6': ['Algebra Introduction', 'English Literature', 'Physics Basics'],
            'Class 7': ['Linear Equations', 'Poetry Analysis', 'Force and Motion'],
            'Class 8': ['Quadratic Equations', 'Novel Study', 'Sound and Light'],
            'Class 9': ['Algebra Concepts', 'English Prose', 'Mechanics'],
            'Class 10': ['Trigonometry', 'Literature Review', 'Waves'],
            'Pre-Medical': ['Biology', 'Chemistry', 'Physics'],
            'Pre-Engineering': ['Mathematics', 'Physics', 'Mechanics'],
            'Commerce': ['Accounting', 'Economics', 'Business'],
            'Arts': ['Literature', 'History', 'Philosophy'],
            'ICS': ['Programming', 'Database', 'Networking'],
        }
        
        topics = topics_by_class.get(class_label, ['General Concepts'])
        for topic in topics:
            queries.append(f"{topic} {suffix}")
        
        return queries
    
    def _get_progression_recommendations(self, user_id: int, user_profile: Dict) -> List[Dict]:
        """
        Recommend next-level content for topics the user is mastering.
        """
        
        # Fetch high-scoring topics
        high_score_topics = fetch_query(
            """SELECT topic, last_score FROM topic_difficulty
               WHERE user_id = %s AND last_score >= 80
               ORDER BY last_score DESC
               LIMIT 3""",
            (user_id,)
        )
        
        recommendations = []
        
        for topic_data in high_score_topics:
            topic = topic_data['topic']
            rec = {
                'id': f'prog_{user_id}_{topic}',
                'title': f'{topic} - Advanced Concepts',
                'channel': 'Expert Channel',
                'thumbnail': 'https://via.placeholder.com/320x180',
                'difficulty': 'Advanced',
                'topic': f'{topic} (Advanced)',
                'reason': '⭐ You\'re Excelling',
                'video_id': f'video_{topic}_advanced',
                'estimated_duration': '18 mins',
                'priority': 'MEDIUM'
            }
            recommendations.append(rec)
        
        return recommendations
    
    def _get_diverse_recommendations(self, user_id: int, user_profile: Dict) -> List[Dict]:
        """
        Recommend diverse topics to broaden learning.
        """
        
        field_id = user_profile.get('university_field_id')
        learning_level = user_profile.get('learning_level', 'Intermediate')
        
        # Related topics
        related_topics = self._get_related_topics(field_id)
        
        recommendations = []
        for topic in related_topics[:3]:
            rec = {
                'id': f'div_{user_id}_{topic}',
                'title': f'{topic} Fundamentals',
                'channel': 'Knowledge Channel',
                'thumbnail': 'https://via.placeholder.com/320x180',
                'difficulty': 'Intermediate',
                'topic': topic,
                'reason': '🎓 Explore Related Topics',
                'video_id': f'video_{topic.replace(" ", "_")}',
                'estimated_duration': '10 mins',
                'priority': 'LOW'
            }
            recommendations.append(rec)
        
        return recommendations
    
    def _get_related_topics(self, field_id: Optional[int]) -> List[str]:
        """Get related topics based on field of study"""
        
        related_topics_map = {
            1: ['Data Analysis', 'Database Design', 'Web Development'],
            2: ['Machine Learning', 'Cloud Computing', 'DevOps'],
            3: ['API Design', 'Frontend Development', 'Mobile Development'],
            4: ['Network Security', 'Systems Security', 'Compliance'],
            5: ['Mobile Optimization', 'UX Design', 'Performance'],
        }
        
        return related_topics_map.get(field_id or 1, ['Computer Science Basics', 'IT Fundamentals'])
    
    def record_recommendation(self, user_id: int, video_id: str, reason: str) -> bool:
        """Record that a recommendation was shown to the user"""
        
        try:
            execute_query(
                """INSERT INTO recommendation_history 
                   (user_id, video_id, reason)
                   VALUES (%s, %s, %s)""",
                (user_id, video_id, reason)
            )
            return True
        except Exception as e:
            print(f"Error recording recommendation: {e}")
            return False
    
    def update_topic_difficulty(self, user_id: int, topic: str, score: float, level: str = 'Medium'):
        """
        Update topic difficulty based on user performance.
        
        Adaptive difficulty algorithm:
        - Score >= 85: Increase to next level
        - Score 60-84: Maintain current level
        - Score < 60: Decrease to easier level
        """
        
        difficulty_levels = ['Easy', 'Medium', 'Hard']
        current_idx = difficulty_levels.index(level)
        
        if score >= 85 and current_idx < 2:
            new_level = difficulty_levels[current_idx + 1]
        elif score < 60 and current_idx > 0:
            new_level = difficulty_levels[current_idx - 1]
        else:
            new_level = level
        
        execute_query(
            """UPDATE topic_difficulty
               SET difficulty_level = %s, last_score = %s, attempts = attempts + 1
               WHERE user_id = %s AND topic = %s""",
            (new_level, score, user_id, topic)
        )
        
        return new_level


# ============================================================
# Helper Functions
# ============================================================

def get_user_recommendations(user_id: int, num: int = 12) -> List[Dict]:
    """Get recommendations for a user"""
    engine = RecommendationEngine()
    return engine.get_recommendations(user_id, num)


def record_video_watch(user_id: int, video_id: str, video_title: str, topic: str):
    """Record a video watch"""
    try:
        execute_query(
            """INSERT INTO watched_videos 
               (user_id, video_id, video_title, topic)
               VALUES (%s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE watched_at = NOW()""",
            (user_id, video_id, video_title, topic)
        )
    except Exception as e:
        print(f"Error recording watch: {e}")


def get_continue_watching(user_id: int, num: int = 5) -> List[Dict]:
    """Get videos the user was watching"""
    
    videos = fetch_query(
        """SELECT video_id, video_title, topic, watched_at
           FROM watched_videos
           WHERE user_id = %s
           ORDER BY watched_at DESC
           LIMIT %s""",
        (user_id, num)
    )
    
    return videos or []
