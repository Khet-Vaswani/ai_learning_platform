# ============================================================
# moe_engine.py — Transformer-Based MoE Recommendation Engine
# 
# Architecture:
# 1. Feature Extraction  → Student context vector banao
# 2. Attention Router    → Dynamic weights calculate karo
# 3. Expert Networks     → Har expert score deta hai
# 4. Weighted Combiner   → Final recommendation sort karo
#
# Experts:
# - Expert 1: Weak Topic Expert    (quiz fail detection)
# - Expert 2: Performance Expert   (score-based difficulty)
# - Expert 3: Watch History Expert (unexplored topics)
# ============================================================

import math
from app.utils.db import execute_query

from app.ai import moe_engine

class AttentionRouter:
    """
    Transformer-style Attention Router.
    
    Instead of fixed weights, calculates dynamic weights
    based on student's current context.
    
    Attention Formula:
    weight_i = softmax(Q · K_i / sqrt(d_k))
    
    Where:
    Q   = Query vector (student context)
    K_i = Key vector (expert relevance)
    d_k = dimension (scaling factor)
    """

    def __init__(self, student_context):
        self.context = student_context

    def _softmax(self, scores):
        """Softmax to convert scores to probabilities"""
        max_s = max(scores)
        exp_s = [math.exp(s - max_s) for s in scores]
        total = sum(exp_s)
        return [e / total for e in exp_s]

    def compute_weights(self):
        """
        Compute dynamic attention weights per expert.
        
        Query  = Student context features
        Keys   = Expert relevance signals
        
        Returns: {'weak_topic': w1, 'performance': w2, 'history': w3}
        """
        ctx = self.context

        # ── Query Vector (Student Context) ────────────────
        # How many weak topics does student have?
        weak_signal     = min(ctx['weak_count'] * 0.3, 1.0)

        # How many quizzes attempted?
        quiz_signal     = min(ctx['quiz_count'] * 0.1, 1.0)

        # How many videos watched?
        watch_signal    = min(ctx['watch_count'] * 0.05, 1.0)

        # Average performance
        avg_perf        = ctx['avg_score'] / 100.0

        # ── Key Vectors (Expert Relevance) ────────────────
        # Expert 1: Weak Topic Expert
        # Relevant when: many failures, low scores
        k_weak = (
            weak_signal * 0.5 +          # Fail count signal
            (1 - avg_perf) * 0.3 +       # Low performance
            quiz_signal * 0.2            # Has attempted quizzes
        )

        # Expert 2: Performance Expert
        # Relevant when: has quiz history, varying scores
        k_perf = (
            quiz_signal * 0.5 +          # Has quiz data
            avg_perf * 0.3 +             # Performance data exists
            weak_signal * 0.2            # Some failures
        )

        # Expert 3: Watch History Expert
        # Relevant when: has watched videos, new topics available
        k_hist = (
            watch_signal * 0.5 +         # Watch history exists
            (1 - watch_signal) * 0.3 +   # New topics to explore
            (1 - weak_signal) * 0.2      # Not too many failures
        )

        # ── Attention Scores (Q · K / sqrt(d_k)) ─────────
        d_k = math.sqrt(3)  # scaling factor (num experts)

        attn_scores = [
            (weak_signal * k_weak) / d_k,
            (quiz_signal * k_perf) / d_k,
            (watch_signal * k_hist) / d_k
        ]

        # ── Softmax → Probabilities ───────────────────────
        weights = self._softmax(attn_scores)

        return {
            'weak_topic' : weights[0],
            'performance': weights[1],
            'history'    : weights[2]
        }


class TransformerMoE:
    """
    Transformer-Based Mixture of Experts
    
    3 Specialized Experts:
    1. Weak Topic Expert    → Topics where student failed
    2. Performance Expert   → Score-based difficulty adjust
    3. Watch History Expert → New unexplored topics
    
    Dynamic Router:
    - Attention mechanism calculates weights per student
    - No fixed weights — adapts to each student's context
    """

    def __init__(self, user_id):
        self.user_id  = user_id
        self.data     = self._load_student_data()
        self.context  = self._build_context()
        self.router   = AttentionRouter(self.context)
        self.weights  = self.router.compute_weights()

        print(f"\n🤖 TransformerMoE initialized for user {user_id}")
        print(f"   Context: weak={self.context['weak_count']}, "
              f"quizzes={self.context['quiz_count']}, "
              f"watched={self.context['watch_count']}, "
              f"avg={self.context['avg_score']}%")
        print(f"   Dynamic Weights: "
              f"weak={self.weights['weak_topic']:.3f}, "
              f"perf={self.weights['performance']:.3f}, "
              f"hist={self.weights['history']:.3f}")

    # ── Load Student Data ─────────────────────────────────
    def _load_student_data(self):
        """Load all relevant student data"""

        # Weak topics
        weak = execute_query(
            """SELECT topic, fail_count
               FROM weak_topics
               WHERE user_id=%s
               ORDER BY fail_count DESC""",
            (self.user_id,), fetch=True
        ) or []

        # Quiz performance per topic
        performance = execute_query(
            """SELECT topic,
                      ROUND(AVG(score/total*100), 1) as avg_score,
                      COUNT(*) as attempts,
                      MAX(ROUND(score/total*100, 1)) as best_score,
                      MIN(ROUND(score/total*100, 1)) as worst_score
               FROM video_quizzes
               WHERE user_id=%s AND attempted=1 AND total>0
               GROUP BY topic
               ORDER BY avg_score ASC""",
            (self.user_id,), fetch=True
        ) or []

        # Watch history
        watched = execute_query(
            """SELECT DISTINCT video_id, topic
               FROM watched_videos
               WHERE user_id=%s""",
            (self.user_id,), fetch=True
        ) or []

        # Learning curves
        curves = execute_query(
            """SELECT topic, curve_stage,
                      current_score, predicted_next,
                      difficulty_level, learning_rate
               FROM learning_curves
               WHERE user_id=%s""",
            (self.user_id,), fetch=True
        ) or []

        # Overall avg score
        avg = execute_query(
            """SELECT ROUND(AVG(score/total*100), 1) as avg
               FROM video_quizzes
               WHERE user_id=%s AND attempted=1 AND total>0""",
            (self.user_id,), fetch=True
        )
        avg_score = float(avg[0]['avg'] or 0) if avg else 0

        return {
            'weak'       : weak,
            'performance': performance,
            'watched'    : watched,
            'curves'     : curves,
            'avg_score'  : avg_score
        }

    # ── Build Context Vector ──────────────────────────────
    def _build_context(self):
        """
        Build student context vector for attention router.
        This is the 'Query' in attention mechanism.
        """
        d = self.data
        return {
            'weak_count' : len(d['weak']),
            'quiz_count' : len(d['performance']),
            'watch_count': len(d['watched']),
            'avg_score'  : d['avg_score']
        }

    # ========================================================
    # EXPERT 1: Weak Topic Expert
    # Analyzes failed quiz topics
    # ========================================================
    def expert_weak_topics(self):
        """
        Detects topics where student failed.
        Higher fail_count = Higher priority.
        
        Also uses learning curve stage for context.
        """
        queries  = []
        weak     = self.data['weak']
        curves   = {c['topic']: c for c in self.data['curves']}

        if not weak:
            return queries

        for wt in weak[:5]:
            topic      = wt['topic']
            fail_count = wt['fail_count']

            # Base score from fail count
            base_score = min(fail_count * 0.25, 1.0)

            # Boost if learning curve shows struggling
            curve = curves.get(topic)
            if curve and curve['curve_stage'] == 'Struggling':
                base_score = min(base_score + 0.2, 1.0)
                query  = f"{topic} basics explained simply beginners"
                reason = f"⚠️ Struggling with {topic} — failed {fail_count}x"
            elif curve and curve['curve_stage'] == 'Plateau':
                base_score = min(base_score + 0.1, 1.0)
                query  = f"{topic} different approach new perspective"
                reason = f"📊 Plateau in {topic} — try new approach"
            else:
                query  = f"{topic} tutorial beginners step by step"
                reason = f"⚠️ Weak topic: {topic} (failed {fail_count}x)"

            # Final score with attention weight
            final = round(
                base_score * self.weights['weak_topic'], 4
            )

            queries.append({
                'query'       : query,
                'topic'       : topic,
                'expert'      : 'weak_topic',
                'expert_score': base_score,
                'final_score' : final,
                'reason'      : reason,
                'priority'    : 'high',
                'weight_used' : round(self.weights['weak_topic'], 3)
            })

        return queries

    # ========================================================
    # EXPERT 2: Performance Expert
    # Analyzes quiz scores to adjust difficulty
    # ========================================================
    def expert_performance(self):
        """
        Uses quiz performance history to recommend
        appropriate difficulty level videos.
        
        Low score    → Basic videos
        Medium score → Intermediate
        High score   → Advanced
        """
        queries     = []
        performance = self.data['performance']
        curves      = {c['topic']: c for c in self.data['curves']}

        if not performance:
            return queries

        for perf in performance[:5]:
            topic     = perf['topic']
            avg       = float(perf['avg_score'] or 0)
            attempts  = perf['attempts']
            best      = float(perf['best_score'] or 0)
            worst     = float(perf['worst_score'] or 0)

            # Learning curve context
            curve = curves.get(topic)
            stage = curve['curve_stage'] if curve else 'Unknown'

            # Calculate expert score
            if avg < 40:
                expert_score = 0.95
                query  = f"{topic} simplified easy explanation beginners"
                reason = f"📉 Very low score {avg:.0f}% in {topic}"
            elif avg < 60:
                expert_score = 0.80
                query  = f"{topic} tutorial practice exercises"
                reason = f"📊 Below average {avg:.0f}% in {topic}"
            elif avg < 75:
                expert_score = 0.60
                query  = f"{topic} intermediate concepts examples"
                reason = f"📈 Improving in {topic} ({avg:.0f}%)"
            else:
                expert_score = 0.35
                query  = f"{topic} advanced deep dive projects"
                reason = f"🏆 Good score {avg:.0f}% — ready to advance"

            # Boost if many attempts but still low
            if attempts >= 3 and avg < 60:
                expert_score = min(expert_score + 0.1, 1.0)

            final = round(
                expert_score * self.weights['performance'], 4
            )

            queries.append({
                'query'       : query,
                'topic'       : topic,
                'expert'      : 'performance',
                'expert_score': expert_score,
                'final_score' : final,
                'reason'      : reason,
                'priority'    : 'high' if avg < 60 else 'medium',
                'weight_used' : round(self.weights['performance'], 3),
                'curve_stage' : stage
            })

        return queries

    # ========================================================
    # EXPERT 3: Watch History Expert
    # Suggests unexplored topics
    # ========================================================
    def expert_history(self):
        """
        Analyzes watch history to find unexplored topics.
        Boosts topics student has never seen.
        """
        queries     = []
        watched     = self.data['watched']
        weak_topics = {w['topic'].lower() for w in self.data['weak']}

        watched_topics = set(
            w['topic'].lower()
            for w in watched if w['topic']
        )

        # All available topics
        all_topics = [
            ('Python Programming',  'python programming tutorial'),
            ('Web Development',     'html css javascript web development'),
            ('Machine Learning',    'machine learning beginners'),
            ('Data Science',        'data science python pandas'),
            ('JavaScript',          'javascript tutorial es6'),
            ('Database SQL',        'sql mysql database tutorial'),
            ('Algorithms',          'algorithms data structures'),
            ('Flask Framework',     'flask python web framework'),
            ('Deep Learning',       'deep learning neural networks'),
            ('Data Analysis',       'data analysis python numpy'),
        ]

        for topic_name, query in all_topics:
            t_lower = topic_name.lower()

            # Skip if already watched
            if t_lower in watched_topics:
                continue

            # Skip if already in weak topics
            # (handled by Expert 1)
            if t_lower in weak_topics:
                continue

            expert_score = 0.5

            final = round(
                expert_score * self.weights['history'], 4
            )

            queries.append({
                'query'       : query,
                'topic'       : topic_name,
                'expert'      : 'history',
                'expert_score': expert_score,
                'final_score' : final,
                'reason'      : f"📺 New topic to explore: {topic_name}",
                'priority'    : 'low',
                'weight_used' : round(self.weights['history'], 3)
            })

        return queries[:3]

    # ========================================================
    # ROUTER — Combine All Experts
    # ========================================================
    def get_recommendations(self):
        """
        Main routing function:
        1. Collect from all 3 experts
        2. Apply dynamic attention weights
        3. Sort by final_score
        4. Remove duplicates
        5. Return top queries
        """
        all_queries = []

        # Collect from experts
        e1 = self.expert_weak_topics()
        e2 = self.expert_performance()
        e3 = self.expert_history()

        all_queries.extend(e1)
        all_queries.extend(e2)
        all_queries.extend(e3)

        print(f"\n📊 Expert Outputs:")
        print(f"   Expert 1 (Weak Topics) : {len(e1)} queries")
        print(f"   Expert 2 (Performance) : {len(e2)} queries")
        print(f"   Expert 3 (History)     : {len(e3)} queries")
        print(f"   Total                  : {len(all_queries)} queries")

        # Sort by final score
        all_queries.sort(
            key=lambda x: x['final_score'],
            reverse=True
        )

        # Remove duplicates
        seen   = set()
        unique = []
        for q in all_queries:
            key = q['query'][:30].lower()
            if key not in seen:
                seen.add(key)
                unique.append(q)

        print(f"\n🎯 Top Recommendations:")
        for q in unique[:5]:
            print(f"   [{q['expert']:12}] "
                  f"score={q['final_score']:.4f} "
                  f"w={q['weight_used']:.3f} "
                  f"— {q['reason'][:40]}")

        return unique

    # ── Get Expert Analysis ───────────────────────────────
    def get_analysis(self):
        """Return MoE analysis for display"""
        return {
            'weights'   : self.weights,
            'context'   : self.context,
            'experts'   : {
                'weak_topic': {
                    'name'  : 'Weak Topic Expert',
                    'icon'  : '⚠️',
                    'weight': round(self.weights['weak_topic'], 3),
                    'data'  : len(self.data['weak'])
                },
                'performance': {
                    'name'  : 'Performance Expert',
                    'icon'  : '📊',
                    'weight': round(self.weights['performance'], 3),
                    'data'  : len(self.data['performance'])
                },
                'history': {
                    'name'  : 'History Expert',
                    'icon'  : '📺',
                    'weight': round(self.weights['history'], 3),
                    'data'  : len(self.data['watched'])
                }
            }
        }