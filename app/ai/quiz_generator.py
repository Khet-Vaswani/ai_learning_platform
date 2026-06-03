# ============================================================
# ai/quiz_generator.py — AI-Powered Quiz Generation
# ============================================================

import json
import re
from typing import Dict, List, Optional
import google.generativeai as genai
from app.utils.db import execute_query, fetch_query

class QuizGenerator:
    """Generate MCQ quizzes from video transcripts using Gemini AI"""
    
    def __init__(self, api_key: str = None):
        """Initialize with Gemini API key"""
        if api_key:
            genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    def generate_quiz(self, 
                     video_id: str,
                     transcript: str,
                     topic: str,
                     num_questions: int = 10,
                     difficulty: str = 'Medium') -> Dict:
        """
        Generate multiple-choice quiz from video transcript.
        
        Args:
            video_id: YouTube video ID
            transcript: Full video transcript
            topic: Topic/subject of the video
            num_questions: Number of MCQs to generate
            difficulty: Easy/Medium/Hard
            
        Returns:
            Dictionary with quiz questions and answers
        """
        
        # Limit transcript for API
        transcript_limited = transcript[:6000]
        
        prompt = f"""
        Based on the following video transcript about "{topic}", generate {num_questions} 
        multiple-choice questions suitable for {difficulty} level learners.
        
        TRANSCRIPT:
        {transcript_limited}
        
        Generate the quiz in the following JSON format:
        {{
            "topic": "{topic}",
            "difficulty": "{difficulty}",
            "num_questions": {num_questions},
            "questions": [
                {{
                    "id": 1,
                    "question": "The question text?",
                    "options": {{
                        "A": "Option A",
                        "B": "Option B",
                        "C": "Option C",
                        "D": "Option D"
                    }},
                    "correct_answer": "B",
                    "explanation": "Why B is correct and others are wrong",
                    "concept_tested": "The concept being tested",
                    "difficulty": "Medium"
                }},
                ...more questions
            ],
            "passing_score": 70,
            "estimated_time": "15 minutes"
        }}
        
        IMPORTANT:
        - Questions should directly relate to the transcript content
        - Ensure accuracy of the correct answers
        - Provide clear explanations
        - Mix question types (definition, application, analysis)
        - For Hard difficulty, include complex reasoning questions
        """
        
        try:
            response = self.model.generate_content(prompt)
            quiz_data = self._extract_json(response.text)
            
            return {
                'success': True,
                'quiz': quiz_data,
                'video_id': video_id
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'raw_response': response.text if 'response' in locals() else None
            }
    
    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from AI response"""
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json.loads(json_match.group())
        raise ValueError("No JSON found in response")
    
    def save_quiz(self, user_id: int, video_id: str, quiz_data: Dict) -> int:
        """Save generated quiz to database and return quiz ID"""
        
        try:
            # Insert quiz record
            quiz_id = execute_query(
                """INSERT INTO video_quizzes 
                   (user_id, video_id, video_title, topic, questions)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, video_id, quiz_data.get('topic', ''),
                 quiz_data.get('topic', ''), json.dumps(quiz_data.get('questions', [])))
            )
            return quiz_id
        except Exception as e:
            print(f"Error saving quiz: {e}")
            return None
    
    def grade_quiz(self, user_id: int, quiz_id: int, answers: Dict[int, str]) -> Dict:
        """
        Grade a completed quiz.
        
        Args:
            user_id: User who took the quiz
            quiz_id: Quiz ID
            answers: Dict mapping question_id to answer (A/B/C/D)
            
        Returns:
            Dictionary with score, result, and weak topics
        """
        
        # Fetch quiz questions
        quiz_data = fetch_query(
            "SELECT questions FROM video_quizzes WHERE id = %s",
            (quiz_id,)
        )
        
        if not quiz_data:
            return {'success': False, 'error': 'Quiz not found'}
        
        questions = json.loads(quiz_data[0]['questions'])
        
        score = 0
        total = len(questions)
        incorrect_concepts = []
        
        for question in questions:
            q_id = question['id']
            correct = question['correct_answer']
            user_answer = answers.get(str(q_id), '')
            
            if user_answer == correct:
                score += 1
            else:
                # Track weak concept
                incorrect_concepts.append({
                    'concept': question.get('concept_tested', 'General'),
                    'question': question['question'],
                    'explanation': question['explanation']
                })
        
        percentage = (score / total * 100) if total > 0 else 0
        
        # Save quiz attempt
        execute_query(
            """INSERT INTO quiz_attempts
               (user_id, quiz_id, score, total_questions, percentage)
               VALUES (%s, %s, %s, %s, %s)""",
            (user_id, quiz_id, score, total, percentage)
        )
        
        # Detect weak topics if score is low
        if percentage < 60:
            self._track_weak_topics(user_id, incorrect_concepts)
        
        return {
            'success': True,
            'score': score,
            'total': total,
            'percentage': round(percentage, 2),
            'passed': percentage >= 60,
            'incorrect_concepts': incorrect_concepts[:5],  # Top 5
            'feedback': self._generate_feedback(percentage, incorrect_concepts)
        }
    
    def _track_weak_topics(self, user_id: int, concepts: List[Dict]) -> None:
        """Track weak topics for adaptive recommendations"""
        
        for concept in concepts:
            topic = concept['concept']
            
            # Update or insert weak topic
            execute_query(
                """INSERT INTO weak_topics (user_id, topic, fail_count)
                   VALUES (%s, %s, 1)
                   ON DUPLICATE KEY UPDATE
                   fail_count = fail_count + 1,
                   last_detected = NOW()""",
                (user_id, topic)
            )
    
    def _generate_feedback(self, percentage: float, incorrect_concepts: List[Dict]) -> str:
        """Generate feedback based on performance"""
        
        if percentage >= 90:
            return "Excellent! You have mastered this topic. 🌟"
        elif percentage >= 75:
            return "Great work! You understand most concepts. Keep practicing! 👍"
        elif percentage >= 60:
            return "Good effort! Review the weak areas below. 📖"
        else:
            return "Keep learning! Study the concepts below and try again. 💪"
    
    def format_quiz_html(self, quiz: Dict) -> str:
        """Format quiz for HTML display"""
        
        html = f"""
        <div class="quiz-container">
            <div class="quiz-header">
                <h1>{quiz.get('topic', 'Quiz')}</h1>
                <div class="quiz-meta">
                    <span class="difficulty {quiz.get('difficulty', 'Medium').lower()}">
                        {quiz.get('difficulty', 'Medium')}
                    </span>
                    <span class="question-count">{quiz.get('num_questions', 0)} Questions</span>
                    <span class="est-time">{quiz.get('estimated_time', '15 minutes')}</span>
                </div>
            </div>
            
            <form id="quizForm" class="quiz-form">
        """
        
        for question in quiz.get('questions', []):
            html += f"""
                <div class="question-block">
                    <h3>Q{question.get('id', 1)}: {question.get('question', '')}</h3>
                    
                    <div class="options">
            """
            
            for option_key, option_text in question.get('options', {}).items():
                html += f"""
                        <label class="option-label">
                            <input type="radio" name="q{question.get('id', 1)}" 
                                   value="{option_key}" required>
                            <span class="option-key">{option_key}.</span>
                            <span class="option-text">{option_text}</span>
                        </label>
                """
            
            html += """
                    </div>
                </div>
            """
        
        html += f"""
            </form>
            
            <div class="quiz-footer">
                <p class="passing-score">Passing Score: {quiz.get('passing_score', 70)}%</p>
                <button type="submit" form="quizForm" class="btn-submit">Submit Quiz</button>
            </div>
        </div>
        """
        
        return html
    
    def get_adaptive_questions(self, user_id: int, difficulty: str = 'Medium', num: int = 5) -> List[Dict]:
        """
        Get questions adapted to user's weak topics.
        
        Returns questions related to concepts the user struggled with.
        """
        
        # Fetch user's weak topics
        weak_topics = fetch_query(
            """SELECT topic, fail_count FROM weak_topics 
               WHERE user_id = %s 
               ORDER BY fail_count DESC, last_detected DESC
               LIMIT 3""",
            (user_id,)
        )
        
        if not weak_topics:
            return []
        
        topics_list = [t['topic'] for t in weak_topics]
        topic_string = ', '.join(topics_list)
        
        # Generate adaptive questions
        prompt = f"""
        Generate {num} focused multiple-choice questions on these topics:
        {topic_string}
        
        These questions are for a student who struggled with these concepts.
        Make them progressively challenging from current level.
        
        Return as JSON array of questions with the same format as before.
        """
        
        try:
            response = self.model.generate_content(prompt)
            questions = self._extract_json(response.text)
            return questions.get('questions', []) if isinstance(questions, dict) else questions
        except:
            return []


# ============================================================
# Helper function for quiz generation in Flask
# ============================================================

def generate_quiz_sync(video_id: str, transcript: str, topic: str, 
                       num_questions: int = 10, difficulty: str = 'Medium') -> Dict:
    """Synchronous wrapper for quiz generation"""
    
    generator = QuizGenerator()
    return generator.generate_quiz(video_id, transcript, topic, num_questions, difficulty)


def grade_quiz_sync(user_id: int, quiz_id: int, answers: Dict) -> Dict:
    """Synchronous wrapper for quiz grading"""
    
    generator = QuizGenerator()
    return generator.grade_quiz(user_id, quiz_id, answers)
