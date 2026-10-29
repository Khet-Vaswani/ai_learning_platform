"""
Unit tests for the platform's core logic (no database, no network, no API keys).

Run from the project folder:
    venv\\Scripts\\python.exe -m unittest tests.test_core_logic -v

The database helper `execute_query` is replaced with fakes, and no LLM,
YouTube or Whisper call is made, so these tests check the platform's own
rules: transcript validation, quiz grounding, scoring and levelling,
adaptive difficulty, learning curves, the MoE gate and experts, topic
mapping, the educational filter, evaluation metrics and password hashing.
"""

import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ai import transcript_extractor as te
from app.ai import quiz_generator as qg
from app.ai import learning_curve as lcm
from app.ai import moe_engine as moe
from app.ai.evaluator import RecommendationEvaluator
from app.utils.auth_helpers import hash_password, verify_password


TRANSCRIPT = (
    "Today we will learn about photosynthesis. Photosynthesis is the process by which green plants "
    "use sunlight, water and carbon dioxide to make glucose and release oxygen. The process takes "
    "place inside the chloroplasts, which contain a green pigment called chlorophyll. Chlorophyll "
    "absorbs light energy mainly from the blue and red parts of the spectrum. The light reactions "
    "happen in the thylakoid membranes and produce ATP and NADPH. The Calvin cycle happens in the "
    "stroma and uses ATP and NADPH to fix carbon dioxide into sugar."
)


def _question(q, correct='B', evidence=None, options=None):
    return {
        'question': q,
        'options': options or {'A': 'Mitochondria', 'B': 'Chloroplasts', 'C': 'Nucleus', 'D': 'Ribosomes'},
        'correct': correct,
        'explanation': 'Stated in the video.',
        'evidence': evidence if evidence is not None else
        'The process takes place inside the chloroplasts, which contain a green pigment called chlorophyll',
    }


# ════════════════════════════════════════════════════════════
# 1. Transcript validation and cleaning
# ════════════════════════════════════════════════════════════
class TestTranscriptValidation(unittest.TestCase):

    def test_UT01_valid_transcript_accepted(self):
        """UT-01 A real spoken transcript is accepted"""
        self.assertTrue(te.is_valid_transcript(TRANSCRIPT))

    def test_UT02_short_text_rejected(self):
        """UT-02 Text under 80 characters / 20 words is rejected"""
        self.assertFalse(te.is_valid_transcript("Photosynthesis explained in five minutes"))

    def test_UT03_title_fallback_rejected(self):
        """UT-03 A title/description summary is never accepted as a transcript"""
        fake = "Video Title: Photosynthesis. Summary & Overview: " + "words " * 40
        self.assertFalse(te.is_valid_transcript(fake))

    def test_UT04_unavailable_message_rejected(self):
        """UT-04 A 'transcript not available' message is rejected"""
        self.assertFalse(te.is_valid_transcript("Sorry, transcript not available for this video. " * 5))

    def test_UT05_cleaning_removes_noise(self):
        """UT-05 Cleaning removes [Music], timestamps, URLs, HTML and speaker marks"""
        raw = "[Music] >> Hello 00:01:23 class, visit https://x.com <b>today</b> (laughter) we learn"
        out = te.clean_transcript(raw)
        for noise in ('[Music]', '00:01:23', 'https://', '<b>', '(laughter)', '>>'):
            self.assertNotIn(noise, out)
        self.assertIn('Hello', out)


# ════════════════════════════════════════════════════════════
# 2. Quiz grounding and validation
# ════════════════════════════════════════════════════════════
class TestQuizGrounding(unittest.TestCase):

    def setUp(self):
        self.g = qg._Grounding(TRANSCRIPT)

    def test_UT06_verbatim_quote_supported(self):
        """UT-06 A verbatim transcript passage is accepted as evidence"""
        self.assertTrue(self.g.supports("Chlorophyll absorbs light energy mainly from the blue and red parts"))

    def test_UT07_small_difference_supported(self):
        """UT-07 A passage with small punctuation/word differences passes the 75% trigram rule"""
        self.assertTrue(self.g.supports("the light reactions happen in the thylakoid membranes, and they produce ATP and NADPH"))

    def test_UT08_invented_quote_rejected(self):
        """UT-08 An invented passage that is not in the transcript is rejected"""
        self.assertFalse(self.g.supports("Photosynthesis was discovered by Jan Ingenhousz in the year 1779"))

    def test_UT09_too_short_quote_rejected(self):
        """UT-09 Evidence shorter than five words is rejected"""
        self.assertFalse(self.g.supports("in the stroma"))

    def test_UT10_validation_filters_bad_questions(self):
        """UT-10 Validation keeps grounded questions and drops malformed, duplicate and ungrounded ones"""
        good = _question("Where does photosynthesis take place?")
        dup = _question("Where does photosynthesis take place?")
        bad_options = _question("Which pigment absorbs light?", options={'A': 'x', 'B': 'x', 'C': 'y', 'D': 'z'})
        missing_d = _question("What is produced?", options={'A': 'a', 'B': 'b', 'C': 'c'})
        wrong_key = _question("Which gas is released?", correct='E')
        ungrounded = _question("Who discovered photosynthesis?", evidence="It was discovered by a Dutch scientist in 1779 after many experiments")
        kept, dropped = qg._validate([good, dup, bad_options, missing_d, wrong_key, ungrounded], self.g, set())
        self.assertEqual(len(kept), 1)
        self.assertEqual(dropped, 5)

    def test_UT11_long_transcript_sampled(self):
        """UT-11 Transcripts over 18,000 characters are sampled from start, middle and end"""
        long_text = "a" * 10000 + "M" * 10000 + "z" * 10000
        sample = qg._sample_transcript(long_text)
        self.assertLessEqual(len(sample), 18000 + 20)
        self.assertTrue(sample.startswith('a') and sample.rstrip().endswith('z') and 'M' in sample)

    def test_UT12_quiz_refused_without_real_transcript(self):
        """UT-12 No quiz is generated when the source is the video title (no AI call made)"""
        with patch.object(qg, '_generate') as gen:
            result = qg.generate_quiz('abc123def45', 'Title', 'Biology', 1, TRANSCRIPT, source='title')
            gen.assert_not_called()
        self.assertFalse(result['success'])
        self.assertTrue(result.get('transcript_unavailable'))


# ════════════════════════════════════════════════════════════
# 3. Quiz scoring, levelling and weak-topic detection
# ════════════════════════════════════════════════════════════
class TestQuizScoring(unittest.TestCase):

    def _run(self, n_correct, n_total=10):
        questions = [_question(f"Question {i}?") for i in range(n_total)]   # correct answer = 'B'
        answers = {str(i): ('B' if i < n_correct else 'A') for i in range(n_total)}
        calls = []

        def fake_db(query, params=None, fetch=True):
            calls.append(' '.join(query.split()))
            if query.strip().upper().startswith('SELECT') and 'video_quizzes' in query and 'id=%s' in query:
                return [{'id': 1, 'questions': json.dumps(questions)}]
            if query.strip().upper().startswith('SELECT'):
                return []
            return True

        with patch.object(qg, 'execute_query', side_effect=fake_db), \
             patch.object(lcm, 'execute_query', side_effect=fake_db):
            result = qg.submit_quiz(quiz_id=1, user_id=7, answers=answers, topic='Biology')
        return result, calls

    def test_UT13_low_score(self):
        """UT-13 3/10 (30%) → Beginner next and topic recorded as weak"""
        r, calls = self._run(3)
        self.assertEqual((r['score'], r['percentage'], r['new_level'], r['is_weak']), (3, 30.0, 'Beginner', True))
        self.assertTrue(any('INSERT INTO weak_topics' in c for c in calls))

    def test_UT14_medium_score(self):
        """UT-14 6/10 (60%) → Intermediate next, not weak"""
        r, calls = self._run(6)
        self.assertEqual((r['percentage'], r['new_level'], r['is_weak']), (60.0, 'Intermediate', False))
        self.assertFalse(any('INSERT INTO weak_topics' in c for c in calls))

    def test_UT15_high_score(self):
        """UT-15 8/10 (80%) → Advanced next"""
        r, _ = self._run(8)
        self.assertEqual((r['percentage'], r['new_level']), (80.0, 'Advanced'))

    def test_UT16_boundary_50(self):
        """UT-16 5/10 (exactly 50%) → Intermediate and not weak (boundary)"""
        r, _ = self._run(5)
        self.assertEqual((r['new_level'], r['is_weak']), ('Intermediate', False))


# ════════════════════════════════════════════════════════════
# 4. Adaptive quiz difficulty
# ════════════════════════════════════════════════════════════
class TestAdaptiveDifficulty(unittest.TestCase):

    def _level(self, curve_stage=None, td=None):
        def fake_db(query, params=None, fetch=True):
            if 'learning_curves' in query:
                return [{'curve_stage': curve_stage}] if curve_stage else []
            if 'topic_difficulty' in query:
                return [td] if td else []
            return []
        with patch.object(qg, 'execute_query', side_effect=fake_db):
            return qg._get_difficulty(1, 'Biology')

    def test_UT17_no_history(self):
        """UT-17 No history on a topic → Intermediate"""
        self.assertEqual(self._level(), 'Intermediate')

    def test_UT18_curve_stage_rules(self):
        """UT-18 Struggling → Beginner, Mastery → Advanced, Plateau → Intermediate"""
        self.assertEqual(self._level('Struggling'), 'Beginner')
        self.assertEqual(self._level('Mastery'), 'Advanced')
        self.assertEqual(self._level('Plateau'), 'Intermediate')

    def test_UT19_last_score_rules(self):
        """UT-19 Without a curve: last score 85 → Advanced, 55 → Intermediate, 30 → Beginner"""
        self.assertEqual(self._level(td={'difficulty_level': 'Medium', 'last_score': 85, 'attempts': 1}), 'Advanced')
        self.assertEqual(self._level(td={'difficulty_level': 'Medium', 'last_score': 55, 'attempts': 1}), 'Intermediate')
        self.assertEqual(self._level(td={'difficulty_level': 'Medium', 'last_score': 30, 'attempts': 1}), 'Beginner')


# ════════════════════════════════════════════════════════════
# 5. Learning-curve model
# ════════════════════════════════════════════════════════════
class TestLearningCurve(unittest.TestCase):

    def _curve(self, scores):
        rows = [{'score': s, 'total': 100, 'created_at': i, 'pct': s} for i, s in enumerate(scores)]
        with patch.object(lcm, 'execute_query', return_value=rows):
            return lcm.LearningCurveModel(1).calculate_curve('Biology')

    def test_UT20_rapid_growth(self):
        """UT-20 Scores 40→55→70: rate 15, predicted 82, stage Rapid Growth"""
        c = self._curve([40, 55, 70])
        self.assertEqual((c['learning_rate'], c['predicted_next'], c['curve_stage']), (15.0, 82.0, 'Rapid Growth'))

    def test_UT21_mastery(self):
        """UT-21 Latest score ≥ 80 → Mastery"""
        self.assertEqual(self._curve([60, 85])['curve_stage'], 'Mastery')

    def test_UT22_struggling(self):
        """UT-22 Falling scores below 50 → Struggling"""
        self.assertEqual(self._curve([45, 40, 30])['curve_stage'], 'Struggling')

    def test_UT23_single_attempt(self):
        """UT-23 One attempt → Initial Stage, prediction = current score"""
        c = self._curve([60])
        self.assertEqual((c['curve_stage'], c['predicted_next']), ('Initial Stage', 60))

    def test_UT24_no_attempts(self):
        """UT-24 No attempts → Not Started"""
        self.assertEqual(self._curve([])['curve_stage'], 'Not Started')


# ════════════════════════════════════════════════════════════
# 6. MoE gating function and experts
# ════════════════════════════════════════════════════════════
class TestMoEGate(unittest.TestCase):

    def test_UT25_new_learner_weights(self):
        """UT-25 New learner → fixed weights 0.05 / 0.05 / 0.90"""
        w = moe.AttentionRouter({'is_new_user': True}).compute_weights()
        self.assertEqual((w['weak_topic'], w['performance'], w['history']), (0.05, 0.05, 0.90))

    def test_UT26_weights_sum_to_one(self):
        """UT-26 Returning learner → weights are a valid distribution (sum = 1)"""
        ctx = {'is_new_user': False, 'weak_count': 2, 'quiz_count': 4, 'watch_count': 10, 'avg_score': 55}
        w = moe.AttentionRouter(ctx).compute_weights()
        self.assertAlmostEqual(sum(w.values()), 1.0, places=6)

    def test_UT27_weak_evidence_raises_weak_weight(self):
        """UT-27 More weak topics + lower average → higher Weak-Topic weight"""
        base = {'is_new_user': False, 'quiz_count': 5, 'watch_count': 5}
        low = moe.AttentionRouter({**base, 'weak_count': 0, 'avg_score': 85}).compute_weights()
        high = moe.AttentionRouter({**base, 'weak_count': 4, 'avg_score': 30}).compute_weights()
        self.assertGreater(high['weak_topic'], low['weak_topic'])


class TestMoEExperts(unittest.TestCase):

    def _engine(self, weak=(), perf=(), watched=(), avg=0.0, field='Biology'):
        def fake_db(query, params=None, fetch=True):
            q = ' '.join(query.split())
            if 'FROM users' in q:
                return [{'field_of_interest': field, 'skill_level': 'Beginner', 'onboarding_done': 1,
                         'education_category': 'University', 'learning_level': 'Beginner'}]
            if 'FROM weak_topics' in q:
                return list(weak)
            if 'GROUP BY topic' in q:
                return list(perf)
            if 'watched_videos' in q:
                return list(watched)
            if 'learning_curves' in q:
                return []
            if 'as avg' in q:
                return [{'avg': avg}]
            return []
        with patch.object(moe, 'execute_query', side_effect=fake_db):
            return moe.TransformerMoE(1)

    def test_UT28_cold_start_preference_only(self):
        """UT-28 New learner → only Preference-Expert recommendations, from onboarding topics"""
        e = self._engine()
        recs = e.get_recommendations()
        self.assertTrue(e.context['is_new_user'])
        self.assertTrue(recs and all(r['expert'] == 'history' for r in recs))
        self.assertIn(recs[0]['topic'], moe.FIELD_TOPICS['Biology'])

    def test_UT29_struggling_learner_gets_weak_topic_help(self):
        """UT-29 Learner failing a topic → a Weak-Topic recommendation for that topic is produced"""
        e = self._engine(weak=[{'topic': 'Genetics', 'fail_count': 3}],
                         perf=[{'topic': 'Genetics', 'avg_score': 25, 'attempts': 3}],
                         watched=[{'video_id': 'v1', 'topic': 'Genetics'}], avg=25)
        recs = e.get_recommendations()
        weak_recs = [r for r in recs if r['expert'] == 'weak_topic']
        self.assertTrue(weak_recs and weak_recs[0]['topic'] == 'Genetics')
        self.assertEqual(weak_recs[0]['expert_score'], 1.0)

    def test_UT30_strong_learner_advanced(self):
        """UT-30 Learner scoring ≥75% → Performance-Expert recommends advanced content"""
        e = self._engine(perf=[{'topic': 'Ecology', 'avg_score': 90, 'attempts': 2}],
                         watched=[{'video_id': 'v1', 'topic': 'Ecology'}], avg=90)
        recs = [r for r in e.get_recommendations() if r['expert'] == 'performance']
        self.assertTrue(any('advanced' in r['query'].lower() for r in recs))

    def test_UT31_results_sorted_by_score(self):
        """UT-31 Recommendations are ordered by final score (descending)"""
        e = self._engine(weak=[{'topic': 'Genetics', 'fail_count': 1}],
                         perf=[{'topic': 'Genetics', 'avg_score': 45, 'attempts': 1}],
                         watched=[{'video_id': 'v1', 'topic': 'Genetics'}], avg=45)
        scores = [r['final_score'] for r in e.get_recommendations()]
        self.assertEqual(scores, sorted(scores, reverse=True))


# ════════════════════════════════════════════════════════════
# 7. Onboarding topic mapping
# ════════════════════════════════════════════════════════════
class TestTopicMapping(unittest.TestCase):

    def test_UT32_class_label_mapped(self):
        """UT-32 'Class 9 — Science' maps to Class 9 science subjects"""
        self.assertIn('Physics Class 9', moe.get_topics_for_field('Class 9 — Science'))

    def test_UT33_university_field_mapped(self):
        """UT-33 A university field maps to its topic list"""
        self.assertIn('Contract Law', moe.get_topics_for_field('Civil Law'))

    def test_UT34_unknown_field_never_empty(self):
        """UT-34 Unknown or empty field still returns topics (no empty cold start)"""
        self.assertTrue(moe.get_topics_for_field('Something Unusual'))
        self.assertTrue(moe.get_topics_for_field(''))


# ════════════════════════════════════════════════════════════
# 8. Educational content filter
# ════════════════════════════════════════════════════════════
class TestEducationalFilter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from app.routes import youtube
        cls.yt = youtube

    def test_UT35_entertainment_blocked(self):
        """UT-35 Pure entertainment queries are blocked"""
        for q in ('bollywood full movie', 'new punjabi song 2026', 'pubg gameplay'):
            self.assertTrue(self.yt.is_entertainment_query(q), q)

    def test_UT36_educational_allowed(self):
        """UT-36 Educational queries pass, including ones with entertainment words in an educational context"""
        for q in ('physics class 9 lecture', 'history of film tutorial', 'python programming course'):
            self.assertFalse(self.yt.is_entertainment_query(q), q)


# ════════════════════════════════════════════════════════════
# 9. Recommendation evaluation metrics
# ════════════════════════════════════════════════════════════
class TestEvaluationMetrics(unittest.TestCase):

    def setUp(self):
        self.ev = RecommendationEvaluator(user_id=1)

    def test_UT37_precision_recall(self):
        """UT-37 Precision@3 and Recall@3 on a known example"""
        rec, rel = ['A', 'X', 'B'], ['A', 'B', 'C', 'D']
        self.assertAlmostEqual(self.ev.precision_at_k(rec, rel, 3), 0.6667, places=4)
        self.assertAlmostEqual(self.ev.recall_at_k(rec, rel, 3), 0.5, places=4)

    def test_UT38_ndcg_perfect_and_partial(self):
        """UT-38 NDCG@2 = 1 for an ideal ranking and < 1 when the relevant item is ranked second"""
        self.assertEqual(self.ev.ndcg_at_k(['A', 'B'], ['A', 'B'], 2), 1.0)
        self.assertLess(self.ev.ndcg_at_k(['X', 'A'], ['A'], 2), 1.0)

    def test_UT39_hit_rate_and_diversity(self):
        """UT-39 Hit rate and diversity on known examples"""
        self.assertEqual(self.ev.hit_rate(['X', 'A'], ['A'], 2), 1)
        self.assertEqual(self.ev.hit_rate(['X', 'Y'], ['A'], 2), 0)
        self.assertEqual(self.ev.diversity(['A', 'A', 'B', 'C']), 0.75)


# ════════════════════════════════════════════════════════════
# 10. Security helpers
# ════════════════════════════════════════════════════════════
class TestPasswordHashing(unittest.TestCase):

    def test_UT40_bcrypt_hash_and_verify(self):
        """UT-40 Passwords are stored hashed and verified correctly"""
        h = hash_password('S3cure!pass')
        self.assertNotIn('S3cure!pass', str(h))
        self.assertTrue(verify_password('S3cure!pass', h))
        self.assertFalse(verify_password('wrong-pass', h))


if __name__ == '__main__':
    unittest.main(verbosity=2)
