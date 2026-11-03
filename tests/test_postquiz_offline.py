"""
Integration test (offline): quiz result → post-quiz video suggestions.

YouTube is switched off (`get_yt` returns None) and the database is not
needed, so the suggestion route falls back to the curated catalogue.
Run:  venv\\Scripts\\python.exe -m unittest tests.test_postquiz_offline -v
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app.routes.recommend as rec
from app.routes import gemini


class TestPostQuizSuggestions(unittest.TestCase):

    def _suggest(self, pct):
        with patch.object(rec, 'get_yt', return_value=None), \
             patch.object(gemini, 'execute_query', return_value=[]):
            return gemini._get_postquiz_recommendations(topic='Python Programming', percentage=pct, user_id=999999)

    def test_IT01_level_matches_score(self):
        """IT-01 Post-quiz suggestions: <60% beginner, 60–79% intermediate, ≥80% advanced"""
        self.assertEqual([self._suggest(p)['difficulty_level'] for p in (35, 70, 90)],
                         ['beginner', 'intermediate', 'advanced'])

    def test_IT02_suggestions_returned_without_duplicates(self):
        """IT-02 At least one suggestion is returned offline and no video is repeated"""
        r = self._suggest(35)
        ids = [v['video_id'] for v in r['recommendations']]
        self.assertGreaterEqual(len(ids), 1)
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
