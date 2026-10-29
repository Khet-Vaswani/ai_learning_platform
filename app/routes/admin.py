# ============================================================
# admin.py — Admin Panel
# Routes: /admin/login, /admin/dashboard, /admin/students,
#         /admin/student/<id>, /admin/categories,
#         /admin/reports, /admin/moe-evaluation, /admin/logout
# Pages are rendered from templates/admin/*.html (Jinja escapes all values).
# ============================================================

from flask import (Blueprint, request, redirect, session, render_template, flash)
from app.utils.db import execute_query
from app.utils.auth_helpers import check_rate_limit
from functools import wraps
import bcrypt, math, random

admin_bp = Blueprint('admin_bp', __name__)


# ── Decorator ─────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('user_role') != 'admin':
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated


def _count(sql, params=None):
    rows = execute_query(sql, params, fetch=True)
    return (rows[0]['c'] or 0) if rows else 0


def _int(value, default=99):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ============================================================
# LOGIN & ADMIN ROOT
# ============================================================
@admin_bp.route('/admin')
@admin_bp.route('/admin/')
def admin_root():
    if session.get('user_role') == 'admin':
        return redirect('/admin/dashboard')
    return redirect('/admin/login')


@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('user_role') == 'admin':
        return redirect('/admin/dashboard')
    error = ''
    if request.method == 'POST' and not check_rate_limit('admin:' + (request.remote_addr or '')):
        error = 'Too many attempts. Wait 5 minutes and try again.'
    elif request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user     = execute_query(
            "SELECT * FROM users WHERE email=%s AND role='admin'",
            (email,), fetch=True
        )
        if user is False:
            error = 'Database connection failed. Make sure MySQL is running.'
        elif not user:
            # Same message as a wrong password, so admin emails can't be discovered
            error = 'Email or password is incorrect.'
        else:
            try:
                ok = bcrypt.checkpw(password.encode(), user[0]['password'].encode())
            except Exception:
                ok = False
            if not ok:
                error = 'Email or password is incorrect.'
            else:
                session['user_id']         = user[0]['id']
                session['user_name']       = user[0]['full_name']
                session['user_email']      = user[0]['email']
                session['user_role']       = 'admin'
                session['onboarding_done'] = 1
                return redirect('/admin/dashboard')

    return render_template('admin/login.html', error=error,
                           email=request.form.get('email', ''))


@admin_bp.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/admin/login')


# ============================================================
# DASHBOARD
# ============================================================
@admin_bp.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    total_users   = _count("SELECT COUNT(*) as c FROM users WHERE role='student'")
    total_videos  = _count("SELECT COUNT(*) as c FROM watched_videos")
    total_quizzes = _count("SELECT COUNT(*) as c FROM video_quizzes WHERE attempted=1")
    total_weak    = _count("SELECT COUNT(*) as c FROM weak_topics")
    onboarded     = _count("SELECT COUNT(*) as c FROM users WHERE role='student' AND onboarding_done=1")
    avg_rows      = execute_query("SELECT ROUND(AVG(score/total*100),1) as a FROM video_quizzes WHERE attempted=1 AND total>0", fetch=True)
    avg_score     = float(avg_rows[0]['a'] or 0) if avg_rows else 0.0

    students = execute_query(
        """SELECT u.id, u.full_name, u.email, u.created_at, u.onboarding_done,
               u.education_category, u.skill_level,
               COUNT(DISTINCT wv.video_id)          as vw,
               COUNT(DISTINCT vq.id)                as qt,
               ROUND(AVG(vq.score/vq.total*100),1)  as avs,
               COUNT(DISTINCT wt.id)                as wk
           FROM users u
           LEFT JOIN watched_videos wv  ON wv.user_id=u.id
           LEFT JOIN video_quizzes vq   ON vq.user_id=u.id AND vq.attempted=1 AND vq.total>0
           LEFT JOIN weak_topics wt     ON wt.user_id=u.id
           WHERE u.role='student'
           GROUP BY u.id ORDER BY u.created_at DESC LIMIT 8""",
        fetch=True
    ) or []

    recent = execute_query(
        """SELECT u.id as uid, u.full_name, vq.topic,
               ROUND(vq.score/vq.total*100,1) as pct, vq.created_at
           FROM video_quizzes vq JOIN users u ON u.id=vq.user_id
           WHERE vq.attempted=1 AND vq.total>0
           ORDER BY vq.created_at DESC LIMIT 8""", fetch=True
    ) or []

    top_weak = execute_query(
        """SELECT topic, SUM(fail_count) as tf, COUNT(DISTINCT user_id) as st
           FROM weak_topics GROUP BY topic ORDER BY tf DESC LIMIT 6""", fetch=True
    ) or []

    cat_dist = execute_query(
        """SELECT education_category, COUNT(*) as cnt FROM users
           WHERE role='student' AND education_category IS NOT NULL
           GROUP BY education_category ORDER BY cnt DESC""", fetch=True
    ) or []

    return render_template(
        'admin/dashboard.html', active='dashboard',
        total_users=total_users, total_videos=total_videos, total_quizzes=total_quizzes,
        avg_score=avg_score, total_weak=total_weak,
        onboard_pct=round(onboarded / total_users * 100) if total_users else 0,
        students=students, recent=recent, top_weak=top_weak, cat_dist=cat_dist,
    )


# ============================================================
# STUDENTS LIST
# ============================================================
@admin_bp.route('/admin/students')
@admin_required
def admin_students():
    search = request.args.get('q', '').strip()
    cat    = request.args.get('cat', '').strip()
    level  = request.args.get('level', '').strip()

    where  = ["u.role='student'"]
    params = []
    if search:
        where.append("(u.full_name LIKE %s OR u.email LIKE %s)")
        params += [f'%{search}%', f'%{search}%']
    if cat:
        where.append("u.education_category=%s")
        params.append(cat)
    if level:
        where.append("u.skill_level=%s")
        params.append(level)

    students = execute_query(
        f"""SELECT u.id, u.full_name, u.email, u.education_category,
               u.field_of_interest, u.skill_level, u.onboarding_done, u.created_at,
               COUNT(DISTINCT wv.video_id)          as vw,
               COUNT(DISTINCT vq.id)                as qt,
               ROUND(AVG(vq.score/vq.total*100),1)  as avs,
               COUNT(DISTINCT wt.id)                as wk
           FROM users u
           LEFT JOIN watched_videos wv  ON wv.user_id=u.id
           LEFT JOIN video_quizzes vq   ON vq.user_id=u.id AND vq.attempted=1 AND vq.total>0
           LEFT JOIN weak_topics wt     ON wt.user_id=u.id
           WHERE {' AND '.join(where)}
           GROUP BY u.id ORDER BY u.created_at DESC""",
        params or None, fetch=True
    ) or []

    cats = execute_query(
        """SELECT DISTINCT education_category FROM users
           WHERE role='student' AND education_category IS NOT NULL
           ORDER BY education_category""",
        fetch=True
    ) or []

    return render_template(
        'admin/students.html', active='students',
        students=students, cats=[c['education_category'] for c in cats],
        search=search, cat=cat, level=level,
    )


# ============================================================
# STUDENT DETAIL
# ============================================================
@admin_bp.route('/admin/student/<int:sid>')
@admin_required
def admin_student_detail(sid):
    student = execute_query(
        "SELECT * FROM users WHERE id=%s AND role='student'",
        (sid,), fetch=True
    )
    if not student:
        flash('That student no longer exists.', 'error')
        return redirect('/admin/students')
    s = student[0]

    quizzes = execute_query(
        """SELECT video_title, topic, score, total,
               ROUND(score/total*100,1) as pct, created_at
           FROM video_quizzes
           WHERE user_id=%s AND attempted=1 AND total>0
           ORDER BY created_at DESC""",
        (sid,), fetch=True
    ) or []

    weak = execute_query(
        "SELECT topic, fail_count, last_detected FROM weak_topics WHERE user_id=%s ORDER BY fail_count DESC",
        (sid,), fetch=True
    ) or []

    watched = execute_query(
        "SELECT video_title, topic, watched_at FROM watched_videos WHERE user_id=%s ORDER BY watched_at DESC LIMIT 10",
        (sid,), fetch=True
    ) or []

    avg = round(sum(float(q['pct'] or 0) for q in quizzes) / len(quizzes), 1) if quizzes else None
    best = max((float(q['pct'] or 0) for q in quizzes), default=None)

    return render_template(
        'admin/student_detail.html', active='students',
        s=s, quizzes=quizzes, weak=weak, watched=watched, avg=avg, best=best,
    )


# ── Delete student ────────────────────────────────────────
@admin_bp.route('/admin/delete/<int:sid>', methods=['POST'])
@admin_required
def admin_delete(sid):
    row = execute_query("SELECT full_name FROM users WHERE id=%s AND role='student'", (sid,), fetch=True)
    if row and execute_query("DELETE FROM users WHERE id=%s AND role='student'", (sid,)) is not False:
        flash(f"Deleted {row[0]['full_name']} and all their activity.", 'success')
    else:
        flash("Couldn't delete that student.", 'error')
    return redirect('/admin/students')


# ============================================================
# CATEGORIES MANAGEMENT
# ============================================================
@admin_bp.route('/admin/categories')
@admin_required
def admin_categories():
    cats   = execute_query("SELECT * FROM educational_categories ORDER BY display_order", fetch=True) or []
    depts  = execute_query(
        """SELECT d.*, COUNT(f.id) as field_count
           FROM university_departments d
           LEFT JOIN university_fields_of_study f ON f.department_id=d.id
           GROUP BY d.id ORDER BY d.display_order""", fetch=True
    ) or []
    fields = execute_query(
        """SELECT f.*, d.name as dept_name FROM university_fields_of_study f
           JOIN university_departments d ON d.id=f.department_id
           ORDER BY d.display_order, f.display_order""", fetch=True
    ) or []
    cnt_map = {
        r['education_category']: r['c'] for r in (execute_query(
            "SELECT education_category, COUNT(*) as c FROM users WHERE role='student' GROUP BY education_category",
            fetch=True) or [])
    }
    return render_template(
        'admin/categories.html', active='categories',
        cats=cats, depts=depts, fields=fields, cnt_map=cnt_map,
        tab=request.args.get('tab', 'categories'),
    )


def _done(ok, success_msg, tab):
    if ok is False:
        flash("That didn't work. It may still be in use, or the name already exists.", 'error')
    else:
        flash(success_msg, 'success')
    return redirect(f'/admin/categories?tab={tab}')


# ── Category CRUD ─────────────────────────────────────────
@admin_bp.route('/admin/categories/add', methods=['POST'])
@admin_required
def cat_add():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Enter a category name.', 'error')
        return redirect('/admin/categories?tab=categories')
    ok = execute_query(
        "INSERT INTO educational_categories (name,description,icon,display_order) VALUES(%s,%s,%s,%s)",
        (name, request.form.get('description', '').strip(),
         request.form.get('icon', '').strip() or 'fas fa-book', _int(request.form.get('display_order'))))
    return _done(ok, f'Added category "{name}".', 'categories')


@admin_bp.route('/admin/categories/delete/<int:cid>', methods=['POST'])
@admin_required
def cat_delete(cid):
    ok = execute_query("DELETE FROM educational_categories WHERE id=%s", (cid,))
    return _done(ok, 'Category deleted.', 'categories')


@admin_bp.route('/admin/dept/add', methods=['POST'])
@admin_required
def dept_add():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Enter a department name.', 'error')
        return redirect('/admin/categories?tab=departments')
    ok = execute_query(
        "INSERT INTO university_departments (name,icon,display_order) VALUES(%s,%s,%s)",
        (name, request.form.get('icon', '').strip() or 'fas fa-university', _int(request.form.get('display_order'))))
    return _done(ok, f'Added department "{name}".', 'departments')


@admin_bp.route('/admin/dept/delete/<int:did>', methods=['POST'])
@admin_required
def dept_delete(did):
    ok = execute_query("DELETE FROM university_departments WHERE id=%s", (did,))
    return _done(ok, 'Department deleted.', 'departments')


@admin_bp.route('/admin/field/add', methods=['POST'])
@admin_required
def field_add():
    did  = request.form.get('department_id')
    name = request.form.get('field_name', '').strip()
    if not (name and did):
        flash('Choose a department and enter a field name.', 'error')
        return redirect('/admin/categories?tab=fields')
    ok = execute_query(
        "INSERT INTO university_fields_of_study (department_id,field_name,display_order) VALUES(%s,%s,%s)",
        (did, name, _int(request.form.get('display_order'))))
    return _done(ok, f'Added field "{name}".', 'fields')


@admin_bp.route('/admin/field/delete/<int:fid>', methods=['POST'])
@admin_required
def field_delete(fid):
    ok = execute_query("DELETE FROM university_fields_of_study WHERE id=%s", (fid,))
    return _done(ok, 'Field deleted.', 'fields')


# ============================================================
# REPORTS & ANALYTICS
# ============================================================
@admin_bp.route('/admin/reports')
@admin_required
def admin_reports():
    top_students = execute_query(
        """SELECT u.id, u.full_name, u.education_category, u.field_of_interest,
               ROUND(AVG(vq.score/vq.total*100),1) as avg_score,
               COUNT(vq.id) as qc
           FROM users u JOIN video_quizzes vq ON vq.user_id=u.id
           WHERE u.role='student' AND vq.attempted=1 AND vq.total>0
           GROUP BY u.id HAVING qc>=1 ORDER BY avg_score DESC LIMIT 10""", fetch=True
    ) or []

    weak_agg = execute_query(
        """SELECT topic, SUM(fail_count) as tf, COUNT(DISTINCT user_id) as st
           FROM weak_topics GROUP BY topic ORDER BY tf DESC LIMIT 8""", fetch=True
    ) or []

    daily = execute_query(
        """SELECT DATE(created_at) as day, COUNT(*) as quizzes,
               ROUND(AVG(score/total*100),1) as avg_score
           FROM video_quizzes WHERE attempted=1 AND total>0
           AND created_at >= DATE_SUB(NOW(), INTERVAL 14 DAY)
           GROUP BY DATE(created_at) ORDER BY day""", fetch=True
    ) or []

    level_dist = execute_query(
        """SELECT skill_level, COUNT(*) as cnt FROM users
           WHERE role='student' AND skill_level IS NOT NULL GROUP BY skill_level""", fetch=True
    ) or []

    topic_perf = execute_query(
        """SELECT topic, ROUND(AVG(score/total*100),1) as avg_score, COUNT(*) as att
           FROM video_quizzes WHERE attempted=1 AND total>0
           GROUP BY topic ORDER BY avg_score ASC LIMIT 8""", fetch=True
    ) or []

    charts = {
        'daily_labels': [r['day'].strftime('%d %b') if hasattr(r['day'], 'strftime') else str(r['day']) for r in daily],
        'daily_quiz':   [r['quizzes'] for r in daily],
        'daily_score':  [float(r['avg_score'] or 0) for r in daily],
        'level_labels': [r['skill_level'] for r in level_dist],
        'level_data':   [r['cnt'] for r in level_dist],
        'topic_labels': [(r['topic'] or 'Quiz')[:22] for r in topic_perf],
        'topic_scores': [float(r['avg_score'] or 0) for r in topic_perf],
    }
    return render_template(
        'admin/reports.html', active='reports',
        top_students=top_students, weak_agg=weak_agg, charts=charts,
    )


# ============================================================
# RECOMMENDER (MoE) EVALUATION
# ============================================================
@admin_bp.route('/admin/moe-evaluation')
@admin_required
def moe_evaluation():
    from app.ai.moe_engine import TransformerMoE

    students = execute_query("SELECT id, full_name FROM users WHERE role='student'", fetch=True) or []
    user_metrics = []
    k = 10

    for s in students:
        uid  = s['id']
        perf = execute_query(
            "SELECT topic, ROUND(AVG(score/total*100),1) as avg_score FROM video_quizzes WHERE user_id=%s AND attempted=1 AND total>0 GROUP BY topic",
            (uid,), fetch=True
        ) or []
        if not perf:
            continue

        weak = execute_query("SELECT topic FROM weak_topics WHERE user_id=%s AND fail_count>0", (uid,), fetch=True) or []
        weak_set = {w['topic'].lower() for w in weak}
        watched  = execute_query("SELECT DISTINCT video_id FROM watched_videos WHERE user_id=%s", (uid,), fetch=True) or []
        shist    = execute_query(
            "SELECT ROUND(score/total*100,1) as pct FROM video_quizzes WHERE user_id=%s AND attempted=1 AND total>0 ORDER BY created_at ASC",
            (uid,), fetch=True
        ) or []

        try:
            moe        = TransformerMoE(uid)
            rec_topics = [r['topic'].lower() for r in moe.get_recommendations()]
            weights    = moe.weights
        except Exception:
            rec_topics = []
            weights    = {'weak_topic': 0.33, 'performance': 0.33, 'history': 0.34}

        relevant = list(weak_set)
        for p in perf:
            t = p['topic'].lower()
            if float(p['avg_score'] or 0) < 60 and t not in relevant:
                relevant.append(t)
        if not relevant:
            relevant = [p['topic'].lower() for p in perf[:3]]

        rec_k   = rec_topics[:k]
        rel_set = set(relevant)

        hits = sum(1 for t in rec_k if t in rel_set)
        prec = round(hits / k, 4)

        # Unique relevant topics retrieved, bounded to [0, 1]
        unique_hits = len(set(rec_k) & rel_set)
        recall = round(unique_hits / len(rel_set), 4) if rel_set else 0.0

        # NDCG with first-time topic gain, bounded to [0, 1]
        seen_topics, dcg = set(), 0.0
        for i, t in enumerate(rec_k):
            if t in rel_set and t not in seen_topics:
                seen_topics.add(t)
                dcg += 1.0 / math.log2(i + 2)
        ideal_count = min(len(rel_set), k)
        idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_count)) if ideal_count else 0.0
        ndcg = round(min(1.0, dcg / idcg), 4) if idcg > 0 else 0.0

        lir = 0.0
        if len(shist) >= 2:
            first, latest = float(shist[0]['pct'] or 0), float(shist[-1]['pct'] or 0)
            lir = round(((latest - first) / first) * 100, 1) if first > 0 else 0.0

        user_metrics.append({
            'id': uid, 'name': s['full_name'], 'precision': prec, 'recall': recall,
            'ndcg': ndcg, 'hit_rate': 1 if unique_hits > 0 else 0, 'lir': lir, 'weights': weights,
            'rel_set': rel_set, 'quizzes': len(perf), 'watched': len(watched),
        })

    def avg(lst):
        return round(sum(lst) / len(lst), 4) if lst else 0

    summary = {
        'precision': avg([m['precision'] for m in user_metrics]),
        'recall':    avg([m['recall'] for m in user_metrics]),
        'ndcg':      avg([m['ndcg'] for m in user_metrics]),
        'hit_rate':  avg([m['hit_rate'] for m in user_metrics]),
        'lir':       avg([m['lir'] for m in user_metrics]),
    }

    # Random baseline: sample k topics from the catalog and score them against each student's relevant set.
    # Only reported when there is real data; no invented fallback value.
    catalog = list({t['topic'].lower() for t in (execute_query(
        "SELECT DISTINCT topic FROM video_quizzes WHERE topic IS NOT NULL", fetch=True) or []) if t.get('topic')})
    random_prec = []
    if catalog:
        for m in user_metrics:
            if m['rel_set']:
                sample = random.sample(catalog, min(k, len(catalog)))
                random_prec.append(len(set(sample) & m['rel_set']) / k)
    baseline = avg(random_prec) if random_prec else None
    gain = (round((summary['precision'] - baseline) / baseline * 100, 1)
            if baseline else None)

    weights = {
        'weak_topic':  avg([m['weights'].get('weak_topic', 0.33) for m in user_metrics]),
        'performance': avg([m['weights'].get('performance', 0.33) for m in user_metrics]),
        'history':     avg([m['weights'].get('history', 0.34) for m in user_metrics]),
    }

    topic_perf = execute_query(
        "SELECT topic, ROUND(AVG(score/total*100),1) as avg_score FROM video_quizzes WHERE attempted=1 AND total>0 GROUP BY topic ORDER BY avg_score ASC LIMIT 10",
        fetch=True
    ) or []
    dist_rows = execute_query(
        """SELECT SUM(CASE WHEN score/total*100<40 THEN 1 ELSE 0 END) as vl,
             SUM(CASE WHEN score/total*100>=40 AND score/total*100<60 THEN 1 ELSE 0 END) as lo,
             SUM(CASE WHEN score/total*100>=60 AND score/total*100<75 THEN 1 ELSE 0 END) as me,
             SUM(CASE WHEN score/total*100>=75 AND score/total*100<90 THEN 1 ELSE 0 END) as hi,
             SUM(CASE WHEN score/total*100>=90 THEN 1 ELSE 0 END) as ex
           FROM video_quizzes WHERE attempted=1 AND total>0""", fetch=True
    )
    dist = dist_rows[0] if dist_rows else {}

    charts = {
        'names':        [m['name'].split()[0] if m['name'] else '?' for m in user_metrics],
        'precision':    [round(m['precision'] * 100, 1) for m in user_metrics],
        'ndcg':         [round(m['ndcg'] * 100, 1) for m in user_metrics],
        'topic_labels': [(t['topic'] or 'Quiz')[:22] for t in topic_perf],
        'topic_scores': [float(t['avg_score'] or 0) for t in topic_perf],
        'dist':         [int(dist.get(key) or 0) for key in ('vl', 'lo', 'me', 'hi', 'ex')],
    }
    return render_template(
        'admin/moe.html', active='moe', k=k,
        user_metrics=user_metrics, summary=summary, baseline=baseline, gain=gain,
        weights=weights, charts=charts,
    )
