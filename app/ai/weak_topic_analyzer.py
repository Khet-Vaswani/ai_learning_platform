# ============================================================
# ai/weak_topic_analyzer.py — Weak Topic Detection & Analysis
# ============================================================

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from app.utils.db import execute_query, fetch_query
import json

class WeakTopicAnalyzer:
    """
    Analyzes user performance to identify weak topics
    and creates personalized learning strategies.
    """
    
    # Thresholds
    WEAK_THRESHOLD = 60  # % score below which topic is marked weak
    CRITICAL_THRESHOLD = 40  # Critical weakness
    FAIL_COUNT_CRITICAL = 3  # Mark as critical after 3+ failures
    
    def __init__(self):
        pass
    
    def analyze_quiz_performance(self, user_id: int, quiz_id: int, 
                                score: float, concepts: List[Dict]) -> Dict:
        """
        Analyze quiz performance and update weak topics.
        
        Args:
            user_id: User ID
            quiz_id: Quiz ID
            score: Quiz percentage score (0-100)
            concepts: List of incorrect concepts with explanations
            
        Returns:
            Analysis with weak topics and recommendations
        """
        
        analysis = {
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'score': score,
            'status': self._get_status(score),
            'weak_topics': [],
            'learning_strategy': None,
            'action_items': []
        }
        
        # If score is below threshold, mark concepts as weak
        if score < self.WEAK_THRESHOLD:
            for concept in concepts:
                self._mark_weak_topic(user_id, concept)
                analysis['weak_topics'].append(concept)
        
        # Generate learning strategy based on performance
        analysis['learning_strategy'] = self._generate_strategy(user_id, score, concepts)
        
        # Generate action items
        analysis['action_items'] = self._generate_action_items(user_id, score)
        
        return analysis
    
    def _get_status(self, score: float) -> str:
        """Determine performance status"""
        if score >= 90:
            return 'Excellent'
        elif score >= 75:
            return 'Good'
        elif score >= 60:
            return 'Satisfactory'
        elif score >= 40:
            return 'Needs Improvement'
        else:
            return 'Critical'
    
    def _mark_weak_topic(self, user_id: int, concept: Dict) -> None:
        """
        Mark a topic as weak and track fail count.
        """
        
        topic = concept.get('concept', 'Unknown Topic')
        
        # Insert or update weak topic
        try:
            execute_query(
                """INSERT INTO weak_topics (user_id, topic, fail_count)
                   VALUES (%s, %s, 1)
                   ON DUPLICATE KEY UPDATE
                   fail_count = fail_count + 1,
                   last_detected = NOW()""",
                (user_id, topic)
            )
        except Exception as e:
            print(f"Error marking weak topic: {e}")
    
    def _generate_strategy(self, user_id: int, score: float, concepts: List[Dict]) -> Dict:
        """Generate personalized learning strategy based on performance"""
        
        strategy = {
            'focus_areas': [],
            'video_level': 'Beginner',
            'practice_intensity': 'Medium',
            'estimated_time': '30 minutes',
            'recommended_approach': ''
        }
        
        # Determine focus areas
        if score < self.CRITICAL_THRESHOLD:
            strategy['focus_areas'] = [c['concept'] for c in concepts[:3]]
            strategy['video_level'] = 'Beginner'
            strategy['practice_intensity'] = 'High'
            strategy['estimated_time'] = '45 minutes'
            strategy['recommended_approach'] = (
                'Start with foundational videos, then practice with guided problems. '
                'Take this step-by-step and build strong fundamentals.'
            )
        
        elif score < self.WEAK_THRESHOLD:
            strategy['focus_areas'] = [c['concept'] for c in concepts[:2]]
            strategy['video_level'] = 'Beginner to Intermediate'
            strategy['practice_intensity'] = 'Medium'
            strategy['estimated_time'] = '30 minutes'
            strategy['recommended_approach'] = (
                'Review key concepts through videos, then practice problems. '
                'Focus on understanding the "why" behind each concept.'
            )
        
        else:
            strategy['focus_areas'] = [c['concept'] for c in concepts[:1]] if concepts else []
            strategy['video_level'] = 'Intermediate'
            strategy['practice_intensity'] = 'Low'
            strategy['estimated_time'] = '20 minutes'
            strategy['recommended_approach'] = (
                'You\'re doing well! Focus on advanced applications and edge cases. '
                'Try progressively harder problems.'
            )
        
        return strategy
    
    def _generate_action_items(self, user_id: int, score: float) -> List[Dict]:
        """Generate specific action items for the user"""
        
        actions = []
        
        if score < self.CRITICAL_THRESHOLD:
            actions.append({
                'priority': 'CRITICAL',
                'action': 'Watch foundational videos',
                'description': 'Review basics before attempting advanced problems',
                'estimated_time': '20 mins'
            })
            actions.append({
                'priority': 'CRITICAL',
                'action': 'Work through guided examples',
                'description': 'Practice similar problems with step-by-step solutions',
                'estimated_time': '20 mins'
            })
            actions.append({
                'priority': 'HIGH',
                'action': 'Retake quiz',
                'description': 'After studying, retake the quiz to assess improvement',
                'estimated_time': '15 mins'
            })
        
        elif score < self.WEAK_THRESHOLD:
            actions.append({
                'priority': 'HIGH',
                'action': 'Review key concepts',
                'description': 'Watch explanatory videos for concepts you struggled with',
                'estimated_time': '15 mins'
            })
            actions.append({
                'priority': 'MEDIUM',
                'action': 'Practice related problems',
                'description': 'Solve practice problems to reinforce learning',
                'estimated_time': '20 mins'
            })
            actions.append({
                'priority': 'MEDIUM',
                'action': 'Schedule review session',
                'description': 'Set a reminder to review these topics tomorrow',
                'estimated_time': '5 mins'
            })
        
        else:
            actions.append({
                'priority': 'MEDIUM',
                'action': 'Explore advanced topics',
                'description': 'You\'re ready for more challenging material',
                'estimated_time': '20 mins'
            })
        
        return actions
    
    def get_weak_topics_summary(self, user_id: int) -> Dict:
        """Get comprehensive summary of user's weak topics"""
        
        weak_topics = fetch_query(
            """SELECT topic, fail_count, last_detected
               FROM weak_topics
               WHERE user_id = %s
               ORDER BY fail_count DESC, last_detected DESC""",
            (user_id,)
        )
        
        if not weak_topics:
            return {
                'has_weak_topics': False,
                'message': 'Great! No weak topics identified yet. Keep practicing!'
            }
        
        # Categorize by severity
        critical = []
        moderate = []
        minor = []
        
        for topic in weak_topics:
            fail_count = topic['fail_count']
            topic_data = {
                'name': topic['topic'],
                'fail_count': fail_count,
                'last_detected': topic['last_detected'].isoformat(),
                'severity': self._get_severity(fail_count)
            }
            
            if fail_count >= self.FAIL_COUNT_CRITICAL:
                critical.append(topic_data)
            elif fail_count == 2:
                moderate.append(topic_data)
            else:
                minor.append(topic_data)
        
        return {
            'has_weak_topics': True,
            'summary': {
                'total_weak_topics': len(weak_topics),
                'critical': len(critical),
                'moderate': len(moderate),
                'minor': len(minor)
            },
            'critical_topics': critical,
            'moderate_topics': moderate,
            'minor_topics': minor,
            'recommendations': self._get_recommendations(critical, moderate, minor)
        }
    
    def _get_severity(self, fail_count: int) -> str:
        """Determine severity based on fail count"""
        if fail_count >= 3:
            return 'Critical'
        elif fail_count == 2:
            return 'Moderate'
        else:
            return 'Minor'
    
    def _get_recommendations(self, critical: List, moderate: List, minor: List) -> List[str]:
        """Generate recommendations based on weak topic severity"""
        
        recommendations = []
        
        if critical:
            recommendations.append(
                f"🔴 URGENT: Focus on {critical[0]['name']} first. "
                f"You've struggled with this concept {critical[0]['fail_count']} times. "
                f"Start with beginner-level videos and work through examples step-by-step."
            )
        
        if moderate:
            recommendations.append(
                f"🟡 NEXT: After mastering {critical[0]['name'] if critical else 'the critical topics'}, "
                f"review {moderate[0]['name']}. "
                f"Try intermediate-level problems."
            )
        
        if critical or moderate or minor:
            recommendations.append(
                "📅 SCHEDULE: Set aside 30 minutes daily to review weak topics. "
                "Spaced repetition is key to mastering difficult concepts."
            )
        
        recommendations.append(
            "💪 STRATEGY: After learning, immediately practice. "
            "Take quizzes to reinforce understanding and track progress."
        )
        
        return recommendations
    
    def get_progress_chart_data(self, user_id: int) -> Dict:
        """
        Generate data for progress visualization.
        Shows improvement trajectory for weak topics.
        """
        
        # Fetch quiz attempts for last 30 days
        attempts = fetch_query(
            """SELECT 
                   DATE(attempted_at) as date,
                   AVG(percentage) as avg_score,
                   COUNT(*) as num_attempts
               FROM quiz_attempts
               WHERE user_id = %s AND attempted_at > DATE_SUB(NOW(), INTERVAL 30 DAY)
               GROUP BY DATE(attempted_at)
               ORDER BY date ASC""",
            (user_id,)
        )
        
        # Calculate trend
        if len(attempts) >= 2:
            first_score = attempts[0]['avg_score']
            last_score = attempts[-1]['avg_score']
            trend = ((last_score - first_score) / first_score * 100) if first_score > 0 else 0
            direction = 'improving' if trend > 0 else 'declining' if trend < 0 else 'stable'
        else:
            trend = 0
            direction = 'not enough data'
        
        return {
            'chart_data': attempts,
            'trend': {
                'direction': direction,
                'percentage': abs(round(trend, 2)),
                'interpretation': self._interpret_trend(trend, direction)
            },
            'consistency': self._calculate_consistency(attempts)
        }
    
    def _interpret_trend(self, trend: float, direction: str) -> str:
        """Interpret trend in human-readable format"""
        
        if abs(trend) < 5:
            return "Your scores are staying consistent."
        elif trend > 15:
            return "Excellent! You're making rapid progress. Keep it up! 🚀"
        elif trend > 5:
            return "Good progress! You're improving. 📈"
        elif trend < -15:
            return "Scores are declining. Let's focus on weak areas. 🔄"
        else:
            return "Take more quizzes to track progress better."
    
    def _calculate_consistency(self, attempts: List[Dict]) -> str:
        """Calculate score consistency"""
        
        if not attempts or len(attempts) < 3:
            return "Not enough data"
        
        scores = [a['avg_score'] for a in attempts]
        avg_score = sum(scores) / len(scores)
        variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
        std_dev = variance ** 0.5
        
        if std_dev < 10:
            return "Very Consistent"
        elif std_dev < 20:
            return "Somewhat Consistent"
        else:
            return "Variable Performance"
    
    def generate_study_plan(self, user_id: int, duration_minutes: int = 60) -> Dict:
        """
        Generate a personalized study plan for the user.
        """
        
        weak_summary = self.get_weak_topics_summary(user_id)
        
        if not weak_summary['has_weak_topics']:
            return {
                'message': 'No weak topics to study. Great job!',
                'suggestion': 'Take quizzes on new topics to challenge yourself.'
            }
        
        plan = {
            'duration_minutes': duration_minutes,
            'sessions': [],
            'total_time_allocated': 0
        }
        
        # Allocate time based on severity
        session_number = 1
        remaining_time = duration_minutes
        
        # Critical topics get 50% of time
        if weak_summary['critical_topics'] and remaining_time > 0:
            time_for_critical = min(int(remaining_time * 0.5), 30)
            for topic in weak_summary['critical_topics'][:2]:
                if remaining_time <= 0:
                    break
                session_time = min(time_for_critical, remaining_time)
                plan['sessions'].append({
                    'number': session_number,
                    'topic': topic['name'],
                    'severity': 'Critical',
                    'activities': [
                        {'type': 'video', 'duration': int(session_time * 0.5), 
                         'level': 'Beginner'},
                        {'type': 'practice', 'duration': int(session_time * 0.35), 
                         'level': 'Beginner'},
                        {'type': 'quiz', 'duration': int(session_time * 0.15), 
                         'level': 'Easy'}
                    ],
                    'total_time': session_time
                })
                remaining_time -= session_time
                plan['total_time_allocated'] += session_time
                session_number += 1
        
        # Moderate topics get 30% of time
        if weak_summary['moderate_topics'] and remaining_time > 0:
            time_for_moderate = min(int(remaining_time * 0.6), 20)
            for topic in weak_summary['moderate_topics'][:1]:
                if remaining_time <= 0:
                    break
                session_time = min(time_for_moderate, remaining_time)
                plan['sessions'].append({
                    'number': session_number,
                    'topic': topic['name'],
                    'severity': 'Moderate',
                    'activities': [
                        {'type': 'video', 'duration': int(session_time * 0.4), 
                         'level': 'Intermediate'},
                        {'type': 'practice', 'duration': int(session_time * 0.4), 
                         'level': 'Intermediate'},
                        {'type': 'quiz', 'duration': int(session_time * 0.2), 
                         'level': 'Medium'}
                    ],
                    'total_time': session_time
                })
                remaining_time -= session_time
                plan['total_time_allocated'] += session_time
                session_number += 1
        
        plan['summary'] = (
            f"Study for {plan['total_time_allocated']} minutes across {len(plan['sessions'])} sessions. "
            f"Focus on critical topics first, then move to moderate areas."
        )
        
        return plan


# ============================================================
# Helper Functions
# ============================================================

def analyze_user_performance(user_id: int) -> Dict:
    """Get complete analysis of user's performance"""
    analyzer = WeakTopicAnalyzer()
    return analyzer.get_weak_topics_summary(user_id)


def generate_study_plan(user_id: int, duration: int = 60) -> Dict:
    """Generate personalized study plan"""
    analyzer = WeakTopicAnalyzer()
    return analyzer.generate_study_plan(user_id, duration)


def get_progress_analytics(user_id: int) -> Dict:
    """Get progress analytics and trends"""
    analyzer = WeakTopicAnalyzer()
    return analyzer.get_progress_chart_data(user_id)
