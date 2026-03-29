# ============================================================
# evaluator.py — Quantitative Evaluation of MoE System
# ============================================================

import math
from app.ai.moe_engine import TransformerMoE
from app.utils.db import execute_query

MoEEngine = TransformerMoE
class RecommendationEvaluator:
    """
    Evaluates MoE Recommendation Engine using:
    1. Precision@K
    2. Recall@K
    3. NDCG@K
    4. Hit Rate
    5. Coverage
    6. Diversity
    7. Learning Improvement Rate
    """

    def __init__(self, user_id):
        self.user_id = user_id

    # ── Get Ground Truth ─────────────────────────────────
    def get_ground_truth(self):
        """
        Ground truth = topics where user has weak performance
        These SHOULD be recommended by system
        """
        weak = execute_query(
            """SELECT wt.topic, fail_count,
                      AVG(vq.score/vq.total*100) as avg_score
               FROM weak_topics wt
               LEFT JOIN video_quizzes vq
               ON vq.user_id=wt.user_id AND vq.topic=wt.topic
               WHERE wt.user_id=%s
               GROUP BY wt.topic, wt.fail_count
               ORDER BY fail_count DESC""",
            (self.user_id,), fetch=True
        ) or []

        return [w['topic'] for w in weak]

    # ── Get Recommendations ───────────────────────────────
    def get_recommendations(self, k=10):
        """Get MoE recommended topics"""
        from app.ai.moe_engine import TransformerMoE
        try:
            engine = TransformerMoE(self.user_id)
            recs   = engine.get_recommendations()
            return [r['topic'] for r in recs[:k]]
        except Exception as e:
            print(f"MoE error: {e}")
            return []

    # ══════════════════════════════════════════════════════
    # METRIC 1 — Precision@K
    # ══════════════════════════════════════════════════════
    def precision_at_k(self, recommended, relevant, k):
        """
        Precision@K = Relevant in Top-K / K

        How many recommended items are actually relevant?
        Higher = Better
        """
        if not recommended or k == 0:
            return 0.0

        top_k     = recommended[:k]
        hits      = sum(1 for r in top_k if r in relevant)
        precision = hits / k

        return round(precision, 4)

    # ══════════════════════════════════════════════════════
    # METRIC 2 — Recall@K
    # ══════════════════════════════════════════════════════
    def recall_at_k(self, recommended, relevant, k):
        """
        Recall@K = Relevant in Top-K / Total Relevant

        How many relevant items were found?
        Higher = Better
        """
        if not recommended or not relevant:
            return 0.0

        top_k  = recommended[:k]
        hits   = sum(1 for r in top_k if r in relevant)
        recall = hits / len(relevant)

        return round(recall, 4)

    # ══════════════════════════════════════════════════════
    # METRIC 3 — NDCG@K
    # ══════════════════════════════════════════════════════
    def ndcg_at_k(self, recommended, relevant, k):
        """
        NDCG@K = DCG@K / IDCG@K

        Measures ranking quality — relevant items
        should appear at top positions.
        Higher = Better (max = 1.0)
        """
        if not recommended or not relevant:
            return 0.0

        top_k = recommended[:k]

        # DCG — actual ranking
        dcg = 0.0
        for i, item in enumerate(top_k):
            if item in relevant:
                # Position 1-indexed
                dcg += 1.0 / math.log2(i + 2)

        # IDCG — ideal ranking (all relevant first)
        ideal_hits = min(len(relevant), k)
        idcg       = sum(1.0 / math.log2(i + 2)
                         for i in range(ideal_hits))

        if idcg == 0:
            return 0.0

        ndcg = dcg / idcg
        return round(ndcg, 4)

    # ══════════════════════════════════════════════════════
    # METRIC 4 — Hit Rate
    # ══════════════════════════════════════════════════════
    def hit_rate(self, recommended, relevant, k):
        """
        Hit Rate = 1 if at least 1 relevant item in Top-K

        Did the system find at least 1 relevant item?
        Binary metric: 0 or 1
        """
        if not recommended or not relevant:
            return 0

        top_k = recommended[:k]
        for item in top_k:
            if item in  relevant:
                return 1
        return 0

    # ══════════════════════════════════════════════════════
    # METRIC 5 — Coverage
    # ══════════════════════════════════════════════════════
    def coverage(self, recommended):
        """
        Coverage = Unique Topics Recommended / Total Topics

        How much of the catalog does system cover?
        Higher = Better
        """
        all_topics = execute_query(
            """SELECT DISTINCT topic FROM video_quizzes
               WHERE user_id=%s""",
            (self.user_id,), fetch=True
        ) or []

        total = len(all_topics)
        if total == 0:
            return 0.0

        unique_recs = len(set(recommended))
        return round(unique_recs / total, 4)

    # ══════════════════════════════════════════════════════
    # METRIC 6 — Diversity
    # ══════════════════════════════════════════════════════
    def diversity(self, recommended):
        """
        Diversity = Unique items / Total recommended

        Are recommendations diverse or repetitive?
        Higher = More diverse
        """
        if not recommended:
            return 0.0

        unique = len(set(recommended))
        total  = len(recommended)
        return round(unique / total, 4)

    # ══════════════════════════════════════════════════════
    # METRIC 7 — Learning Improvement Rate
    # ══════════════════════════════════════════════════════
    def learning_improvement_rate(self):
        """
        LIR = (Current Avg - Initial Avg) / Initial Avg * 100

        Did scores improve over time?
        Positive = Improving
        """
        quizzes = execute_query(
            """SELECT score, total, created_at,
                      ROUND(score/total*100, 1) as pct
               FROM video_quizzes
               WHERE user_id=%s AND attempted=1 AND total>0
               ORDER BY created_at ASC""",
            (self.user_id,), fetch=True
        ) or []

        if len(quizzes) < 2:
            return 0.0

        scores = [float(q['pct']) for q in quizzes]
        n      = len(scores)

        # First 30% as initial, last 30% as current
        split  = max(1, n // 3)
        initial_avg = sum(scores[:split]) / split
        current_avg = sum(scores[-split:]) / split

        if initial_avg == 0:
            return 0.0

        lir = ((current_avg - initial_avg) / initial_avg) * 100
        return round(lir, 2)

    # ══════════════════════════════════════════════════════
    # METRIC 8 — MoE vs Random Baseline
    # ══════════════════════════════════════════════════════
    def moe_vs_random(self, relevant, k=5):
        """
        Compare MoE recommendations against random baseline.
        Shows how much better MoE is than random.
        """
        import random

        # All available topics
        all_topics_q = execute_query(
            """SELECT DISTINCT topic FROM video_quizzes
               WHERE topic IS NOT NULL""",
            fetch=True
        ) or []

        all_topics = [t['topic'] for t in all_topics_q]

        if not all_topics or not relevant:
            return {
                'moe_precision'   : 0,
                'random_precision': 0,
                'improvement'     : 0
            }

        # Random recommendations
        random_recs = random.sample(
            all_topics,
            min(k, len(all_topics))
        )

        # MoE recommendations
        moe_recs = self.get_recommendations(k)

        moe_p    = self.precision_at_k(moe_recs, relevant, k)
        random_p = self.precision_at_k(random_recs, relevant, k)

        improvement = 0
        if random_p > 0:
            improvement = round(
                ((moe_p - random_p) / random_p) * 100, 1
            )
        elif moe_p > 0:
            improvement = 100.0

        return {
            'moe_precision'   : moe_p,
            'random_precision': random_p,
            'improvement_pct' : improvement
        }

    # ══════════════════════════════════════════════════════
    # FULL EVALUATION REPORT
    # ══════════════════════════════════════════════════════
    def full_evaluation(self, k=5):
        """Run complete evaluation and return all metrics"""

        relevant     = self.get_ground_truth()
        recommended  = self.get_recommendations(k)
        baseline     = self.moe_vs_random(relevant, k)
        lir          = self.learning_improvement_rate()

        # Calculate all metrics
        p_at_k  = self.precision_at_k(recommended, relevant, k)
        r_at_k  = self.recall_at_k(recommended, relevant, k)
        ndcg    = self.ndcg_at_k(recommended, relevant, k)
        hr      = self.hit_rate(recommended, relevant, k)
        cov     = self.coverage(recommended)
        div     = self.diversity(recommended)

        # Overall score (weighted average)
        overall = round(
            (p_at_k * 0.25 +
             r_at_k * 0.20 +
             ndcg   * 0.25 +
             hr     * 0.15 +
             cov    * 0.075 +
             div    * 0.075) * 100, 1
        )

        # Grade
        if overall >= 75:   grade = 'Excellent'
        elif overall >= 55: grade = 'Good'
        elif overall >= 35: grade = 'Fair'
        else:               grade = 'Needs Improvement'

        return {
            'k'                  : k,
            'relevant_count'     : len(relevant),
            'recommended_count'  : len(recommended),
            'relevant_topics'    : relevant,
            'recommended_topics' : recommended,

            # Core metrics
            'precision_at_k'     : p_at_k,
            'recall_at_k'        : r_at_k,
            'ndcg_at_k'          : ndcg,
            'hit_rate'           : hr,
            'coverage'           : cov,
            'diversity'          : div,

            # Improvement
            'learning_improvement': lir,

            # Baseline comparison
            'moe_precision'       : baseline['moe_precision'],
            'random_precision'    : baseline['random_precision'],
            'improvement_pct'     : baseline['improvement_pct'],

            # Summary
            'overall_score'       : overall,
            'grade'               : grade
        }