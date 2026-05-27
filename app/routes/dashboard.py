# ============================================================
# dashboard.py — Dashboard Routes
# ============================================================

from flask import (Blueprint, jsonify, render_template,
                   request, session)
from app.utils.db import execute_query
from app.utils.auth_helpers import login_required
import json
from datetime import date, timedelta

dashboard = Blueprint('dashboard', __name__)


@dashboard.route('/dashboard')
@login_required
def index():
    user_id      = session['user_id']
    search_query = request.args.get('search', '').strip()

    # ── Watched count ──────────────────────────────────────
    watched = execute_query(
        "SELECT COUNT(*) as cnt FROM watched_videos WHERE user_id=%s",
        (user_id,), fetch=True
    )
    watched_count = watched[0]['cnt'] if watched else 0

    # ── Avg quiz score ─────────────────────────────────────
    avg = execute_query(
        """SELECT AVG(score/total*100) as avg_score
           FROM video_quizzes
           WHERE user_id=%s AND attempted=1 AND total>0""",
        (user_id,), fetch=True
    )
    avg_score = round(float(avg[0]['avg_score'] or 0), 1) if avg else 0

    # ── Quiz attempts check ────────────────────────────────
    qa = execute_query(
        """SELECT COUNT(*) as cnt FROM video_quizzes
           WHERE user_id=%s AND attempted=1""",
        (user_id,), fetch=True
    )
    has_quiz_attempts = (qa[0]['cnt'] if qa else 0) > 0

    # ── Weak topics (ONLY after quiz attempts) ─────────────
    weak = []
    if has_quiz_attempts:
        weak = execute_query(
            """SELECT topic, fail_count FROM weak_topics
               WHERE user_id=%s AND fail_count > 0
               ORDER BY fail_count DESC""",
            (user_id,), fetch=True
        ) or []

    # ── Cognitive ──────────────────────────────────────────
    cognitive = execute_query(
        "SELECT * FROM cognitive_results WHERE user_id=%s",
        (user_id,), fetch=True
    )
    cognitive_data = cognitive[0] if cognitive else None

    # ── Recent watched ─────────────────────────────────────
    recent_watched = execute_query(
        """SELECT video_id, video_title, topic
           FROM watched_videos WHERE user_id=%s
           ORDER BY watched_at DESC LIMIT 3""",
        (user_id,), fetch=True
    )

    # ── User preferences ───────────────────────────────────
    user_prefs = execute_query(
        """SELECT field_of_interest, skill_level, onboarding_done
           FROM users WHERE id=%s""",
        (user_id,), fetch=True
    )
    field_of_interest = None
    skill_level       = 'Beginner'
    onboarding_done   = 0

    if user_prefs:
        field_of_interest = user_prefs[0].get('field_of_interest')
        skill_level       = user_prefs[0].get('skill_level') or 'Beginner'
        onboarding_done   = user_prefs[0].get('onboarding_done', 0)

    # ── Is new user? ───────────────────────────────────────
    is_new_user = (watched_count == 0 and not has_quiz_attempts)

    # ── Show logic ─────────────────────────────────────────
    # New user + has preferences → show preference-based videos
    show_preference_videos = (
        is_new_user and
        field_of_interest is not None and
        onboarding_done == 1
    )

    # After quizzes → show MoE recommendations
    show_moe_recommendations = has_quiz_attempts or watched_count > 0

    # Weak topics ONLY after quiz attempts
    show_weak_topics = has_quiz_attempts and len(weak) > 0

    return render_template(
        'dashboard.html',
        user_name               = session.get('user_name'),
        watched_count           = watched_count,
        avg_score               = avg_score,
        weak_count              = len(weak) if weak else 0,
        weak_topics             = weak[:5] if weak else [],
        cognitive               = cognitive_data,
        recent_watched          = recent_watched,
        search_query            = search_query,
        field_of_interest       = field_of_interest,
        skill_level             = skill_level,
        is_new_user             = is_new_user,
        show_preference_videos  = show_preference_videos,
        show_moe_recommendations= show_moe_recommendations,
        show_weak_topics        = show_weak_topics,
        has_quiz_attempts       = has_quiz_attempts,
    )


# ── My Learning ────────────────────────────────────────────
@dashboard.route('/my-learning')
@login_required
def my_learning():
    user_id = session['user_id']
    videos  = execute_query(
        """SELECT video_id, video_title, topic, watched_at
           FROM watched_videos WHERE user_id=%s
           ORDER BY watched_at DESC""",
        (user_id,), fetch=True
    )
    return render_template('my_learning.html',
                           videos=videos or [],
                           user_name=session.get('user_name'))


# ── Weak Topics ────────────────────────────────────────────
@dashboard.route('/weak-topics')
@login_required
def weak_topics():
    user_id = session['user_id']
    weak    = execute_query(
        """SELECT topic, fail_count, last_detected
           FROM weak_topics WHERE user_id=%s
           ORDER BY fail_count DESC""",
        (user_id,), fetch=True
    )
    return render_template('weak_topics.html',
                           weak_topics=weak or [],
                           user_name=session.get('user_name'))


# ── Quiz History ───────────────────────────────────────────
@dashboard.route('/quiz-history')
@login_required
def quiz_history():
    user_id = session['user_id']
    quizzes = execute_query(
        """SELECT video_title, topic, score, total,
                  attempted, created_at
           FROM video_quizzes WHERE user_id=%s
           ORDER BY created_at DESC""",
        (user_id,), fetch=True
    )
    return render_template('quiz_history.html',
                           quizzes=quizzes or [],
                           user_name=session.get('user_name'))


# ── Chatbot ────────────────────────────────────────────────
@dashboard.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot.html',
                           user_name=session.get('user_name'))


# ── Progress ───────────────────────────────────────────────
@dashboard.route('/progress')
@login_required
def progress():
    user_id = session['user_id']

    quizzes = execute_query(
        """SELECT video_title, topic, score, total,
                  attempted, created_at,
                  ROUND(score/total*100, 1) as percentage
           FROM video_quizzes
           WHERE user_id=%s AND attempted=1 AND total>0
           ORDER BY created_at ASC""",
        (user_id,), fetch=True
    )
    weak = execute_query(
        """SELECT topic, fail_count FROM weak_topics
           WHERE user_id=%s ORDER BY fail_count DESC""",
        (user_id,), fetch=True
    )
    watched = execute_query(
        "SELECT COUNT(*) as cnt FROM watched_videos WHERE user_id=%s",
        (user_id,), fetch=True
    )
    topics_perf = execute_query(
        """SELECT topic, COUNT(*) as attempts,
                  ROUND(AVG(score/total*100),1) as avg_score,
                  MAX(ROUND(score/total*100,1)) as best_score
           FROM video_quizzes
           WHERE user_id=%s AND attempted=1 AND total>0
           GROUP BY topic ORDER BY avg_score DESC""",
        (user_id,), fetch=True
    )
    cognitive = execute_query(
        "SELECT * FROM cognitive_results WHERE user_id=%s",
        (user_id,), fetch=True
    )

    total_quizzes = len(quizzes) if quizzes else 0
    avg_score = round(
        sum(float(q['percentage']) for q in quizzes) / total_quizzes, 1
    ) if total_quizzes > 0 else 0
    best_score    = max((float(q['percentage']) for q in quizzes), default=0)
    watched_count = watched[0]['cnt'] if watched else 0

    chart_labels, chart_scores = [], []
    for q in (quizzes or [])[-10:]:
        chart_labels.append((q['topic'] or 'Quiz')[:15])
        chart_scores.append(float(q['percentage']))

    return render_template('progress.html',
        quizzes       = quizzes or [],
        weak_topics   = weak or [],
        topics_perf   = topics_perf or [],
        cognitive     = cognitive[0] if cognitive else None,
        total_quizzes = total_quizzes,
        avg_score     = avg_score,
        best_score    = best_score,
        watched_count = watched_count,
        chart_labels  = chart_labels,
        chart_scores  = chart_scores,
        user_name     = session.get('user_name'))


# ── Learning Curve ─────────────────────────────────────────
@dashboard.route('/learning-curve/all')
@login_required
def learning_curves():
    from app.ai.learning_curve import LearningCurveModel
    user_id = session['user_id']
    model   = LearningCurveModel(user_id)
    curves  = model.get_all_curves()
    return jsonify({'success': True, 'curves': curves})


# ── Study Streak ───────────────────────────────────────────
@dashboard.route('/study/streak')
@login_required
def study_streak():
    user_id  = session['user_id']
    sessions = execute_query(
        """SELECT DISTINCT DATE(created_at) as day
           FROM study_sessions WHERE user_id=%s
           ORDER BY day DESC""",
        (user_id,), fetch=True
    ) or []
    days   = [str(s['day']) for s in sessions]
    streak = 0
    check  = date.today()
    while str(check) in days:
        streak += 1
        check   = check - timedelta(days=1)
    return jsonify({'success': True, 'days': days,
                    'current_streak': streak, 'total_days': len(days)})


# ── Study Plans ────────────────────────────────────────────
@dashboard.route('/study/plans')
@login_required
def get_plans():
    user_id = session['user_id']
    today   = str(date.today())
    plans   = execute_query(
        """SELECT * FROM study_schedule
           WHERE user_id=%s AND study_date >= %s
           ORDER BY study_date ASC, priority DESC LIMIT 10""",
        (user_id, today), fetch=True
    ) or []
    result = [{'id': p['id'], 'topic': p['topic'],
               'study_date': str(p['study_date']),
               'duration': p['duration'],
               'priority': p.get('priority', 'medium'),
               'completed': bool(p['completed'])} for p in plans]
    return jsonify({'success': True, 'plans': result})


@dashboard.route('/study/plan/add', methods=['POST'])
@login_required
def add_plan():
    data    = request.get_json()
    user_id = session['user_id']
    execute_query(
        """INSERT INTO study_schedule
           (user_id, topic, study_date, duration, priority)
           VALUES (%s,%s,%s,%s,%s)""",
        (user_id, data['topic'], data['date'],
         data['duration'], data.get('priority', 'medium'))
    )
    return jsonify({'success': True})


@dashboard.route('/study/plan/toggle', methods=['POST'])
@login_required
def toggle_plan():
    data    = request.get_json()
    user_id = session['user_id']
    execute_query(
        "UPDATE study_schedule SET completed=%s WHERE id=%s AND user_id=%s",
        (data['completed'], data['id'], user_id)
    )
    return jsonify({'success': True})


@dashboard.route('/study/plan/delete', methods=['POST'])
@login_required
def delete_plan():
    data    = request.get_json()
    user_id = session['user_id']
    execute_query(
        "DELETE FROM study_schedule WHERE id=%s AND user_id=%s",
        (data['id'], user_id)
    )
    return jsonify({'success': True})


@dashboard.route('/study/session/save', methods=['POST'])
@login_required
def save_session():
    data    = request.get_json()
    user_id = session['user_id']
    execute_query(
        """INSERT INTO study_sessions
           (user_id, topic, duration_min, session_date)
           VALUES (%s,%s,%s,CURDATE())""",
        (user_id, data['topic'], data['duration'])
    )
    return jsonify({'success': True})


@dashboard.route('/study/sessions')
@login_required
def get_sessions():
    user_id    = session['user_id']
    today_res  = execute_query(
        """SELECT COALESCE(SUM(duration_min),0) as total
           FROM study_sessions
           WHERE user_id=%s AND session_date=CURDATE()""",
        (user_id,), fetch=True
    )
    today_mins = int(today_res[0]['total']) if today_res else 0

    weekly_res = execute_query(
        """SELECT DAYOFWEEK(session_date)-1 as dow,
                  COALESCE(SUM(duration_min),0) as mins
           FROM study_sessions WHERE user_id=%s
           AND session_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
           GROUP BY dow""",
        (user_id,), fetch=True
    ) or []

    weekly = [{'dow': i, 'mins': 0} for i in range(7)]
    for w in weekly_res:
        weekly[int(w['dow'])]['mins'] = int(w['mins'])

    recent = execute_query(
        """SELECT topic, duration_min, session_date
           FROM study_sessions WHERE user_id=%s
           ORDER BY created_at DESC LIMIT 5""",
        (user_id,), fetch=True
    ) or []

    return jsonify({'success': True, 'today_mins': today_mins,
                    'weekly': weekly,
                    'recent': [{'topic': r['topic'],
                                'duration_min': r['duration_min'],
                                'session_date': str(r['session_date'])}
                               for r in recent]})


# ── Evaluation ─────────────────────────────────────────────
@dashboard.route('/evaluation/report')
@login_required
def evaluation_report():
    return render_template('evaluation.html')


@dashboard.route('/evaluation/run')
@login_required
def run_evaluation():
    from app.ai.evaluator import RecommendationEvaluator
    user_id = session['user_id']
    try:
        k         = int(request.args.get('k', 5))
        evaluator = RecommendationEvaluator(user_id)
        results   = evaluator.full_evaluation(k=k)
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        print(f"Evaluation error: {e}")
        return jsonify({'success': False, 'message': str(e)})