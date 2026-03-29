# ============================================================
# admin.py — Admin Dashboard (No Template Files)
# ============================================================

from flask import (Blueprint, request, jsonify,
                   redirect, url_for, session, make_response)
from app.utils.db import execute_query
from functools import wraps
import bcrypt

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
        "SELECT COUNT(*) as cnt FROM users WHERE role='student'",
        fetch=True
    )
    total_users = total_users[0]['cnt'] if total_users else 0

    total_videos = execute_query(
        "SELECT COUNT(*) as cnt FROM watched_videos",
        fetch=True
    )
    total_videos = total_videos[0]['cnt'] if total_videos else 0

    total_quizzes = execute_query(
        "SELECT COUNT(*) as cnt FROM video_quizzes WHERE attempted=1",
        fetch=True
    )
    total_quizzes = total_quizzes[0]['cnt'] if total_quizzes else 0

    avg_score = execute_query(
        "SELECT ROUND(AVG(score/total*100),1) as avg FROM video_quizzes WHERE attempted=1 AND total>0",
        fetch=True
    )
    avg_score = float(avg_score[0]['avg'] or 0) if avg_score else 0

    total_weak = execute_query(
        "SELECT COUNT(*) as cnt FROM weak_topics",
        fetch=True
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

    # Build students rows HTML
    rows_html = ''
    if students:
        for i, s in enumerate(students, 1):
            sc   = float(s['avg_score'] or 0)
            sclr = '#059669' if sc >= 70 else '#d97706' if sc >= 40 else '#dc2626'
            wk   = s['weak_topics'] or 0
            cog  = s['cognitive_score']
            name = s['full_name']
            av   = name[0].upper() if name else 'S'
            del_confirm = f"Delete {name}?"

            rows_html += f'''<tr>
<td style="color:#94a3b8;font-size:0.72rem;">{i}</td>
<td>
  <div style="display:flex;align-items:center;gap:8px;">
    <div style="width:30px;height:30px;background:linear-gradient(135deg,#2563eb,#7c3aed);border-radius:8px;display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:0.75rem;">{av}</div>
    <div>
      <div style="font-weight:600;color:#1e293b;font-size:0.8rem;">{name}</div>
      <div style="font-size:0.68rem;color:#94a3b8;">{s["email"]}</div>
    </div>
  </div>
</td>
<td><strong>{s["videos_watched"] or 0}</strong></td>
<td><strong>{s["quizzes_taken"] or 0}</strong></td>
<td>
  <div style="display:flex;align-items:center;gap:6px;">
    <div style="height:5px;background:#f1f5f9;border-radius:3px;overflow:hidden;width:50px;">
      <div style="width:{sc}%;height:100%;border-radius:3px;background:{sclr};"></div>
    </div>
    <span style="font-size:0.75rem;font-weight:600;color:{sclr};">{sc}%</span>
  </div>
</td>
<td>{"<span style='background:#fef2f2;color:#dc2626;padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:700;'>" + str(wk) + "</span>" if wk > 0 else "<span style='background:#f0fdf4;color:#059669;padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:700;'>None ✅</span>"}</td>
<td>{"<span style='background:#eff6ff;color:#2563eb;padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:700;'>" + str(cog) + "/10</span>" if cog is not None else "<span style='background:#f8fafc;color:#94a3b8;padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:700;'>Pending</span>"}</td>
<td>{"<span style='background:#f0fdf4;color:#059669;padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:700;'>Active</span>" if s["onboarding_done"] else "<span style='background:#f8fafc;color:#94a3b8;padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:700;'>New</span>"}</td>
<td>
  <div style="display:flex;gap:5px;">
    <a href="/admin/student/{s["id"]}" style="padding:4px 10px;border-radius:7px;background:#eff6ff;color:#2563eb;border:1px solid #bfdbfe;font-size:0.72rem;font-weight:600;text-decoration:none;">
      <i class="fas fa-eye"></i> View
    </a>
    <form method="POST" action="/admin/delete/{s["id"]}" onsubmit="return confirm('{del_confirm}')">
      <button style="padding:4px 8px;border-radius:7px;background:#fef2f2;color:#dc2626;border:1px solid #fecaca;font-size:0.72rem;font-weight:600;cursor:pointer;" type="submit">
        <i class="fas fa-trash"></i>
      </button>
    </form>
  </div>
</td>
</tr>'''
    else:
        rows_html = '<tr><td colspan="9" style="text-align:center;padding:30px;color:#94a3b8;">No students yet.</td></tr>'

    # Build activity HTML
    act_html = ''
    if recent:
        for a in recent:
            pct  = float(a['pct'] or 0)
            pclr = '#059669' if pct >= 70 else '#d97706' if pct >= 40 else '#dc2626'
            fname= a['full_name']
            av   = fname[0].upper() if fname else 'S'
            dt   = a['created_at'].strftime('%d %b') if a['created_at'] else ''
            topic= (a['topic'] or 'Quiz')[:20]
            act_html += f'''<div style="display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid #f1f5f9;">
<div style="width:30px;height:30px;border-radius:8px;background:linear-gradient(135deg,#2563eb,#7c3aed);display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:0.75rem;flex-shrink:0;">{av}</div>
<div style="flex:1;min-width:0;">
  <div style="font-size:0.78rem;font-weight:600;color:#1e293b;">{fname}</div>
  <div style="font-size:0.68rem;color:#94a3b8;">{topic} — <span style="color:{pclr};font-weight:600;">{pct}%</span></div>
</div>
<div style="font-size:0.65rem;color:#94a3b8;flex-shrink:0;">{dt}</div>
</div>'''
    else:
        act_html = '<p style="text-align:center;color:#94a3b8;padding:20px;font-size:0.8rem;">No activity yet</p>'

    # Build weak topics HTML
    wk_html = ''
    if top_weak:
        for w in top_weak:
            wk_html += f'''<div style="display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f1f5f9;">
<div>
  <div style="font-size:0.8rem;font-weight:600;color:#92400e;">⚠️ {w["topic"]}</div>
  <div style="font-size:0.68rem;color:#94a3b8;">{w["students"]} student(s)</div>
</div>
<span style="background:#dc2626;color:white;padding:2px 7px;border-radius:7px;font-size:0.68rem;font-weight:700;">{w["total_fails"]} fails</span>
</div>'''
    else:
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
.top-link{{color:rgba(255,255,255,0.6);padding:6px 12px;border-radius:8px;font-size:0.8rem;text-decoration:none;display:flex;align-items:center;gap:5px;}}
.top-link:hover{{background:rgba(255,255,255,0.1);color:white;}}
.logout-a{{background:rgba(220,38,38,0.15);border:1px solid rgba(220,38,38,0.25);color:#fca5a5;padding:6px 12px;border-radius:8px;font-size:0.8rem;text-decoration:none;display:flex;align-items:center;gap:5px;}}
.logout-a:hover{{background:rgba(220,38,38,0.3);color:white;}}
.main{{padding:24px;max-width:1400px;margin:0 auto;}}
.hero{{background:linear-gradient(135deg,#0f172a,#1e1b4b);border-radius:16px;padding:24px 28px;margin-bottom:24px;color:white;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;}}
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
  <div style="display:flex;align-items:center;gap:8px;">
    <a href="/admin/dashboard" class="top-link"><i class="fas fa-home"></i> Dashboard</a>
    
    <a href="/admin/logout" class="logout-a"><i class="fas fa-sign-out-alt"></i> Logout</a>
  </div>
</nav>

<div class="main">

  <div class="hero">
    <div>
      <h3 style="font-weight:800;font-size:1.3rem;margin:0 0 3px;">📊 Admin Dashboard</h3>
      <p style="color:rgba(255,255,255,0.5);margin:0;font-size:0.82rem;">AI Learning Platform — Complete Overview</p>
    </div>
    <div style="color:rgba(255,255,255,0.4);font-size:0.8rem;" id="dt"></div>
  </div>

  <div class="row g-3 mb-4">
    <div class="col-md col-6">
      <div class="sc s1">
        <div style="width:40px;height:40px;border-radius:10px;background:#eff6ff;color:#2563eb;display:flex;align-items:center;justify-content:center;margin-bottom:12px;"><i class="fas fa-users"></i></div>
        <span style="font-size:1.9rem;font-weight:800;color:#0f172a;line-height:1;display:block;">{total_users}</span>
        <span style="font-size:0.73rem;color:#94a3b8;font-weight:500;margin-top:4px;display:block;">Total Students</span>
      </div>
    </div>
    <div class="col-md col-6">
      <div class="sc s2">
        <div style="width:40px;height:40px;border-radius:10px;background:#f0fdf4;color:#059669;display:flex;align-items:center;justify-content:center;margin-bottom:12px;"><i class="fas fa-play-circle"></i></div>
        <span style="font-size:1.9rem;font-weight:800;color:#0f172a;line-height:1;display:block;">{total_videos}</span>
        <span style="font-size:0.73rem;color:#94a3b8;font-weight:500;margin-top:4px;display:block;">Videos Watched</span>
      </div>
    </div>
    <div class="col-md col-6">
      <div class="sc s3">
        <div style="width:40px;height:40px;border-radius:10px;background:#fffbeb;color:#d97706;display:flex;align-items:center;justify-content:center;margin-bottom:12px;"><i class="fas fa-clipboard-check"></i></div>
        <span style="font-size:1.9rem;font-weight:800;color:#0f172a;line-height:1;display:block;">{total_quizzes}</span>
        <span style="font-size:0.73rem;color:#94a3b8;font-weight:500;margin-top:4px;display:block;">Quizzes Taken</span>
      </div>
    </div>
    <div class="col-md col-6">
      <div class="sc s4">
        <div style="width:40px;height:40px;border-radius:10px;background:#faf5ff;color:#7c3aed;display:flex;align-items:center;justify-content:center;margin-bottom:12px;"><i class="fas fa-chart-line"></i></div>
        <span style="font-size:1.9rem;font-weight:800;color:#0f172a;line-height:1;display:block;">{avg_score}%</span>
        <span style="font-size:0.73rem;color:#94a3b8;font-weight:500;margin-top:4px;display:block;">Avg Score</span>
      </div>
    </div>
    <div class="col-md col-6">
      <div class="sc s5">
        <div style="width:40px;height:40px;border-radius:10px;background:#fef2f2;color:#dc2626;display:flex;align-items:center;justify-content:center;margin-bottom:12px;"><i class="fas fa-exclamation-triangle"></i></div>
        <span style="font-size:1.9rem;font-weight:800;color:#0f172a;line-height:1;display:block;">{total_weak}</span>
        <span style="font-size:0.73rem;color:#94a3b8;font-weight:500;margin-top:4px;display:block;">Weak Records</span>
      </div>
    </div>
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
            <thead>
              <tr>
                <th>#</th><th>Student</th><th>Videos</th><th>Quizzes</th>
                <th>Avg Score</th><th>Weak</th><th>Cognitive</th>
                <th>Status</th><th>Actions</th>
              </tr>
            </thead>
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
document.getElementById('dt').innerHTML = '<i class="fas fa-calendar me-1"></i>' + new Date().toLocaleDateString('en-US',{{weekday:'long',year:'numeric',month:'long',day:'numeric'}});
document.getElementById('ss').addEventListener('input',function(){{
    var q=this.value.toLowerCase();
    document.querySelectorAll('#st tbody tr').forEach(function(r){{
        r.style.display=r.textContent.toLowerCase().includes(q)?'':'none';
    }});
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

    # Stats
    total_pct = sum(float(q['pct'] or 0) for q in quizzes)
    avg       = round(total_pct / len(quizzes), 1) if quizzes else 0

    # Build quiz rows
    quiz_rows = ''
    for i, q in enumerate(quizzes, 1):
        p    = float(q['pct'] or 0)
        pclr = '#059669' if p >= 70 else '#d97706' if p >= 40 else '#dc2626'
        pbg  = '#f0fdf4' if p >= 70 else '#fffbeb' if p >= 40 else '#fef2f2'
        st   = '✅ Good' if p >= 70 else '⚠️ Avg' if p >= 40 else '❌ Weak'
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

    # Build watched rows
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

    # Build weak topics
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
        weak_html = '<div style="text-align:center;padding:20px;color:#94a3b8;font-size:0.8rem;">🎉 No weak topics!</div>'

    # Cognitive bars
    cog_html = ''
    if s['cognitive_score'] is not None:
        bars = [
            ('🔷 Logical',   s['logical_score'],          3, '#2563eb'),
            ('🔢 Numerical', s['numerical_score'],         3, '#059669'),
            ('📝 Verbal',    s['verbal_score'],            2, '#d97706'),
            ('💡 Problem',   s['problem_solving_score'],   2, '#7c3aed'),
        ]
        for label, score, max_s, color in bars:
            pct = int((score / max_s) * 100) if max_s else 0
            cog_html += f'''<div style="margin-bottom:12px;">
<div style="display:flex;justify-content:space-between;margin-bottom:3px;">
  <small style="font-size:0.75rem;font-weight:600;color:#475569;">{label}</small>
  <small style="font-size:0.72rem;color:#94a3b8;">{score}/{max_s}</small>
</div>
<div style="height:5px;background:#f1f5f9;border-radius:3px;overflow:hidden;">
  <div style="width:{pct}%;height:100%;border-radius:3px;background:{color};"></div>
</div>
</div>'''

    name = s['full_name']
    av   = name[0].upper() if name else 'S'
    joined = s['created_at'].strftime('%d %b %Y') if s['created_at'] else 'N/A'
    style_badge = f"<span style='background:rgba(255,255,255,0.12);color:white;padding:4px 12px;border-radius:12px;font-size:0.72rem;font-weight:600;margin-top:8px;display:inline-block;'>🧠 {s['learning_style']}</span>" if s['learning_style'] else ''
    cog_section = f'''<div style="background:white;border-radius:14px;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.05);overflow:hidden;margin-bottom:16px;">
<div style="padding:13px 18px;border-bottom:1px solid #f1f5f9;display:flex;align-items:center;justify-content:space-between;">
  <div style="font-size:0.87rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px;">
    <div style="width:26px;height:26px;border-radius:7px;background:#eff6ff;color:#2563eb;display:flex;align-items:center;justify-content:center;font-size:0.75rem;"><i class="fas fa-brain"></i></div>
    Cognitive Profile
  </div>
  <span style="background:#eff6ff;color:#2563eb;padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:700;">{s["cognitive_score"]}/10</span>
</div>
<div style="padding:14px 18px;">{cog_html}</div>
</div>''' if s['cognitive_score'] is not None else ''

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
.topbar{{background:#0f172a;height:60px;padding:0 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;box-shadow:0 2px 10px rgba(0,0,0,0.3);}}
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
  <div class="brand">
    <div class="brand-icon"><i class="fas fa-shield-alt"></i></div>
    Admin Panel
  </div>
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
    <div class="col-6 col-md-3">
      <div style="background:white;border-radius:12px;padding:14px 16px;border:1px solid #e2e8f0;text-align:center;">
        <div style="font-size:1.5rem;font-weight:800;color:#2563eb;">{len(watched)}</div>
        <div style="font-size:0.7rem;color:#94a3b8;margin-top:3px;">Videos</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div style="background:white;border-radius:12px;padding:14px 16px;border:1px solid #e2e8f0;text-align:center;">
        <div style="font-size:1.5rem;font-weight:800;color:#059669;">{len(quizzes)}</div>
        <div style="font-size:0.7rem;color:#94a3b8;margin-top:3px;">Quizzes</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div style="background:white;border-radius:12px;padding:14px 16px;border:1px solid #e2e8f0;text-align:center;">
        <div style="font-size:1.5rem;font-weight:800;color:#d97706;">{avg}%</div>
        <div style="font-size:0.7rem;color:#94a3b8;margin-top:3px;">Avg Score</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div style="background:white;border-radius:12px;padding:14px 16px;border:1px solid #e2e8f0;text-align:center;">
        <div style="font-size:1.5rem;font-weight:800;color:#dc2626;">{len(weak)}</div>
        <div style="font-size:0.7rem;color:#94a3b8;margin-top:3px;">Weak Topics</div>
      </div>
    </div>
  </div>

  <div class="row g-4">
    <div class="col-lg-8">

      <div style="background:white;border-radius:14px;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.05);overflow:hidden;margin-bottom:16px;">
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

      <div style="background:white;border-radius:14px;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.05);overflow:hidden;">
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
      <div style="background:white;border-radius:14px;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.05);overflow:hidden;">
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
