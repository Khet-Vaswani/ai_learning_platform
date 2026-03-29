# ============================================================
# learning_curve.py — Learning Curve Model
# MoE based difficulty prediction per topic
# ============================================================

import math
from app.utils.db import execute_query


class LearningCurveModel:
    """
    Models learning curve for each topic per student.
    
    Learning Curve Formula:
    Performance(t) = Max_Score × (1 - e^(-attempts/lambda))
    
    Where:
    - t      = number of attempts
    - lambda = learning rate (how fast student learns)
    - Max    = theoretical maximum performance
    """

    def __init__(self, user_id):
        self.user_id = user_id

    # ── Calculate Learning Curve Per Topic ────────────────
    def calculate_curve(self, topic):
        """
        Get all quiz attempts for a topic and
        calculate the learning curve parameters.
        """
        attempts = execute_query(
            """SELECT score, total, created_at,
                      ROUND(score/total*100, 1) as pct
               FROM video_quizzes
               WHERE user_id=%s AND topic=%s
               AND attempted=1 AND total > 0
               ORDER BY created_at ASC""",
            (self.user_id, topic), fetch=True
        ) or []

        if not attempts:
            return {
                'topic'           : topic,
                'attempts'        : 0,
                'current_score'   : 0,
                'predicted_next'  : 0,
                'learning_rate'   : 0,
                'difficulty_level': 'Unknown',
                'curve_stage'     : 'Not Started',
                'mastery_eta'     : 'N/A',
                'scores'          : []
            }

        scores = [float(a['pct']) for a in attempts]
        n      = len(scores)

        # Current performance
        current = scores[-1]
        avg     = sum(scores) / n

        # Learning Rate — how fast improving
        if n >= 2:
            # Calculate improvement per attempt
            improvements = []
            for i in range(1, n):
                imp = scores[i] - scores[i-1]
                improvements.append(imp)
            learning_rate = sum(improvements) / len(improvements)
        else:
            learning_rate = 0

        # Predict next score using exponential model
        if n >= 2:
            # Fit simple exponential: score = max*(1-e^(-t/λ))
            predicted_next = min(
                current + max(learning_rate, 0) * 0.8,
                100
            )
        else:
            predicted_next = current

        # Determine curve stage
        curve_stage = self._get_curve_stage(
            scores, learning_rate
        )

        # Difficulty level based on curve
        difficulty = self._predict_difficulty(
            current, learning_rate, n
        )

        # Mastery ETA
        mastery_eta = self._estimate_mastery(
            current, learning_rate, n
        )

        return {
            'topic'           : topic,
            'attempts'        : n,
            'scores'          : scores,
            'current_score'   : current,
            'avg_score'       : round(avg, 1),
            'predicted_next'  : round(predicted_next, 1),
            'learning_rate'   : round(learning_rate, 2),
            'difficulty_level': difficulty,
            'curve_stage'     : curve_stage,
            'mastery_eta'     : mastery_eta
        }

    def _get_curve_stage(self, scores, learning_rate):
        """
        Learning Curve has 4 stages:
        1. Initial (just started)
        2. Rapid Growth (improving fast)
        3. Plateau (slowing down)
        4. Mastery (high performance)
        """
        if not scores:
            return 'Not Started'

        current = scores[-1]
        n       = len(scores)

        if n <= 1:
            return 'Initial Stage'
        elif current >= 80:
            return 'Mastery'
        elif learning_rate > 5:
            return 'Rapid Growth'
        elif learning_rate > 0:
            return 'Steady Progress'
        elif learning_rate <= 0 and current < 50:
            return 'Struggling'
        else:
            return 'Plateau'

    def _predict_difficulty(self, current, learning_rate, attempts):
        """
        Predict topic difficulty based on learning curve.
        Different from just checking score!
        
        Logic:
        - High score + few attempts = Easy topic
        - Low score + many attempts = Hard topic
        - Improving fast = Medium topic
        """
        if attempts == 0:
            return 'Unknown'

        # Score-based difficulty
        if current >= 80:
            base_diff = 'Easy'
        elif current >= 60:
            base_diff = 'Medium'
        else:
            base_diff = 'Hard'

        # Adjust based on learning rate
        if learning_rate > 10:
            # Improving rapidly → getting easier
            if base_diff == 'Hard':
                return 'Medium'
        elif learning_rate < -5:
            # Declining → harder than expected
            if base_diff == 'Medium':
                return 'Hard'

        # Many attempts still low → Very Hard
        if attempts >= 4 and current < 50:
            return 'Very Hard'

        return base_diff

    def _estimate_mastery(self, current, learning_rate, attempts):
        """
        Estimate how many more attempts to reach mastery (80%)
        """
        if current >= 80:
            return 'Already Mastered! 🎉'

        if learning_rate <= 0:
            return 'Need different approach'

        remaining = 80 - current
        eta       = math.ceil(remaining / max(learning_rate, 1))

        if eta <= 1:
            return '1 more attempt'
        elif eta <= 3:
            return f'{eta} more attempts'
        else:
            return f'{eta}+ attempts needed'

    # ── Get All Topics Curves ─────────────────────────────
    def get_all_curves(self):
        """Get learning curves for all topics student attempted"""
        topics = execute_query(
            """SELECT DISTINCT topic FROM video_quizzes
               WHERE user_id=%s AND attempted=1 AND total>0""",
            (self.user_id,), fetch=True
        ) or []

        curves = []
        for t in topics:
            curve = self.calculate_curve(t['topic'])
            curves.append(curve)

        # Sort by difficulty (hardest first)
        difficulty_order = {
            'Very Hard': 0,
            'Hard'     : 1,
            'Medium'   : 2,
            'Easy'     : 3,
            'Unknown'  : 4
        }
        curves.sort(
            key=lambda x: difficulty_order.get(
                x['difficulty_level'], 5
            )
        )

        return curves

    # ── Save Curve to DB ──────────────────────────────────
    def save_curve(self, topic):
        """Save learning curve data to database"""
        curve = self.calculate_curve(topic)

        execute_query(
            """INSERT INTO learning_curves
               (user_id, topic, attempts, current_score,
                predicted_next, learning_rate,
                difficulty_level, curve_stage)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE
               attempts         = %s,
               current_score    = %s,
               predicted_next   = %s,
               learning_rate    = %s,
               difficulty_level = %s,
               curve_stage      = %s,
               updated_at       = CURRENT_TIMESTAMP""",
            (
                self.user_id, topic,
                curve['attempts'], curve['current_score'],
                curve['predicted_next'], curve['learning_rate'],
                curve['difficulty_level'], curve['curve_stage'],
                curve['attempts'], curve['current_score'],
                curve['predicted_next'], curve['learning_rate'],
                curve['difficulty_level'], curve['curve_stage']
            )
        )
        return curve


# ============================================================
# MoE + Learning Curve Integration
# ============================================================
class MoELearningCurve:
    """
    Mixture of Experts with Learning Curve

    Expert 1: Curve Stage Expert
    - What stage is student at per topic?

    Expert 2: Difficulty Prediction Expert
    - How hard is this topic for this student?

    Expert 3: Next Video Expert
    - What video will help most right now?

    Expert 4: Mastery Prediction Expert
    - How close to mastery?
    """

    WEIGHTS = {
        'curve_stage'  : 0.35,
        'difficulty'   : 0.30,
        'next_video'   : 0.20,
        'mastery'      : 0.15
    }

    def __init__(self, user_id):
        self.user_id = user_id
        self.model   = LearningCurveModel(user_id)
        self.curves  = self.model.get_all_curves()

    def get_recommendations(self):
        """
        Use learning curves to recommend best videos
        """
        queries = []

        for curve in self.curves:
            topic = curve['topic']
            stage = curve['curve_stage']
            diff  = curve['difficulty_level']
            rate  = curve['learning_rate']

            # Expert 1: Based on curve stage
            if stage == 'Struggling':
                # Need basic help
                q = f"{topic} explained simply for beginners"
                s = 0.9
                r = f"📉 Struggling with {topic} — need basics"
            elif stage == 'Rapid Growth':
                # Keep momentum
                q = f"{topic} intermediate exercises practice"
                s = 0.7
                r = f"📈 Great progress in {topic} — keep going!"
            elif stage == 'Plateau':
                # Need new approach
                q = f"{topic} different approach tutorial"
                s = 0.8
                r = f"📊 Plateau in {topic} — try new approach"
            elif stage == 'Mastery':
                # Advance to next level
                q = f"{topic} advanced concepts projects"
                s = 0.4
                r = f"🏆 Mastered {topic} — try advanced!"
            else:
                q = f"{topic} tutorial beginners"
                s = 0.5
                r = f"🎯 Start learning {topic}"

            # Expert 2: Based on difficulty
            if diff == 'Very Hard':
                s = min(s + 0.1, 1.0)  # Boost priority

            # Calculate final score
            final = round(
                s * self.WEIGHTS['curve_stage'] +
                (1 - curve['current_score']/100) *
                self.WEIGHTS['difficulty'],
                4
            )

            queries.append({
                'query'       : q,
                'topic'       : topic,
                'expert'      : 'learning_curve',
                'expert_score': s,
                'final_score' : final,
                'reason'      : r,
                'curve_stage' : stage,
                'priority'    : 'high' if s >= 0.8 else 'medium',
                'predicted'   : curve['predicted_next'],
                'current'     : curve['current_score']
            })

        # Sort by final score
        queries.sort(key=lambda x: x['final_score'], reverse=True)
        return queries