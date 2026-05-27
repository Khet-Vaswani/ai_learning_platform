# ============================================================
# admin.py — Admin Dashboard + MoE Evaluation (FIXED)
# Fixes:
#   1. min/abs override removed — use _min/_abs instead
#   2. builtins imported safely at top
#   3. All routes working
# ============================================================

from flask import (Blueprint, request, jsonify,
                   redirect, url_for, session, make_response)
from app.utils.db import execute_query
from functools import wraps
import bcrypt, json, math
import builtins as _builtins

# Safe aliases — avoids overriding Python built-ins
_min = _builtins.min
_abs = _builtins.abs

admin_bp = Blueprint('admin_bp', __name__)


# ── Admin Required ────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('user_role') != 'admin':
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated


# ============================================================
# ADMIN LOGIN
# ============================================================
@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('user_role') == 'admin':
        return redirect('/admin/dashboard')

    error = ''

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = execute_query(
            "SELECT * FROM users WHERE email=%s AND role='admin'",
            (email,), fetch=True
        )

        if not user:
            error = 'Admin account not found.'
        else:
            try:
                pw_ok = bcrypt.checkpw(
                    password.encode('utf-8'),
                    user[0]['password'].encode('utf-8')
                )
            except Exception:
                pw_ok = False

            if not pw_ok:
                error = 'Incorrect password.'
            else:
                session['user_id']         = user[0]['id']
                session['user_name']       = user[0]['full_name']
                session['user_role']       = 'admin'
                session['onboarding_done'] = 1
                return redirect('/admin/dashboard')

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Login</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:'Inter',sans-serif;background:#0f172a;min-height:100vh;display:flex;align-items:center;justify-content:center;overflow:hidden;}}
.orb{{position:fixed;border-radius:50%;filter:blur(80px);opacity:0.12;}}
.orb1{{width:400px;height:400px;background:#dc2626;top:-100px;right:-100px;animation:float 8s ease-in-out infinite;}}
.orb2{{width:300px;height:300px;background:#7c3aed;bottom:-80px;left:-80px;animation:float 6s ease-in-out infinite reverse;}}
@keyframes float{{0%,100%{{transform:translate(0,0);}}50%{{transform:translate(15px,-15px);}}}}
.box{{background:rgba(255,255,255,0.04);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.08);border-radius:24px;padding:44px 40px;width:100%;max-width:420px;position:relative;z-index:10;box-shadow:0 25px 50px rgba(0,0,0,0.5);animation:up 0.4s ease;}}
@keyframes up{{from{{opacity:0;transform:translateY(20px);}}to{{opacity:1;transform:translateY(0);}}}}
.logo{{width:56px;height:56px;background:linear-gradient(135deg,#dc2626,#7c3aed);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:1.4rem;color:white;margin-bottom:20px;}}
.title{{color:white;font-size:1.4rem;font-weight:800;margin:0 0 4px;}}
.sub{{color:rgba(255,255,255,0.4);font-size:0.82rem;margin:0 0 28px;}}
.lbl{{color:rgba(255,255,255,0.6);font-size:0.75rem;font-weight:600;margin-bottom:6px;display:block;}}
.inp{{width:100%;background:rgba(255,255,255,0.06);border:1.5px solid rgba(255,255,255,0.1);border-radius:10px;padding:11px 14px;color:white;font-size:0.875rem;outline:none;transition:all 0.2s;box-sizing:border-box;font-family:inherit;}}
.inp:focus{{border-color:#dc2626;background:rgba(220,38,38,0.08);}}
.inp::placeholder{{color:rgba(255,255,255,0.2);}}
.btn{{width:100%;background:linear-gradient(135deg,#dc2626,#7c3aed);border:none;border-radius:10px;padding:13px;color:white;font-size:0.9rem;font-weight:700;cursor:pointer;transition:all 0.2s;margin-top:6px;font-family:inherit;}}
.btn:hover{{transform:translateY(-2px);box-shadow:0 8px 25px rgba(220,38,38,0.4);}}
.err{{background:rgba(220,38,38,0.12);border:1px solid rgba(220,38,38,0.3);color:#fca5a5;border-radius:10px;padding:10px 14px;font-size:0.8rem;margin-bottom:16px;}}
.back{{display:block;text-align:center;margin-top:18px;color:rgba(255,255,255,0.3);font-size:0.78rem;text-decoration:none;}}
.back:hover{{color:rgba(255,255,255,0.6);}}
</style>
</head>
<body>
<div class="orb orb1"></div>
<div class="orb orb2"></div>
<div class="box">
    <div class="logo"><i class="fas fa-shield-alt"></i></div>
    <h2 class="title">Admin Panel</h2>
    <p class="sub">AI Learning Platform</p>
    {"<div class='err'><i class='fas fa-exclamation-circle me-2'></i>" + error + "</div>" if error else ""}
    <form method="POST">
        <div style="margin-bottom:16px;">
            <label class="lbl">Email</label>
            <input type="email" name="email" class="inp" placeholder="admin@ailearn.com" required>
        </div>
        <div style="margin-bottom:20px;">
            <label class="lbl">Password</label>
            <input type="password" name="password" class="inp" placeholder="Password" required>
        </div>
        <button type="submit" class="btn">
            <i class="fas fa-shield-alt me-2"></i>Access Admin Panel
        </button>
    </form>
    <a href="/login" class="back">← Back to Student Login</a>
</div>
</body>
</html>'''
    return make_response(html)


# ============================================================
# ADMIN LOGOUT
# ============================================================
@admin_bp.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/admin/login')


# ============================================================
# ADMIN DASHBOARD
# ============================================================
@admin_bp.route('/admin/dashboard')
@admin_required
def admin_dashboard():

    total_users = execute_query(
        "SELECT COUNT(*) as cnt FROM users WHERE role='student'", fetch=True
    )
    total_users = total_users[0]['cnt'] if total_users else 0

    total_videos = execute_query(
        "SELECT COUNT(*) as cnt FROM watched_videos", fetch=True
    )
    total_videos = total_videos[0]['cnt'] if total_videos else 0

    total_quizzes = execute_query(
        "SELECT COUNT(*) as cnt FROM video_quizzes WHERE attempted=1", fetch=True
    )
    total_quizzes = total_quizzes[0]['cnt'] if total_quizzes else 0

    avg_score = execute_query(
        "SELECT ROUND(AVG(score/total*100),1) as avg FROM video_quizzes WHERE attempted=1 AND total>0",
        fetch=True
    )
    avg_score = float(avg_score[0]['avg'] or 0) if avg_score else 0

    total_weak = execute_query(
        "SELECT COUNT(*) as cnt FROM weak_topics", fetch=True
    )
    total_weak = total_weak[0]['cnt'] if total_weak else 0

    students = execute_query(
        """SELECT u.id, u.full_name, u.email, u.created_at,
               u.onboarding_done,
               COUNT(DISTINCT wv.video_id) as videos_watched,
               COUNT(DISTINCT vq.id)       as quizzes_taken,
               ROUND(AVG(vq.score/vq.total*100),1) as avg_score,
               COUNT(DISTINCT wt.id)       as weak_topics,
               cr.learning_style,
               cr.total_score              as cognitive_score
           FROM users u
           LEFT JOIN watched_videos wv ON wv.user_id=u.id
           LEFT JOIN video_quizzes vq ON vq.user_id=u.id AND vq.attempted=1 AND vq.total>0
           LEFT JOIN weak_topics wt ON wt.user_id=u.id
           LEFT JOIN cognitive_results cr ON cr.user_id=u.id
           WHERE u.role='student'
           GROUP BY u.id,u.full_name,u.email,u.created_at,
                    u.onboarding_done,cr.learning_style,cr.total_score
           ORDER BY u.created_at DESC""",
        fetch=True
    ) or []

    recent = execute_query(
        """SELECT u.full_name, vq.topic,
               ROUND(vq.score/vq.total*100,1) as pct,
               vq.created_at
           FROM video_quizzes vq
           JOIN users u ON u.id=vq.user_id
           WHERE vq.attempted=1 AND vq.total>0
           ORDER BY vq.created_at DESC LIMIT 8""",
        fetch=True
    ) or []

    top_weak = execute_query(
        """SELECT topic, SUM(fail_count) as total_fails,
               COUNT(DISTINCT user_id) as students
           FROM weak_topics
           GROUP BY topic ORDER BY total_fails DESC LIMIT 6""",
        fetch=True
    ) or []

    rows_html = ''
    if students:
        for i, s in enumerate(students, 1):
            sc   = float(s['avg_score'] or 0)
            sclr = '#059669' if sc >= 70 else '#d97706' if sc >= 40 else '#dc2626'
            wk   = s['weak_topics'] or 0
            cog  = s['cognitive_score']
            name = s['full_name']
            av   = name[0].upper() if name else 'S'
            rows_html += f'''<tr>
<td style="color:#94a3b8;font-size:0.72rem;">{i}</td>
<td><div style="display:flex;align-items:center;gap:8px;">
  <div style="width:30px;height:30px;background:linear-gradient(135deg,#2563eb,#7c3aed);border-radius:8px;display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:0.75rem;">{av}</div>
  <div><div style="font-weight:600;color:#1e293b;font-size:0.8rem;">{name}</div><div style="font-size:0.68rem;color:#94a3b8;">{s["email"]}</div></div>
</div></td>
<td><strong>{s["videos_watched"] or 0}</strong></td>
<td><strong>{s["quizzes_taken"] or 0}</strong></td>
<td><div style="display:flex;align-items:center;gap:6px;">
  <div style="height:5px;background:#f1f5f9;border-radius:3px;overflow:hidden;width:50px;">
    <div style="width:{sc}%;height:100%;border-radius:3px;background:{sclr};"></div>
  </div>
  <span style="font-size:0.75rem;font-weight:600;color:{sclr};">{sc}%</span>
</div></td>
<td>{"<span style='background:#fef2f2;color:#dc2626;padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:700;'>" + str(wk) + "</span>" if wk > 0 else "<span style='background:#f0fdf4;color:#059669;padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:700;'>None</span>"}</td>
<td>{"<span style='background:#eff6ff;color:#2563eb;padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:700;'>" + str(cog) + "/10</span>" if cog is not None else "<span style='background:#f8fafc;color:#94a3b8;padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:700;'>Pending</span>"}</td>
<td>{"<span style='background:#f0fdf4;color:#059669;padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:700;'>Active</span>" if s["onboarding_done"] else "<span style='background:#f8fafc;color:#94a3b8;padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:700;'>New</span>"}</td>
<td><div style="display:flex;gap:5px;">
  <a href="/admin/student/{s["id"]}" style="padding:4px 10px;border-radius:7px;background:#eff6ff;color:#2563eb;border:1px solid #bfdbfe;font-size:0.72rem;font-weight:600;text-decoration:none;"><i class="fas fa-eye"></i> View</a>
  <form method="POST" action="/admin/delete/{s["id"]}" onsubmit="return confirm('Delete {name}?')" style="display:inline;">
    <button style="padding:4px 8px;border-radius:7px;background:#fef2f2;color:#dc2626;border:1px solid #fecaca;font-size:0.72rem;font-weight:600;cursor:pointer;" type="submit"><i class="fas fa-trash"></i></button>
  </form>
</div></td>
</tr>'''
    else:
        rows_html = '<tr><td colspan="8" style="text-align:center;padding:30px;color:#94a3b8;">No students yet.</td></tr>'

    act_html = ''
    for a in recent:
        pct   = float(a['pct'] or 0)
        pclr  = '#059669' if pct >= 70 else '#d97706' if pct >= 40 else '#dc2626'
        fname = a['full_name']
        av    = fname[0].upper() if fname else 'S'
        dt    = a['created_at'].strftime('%d %b') if a['created_at'] else ''
        topic = (a['topic'] or 'Quiz')[:20]
        act_html += f'''<div style="display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid #f1f5f9;">
<div style="width:30px;height:30px;border-radius:8px;background:linear-gradient(135deg,#2563eb,#7c3aed);display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:0.75rem;flex-shrink:0;">{av}</div>
<div style="flex:1;min-width:0;">
  <div style="font-size:0.78rem;font-weight:600;color:#1e293b;">{fname}</div>
  <div style="font-size:0.68rem;color:#94a3b8;">{topic} — <span style="color:{pclr};font-weight:600;">{pct}%</span></div>
</div>
<div style="font-size:0.65rem;color:#94a3b8;flex-shrink:0;">{dt}</div>
</div>'''
    if not act_html:
        act_html = '<p style="text-align:center;color:#94a3b8;padding:20px;font-size:0.8rem;">No activity yet</p>'

    wk_html = ''
    for w in top_weak:
        wk_html += f'''<div style="display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f1f5f9;">
<div>
  <div style="font-size:0.8rem;font-weight:600;color:#92400e;">⚠️ {w["topic"]}</div>
  <div style="font-size:0.68rem;color:#94a3b8;">{w["students"]} student(s)</div>
</div>
<span style="background:#dc2626;color:white;padding:2px 7px;border-radius:7px;font-size:0.68rem;font-weight:700;">{w["total_fails"]} fails</span>
</div>'''
    if not wk_html:
        wk_html = '<p style="text-align:center;color:#94a3b8;padding:20px;font-size:0.8rem;">No weak topics</p>'

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:'Inter',sans-serif;background:#f0f2f5;color:#1e293b;}}
.topbar{{background:#0f172a;height:60px;padding:0 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;box-shadow:0 2px 10px rgba(0,0,0,0.3);}}
.brand{{display:flex;align-items:center;gap:10px;color:white;font-weight:800;font-size:1rem;}}
.brand-icon{{width:32px;height:32px;background:linear-gradient(135deg,#dc2626,#7c3aed);border-radius:8px;display:flex;align-items:center;justify-content:center;color:white;font-size:0.85rem;}}
.top-link{{color:rgba(255,255,255,0.6);padding:6px 12px;border-radius:8px;font-size:0.8rem;text-decoration:none;display:flex;align-items:center;gap:5px;transition:all 0.2s;}}
.top-link:hover{{background:rgba(255,255,255,0.1);color:white;}}
.top-link.active{{background:rgba(255,255,255,0.12);color:white;}}
.logout-a{{background:rgba(220,38,38,0.15);border:1px solid rgba(220,38,38,0.25);color:#fca5a5;padding:6px 12px;border-radius:8px;font-size:0.8rem;text-decoration:none;display:flex;align-items:center;gap:5px;}}
.logout-a:hover{{background:rgba(220,38,38,0.3);color:white;}}
.main{{padding:24px;max-width:1400px;margin:0 auto;}}
.sc{{background:white;border-radius:14px;padding:18px 20px;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.05);transition:all 0.25s;position:relative;overflow:hidden;}}
.sc::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:14px 14px 0 0;}}
.s1::before{{background:#2563eb;}} .s2::before{{background:#059669;}} .s3::before{{background:#d97706;}} .s4::before{{background:#7c3aed;}} .s5::before{{background:#dc2626;}}
.sc:hover{{transform:translateY(-3px);box-shadow:0 8px 20px rgba(0,0,0,0.08);}}
.cb{{background:white;border-radius:14px;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.05);overflow:hidden;margin-bottom:20px;}}
.ch{{padding:14px 18px;border-bottom:1px solid #f1f5f9;display:flex;align-items:center;justify-content:space-between;}}
.dt{{width:100%;font-size:0.8rem;border-collapse:collapse;}}
.dt th{{padding:9px 14px;background:#f8fafc;font-size:0.68rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;border-bottom:1px solid #e2e8f0;white-space:nowrap;}}
.dt td{{padding:11px 14px;border-bottom:1px solid #f1f5f9;color:#475569;vertical-align:middle;}}
.dt tr:hover td{{background:#f8fafc;}}
.dt tr:last-child td{{border-bottom:none;}}
.srch{{padding:6px 12px;border-radius:8px;border:1px solid #e2e8f0;font-size:0.8rem;outline:none;width:180px;}}
</style>
</head>
<body>
<nav class="topbar">
  <div class="brand">
    <div class="brand-icon"><i class="fas fa-shield-alt"></i></div>
    Admin Panel
    <span style="background:rgba(220,38,38,0.2);color:#fca5a5;padding:2px 8px;border-radius:6px;font-size:0.65rem;font-weight:700;">ADMIN</span>
  </div>
  <div style="display:flex;align-items:center;gap:6px;">
    <a href="/admin/dashboard" class="top-link active"><i class="fas fa-home"></i> Dashboard</a>
    <a href="/admin/moe-evaluation" class="top-link"><i class="fas fa-chart-bar"></i> MoE Evaluation</a>
    <a href="/admin/logout" class="logout-a"><i class="fas fa-sign-out-alt"></i> Logout</a>
  </div>
</nav>

<div class="main">
  <div style="background:linear-gradient(135deg,#0f172a,#1e1b4b);border-radius:16px;padding:24px 28px;margin-bottom:24px;color:white;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
    <div>
      <h3 style="font-weight:800;font-size:1.3rem;margin:0 0 3px;">Admin Dashboard</h3>
      <p style="color:rgba(255,255,255,0.5);margin:0;font-size:0.82rem;">AI Learning Platform — Complete Overview</p>
    </div>
    <div style="display:flex;align-items:center;gap:10px;">
      <a href="/admin/moe-evaluation" style="background:linear-gradient(135deg,#7c3aed,#2563eb);color:white;padding:9px 18px;border-radius:10px;font-size:0.8rem;font-weight:700;text-decoration:none;display:flex;align-items:center;gap:6px;">
        <i class="fas fa-chart-bar"></i> MoE Evaluation
      </a>
      <div style="color:rgba(255,255,255,0.4);font-size:0.8rem;" id="dt"></div>
    </div>
  </div>

  <div class="row g-3 mb-4">
    <div class="col-md col-6"><div class="sc s1">
      <div style="width:40px;height:40px;border-radius:10px;background:#eff6ff;color:#2563eb;display:flex;align-items:center;justify-content:center;margin-bottom:12px;"><i class="fas fa-users"></i></div>
      <span style="font-size:1.9rem;font-weight:800;color:#0f172a;line-height:1;display:block;">{total_users}</span>
      <span style="font-size:0.73rem;color:#94a3b8;font-weight:500;margin-top:4px;display:block;">Total Students</span>
    </div></div>
    <div class="col-md col-6"><div class="sc s2">
      <div style="width:40px;height:40px;border-radius:10px;background:#f0fdf4;color:#059669;display:flex;align-items:center;justify-content:center;margin-bottom:12px;"><i class="fas fa-play-circle"></i></div>
      <span style="font-size:1.9rem;font-weight:800;color:#0f172a;line-height:1;display:block;">{total_videos}</span>
      <span style="font-size:0.73rem;color:#94a3b8;font-weight:500;margin-top:4px;display:block;">Videos Watched</span>
    </div></div>
    <div class="col-md col-6"><div class="sc s3">
      <div style="width:40px;height:40px;border-radius:10px;background:#fffbeb;color:#d97706;display:flex;align-items:center;justify-content:center;margin-bottom:12px;"><i class="fas fa-clipboard-check"></i></div>
      <span style="font-size:1.9rem;font-weight:800;color:#0f172a;line-height:1;display:block;">{total_quizzes}</span>
      <span style="font-size:0.73rem;color:#94a3b8;font-weight:500;margin-top:4px;display:block;">Quizzes Taken</span>
    </div></div>
    <div class="col-md col-6"><div class="sc s4">
      <div style="width:40px;height:40px;border-radius:10px;background:#faf5ff;color:#7c3aed;display:flex;align-items:center;justify-content:center;margin-bottom:12px;"><i class="fas fa-chart-line"></i></div>
      <span style="font-size:1.9rem;font-weight:800;color:#0f172a;line-height:1;display:block;">{avg_score}%</span>
      <span style="font-size:0.73rem;color:#94a3b8;font-weight:500;margin-top:4px;display:block;">Avg Score</span>
    </div></div>
    <div class="col-md col-6"><div class="sc s5">
      <div style="width:40px;height:40px;border-radius:10px;background:#fef2f2;color:#dc2626;display:flex;align-items:center;justify-content:center;margin-bottom:12px;"><i class="fas fa-exclamation-triangle"></i></div>
      <span style="font-size:1.9rem;font-weight:800;color:#0f172a;line-height:1;display:block;">{total_weak}</span>
      <span style="font-size:0.73rem;color:#94a3b8;font-weight:500;margin-top:4px;display:block;">Weak Records</span>
    </div></div>
  </div>

  <div class="row g-4">
    <div class="col-lg-8">
      <div class="cb">
        <div class="ch">
          <div style="font-size:0.88rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px;">
            <div style="width:26px;height:26px;border-radius:7px;background:#eff6ff;color:#2563eb;display:flex;align-items:center;justify-content:center;font-size:0.75rem;"><i class="fas fa-users"></i></div>
            All Students
            <span style="background:#eff6ff;color:#2563eb;padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:700;">{len(students)}</span>
          </div>
          <input type="text" class="srch" id="ss" placeholder="Search...">
        </div>
        <div style="overflow-x:auto;">
          <table class="dt" id="st">
            <thead><tr><th>#</th><th>Student</th><th>Videos</th><th>Quizzes</th><th>Avg Score</th><th>Weak</th><th>Cognitive</th><th>Actions</th></tr></thead>
            <tbody>{rows_html}</tbody>
          </table>
        </div>
      </div>
    </div>
    <div class="col-lg-4">
      <div class="cb mb-4">
        <div class="ch">
          <div style="font-size:0.88rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px;">
            <div style="width:26px;height:26px;border-radius:7px;background:#f0fdf4;color:#059669;display:flex;align-items:center;justify-content:center;font-size:0.75rem;"><i class="fas fa-bolt"></i></div>
            Recent Activity
          </div>
        </div>
        <div style="padding:12px 16px;">{act_html}</div>
      </div>
      <div class="cb">
        <div class="ch">
          <div style="font-size:0.88rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px;">
            <div style="width:26px;height:26px;border-radius:7px;background:#fffbeb;color:#d97706;display:flex;align-items:center;justify-content:center;font-size:0.75rem;"><i class="fas fa-exclamation-triangle"></i></div>
            Top Weak Topics
          </div>
        </div>
        <div style="padding:12px 16px;">{wk_html}</div>
      </div>
    </div>
  </div>
</div>

<script>
document.getElementById('dt').innerHTML = '<i class="fas fa-calendar me-1"></i>' + new Date().toLocaleDateString('en-US', {{weekday:'long',year:'numeric',month:'long',day:'numeric'}});
document.getElementById('ss').addEventListener('input', function() {{
  var q = this.value.toLowerCase();
  document.querySelectorAll('#st tbody tr').forEach(function(r) {{
    r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}});
</script>
</body>
</html>'''
    return make_response(html)


# ============================================================
# MOE EVALUATION PAGE
# ============================================================
@admin_bp.route('/admin/moe-evaluation')
@admin_required
def moe_evaluation():

    students = execute_query(
        "SELECT id, full_name FROM users WHERE role='student'",
        fetch=True
    ) or []

    user_metrics = []
    all_precision, all_recall, all_ndcg, all_hr, all_lir = [], [], [], [], []

    for s in students:
        uid = s['id']

        perf = execute_query(
            """SELECT topic, ROUND(AVG(score/total*100),1) as avg_score,
                      COUNT(*) as attempts
               FROM video_quizzes
               WHERE user_id=%s AND attempted=1 AND total>0
               GROUP BY topic""",
            (uid,), fetch=True
        ) or []

        weak = execute_query(
            "SELECT topic FROM weak_topics WHERE user_id=%s AND fail_count>0",
            (uid,), fetch=True
        ) or []
        weak_set = {w['topic'].lower() for w in weak}

        watched = execute_query(
            "SELECT DISTINCT video_id FROM watched_videos WHERE user_id=%s",
            (uid,), fetch=True
        ) or []

        score_hist = execute_query(
            """SELECT ROUND(score/total*100,1) as pct, created_at
               FROM video_quizzes
               WHERE user_id=%s AND attempted=1 AND total>0
               ORDER BY created_at ASC""",
            (uid,), fetch=True
        ) or []

        if not perf:
            continue

        try:
            from app.ai.moe_engine import TransformerMoE
            moe        = TransformerMoE(uid)
            recs       = moe.get_recommendations()
            rec_topics = [r['topic'].lower() for r in recs]
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

        k       = 10
        rec_k   = rec_topics[:k]
        rel_set = set(relevant)

        hits    = sum(1 for t in rec_k if t in rel_set)
        prec    = round(hits / k, 4) if k else 0
        rec_val = round(hits / len(rel_set), 4) if rel_set else 0

        dcg  = sum(1/math.log2(i+2) for i, t in enumerate(rec_k) if t in rel_set)
        idcg = sum(1/math.log2(i+2) for i in range(_min(len(rel_set), k)))
        ndcg = round(dcg/idcg, 4) if idcg else 0

        hr  = 1 if any(t in rel_set for t in rec_k) else 0

        lir = 0.0
        if len(score_hist) >= 2:
            first  = float(score_hist[0]['pct']  or 0)
            latest = float(score_hist[-1]['pct'] or 0)
            lir    = round(((latest - first) / first) * 100, 1) if first > 0 else 0.0

        user_metrics.append({
            'name'     : s['full_name'],
            'uid'      : uid,
            'precision': prec,
            'recall'   : rec_val,
            'ndcg'     : ndcg,
            'hit_rate' : hr,
            'lir'      : lir,
            'weights'  : weights,
            'rec_count': len(rec_topics),
            'rel_count': len(relevant),
            'quizzes'  : len(perf),
            'watched'  : len(watched),
        })

        all_precision.append(prec)
        all_recall.append(rec_val)
        all_ndcg.append(ndcg)
        all_hr.append(hr)
        all_lir.append(lir)

    def avg(lst):
        return round(sum(lst)/len(lst), 4) if lst else 0

    sys_precision = avg(all_precision)
    sys_recall    = avg(all_recall)
    sys_ndcg      = avg(all_ndcg)
    sys_hit_rate  = avg(all_hr)
    sys_lir       = avg(all_lir)

    import random
    all_topics = ['python programming','web development','machine learning',
                  'data science','javascript','database sql','algorithms',
                  'flask framework','deep learning','data analysis']
    rand_prec_list = []
    for m in user_metrics:
        if m['rel_count'] == 0:
            continue
        rand_recs = random.sample(all_topics, _min(10, len(all_topics)))
        rand_prec_list.append(len(rand_recs) / 10)
    rand_prec   = avg(rand_prec_list) if rand_prec_list else 0.10
    moe_vs_rand = round(((sys_precision - rand_prec) / max(rand_prec, 0.001)) * 100, 1)

    topic_perf = execute_query(
        """SELECT topic,
                  ROUND(AVG(score/total*100),1) as avg_score,
                  COUNT(*) as attempts,
                  COUNT(DISTINCT user_id) as students
           FROM video_quizzes
           WHERE attempted=1 AND total>0
           GROUP BY topic ORDER BY avg_score ASC LIMIT 10""",
        fetch=True
    ) or []

    score_dist = execute_query(
        """SELECT
             SUM(CASE WHEN score/total*100 < 40 THEN 1 ELSE 0 END) as very_low,
             SUM(CASE WHEN score/total*100 >= 40 AND score/total*100 < 60 THEN 1 ELSE 0 END) as low,
             SUM(CASE WHEN score/total*100 >= 60 AND score/total*100 < 75 THEN 1 ELSE 0 END) as medium,
             SUM(CASE WHEN score/total*100 >= 75 AND score/total*100 < 90 THEN 1 ELSE 0 END) as high,
             SUM(CASE WHEN score/total*100 >= 90 THEN 1 ELSE 0 END) as excellent
           FROM video_quizzes WHERE attempted=1 AND total>0""",
        fetch=True
    )
    dist = score_dist[0] if score_dist else {}

    if user_metrics:
        avg_w_weak = avg([m['weights']['weak_topic']  for m in user_metrics])
        avg_w_perf = avg([m['weights']['performance'] for m in user_metrics])
        avg_w_hist = avg([m['weights']['history']     for m in user_metrics])
    else:
        avg_w_weak = avg_w_perf = avg_w_hist = 0.33

    user_rows = ''
    for m in user_metrics:
        p   = m['precision']
        n   = m['ndcg']
        lir = m['lir']
        pc  = '#059669' if p >= 0.6 else '#d97706' if p >= 0.4 else '#dc2626'
        nc  = '#059669' if n >= 0.6 else '#d97706' if n >= 0.4 else '#dc2626'
        lc  = '#059669' if lir > 10 else '#d97706' if lir >= 0 else '#dc2626'
        av  = m['name'][0].upper()
        user_rows += f'''<tr>
<td><div style="display:flex;align-items:center;gap:8px;">
  <div style="width:28px;height:28px;background:linear-gradient(135deg,#2563eb,#7c3aed);border-radius:7px;display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:0.72rem;">{av}</div>
  <span style="font-size:0.8rem;font-weight:600;color:#1e293b;">{m["name"]}</span>
</div></td>
<td><span style="font-weight:700;color:{pc};">{round(p*100)}%</span></td>
<td><span style="font-weight:700;color:#2563eb;">{round(m["recall"]*100)}%</span></td>
<td><span style="font-weight:700;color:{nc};">{round(n*100)}%</span></td>
<td>{"<span style='color:#059669;font-weight:700;'>Hit</span>" if m["hit_rate"] else "<span style='color:#dc2626;'>Miss</span>"}</td>
<td><span style="font-weight:700;color:{lc};">{("+"+str(lir)) if lir>0 else str(lir)}%</span></td>
<td style="color:#94a3b8;">{m["quizzes"]}</td>
<td style="color:#94a3b8;">{m["watched"]}</td>
</tr>'''
    if not user_rows:
        user_rows = '<tr><td colspan="8" style="text-align:center;padding:30px;color:#94a3b8;">No quiz data yet. Users need to attempt quizzes first.</td></tr>'

    chart_users     = json.dumps([m['name'].split()[0] for m in user_metrics])
    chart_prec      = json.dumps([round(m['precision']*100, 1) for m in user_metrics])
    chart_ndcg      = json.dumps([round(m['ndcg']*100, 1)      for m in user_metrics])
    chart_lir       = json.dumps([m['lir']                      for m in user_metrics])
    chart_tp_labels = json.dumps([t['topic'][:15]               for t in topic_perf])
    chart_tp_scores = json.dumps([float(t['avg_score'] or 0)    for t in topic_perf])
    chart_dist      = json.dumps([
        int(dist.get('very_low')  or 0),
        int(dist.get('low')       or 0),
        int(dist.get('medium')    or 0),
        int(dist.get('high')      or 0),
        int(dist.get('excellent') or 0),
    ])

    def badge(val, t1, t2):
        if val >= t1:
            return "<span style='background:#f0fdf4;color:#059669;padding:2px 9px;border-radius:20px;font-size:0.68rem;font-weight:700;'>Excellent</span>"
        if val >= t2:
            return "<span style='background:#fffbeb;color:#d97706;padding:2px 9px;border-radius:20px;font-size:0.68rem;font-weight:700;'>Good</span>"
        return "<span style='background:#fef2f2;color:#dc2626;padding:2px 9px;border-radius:20px;font-size:0.68rem;font-weight:700;'>Low</span>"

    # Safe calculations for radar chart — uses _min and _abs
    sys_lir_radar  = round(_min(_abs(sys_lir)  / 50  * 100, 100), 1)
    sys_mvr_radar  = round(_min(_abs(moe_vs_rand) / 100 * 100, 100), 1)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>MoE Evaluation — Admin</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:'Inter',sans-serif;background:#f0f2f5;color:#1e293b;}}
.topbar{{background:#0f172a;height:60px;padding:0 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;box-shadow:0 2px 10px rgba(0,0,0,0.3);}}
.brand{{display:flex;align-items:center;gap:10px;color:white;font-weight:800;font-size:1rem;}}
.brand-icon{{width:32px;height:32px;background:linear-gradient(135deg,#dc2626,#7c3aed);border-radius:8px;display:flex;align-items:center;justify-content:center;color:white;font-size:0.85rem;}}
.top-link{{color:rgba(255,255,255,0.6);padding:6px 12px;border-radius:8px;font-size:0.8rem;text-decoration:none;display:flex;align-items:center;gap:5px;transition:all 0.2s;}}
.top-link:hover,.top-link.active{{background:rgba(255,255,255,0.1);color:white;}}
.logout-a{{background:rgba(220,38,38,0.15);border:1px solid rgba(220,38,38,0.25);color:#fca5a5;padding:6px 12px;border-radius:8px;font-size:0.8rem;text-decoration:none;display:flex;align-items:center;gap:5px;}}
.logout-a:hover{{background:rgba(220,38,38,0.3);color:white;}}
.main{{padding:24px;max-width:1400px;margin:0 auto;}}
.card{{background:white;border-radius:14px;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.05);overflow:hidden;margin-bottom:20px;}}
.card-head{{padding:14px 18px;border-bottom:1px solid #f1f5f9;display:flex;align-items:center;justify-content:space-between;}}
.card-body{{padding:18px;}}
.mcard{{background:white;border-radius:14px;padding:18px;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.05);position:relative;overflow:hidden;height:100%;transition:all 0.25s;}}
.mcard:hover{{transform:translateY(-3px);box-shadow:0 8px 20px rgba(0,0,0,0.08);}}
.mcard::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:14px 14px 0 0;}}
.mc1::before{{background:linear-gradient(90deg,#2563eb,#7c3aed);}}
.mc2::before{{background:linear-gradient(90deg,#059669,#0891b2);}}
.mc3::before{{background:linear-gradient(90deg,#7c3aed,#ec4899);}}
.mc4::before{{background:linear-gradient(90deg,#d97706,#dc2626);}}
.mc5::before{{background:linear-gradient(90deg,#059669,#047857);}}
.mc6::before{{background:linear-gradient(90deg,#0891b2,#2563eb);}}
.mc7::before{{background:linear-gradient(90deg,#dc2626,#d97706);}}
.mc8::before{{background:linear-gradient(90deg,#10b981,#059669);}}
.dt{{width:100%;font-size:0.78rem;border-collapse:collapse;}}
.dt th{{padding:9px 14px;background:#f8fafc;font-size:0.65rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;border-bottom:1px solid #e2e8f0;white-space:nowrap;}}
.dt td{{padding:10px 14px;border-bottom:1px solid #f1f5f9;color:#475569;vertical-align:middle;}}
.dt tr:last-child td{{border-bottom:none;}}
.dt tr:hover td{{background:#f8fafc;}}
.chart-wrap{{position:relative;height:260px;}}
.weight-bar{{display:flex;align-items:center;gap:10px;margin-bottom:10px;}}
.weight-label{{font-size:0.78rem;font-weight:600;color:#1e293b;width:140px;flex-shrink:0;}}
.weight-track{{flex:1;height:10px;background:#f1f5f9;border-radius:5px;overflow:hidden;}}
.weight-fill{{height:100%;border-radius:5px;transition:width 1.2s ease;}}
.weight-pct{{font-size:0.75rem;font-weight:700;width:38px;text-align:right;flex-shrink:0;}}
</style>
</head>
<body>
<nav class="topbar">
  <div class="brand">
    <div class="brand-icon"><i class="fas fa-shield-alt"></i></div>
    Admin Panel
    <span style="background:rgba(220,38,38,0.2);color:#fca5a5;padding:2px 8px;border-radius:6px;font-size:0.65rem;font-weight:700;">ADMIN</span>
  </div>
  <div style="display:flex;align-items:center;gap:6px;">
    <a href="/admin/dashboard" class="top-link"><i class="fas fa-home"></i> Dashboard</a>
    <a href="/admin/moe-evaluation" class="top-link active"><i class="fas fa-chart-bar"></i> MoE Evaluation</a>
    <a href="/admin/logout" class="logout-a"><i class="fas fa-sign-out-alt"></i> Logout</a>
  </div>
</nav>

<div class="main">
  <div style="background:linear-gradient(135deg,#0f172a 0%,#1e1b4b 100%);border-radius:16px;padding:26px 28px;color:white;margin-bottom:24px;">
    <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px;">
      <div>
        <div style="font-size:0.72rem;font-weight:700;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:0.12em;margin-bottom:6px;">Admin Only — Quantitative Evaluation</div>
        <h2 style="font-weight:900;font-size:1.5rem;margin:0 0 6px;">MoE Recommendation Engine</h2>
        <p style="color:rgba(255,255,255,0.5);margin:0;font-size:0.82rem;">Mixture of Experts — Performance Metrics and Graphs</p>
      </div>
      <div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:14px 20px;text-align:center;">
        <div style="font-size:2rem;font-weight:900;color:white;line-height:1;">{len(user_metrics)}</div>
        <div style="font-size:0.7rem;color:rgba(255,255,255,0.4);margin-top:3px;">Users Evaluated</div>
      </div>
    </div>
  </div>

  <div class="row g-3 mb-4">
    <div class="col-6 col-md-3"><div class="mcard mc1">
      <div style="font-size:0.68rem;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">Precision@10</div>
      <div style="font-size:2rem;font-weight:900;color:#0f172a;line-height:1;">{round(sys_precision*100)}%</div>
      <div style="font-size:0.7rem;color:#94a3b8;margin-top:4px;">Relevant recommendations</div>
      <div style="margin-top:8px;">{badge(sys_precision, 0.7, 0.5)}</div>
    </div></div>
    <div class="col-6 col-md-3"><div class="mcard mc2">
      <div style="font-size:0.68rem;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">Recall@10</div>
      <div style="font-size:2rem;font-weight:900;color:#0f172a;line-height:1;">{round(sys_recall*100)}%</div>
      <div style="font-size:0.7rem;color:#94a3b8;margin-top:4px;">Coverage of relevant items</div>
      <div style="margin-top:8px;">{badge(sys_recall, 0.6, 0.4)}</div>
    </div></div>
    <div class="col-6 col-md-3"><div class="mcard mc3">
      <div style="font-size:0.68rem;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">NDCG@10</div>
      <div style="font-size:2rem;font-weight:900;color:#0f172a;line-height:1;">{round(sys_ndcg*100)}%</div>
      <div style="font-size:0.7rem;color:#94a3b8;margin-top:4px;">Ranking quality</div>
      <div style="margin-top:8px;">{badge(sys_ndcg, 0.7, 0.5)}</div>
    </div></div>
    <div class="col-6 col-md-3"><div class="mcard mc4">
      <div style="font-size:0.68rem;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">Hit Rate</div>
      <div style="font-size:2rem;font-weight:900;color:#0f172a;line-height:1;">{round(sys_hit_rate*100)}%</div>
      <div style="font-size:0.7rem;color:#94a3b8;margin-top:4px;">At least 1 relevant found</div>
      <div style="margin-top:8px;">{badge(sys_hit_rate, 0.8, 0.6)}</div>
    </div></div>
    <div class="col-6 col-md-3"><div class="mcard mc5">
      <div style="font-size:0.68rem;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">LIR</div>
      <div style="font-size:2rem;font-weight:900;color:#0f172a;line-height:1;">{("+"+str(sys_lir)) if sys_lir>0 else str(sys_lir)}%</div>
      <div style="font-size:0.7rem;color:#94a3b8;margin-top:4px;">Learning improvement rate</div>
      <div style="margin-top:8px;">{"<span style='background:#f0fdf4;color:#059669;padding:2px 9px;border-radius:20px;font-size:0.68rem;font-weight:700;'>Improving</span>" if sys_lir>0 else "<span style='background:#fef2f2;color:#dc2626;padding:2px 9px;border-radius:20px;font-size:0.68rem;font-weight:700;'>Need Data</span>"}</div>
    </div></div>
    <div class="col-6 col-md-3"><div class="mcard mc6">
      <div style="font-size:0.68rem;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">MoE vs Random</div>
      <div style="font-size:2rem;font-weight:900;color:#0f172a;line-height:1;">{("+"+str(moe_vs_rand)) if moe_vs_rand>0 else str(moe_vs_rand)}%</div>
      <div style="font-size:0.7rem;color:#94a3b8;margin-top:4px;">Better than baseline</div>
      <div style="margin-top:8px;">{"<span style='background:#f0fdf4;color:#059669;padding:2px 9px;border-radius:20px;font-size:0.68rem;font-weight:700;'>Better</span>" if moe_vs_rand>0 else "<span style='background:#fef2f2;color:#dc2626;padding:2px 9px;border-radius:20px;font-size:0.68rem;font-weight:700;'>Below</span>"}</div>
    </div></div>
    <div class="col-6 col-md-3"><div class="mcard mc7">
      <div style="font-size:0.68rem;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">Weak Expert W.</div>
      <div style="font-size:2rem;font-weight:900;color:#0f172a;line-height:1;">{round(avg_w_weak*100)}%</div>
      <div style="font-size:0.7rem;color:#94a3b8;margin-top:4px;">Avg attention weight</div>
      <div style="margin-top:8px;"><span style="background:#fef2f2;color:#dc2626;padding:2px 9px;border-radius:20px;font-size:0.68rem;font-weight:700;">Expert 1</span></div>
    </div></div>
    <div class="col-6 col-md-3"><div class="mcard mc8">
      <div style="font-size:0.68rem;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">Perf Expert W.</div>
      <div style="font-size:2rem;font-weight:900;color:#0f172a;line-height:1;">{round(avg_w_perf*100)}%</div>
      <div style="font-size:0.7rem;color:#94a3b8;margin-top:4px;">Avg attention weight</div>
      <div style="margin-top:8px;"><span style="background:#f0fdf4;color:#059669;padding:2px 9px;border-radius:20px;font-size:0.68rem;font-weight:700;">Expert 2</span></div>
    </div></div>
  </div>

  <div class="row g-4 mb-4">
    <div class="col-lg-7">
      <div class="card">
        <div class="card-head">
          <div style="font-size:0.88rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px;">
            <div style="width:26px;height:26px;border-radius:7px;background:#eff6ff;color:#2563eb;display:flex;align-items:center;justify-content:center;font-size:0.75rem;"><i class="fas fa-chart-bar"></i></div>
            Precision and NDCG per User
          </div>
          <span style="font-size:0.72rem;color:#94a3b8;">Higher = Better</span>
        </div>
        <div class="card-body"><div class="chart-wrap"><canvas id="precNdcgChart"></canvas></div></div>
      </div>
    </div>
    <div class="col-lg-5">
      <div class="card">
        <div class="card-head">
          <div style="font-size:0.88rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px;">
            <div style="width:26px;height:26px;border-radius:7px;background:#faf5ff;color:#7c3aed;display:flex;align-items:center;justify-content:center;font-size:0.75rem;"><i class="fas fa-chart-pie"></i></div>
            Quiz Score Distribution
          </div>
        </div>
        <div class="card-body"><div class="chart-wrap"><canvas id="distChart"></canvas></div></div>
      </div>
    </div>
  </div>

  <div class="row g-4 mb-4">
    <div class="col-lg-6">
      <div class="card">
        <div class="card-head">
          <div style="font-size:0.88rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px;">
            <div style="width:26px;height:26px;border-radius:7px;background:#fffbeb;color:#d97706;display:flex;align-items:center;justify-content:center;font-size:0.75rem;"><i class="fas fa-exclamation-triangle"></i></div>
            Topic Avg Scores (Weakest First)
          </div>
          <span style="font-size:0.72rem;color:#94a3b8;">Lower = needs more help</span>
        </div>
        <div class="card-body"><div class="chart-wrap"><canvas id="topicChart"></canvas></div></div>
      </div>
    </div>
    <div class="col-lg-6">
      <div class="card">
        <div class="card-head">
          <div style="font-size:0.88rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px;">
            <div style="width:26px;height:26px;border-radius:7px;background:#f0fdf4;color:#059669;display:flex;align-items:center;justify-content:center;font-size:0.75rem;"><i class="fas fa-chart-line"></i></div>
            Learning Improvement Rate (LIR) per User
          </div>
        </div>
        <div class="card-body"><div class="chart-wrap"><canvas id="lirChart"></canvas></div></div>
      </div>
    </div>
  </div>

  <div class="row g-4 mb-4">
    <div class="col-lg-5">
      <div class="card">
        <div class="card-head">
          <div style="font-size:0.88rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px;">
            <div style="width:26px;height:26px;border-radius:7px;background:#faf5ff;color:#7c3aed;display:flex;align-items:center;justify-content:center;font-size:0.75rem;"><i class="fas fa-circle-nodes"></i></div>
            System Metrics Radar
          </div>
        </div>
        <div class="card-body"><div class="chart-wrap"><canvas id="radarChart"></canvas></div></div>
      </div>
    </div>
    <div class="col-lg-7">
      <div class="card">
        <div class="card-head">
          <div style="font-size:0.88rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px;">
            <div style="width:26px;height:26px;border-radius:7px;background:#eff6ff;color:#2563eb;display:flex;align-items:center;justify-content:center;font-size:0.75rem;"><i class="fas fa-sliders"></i></div>
            MoE Expert Attention Weights (System Average)
          </div>
        </div>
        <div class="card-body">
          <div class="weight-bar">
            <div class="weight-label">Expert 1 — Weak Topic</div>
            <div class="weight-track"><div class="weight-fill" style="width:{round(avg_w_weak*100)}%;background:#dc2626;"></div></div>
            <div class="weight-pct" style="color:#dc2626;">{round(avg_w_weak*100)}%</div>
          </div>
          <div style="font-size:0.72rem;color:#94a3b8;margin:-4px 0 14px 150px;">Low quiz score — Simpler foundational videos</div>
          <div class="weight-bar">
            <div class="weight-label">Expert 2 — Performance</div>
            <div class="weight-track"><div class="weight-fill" style="width:{round(avg_w_perf*100)}%;background:#059669;"></div></div>
            <div class="weight-pct" style="color:#059669;">{round(avg_w_perf*100)}%</div>
          </div>
          <div style="font-size:0.72rem;color:#94a3b8;margin:-4px 0 14px 150px;">High score — Advanced + next topic in path</div>
          <div class="weight-bar">
            <div class="weight-label">Expert 3 — Preference</div>
            <div class="weight-track"><div class="weight-fill" style="width:{round(avg_w_hist*100)}%;background:#7c3aed;"></div></div>
            <div class="weight-pct" style="color:#7c3aed;">{round(avg_w_hist*100)}%</div>
          </div>
          <div style="font-size:0.72rem;color:#94a3b8;margin:-4px 0 14px 150px;">New user — Field + level based recommendations</div>
          <div style="background:#f8fafc;border-radius:10px;padding:14px;margin-top:8px;border:1px solid #f1f5f9;">
            <div style="font-size:0.75rem;font-weight:700;color:#1e293b;margin-bottom:8px;">MoE vs Random Baseline</div>
            <div style="display:flex;gap:16px;flex-wrap:wrap;">
              <div><div style="font-size:1.4rem;font-weight:900;color:#2563eb;">{round(sys_precision*100)}%</div><div style="font-size:0.65rem;color:#94a3b8;">MoE Precision</div></div>
              <div><div style="font-size:1.4rem;font-weight:900;color:#94a3b8;">{round(rand_prec*100)}%</div><div style="font-size:0.65rem;color:#94a3b8;">Random Precision</div></div>
              <div><div style="font-size:1.4rem;font-weight:900;color:{'#059669' if moe_vs_rand>0 else '#dc2626'};">{("+"+str(moe_vs_rand)) if moe_vs_rand>0 else str(moe_vs_rand)}%</div><div style="font-size:0.65rem;color:#94a3b8;">Improvement</div></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-head">
      <div style="font-size:0.88rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px;">
        <div style="width:26px;height:26px;border-radius:7px;background:#eff6ff;color:#2563eb;display:flex;align-items:center;justify-content:center;font-size:0.75rem;"><i class="fas fa-table"></i></div>
        Per-User Evaluation Breakdown
      </div>
      <span style="font-size:0.72rem;color:#94a3b8;">K = 10</span>
    </div>
    <div style="overflow-x:auto;">
      <table class="dt">
        <thead><tr>
          <th>User</th><th>Precision@10</th><th>Recall@10</th>
          <th>NDCG@10</th><th>Hit Rate</th><th>LIR</th>
          <th>Quizzes</th><th>Watched</th>
        </tr></thead>
        <tbody>{user_rows}</tbody>
      </table>
    </div>
  </div>
</div>

<script>
var users   = {chart_users};
var precs   = {chart_prec};
var ndcgs   = {chart_ndcg};
var lirs    = {chart_lir};
var tpLbls  = {chart_tp_labels};
var tpScrs  = {chart_tp_scores};
var distD   = {chart_dist};
var sysP    = {round(sys_precision*100, 1)};
var sysR    = {round(sys_recall*100, 1)};
var sysN    = {round(sys_ndcg*100, 1)};
var sysHR   = {round(sys_hit_rate*100, 1)};
var sysLIR  = Math.max(0, {sys_lir_radar});
var sysMvR  = Math.max(0, {sys_mvr_radar});

new Chart(document.getElementById('precNdcgChart'), {{
  type:'bar',
  data:{{
    labels: users.length ? users : ['No data'],
    datasets:[
      {{ label:'Precision@10 (%)', data: precs, backgroundColor:'rgba(37,99,235,0.75)', borderRadius:5 }},
      {{ label:'NDCG@10 (%)',      data: ndcgs, backgroundColor:'rgba(124,58,237,0.75)', borderRadius:5 }}
    ]
  }},
  options:{{
    responsive:true, maintainAspectRatio:false,
    plugins:{{ legend:{{ labels:{{ font:{{ size:11 }} }} }} }},
    scales:{{
      y:{{ min:0, max:100, ticks:{{ callback:v=>v+'%', font:{{ size:10 }} }}, grid:{{ color:'#f1f5f9' }} }},
      x:{{ ticks:{{ font:{{ size:10 }} }}, grid:{{ display:false }} }}
    }}
  }}
}});

new Chart(document.getElementById('distChart'), {{
  type:'doughnut',
  data:{{
    labels:['<40% Very Low','40-60% Low','60-75% Medium','75-90% High','90%+ Excellent'],
    datasets:[{{ data: distD, backgroundColor:['#ef4444','#f97316','#eab308','#22c55e','#3b82f6'], borderWidth:2, borderColor:'white' }}]
  }},
  options:{{
    responsive:true, maintainAspectRatio:false,
    plugins:{{ legend:{{ position:'right', labels:{{ font:{{ size:10 }}, padding:8 }} }} }}
  }}
}});

new Chart(document.getElementById('topicChart'), {{
  type:'bar',
  data:{{
    labels: tpLbls.length ? tpLbls : ['No data'],
    datasets:[{{ label:'Avg Score (%)', data: tpScrs,
      backgroundColor: tpScrs.map(s => s<40?'rgba(220,38,38,0.75)':s<60?'rgba(217,119,6,0.75)':s<75?'rgba(234,179,8,0.75)':'rgba(34,197,94,0.75)'),
      borderRadius:5 }}]
  }},
  options:{{
    indexAxis:'y',
    responsive:true, maintainAspectRatio:false,
    plugins:{{ legend:{{ display:false }} }},
    scales:{{
      x:{{ min:0, max:100, ticks:{{ callback:v=>v+'%', font:{{ size:10 }} }}, grid:{{ color:'#f1f5f9' }} }},
      y:{{ ticks:{{ font:{{ size:10 }} }}, grid:{{ display:false }} }}
    }}
  }}
}});

new Chart(document.getElementById('lirChart'), {{
  type:'bar',
  data:{{
    labels: users.length ? users : ['No data'],
    datasets:[{{ label:'LIR (%)', data: lirs,
      backgroundColor: lirs.map(l => l>20?'rgba(34,197,94,0.75)':l>0?'rgba(234,179,8,0.75)':'rgba(220,38,38,0.75)'),
      borderRadius:5 }}]
  }},
  options:{{
    responsive:true, maintainAspectRatio:false,
    plugins:{{ legend:{{ display:false }} }},
    scales:{{
      y:{{ ticks:{{ callback:v=>v+'%', font:{{ size:10 }} }}, grid:{{ color:'#f1f5f9' }} }},
      x:{{ ticks:{{ font:{{ size:10 }} }}, grid:{{ display:false }} }}
    }}
  }}
}});

new Chart(document.getElementById('radarChart'), {{
  type:'radar',
  data:{{
    labels:['Precision','Recall','NDCG','Hit Rate','LIR','MoE Gain'],
    datasets:[
      {{ label:'MoE System', data:[sysP,sysR,sysN,sysHR,sysLIR,sysMvR],
         backgroundColor:'rgba(124,58,237,0.15)', borderColor:'#7c3aed',
         pointBackgroundColor:'#7c3aed', pointRadius:4, borderWidth:2 }},
      {{ label:'Random Baseline', data:[{round(rand_prec*100,1)},0,0,0,0,0],
         backgroundColor:'rgba(148,163,184,0.1)', borderColor:'#94a3b8',
         pointBackgroundColor:'#94a3b8', pointRadius:3, borderWidth:1.5 }}
    ]
  }},
  options:{{
    responsive:true, maintainAspectRatio:false,
    plugins:{{ legend:{{ labels:{{ font:{{ size:10 }} }} }} }},
    scales:{{ r:{{ min:0, max:100, ticks:{{ stepSize:20, font:{{ size:9 }} }}, grid:{{ color:'#e2e8f0' }}, pointLabels:{{ font:{{ size:10 }} }} }} }}
  }}
}});
</script>
</body>
</html>'''
    return make_response(html)


# ============================================================
# STUDENT DETAIL
# ============================================================
@admin_bp.route('/admin/student/<int:student_id>')
@admin_required
def student_detail(student_id):
    student = execute_query(
        """SELECT u.*, cr.learning_style,
               cr.total_score as cognitive_score,
               cr.logical_score, cr.numerical_score,
               cr.verbal_score, cr.problem_solving_score
           FROM users u
           LEFT JOIN cognitive_results cr ON cr.user_id=u.id
           WHERE u.id=%s AND u.role='student'""",
        (student_id,), fetch=True
    )
    if not student:
        return redirect('/admin/dashboard')

    s = student[0]

    quizzes = execute_query(
        """SELECT video_title, topic, score, total,
               ROUND(score/total*100,1) as pct, created_at
           FROM video_quizzes
           WHERE user_id=%s AND attempted=1 AND total>0
           ORDER BY created_at DESC""",
        (student_id,), fetch=True
    ) or []

    weak = execute_query(
        "SELECT topic, fail_count, last_detected FROM weak_topics WHERE user_id=%s ORDER BY fail_count DESC",
        (student_id,), fetch=True
    ) or []

    watched = execute_query(
        "SELECT video_title, topic, watched_at FROM watched_videos WHERE user_id=%s ORDER BY watched_at DESC LIMIT 10",
        (student_id,), fetch=True
    ) or []

    total_pct = sum(float(q['pct'] or 0) for q in quizzes)
    avg       = round(total_pct / len(quizzes), 1) if quizzes else 0

    quiz_rows = ''
    for i, q in enumerate(quizzes, 1):
        p    = float(q['pct'] or 0)
        pclr = '#059669' if p >= 70 else '#d97706' if p >= 40 else '#dc2626'
        pbg  = '#f0fdf4' if p >= 70 else '#fffbeb' if p >= 40 else '#fef2f2'
        st   = 'Good' if p >= 70 else 'Avg' if p >= 40 else 'Weak'
        dt   = q['created_at'].strftime('%d %b %Y') if q['created_at'] else 'N/A'
        vt   = (q['video_title'] or 'N/A')[:28]
        quiz_rows += f'''<tr>
<td style="color:#94a3b8;">{i}</td>
<td><strong>{q["topic"] or "N/A"}</strong></td>
<td style="color:#94a3b8;">{vt}...</td>
<td><strong>{q["score"]}/{q["total"]}</strong></td>
<td><span style="background:{pbg};color:{pclr};padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:700;">{p}%</span></td>
<td><span style="background:{pbg};color:{pclr};padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:700;">{st}</span></td>
<td style="color:#94a3b8;font-size:0.72rem;">{dt}</td>
</tr>'''
    if not quiz_rows:
        quiz_rows = '<tr><td colspan="7" style="text-align:center;padding:20px;color:#94a3b8;">No quizzes</td></tr>'

    watched_rows = ''
    for i, v in enumerate(watched, 1):
        dt = v['watched_at'].strftime('%d %b %Y') if v['watched_at'] else 'N/A'
        vt = (v['video_title'] or 'N/A')[:40]
        watched_rows += f'''<tr>
<td style="color:#94a3b8;">{i}</td>
<td>{vt}</td>
<td><span style="background:#f1f5f9;color:#64748b;padding:2px 7px;border-radius:5px;font-size:0.68rem;font-weight:600;">{v["topic"]}</span></td>
<td style="color:#94a3b8;font-size:0.72rem;">{dt}</td>
</tr>'''
    if not watched_rows:
        watched_rows = '<tr><td colspan="4" style="text-align:center;padding:20px;color:#94a3b8;">No videos</td></tr>'

    weak_html = ''
    for w in weak:
        dt = w['last_detected'].strftime('%d %b %Y') if w['last_detected'] else ''
        weak_html += f'''<div style="display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f1f5f9;">
<div>
  <div style="font-size:0.8rem;font-weight:600;color:#92400e;">⚠️ {w["topic"]}</div>
  <div style="font-size:0.68rem;color:#94a3b8;margin-top:2px;">{dt}</div>
</div>
<span style="background:#dc2626;color:white;padding:2px 7px;border-radius:7px;font-size:0.68rem;font-weight:700;">{w["fail_count"]}x</span>
</div>'''
    if not weak_html:
        weak_html = '<div style="text-align:center;padding:20px;color:#94a3b8;font-size:0.8rem;">No weak topics!</div>'

    cog_html = ''
    if s['cognitive_score'] is not None:
        bars = [
            ('Logical',       s['logical_score'],          3, '#2563eb'),
            ('Numerical',     s['numerical_score'],         3, '#059669'),
            ('Verbal',        s['verbal_score'],            2, '#d97706'),
            ('Problem Solve', s['problem_solving_score'],   2, '#7c3aed'),
        ]
        for label, score, max_s, color in bars:
            pct = int((score / max_s) * 100) if max_s and score is not None else 0
            cog_html += f'''<div style="margin-bottom:12px;">
<div style="display:flex;justify-content:space-between;margin-bottom:3px;">
  <small style="font-size:0.75rem;font-weight:600;color:#475569;">{label}</small>
  <small style="font-size:0.72rem;color:#94a3b8;">{score}/{max_s}</small>
</div>
<div style="height:5px;background:#f1f5f9;border-radius:3px;overflow:hidden;">
  <div style="width:{pct}%;height:100%;border-radius:3px;background:{color};"></div>
</div></div>'''

    name   = s['full_name']
    av     = name[0].upper() if name else 'S'
    joined = s['created_at'].strftime('%d %b %Y') if s['created_at'] else 'N/A'
    style_badge = f"<span style='background:rgba(255,255,255,0.12);color:white;padding:4px 12px;border-radius:12px;font-size:0.72rem;font-weight:600;margin-top:8px;display:inline-block;'>{s['learning_style']}</span>" if s['learning_style'] else ''

    cog_section = ''
    if s['cognitive_score'] is not None:
        cog_section = f'''<div style="background:white;border-radius:14px;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.05);overflow:hidden;margin-bottom:16px;">
<div style="padding:13px 18px;border-bottom:1px solid #f1f5f9;display:flex;align-items:center;justify-content:space-between;">
  <div style="font-size:0.87rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px;">
    <div style="width:26px;height:26px;border-radius:7px;background:#eff6ff;color:#2563eb;display:flex;align-items:center;justify-content:center;font-size:0.75rem;"><i class="fas fa-brain"></i></div>
    Cognitive Profile
  </div>
  <span style="background:#eff6ff;color:#2563eb;padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:700;">{s["cognitive_score"]}/10</span>
</div>
<div style="padding:14px 18px;">{cog_html}</div>
</div>'''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} — Admin</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:'Inter',sans-serif;background:#f0f2f5;color:#1e293b;}}
.topbar{{background:#0f172a;height:60px;padding:0 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}}
.brand{{display:flex;align-items:center;gap:10px;color:white;font-weight:800;font-size:1rem;}}
.brand-icon{{width:32px;height:32px;background:linear-gradient(135deg,#dc2626,#7c3aed);border-radius:8px;display:flex;align-items:center;justify-content:center;color:white;font-size:0.85rem;}}
.back-a{{color:rgba(255,255,255,0.6);padding:6px 14px;border-radius:8px;font-size:0.8rem;text-decoration:none;display:flex;align-items:center;gap:6px;}}
.back-a:hover{{background:rgba(255,255,255,0.1);color:white;}}
.main{{padding:24px;max-width:1200px;margin:0 auto;}}
.dt{{width:100%;font-size:0.78rem;border-collapse:collapse;}}
.dt th{{padding:8px 14px;background:#f8fafc;font-size:0.65rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;border-bottom:1px solid #e2e8f0;}}
.dt td{{padding:10px 14px;border-bottom:1px solid #f1f5f9;color:#475569;}}
.dt tr:last-child td{{border-bottom:none;}}
.dt tr:hover td{{background:#f8fafc;}}
</style>
</head>
<body>
<nav class="topbar">
  <div class="brand"><div class="brand-icon"><i class="fas fa-shield-alt"></i></div>Admin Panel</div>
  <a href="/admin/dashboard" class="back-a"><i class="fas fa-arrow-left"></i> Back</a>
</nav>
<div class="main">
  <div style="background:linear-gradient(135deg,#0f172a,#1e1b4b);border-radius:16px;padding:26px 28px;color:white;margin-bottom:20px;display:flex;align-items:center;gap:18px;flex-wrap:wrap;">
    <div style="width:60px;height:60px;background:linear-gradient(135deg,#2563eb,#7c3aed);border-radius:14px;display:flex;align-items:center;justify-content:center;color:white;font-weight:800;font-size:1.4rem;flex-shrink:0;">{av}</div>
    <div style="flex:1;">
      <h3 style="font-weight:800;margin:0 0 3px;font-size:1.3rem;">{name}</h3>
      <p style="color:rgba(255,255,255,0.5);margin:0;font-size:0.82rem;">{s["email"]}</p>
      {style_badge}
    </div>
    <div style="text-align:right;">
      <div style="font-size:0.7rem;color:rgba(255,255,255,0.4);margin-bottom:3px;">Joined</div>
      <div style="font-size:0.85rem;color:white;font-weight:600;">{joined}</div>
    </div>
  </div>
  <div class="row g-3 mb-4">
    <div class="col-6 col-md-3"><div style="background:white;border-radius:12px;padding:14px 16px;border:1px solid #e2e8f0;text-align:center;"><div style="font-size:1.5rem;font-weight:800;color:#2563eb;">{len(watched)}</div><div style="font-size:0.7rem;color:#94a3b8;margin-top:3px;">Videos</div></div></div>
    <div class="col-6 col-md-3"><div style="background:white;border-radius:12px;padding:14px 16px;border:1px solid #e2e8f0;text-align:center;"><div style="font-size:1.5rem;font-weight:800;color:#059669;">{len(quizzes)}</div><div style="font-size:0.7rem;color:#94a3b8;margin-top:3px;">Quizzes</div></div></div>
    <div class="col-6 col-md-3"><div style="background:white;border-radius:12px;padding:14px 16px;border:1px solid #e2e8f0;text-align:center;"><div style="font-size:1.5rem;font-weight:800;color:#d97706;">{avg}%</div><div style="font-size:0.7rem;color:#94a3b8;margin-top:3px;">Avg Score</div></div></div>
    <div class="col-6 col-md-3"><div style="background:white;border-radius:12px;padding:14px 16px;border:1px solid #e2e8f0;text-align:center;"><div style="font-size:1.5rem;font-weight:800;color:#dc2626;">{len(weak)}</div><div style="font-size:0.7rem;color:#94a3b8;margin-top:3px;">Weak Topics</div></div></div>
  </div>
  <div class="row g-4">
    <div class="col-lg-8">
      <div style="background:white;border-radius:14px;border:1px solid #e2e8f0;overflow:hidden;margin-bottom:16px;">
        <div style="padding:13px 18px;border-bottom:1px solid #f1f5f9;">
          <div style="font-size:0.87rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px;">
            <div style="width:26px;height:26px;border-radius:7px;background:#f0fdf4;color:#059669;display:flex;align-items:center;justify-content:center;font-size:0.75rem;"><i class="fas fa-clipboard-check"></i></div>
            Quiz History
            <span style="background:#eff6ff;color:#2563eb;padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:700;">{len(quizzes)}</span>
          </div>
        </div>
        <div style="overflow-x:auto;">
          <table class="dt">
            <thead><tr><th>#</th><th>Topic</th><th>Video</th><th>Score</th><th>%</th><th>Status</th><th>Date</th></tr></thead>
            <tbody>{quiz_rows}</tbody>
          </table>
        </div>
      </div>
      <div style="background:white;border-radius:14px;border:1px solid #e2e8f0;overflow:hidden;">
        <div style="padding:13px 18px;border-bottom:1px solid #f1f5f9;">
          <div style="font-size:0.87rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px;">
            <div style="width:26px;height:26px;border-radius:7px;background:#eff6ff;color:#2563eb;display:flex;align-items:center;justify-content:center;font-size:0.75rem;"><i class="fas fa-play-circle"></i></div>
            Watched Videos
            <span style="background:#eff6ff;color:#2563eb;padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:700;">{len(watched)}</span>
          </div>
        </div>
        <div style="overflow-x:auto;">
          <table class="dt">
            <thead><tr><th>#</th><th>Title</th><th>Topic</th><th>Date</th></tr></thead>
            <tbody>{watched_rows}</tbody>
          </table>
        </div>
      </div>
    </div>
    <div class="col-lg-4">
      {cog_section}
      <div style="background:white;border-radius:14px;border:1px solid #e2e8f0;overflow:hidden;">
        <div style="padding:13px 18px;border-bottom:1px solid #f1f5f9;display:flex;align-items:center;justify-content:space-between;">
          <div style="font-size:0.87rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px;">
            <div style="width:26px;height:26px;border-radius:7px;background:#fffbeb;color:#d97706;display:flex;align-items:center;justify-content:center;font-size:0.75rem;"><i class="fas fa-exclamation-triangle"></i></div>
            Weak Topics
          </div>
          <span style="background:#fef2f2;color:#dc2626;padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:700;">{len(weak)}</span>
        </div>
        <div style="padding:12px 16px;">{weak_html}</div>
      </div>
    </div>
  </div>
</div>
</body>
</html>'''
    return make_response(html)


# ============================================================
# DELETE STUDENT
# ============================================================
@admin_bp.route('/admin/delete/<int:student_id>', methods=['POST'])
@admin_required
def delete_student(student_id):
    execute_query(
        "DELETE FROM users WHERE id=%s AND role='student'",
        (student_id,)
    )
    return redirect('/admin/dashboard')