# admin.py — Complete Admin Panel (Single File)
# Routes: /admin/login, /admin/dashboard, /admin/students,
#         /admin/student/<id>, /admin/categories,
#         /admin/reports, /admin/moe-evaluation, /admin/logout
# ============================================================

from flask import (Blueprint, request, jsonify,
                   redirect, url_for, session, make_response)
from app.utils.db import execute_query
from functools import wraps
import bcrypt, json, math
import builtins as _b

_min = _b.min
_abs = _b.abs

admin_bp = Blueprint('admin_bp', __name__)

# ── Decorator ─────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('user_role') != 'admin':
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated

# ── Shared topbar HTML ─────────────────────────────────────
def topbar(active='dashboard'):
    links = [
        ('dashboard',   '/admin/dashboard',       'fa-home',           'Dashboard'),
        ('students',    '/admin/students',         'fa-users',          'Students'),
        ('categories',  '/admin/categories',       'fa-layer-group',    'Categories'),
        ('reports',     '/admin/reports',          'fa-chart-bar',      'Reports'),
        ('moe',         '/admin/moe-evaluation',   'fa-brain',          'MoE Eval'),
    ]
    nav = ''
    for key, href, icon, label in links:
        cls = 'top-link active' if active == key else 'top-link'
        nav += f'<a href="{href}" class="{cls}"><i class="fas {icon}"></i> {label}</a>'
    return f'''
<nav class="topbar">
  <div class="brand">
    <div class="brand-icon"><i class="fas fa-shield-alt"></i></div>
    Admin Panel
    <span style="background:rgba(220,38,38,0.2);color:#fca5a5;
                 padding:2px 8px;border-radius:6px;font-size:0.65rem;font-weight:700;">ADMIN</span>
  </div>
  <div style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;">
    {nav}
    <a href="/admin/logout" class="logout-a"><i class="fas fa-sign-out-alt"></i> Logout</a>
  </div>
</nav>'''

# ── Shared CSS ─────────────────────────────────────────────
COMMON_CSS = '''
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:#f0f2f5;color:#1e293b}
.topbar{background:#0f172a;min-height:60px;padding:0 20px;display:flex;
        align-items:center;justify-content:space-between;
        position:sticky;top:0;z-index:100;box-shadow:0 2px 10px rgba(0,0,0,.3);
        flex-wrap:wrap;gap:6px}
.brand{display:flex;align-items:center;gap:10px;color:white;font-weight:800;font-size:1rem}
.brand-icon{width:32px;height:32px;background:linear-gradient(135deg,#dc2626,#7c3aed);
            border-radius:8px;display:flex;align-items:center;justify-content:center;
            color:white;font-size:0.85rem}
.top-link{color:rgba(255,255,255,.6);padding:6px 10px;border-radius:8px;font-size:0.78rem;
          text-decoration:none;display:flex;align-items:center;gap:5px;transition:all .2s;
          white-space:nowrap}
.top-link:hover,.top-link.active{background:rgba(255,255,255,.1);color:white}
.logout-a{background:rgba(220,38,38,.15);border:1px solid rgba(220,38,38,.25);
          color:#fca5a5;padding:6px 10px;border-radius:8px;font-size:0.78rem;
          text-decoration:none;display:flex;align-items:center;gap:5px}
.logout-a:hover{background:rgba(220,38,38,.3);color:white}
.main{padding:22px;max-width:1400px;margin:0 auto}
.sc{background:white;border-radius:14px;padding:18px 20px;border:1px solid #e2e8f0;
    box-shadow:0 1px 3px rgba(0,0,0,.05);transition:all .25s;position:relative;overflow:hidden}
.sc::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:14px 14px 0 0}
.s1::before{background:#2563eb}.s2::before{background:#059669}
.s3::before{background:#d97706}.s4::before{background:#7c3aed}.s5::before{background:#dc2626}
.sc:hover{transform:translateY(-3px);box-shadow:0 8px 20px rgba(0,0,0,.08)}
.cb{background:white;border-radius:14px;border:1px solid #e2e8f0;
    box-shadow:0 1px 3px rgba(0,0,0,.05);overflow:hidden;margin-bottom:20px}
.ch{padding:13px 16px;border-bottom:1px solid #f1f5f9;
    display:flex;align-items:center;justify-content:space-between}
.dt{width:100%;font-size:0.78rem;border-collapse:collapse}
.dt th{padding:9px 14px;background:#f8fafc;font-size:0.67rem;font-weight:700;
       color:#64748b;text-transform:uppercase;letter-spacing:.05em;
       border-bottom:1px solid #e2e8f0;white-space:nowrap}
.dt td{padding:10px 14px;border-bottom:1px solid #f1f5f9;color:#475569;vertical-align:middle}
.dt tr:hover td{background:#f8fafc}
.dt tr:last-child td{border-bottom:none}
.hero{background:linear-gradient(135deg,#0f172a,#1e1b4b);border-radius:16px;
      padding:24px 28px;margin-bottom:22px;color:white}
.inp{padding:7px 12px;border:1.5px solid #e2e8f0;border-radius:8px;
     font-size:0.8rem;font-family:inherit;outline:none;background:white}
.inp:focus{border-color:#7c3aed}
.btn-sm{padding:5px 12px;border-radius:7px;font-size:0.72rem;font-weight:600;
        cursor:pointer;border:none;font-family:inherit;transition:all .2s}
.chart-wrap{position:relative;height:240px}
'''

def page(title, active, body, extra_head=''):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title} — Admin</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
{extra_head}
<style>{COMMON_CSS}</style>
</head>
<body>
{topbar(active)}
<div class="main">{body}</div>
</body>
</html>'''


# ============================================================
# LOGIN
# ============================================================
@admin_bp.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if session.get('user_role') == 'admin':
        return redirect('/admin/dashboard')
    error = ''
    if request.method == 'POST':
        email    = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        user     = execute_query(
            "SELECT * FROM users WHERE email=%s AND role='admin'",
            (email,), fetch=True
        )
        if not user:
            error = 'Admin account not found.'
        else:
            try:
                ok = bcrypt.checkpw(password.encode(), user[0]['password'].encode())
            except Exception:
                ok = False
            if not ok:
                error = 'Incorrect password.'
            else:
                session['user_id']         = user[0]['id']
                session['user_name']       = user[0]['full_name']
                session['user_role']       = 'admin'
                session['onboarding_done'] = 1
                return redirect('/admin/dashboard')

    err_html = f'<div class="err"><i class="fas fa-exclamation-circle me-2"></i>{error}</div>' if error else ''
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Admin Login</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Inter,sans-serif;background:#0f172a;min-height:100vh;
     display:flex;align-items:center;justify-content:center;overflow:hidden}}
.orb{{position:fixed;border-radius:50%;filter:blur(80px);opacity:.12}}
.o1{{width:400px;height:400px;background:#dc2626;top:-100px;right:-100px;animation:fl 8s ease-in-out infinite}}
.o2{{width:300px;height:300px;background:#7c3aed;bottom:-80px;left:-80px;animation:fl 6s ease-in-out infinite reverse}}
@keyframes fl{{0%,100%{{transform:translate(0,0)}}50%{{transform:translate(15px,-15px)}}}}
.box{{background:rgba(255,255,255,.04);backdrop-filter:blur(20px);
     border:1px solid rgba(255,255,255,.08);border-radius:24px;padding:44px 40px;
     width:100%;max-width:420px;position:relative;z-index:10;
     box-shadow:0 25px 50px rgba(0,0,0,.5);animation:up .4s ease}}
@keyframes up{{from{{opacity:0;transform:translateY(20px)}}to{{opacity:1;transform:translateY(0)}}}}
.logo{{width:56px;height:56px;background:linear-gradient(135deg,#dc2626,#7c3aed);
      border-radius:14px;display:flex;align-items:center;justify-content:center;
      font-size:1.4rem;color:white;margin-bottom:20px}}
h2{{color:white;font-size:1.4rem;font-weight:800;margin:0 0 4px}}
.sub{{color:rgba(255,255,255,.4);font-size:.82rem;margin:0 0 28px}}
label{{color:rgba(255,255,255,.6);font-size:.75rem;font-weight:600;margin-bottom:6px;display:block}}
.inp{{width:100%;background:rgba(255,255,255,.06);border:1.5px solid rgba(255,255,255,.1);
     border-radius:10px;padding:11px 14px;color:white;font-size:.875rem;outline:none;
     transition:all .2s;box-sizing:border-box}}
.inp:focus{{border-color:#dc2626;background:rgba(220,38,38,.08)}}
.inp::placeholder{{color:rgba(255,255,255,.2)}}
.btn{{width:100%;background:linear-gradient(135deg,#dc2626,#7c3aed);border:none;
     border-radius:10px;padding:13px;color:white;font-size:.9rem;font-weight:700;
     cursor:pointer;transition:all .2s;margin-top:6px}}
.btn:hover{{transform:translateY(-2px);box-shadow:0 8px 25px rgba(220,38,38,.4)}}
.err{{background:rgba(220,38,38,.12);border:1px solid rgba(220,38,38,.3);
     color:#fca5a5;border-radius:10px;padding:10px 14px;font-size:.8rem;margin-bottom:16px}}
.back{{display:block;text-align:center;margin-top:18px;color:rgba(255,255,255,.3);
      font-size:.78rem;text-decoration:none}}
.back:hover{{color:rgba(255,255,255,.6)}}
.mb{{margin-bottom:16px}}
</style>
</head>
<body>
<div class="orb o1"></div>
<div class="orb o2"></div>
<div class="box">
  <div class="logo"><i class="fas fa-shield-alt"></i></div>
  <h2>Admin Panel</h2>
  <p class="sub">AI Learning Platform</p>
  {err_html}
  <form method="POST">
    <div class="mb">
      <label>Email Address</label>
      <input type="email" name="email" class="inp" placeholder="admin@ailearn.com" required>
    </div>
    <div style="margin-bottom:20px">
      <label>Password</label>
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


# ── Logout ────────────────────────────────────────────────
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
    total_users   = (execute_query("SELECT COUNT(*) as c FROM users WHERE role='student'", fetch=True) or [{'c':0}])[0]['c']
    total_videos  = (execute_query("SELECT COUNT(*) as c FROM watched_videos", fetch=True) or [{'c':0}])[0]['c']
    total_quizzes = (execute_query("SELECT COUNT(*) as c FROM video_quizzes WHERE attempted=1", fetch=True) or [{'c':0}])[0]['c']
    avg_row       = (execute_query("SELECT ROUND(AVG(score/total*100),1) as a FROM video_quizzes WHERE attempted=1 AND total>0", fetch=True) or [{'a':0}])[0]
    avg_score     = float(avg_row['a'] or 0)
    total_weak    = (execute_query("SELECT COUNT(*) as c FROM weak_topics", fetch=True) or [{'c':0}])[0]['c']
    onboarded     = (execute_query("SELECT COUNT(*) as c FROM users WHERE role='student' AND onboarding_done=1", fetch=True) or [{'c':0}])[0]['c']

    students = execute_query(
        """SELECT u.id, u.full_name, u.email, u.created_at, u.onboarding_done,
               u.education_category, u.skill_level,
               COUNT(DISTINCT wv.video_id)          as vw,
               COUNT(DISTINCT vq.id)                as qt,
               ROUND(AVG(vq.score/vq.total*100),1)  as avs,
               COUNT(DISTINCT wt.id)                as wk,
               cr.total_score                       as cog
           FROM users u
           LEFT JOIN watched_videos wv  ON wv.user_id=u.id
           LEFT JOIN video_quizzes vq   ON vq.user_id=u.id AND vq.attempted=1 AND vq.total>0
           LEFT JOIN weak_topics wt     ON wt.user_id=u.id
           LEFT JOIN cognitive_results cr ON cr.user_id=u.id
           WHERE u.role='student'
           GROUP BY u.id ORDER BY u.created_at DESC LIMIT 50""",
        fetch=True
    ) or []

    recent = execute_query(
        """SELECT u.full_name, vq.topic,
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

    # Build student rows
    rows = ''
    for i, s in enumerate(students, 1):
        sc   = float(s['avs'] or 0)
        sclr = '#059669' if sc>=70 else '#d97706' if sc>=40 else '#dc2626'
        wk   = s['wk'] or 0
        av   = (s['full_name'] or 'S')[0].upper()
        cat  = s['education_category'] or ''
        rows += f'''<tr>
<td style="color:#94a3b8;font-size:.72rem">{i}</td>
<td><div style="display:flex;align-items:center;gap:8px">
  <div style="width:30px;height:30px;background:linear-gradient(135deg,#2563eb,#7c3aed);
              border-radius:8px;display:flex;align-items:center;justify-content:center;
              color:white;font-weight:700;font-size:.75rem">{av}</div>
  <div>
    <div style="font-weight:600;color:#1e293b;font-size:.8rem">{s["full_name"]}</div>
    <div style="font-size:.68rem;color:#94a3b8">{s["email"]}</div>
  </div>
</div></td>
<td style="text-align:center"><span style="background:#eff6ff;color:#2563eb;
   padding:2px 7px;border-radius:7px;font-size:.68rem;font-weight:600">{cat or "—"}</span></td>
<td style="text-align:center"><strong>{s["vw"] or 0}</strong></td>
<td style="text-align:center"><strong>{s["qt"] or 0}</strong></td>
<td><div style="display:flex;align-items:center;gap:6px">
  <div style="height:5px;background:#f1f5f9;border-radius:3px;overflow:hidden;width:50px">
    <div style="width:{_min(sc,100)}%;height:100%;background:{sclr};border-radius:3px"></div>
  </div>
  <span style="font-size:.75rem;font-weight:600;color:{sclr}">{sc}%</span>
</div></td>
<td style="text-align:center">{"<span style='background:#fef2f2;color:#dc2626;padding:2px 7px;border-radius:9px;font-size:.68rem;font-weight:700'>"+str(wk)+"</span>" if wk>0 else "<span style='background:#f0fdf4;color:#059669;padding:2px 7px;border-radius:9px;font-size:.68rem;font-weight:700'>0</span>"}</td>
<td><div style="display:flex;gap:5px">
  <a href="/admin/student/{s["id"]}" style="padding:4px 9px;border-radius:7px;
     background:#eff6ff;color:#2563eb;border:1px solid #bfdbfe;
     font-size:.72rem;font-weight:600;text-decoration:none">
    <i class="fas fa-eye"></i></a>
  <form method="POST" action="/admin/delete/{s["id"]}"
        onsubmit="return confirm('Delete {s["full_name"]}?')" style="display:inline">
    <button style="padding:4px 8px;border-radius:7px;background:#fef2f2;
            color:#dc2626;border:1px solid #fecaca;font-size:.72rem;
            font-weight:600;cursor:pointer" type="submit">
      <i class="fas fa-trash"></i></button>
  </form>
</div></td>
</tr>'''
    if not rows:
        rows = '<tr><td colspan="8" style="text-align:center;padding:30px;color:#94a3b8">No students yet.</td></tr>'

    # Recent activity
    act = ''
    for a in recent:
        pct   = float(a['pct'] or 0)
        pclr  = '#059669' if pct>=70 else '#d97706' if pct>=40 else '#dc2626'
        fname = a['full_name']
        dt    = a['created_at'].strftime('%d %b') if a['created_at'] else ''
        act  += f'''<div style="display:flex;align-items:center;gap:10px;
                     padding:8px 0;border-bottom:1px solid #f1f5f9">
<div style="width:28px;height:28px;border-radius:7px;
            background:linear-gradient(135deg,#2563eb,#7c3aed);
            display:flex;align-items:center;justify-content:center;
            color:white;font-weight:700;font-size:.72rem;flex-shrink:0">
  {fname[0].upper()}</div>
<div style="flex:1;min-width:0">
  <div style="font-size:.77rem;font-weight:600;color:#1e293b">{fname}</div>
  <div style="font-size:.67rem;color:#94a3b8">{(a["topic"] or "Quiz")[:20]}
    — <span style="color:{pclr};font-weight:600">{pct}%</span></div>
</div>
<div style="font-size:.64rem;color:#94a3b8;flex-shrink:0">{dt}</div>
</div>'''
    if not act:
        act = '<p style="text-align:center;color:#94a3b8;padding:20px;font-size:.8rem">No activity yet</p>'

    # Top weak
    wk_html = ''
    for w in top_weak:
        wk_html += f'''<div style="display:flex;align-items:center;justify-content:space-between;
                        padding:8px 0;border-bottom:1px solid #f1f5f9">
<div>
  <div style="font-size:.79rem;font-weight:600;color:#92400e">⚠️ {w["topic"]}</div>
  <div style="font-size:.67rem;color:#94a3b8">{w["st"]} student(s)</div>
</div>
<span style="background:#dc2626;color:white;padding:2px 7px;
             border-radius:7px;font-size:.67rem;font-weight:700">{w["tf"]} fails</span>
</div>'''
    if not wk_html:
        wk_html = '<p style="text-align:center;color:#94a3b8;padding:20px;font-size:.8rem">No weak topics</p>'

    # Category distribution badges
    cat_html = ''
    colors = ['#2563eb','#059669','#7c3aed','#d97706','#dc2626','#0891b2']
    for i,c in enumerate(cat_dist):
        clr = colors[i % len(colors)]
        cat_html += f'''<div style="display:flex;align-items:center;justify-content:space-between;
                         padding:7px 0;border-bottom:1px solid #f1f5f9">
<span style="font-size:.8rem;font-weight:600;color:#1e293b">{c["education_category"]}</span>
<span style="background:{clr}18;color:{clr};border:1px solid {clr}33;
             padding:2px 10px;border-radius:9px;font-size:.68rem;font-weight:700">
  {c["cnt"]} students</span>
</div>'''
    if not cat_html:
        cat_html = '<p style="text-align:center;color:#94a3b8;padding:12px;font-size:.8rem">No data yet</p>'

    onboard_pct = round(onboarded/total_users*100) if total_users else 0

    body = f'''
<div class="hero d-flex justify-content-between align-items-center flex-wrap gap-3">
  <div>
    <div style="font-size:.7rem;font-weight:700;color:rgba(255,255,255,.4);
                text-transform:uppercase;letter-spacing:.12em;margin-bottom:5px">
      Admin Overview</div>
    <h3 style="font-weight:900;font-size:1.3rem;margin:0 0 3px">📊 Admin Dashboard</h3>
    <p style="color:rgba(255,255,255,.5);margin:0;font-size:.82rem">
      AI Learning Platform — Complete Overview</p>
  </div>
  <div style="color:rgba(255,255,255,.35);font-size:.78rem" id="dt"></div>
</div>

<div class="row g-3 mb-4">
  <div class="col-6 col-md-2">
    <div class="sc s1">
      <div style="width:38px;height:38px;border-radius:9px;background:#eff6ff;
                  color:#2563eb;display:flex;align-items:center;justify-content:center;
                  margin-bottom:10px"><i class="fas fa-users"></i></div>
      <div style="font-size:1.8rem;font-weight:800;color:#0f172a;line-height:1">{total_users}</div>
      <div style="font-size:.7rem;color:#94a3b8;margin-top:3px">Total Students</div>
    </div>
  </div>
  <div class="col-6 col-md-2">
    <div class="sc s2">
      <div style="width:38px;height:38px;border-radius:9px;background:#f0fdf4;
                  color:#059669;display:flex;align-items:center;justify-content:center;
                  margin-bottom:10px"><i class="fas fa-play-circle"></i></div>
      <div style="font-size:1.8rem;font-weight:800;color:#0f172a;line-height:1">{total_videos}</div>
      <div style="font-size:.7rem;color:#94a3b8;margin-top:3px">Videos Watched</div>
    </div>
  </div>
  <div class="col-6 col-md-2">
    <div class="sc s3">
      <div style="width:38px;height:38px;border-radius:9px;background:#fffbeb;
                  color:#d97706;display:flex;align-items:center;justify-content:center;
                  margin-bottom:10px"><i class="fas fa-clipboard-check"></i></div>
      <div style="font-size:1.8rem;font-weight:800;color:#0f172a;line-height:1">{total_quizzes}</div>
      <div style="font-size:.7rem;color:#94a3b8;margin-top:3px">Quizzes Taken</div>
    </div>
  </div>
  <div class="col-6 col-md-2">
    <div class="sc s4">
      <div style="width:38px;height:38px;border-radius:9px;background:#faf5ff;
                  color:#7c3aed;display:flex;align-items:center;justify-content:center;
                  margin-bottom:10px"><i class="fas fa-chart-line"></i></div>
      <div style="font-size:1.8rem;font-weight:800;color:#0f172a;line-height:1">{avg_score}%</div>
      <div style="font-size:.7rem;color:#94a3b8;margin-top:3px">Avg Score</div>
    </div>
  </div>
  <div class="col-6 col-md-2">
    <div class="sc s5">
      <div style="width:38px;height:38px;border-radius:9px;background:#fef2f2;
                  color:#dc2626;display:flex;align-items:center;justify-content:center;
                  margin-bottom:10px"><i class="fas fa-exclamation-triangle"></i></div>
      <div style="font-size:1.8rem;font-weight:800;color:#0f172a;line-height:1">{total_weak}</div>
      <div style="font-size:.7rem;color:#94a3b8;margin-top:3px">Weak Records</div>
    </div>
  </div>
  <div class="col-6 col-md-2">
    <div class="sc" style="border-top:3px solid #0891b2">
      <div style="width:38px;height:38px;border-radius:9px;background:#f0f9ff;
                  color:#0891b2;display:flex;align-items:center;justify-content:center;
                  margin-bottom:10px"><i class="fas fa-user-check"></i></div>
      <div style="font-size:1.8rem;font-weight:800;color:#0f172a;line-height:1">{onboard_pct}%</div>
      <div style="font-size:.7rem;color:#94a3b8;margin-top:3px">Onboarded</div>
    </div>
  </div>
</div>

<div class="row g-4">
  <div class="col-lg-8">
    <div class="cb">
      <div class="ch">
        <div style="font-size:.87rem;font-weight:700;color:#1e293b;
                    display:flex;align-items:center;gap:8px">
          <div style="width:26px;height:26px;border-radius:7px;background:#eff6ff;
                      color:#2563eb;display:flex;align-items:center;justify-content:center;
                      font-size:.72rem"><i class="fas fa-users"></i></div>
          Recent Students
          <span style="background:#eff6ff;color:#2563eb;padding:2px 8px;
                       border-radius:10px;font-size:.67rem;font-weight:700">{len(students)}</span>
        </div>
        <div style="display:flex;gap:7px;align-items:center">
          <input type="text" id="srch" class="inp" placeholder="Search..."
                 style="width:160px" oninput="filterTable(this.value)">
          <a href="/admin/students"
             style="padding:5px 11px;border-radius:7px;background:linear-gradient(135deg,#2563eb,#7c3aed);
                    color:white;font-size:.72rem;font-weight:600;text-decoration:none">
            View All</a>
        </div>
      </div>
      <div style="overflow-x:auto">
        <table class="dt" id="stbl">
          <thead><tr>
            <th>#</th><th>Student</th><th>Category</th>
            <th>Videos</th><th>Quizzes</th><th>Avg Score</th>
            <th>Weak</th><th>Actions</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="col-lg-4">
    <div class="cb mb-3">
      <div class="ch">
        <div style="font-size:.87rem;font-weight:700;color:#1e293b;
                    display:flex;align-items:center;gap:8px">
          <div style="width:26px;height:26px;border-radius:7px;background:#f0fdf4;
                      color:#059669;display:flex;align-items:center;justify-content:center;
                      font-size:.72rem"><i class="fas fa-bolt"></i></div>
          Recent Activity
        </div>
      </div>
      <div style="padding:10px 14px">{act}</div>
    </div>

    <div class="cb mb-3">
      <div class="ch">
        <div style="font-size:.87rem;font-weight:700;color:#1e293b;
                    display:flex;align-items:center;gap:8px">
          <div style="width:26px;height:26px;border-radius:7px;background:#fffbeb;
                      color:#d97706;display:flex;align-items:center;justify-content:center;
                      font-size:.72rem"><i class="fas fa-exclamation-triangle"></i></div>
          Top Weak Topics
        </div>
      </div>
      <div style="padding:10px 14px">{wk_html}</div>
    </div>

    <div class="cb">
      <div class="ch">
        <div style="font-size:.87rem;font-weight:700;color:#1e293b;
                    display:flex;align-items:center;gap:8px">
          <div style="width:26px;height:26px;border-radius:7px;background:#f0f9ff;
                      color:#0891b2;display:flex;align-items:center;justify-content:center;
                      font-size:.72rem"><i class="fas fa-layer-group"></i></div>
          Category Distribution
        </div>
      </div>
      <div style="padding:10px 14px">{cat_html}</div>
    </div>
  </div>
</div>

<script>
document.getElementById('dt').innerHTML =
  '<i class="fas fa-calendar me-1"></i>' +
  new Date().toLocaleDateString('en-US',{{weekday:'long',year:'numeric',month:'long',day:'numeric'}});

function filterTable(q) {{
  q = q.toLowerCase();
  document.querySelectorAll('#stbl tbody tr').forEach(function(r) {{
    r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}}
</script>'''

    return make_response(page('Dashboard', 'dashboard', body))


# ============================================================
# STUDENTS LIST
# ============================================================
@admin_bp.route('/admin/students')
@admin_required
def admin_students():
    search = request.args.get('q','').strip()
    cat    = request.args.get('cat','').strip()
    level  = request.args.get('level','').strip()

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
        "SELECT DISTINCT education_category FROM users WHERE role='student' AND education_category IS NOT NULL",
        fetch=True
    ) or []

    rows = ''
    for i, s in enumerate(students, 1):
        sc   = float(s['avs'] or 0)
        sclr = '#059669' if sc>=70 else '#d97706' if sc>=40 else '#dc2626'
        wk   = s['wk'] or 0
        av   = (s['full_name'] or 'S')[0].upper()
        rows += f'''<tr>
<td style="color:#94a3b8;font-size:.72rem">{i}</td>
<td><div style="display:flex;align-items:center;gap:8px">
  <div style="width:28px;height:28px;background:linear-gradient(135deg,#2563eb,#7c3aed);
              border-radius:8px;display:flex;align-items:center;justify-content:center;
              color:white;font-weight:700;font-size:.72rem">{av}</div>
  <div>
    <div style="font-weight:600;color:#1e293b;font-size:.79rem">{s["full_name"]}</div>
    <div style="font-size:.67rem;color:#94a3b8">{s["email"]}</div>
  </div>
</div></td>
<td><span style="background:#eff6ff;color:#2563eb;padding:2px 7px;border-radius:7px;
              font-size:.67rem;font-weight:600">{s["education_category"] or "—"}</span></td>
<td style="font-size:.78rem;color:#475569">{s["field_of_interest"] or "—"}</td>
<td><span style="background:#f0fdf4;color:#059669;padding:2px 7px;border-radius:7px;
              font-size:.67rem;font-weight:600">{s["skill_level"] or "—"}</span></td>
<td style="text-align:center"><strong>{s["vw"] or 0}</strong></td>
<td style="text-align:center"><strong>{s["qt"] or 0}</strong></td>
<td><span style="font-size:.75rem;font-weight:700;color:{sclr}">{sc}%</span></td>
<td style="text-align:center">{"<span style='background:#fef2f2;color:#dc2626;padding:2px 7px;border-radius:9px;font-size:.67rem;font-weight:700'>"+str(wk)+"</span>" if wk>0 else "0"}</td>
<td>{"✅ Active" if s["onboarding_done"] else "⏳ New"}</td>
<td><div style="display:flex;gap:4px">
  <a href="/admin/student/{s["id"]}"
     style="padding:4px 9px;border-radius:7px;background:#eff6ff;color:#2563eb;
            border:1px solid #bfdbfe;font-size:.7rem;font-weight:600;text-decoration:none">
    <i class="fas fa-eye"></i></a>
  <form method="POST" action="/admin/delete/{s["id"]}"
        onsubmit="return confirm('Delete?')" style="display:inline">
    <button style="padding:4px 8px;border-radius:7px;background:#fef2f2;color:#dc2626;
            border:1px solid #fecaca;font-size:.7rem;cursor:pointer" type="submit">
      <i class="fas fa-trash"></i></button>
  </form>
</div></td>
</tr>'''
    if not rows:
        rows = '<tr><td colspan="11" style="text-align:center;padding:30px;color:#94a3b8">No students found.</td></tr>'

    cat_opts = ''.join(f'<option value="{c["education_category"]}" {"selected" if c["education_category"]==cat else ""}>{c["education_category"]}</option>' for c in cats)

    body = f'''
<div class="hero d-flex justify-content-between align-items-center flex-wrap gap-3">
  <div>
    <h3 style="font-weight:900;font-size:1.2rem;margin:0 0 3px">👥 All Students</h3>
    <p style="color:rgba(255,255,255,.5);margin:0;font-size:.82rem">
      {len(students)} students found</p>
  </div>
</div>

<div class="cb">
  <div class="ch flex-wrap gap-2">
    <form method="GET" style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
      <input type="text" name="q" value="{search}" class="inp"
             placeholder="Search name or email..." style="min-width:200px">
      <select name="cat" class="inp">
        <option value="">All Categories</option>
        {cat_opts}
      </select>
      <select name="level" class="inp">
        <option value="">All Levels</option>
        <option value="Beginner"     {"selected" if level=="Beginner" else ""}>Beginner</option>
        <option value="Intermediate" {"selected" if level=="Intermediate" else ""}>Intermediate</option>
        <option value="Advanced"     {"selected" if level=="Advanced" else ""}>Advanced</option>
      </select>
      <button type="submit" class="btn-sm" style="background:#2563eb;color:white">
        <i class="fas fa-search me-1"></i>Filter</button>
      <a href="/admin/students" class="btn-sm"
         style="background:#f1f5f9;color:#64748b;text-decoration:none">Clear</a>
    </form>
  </div>
  <div style="overflow-x:auto">
    <table class="dt">
      <thead><tr>
        <th>#</th><th>Student</th><th>Category</th><th>Field</th><th>Level</th>
        <th>Videos</th><th>Quizzes</th><th>Avg Score</th><th>Weak</th>
        <th>Status</th><th>Actions</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</div>'''

    return make_response(page('Students', 'students', body))


# ============================================================
# STUDENT DETAIL
# ============================================================
@admin_bp.route('/admin/student/<int:sid>')
@admin_required
def admin_student_detail(sid):
    student = execute_query(
        """SELECT u.*, cr.learning_style, cr.total_score as cog,
               cr.logical_score, cr.numerical_score,
               cr.verbal_score, cr.problem_solving_score
           FROM users u
           LEFT JOIN cognitive_results cr ON cr.user_id=u.id
           WHERE u.id=%s AND u.role='student'""",
        (sid,), fetch=True
    )
    if not student:
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

    avg = round(sum(float(q['pct'] or 0) for q in quizzes)/len(quizzes), 1) if quizzes else 0
    av  = (s['full_name'] or 'S')[0].upper()
    joined = s['created_at'].strftime('%d %b %Y') if s['created_at'] else 'N/A'

    quiz_rows = ''
    for i,q in enumerate(quizzes,1):
        p   = float(q['pct'] or 0)
        clr = '#059669' if p>=70 else '#d97706' if p>=40 else '#dc2626'
        bg  = '#f0fdf4' if p>=70 else '#fffbeb' if p>=40 else '#fef2f2'
        dt  = q['created_at'].strftime('%d %b %Y') if q['created_at'] else ''
        quiz_rows += f'<tr><td style="color:#94a3b8">{i}</td><td><strong>{q["topic"] or "N/A"}</strong></td><td style="color:#94a3b8;font-size:.72rem">{(q["video_title"] or "")[:30]}...</td><td><strong>{q["score"]}/{q["total"]}</strong></td><td><span style="background:{bg};color:{clr};padding:2px 8px;border-radius:9px;font-size:.68rem;font-weight:700">{p}%</span></td><td style="color:#94a3b8;font-size:.72rem">{dt}</td></tr>'
    if not quiz_rows:
        quiz_rows = '<tr><td colspan="6" style="text-align:center;padding:20px;color:#94a3b8">No quizzes yet</td></tr>'

    watch_rows = ''
    for i,v in enumerate(watched,1):
        dt = v['watched_at'].strftime('%d %b %Y') if v['watched_at'] else ''
        watch_rows += f'<tr><td style="color:#94a3b8">{i}</td><td>{(v["video_title"] or "")[:40]}</td><td><span style="background:#f1f5f9;color:#64748b;padding:2px 7px;border-radius:5px;font-size:.67rem">{v["topic"]}</span></td><td style="color:#94a3b8;font-size:.72rem">{dt}</td></tr>'
    if not watch_rows:
        watch_rows = '<tr><td colspan="4" style="text-align:center;padding:20px;color:#94a3b8">No videos yet</td></tr>'

    wk_html = ''
    for w in weak:
        dt = w['last_detected'].strftime('%d %b') if w['last_detected'] else ''
        wk_html += f'<div style="display:flex;align-items:center;justify-content:space-between;padding:7px 0;border-bottom:1px solid #f1f5f9"><div><div style="font-size:.79rem;font-weight:600;color:#92400e">⚠️ {w["topic"]}</div><div style="font-size:.67rem;color:#94a3b8">{dt}</div></div><span style="background:#dc2626;color:white;padding:2px 7px;border-radius:6px;font-size:.67rem;font-weight:700">{w["fail_count"]}x</span></div>'
    if not wk_html:
        wk_html = '<p style="text-align:center;padding:16px;color:#94a3b8;font-size:.8rem">No weak topics 🎉</p>'

    cog_html = ''
    if s['cog'] is not None:
        bars = [('Logical', s['logical_score'], 3,'#2563eb'),
                ('Numerical', s['numerical_score'], 3,'#059669'),
                ('Verbal', s['verbal_score'], 2,'#d97706'),
                ('Problem Solve', s['problem_solving_score'], 2,'#7c3aed')]
        for lbl,sc,mx,clr in bars:
            pct = int((sc/mx)*100) if mx and sc is not None else 0
            cog_html += f'<div style="margin-bottom:10px"><div style="display:flex;justify-content:space-between;margin-bottom:3px"><small style="font-size:.74rem;font-weight:600;color:#475569">{lbl}</small><small style="font-size:.71rem;color:#94a3b8">{sc}/{mx}</small></div><div style="height:5px;background:#f1f5f9;border-radius:3px;overflow:hidden"><div style="width:{pct}%;height:100%;background:{clr};border-radius:3px"></div></div></div>'

    body = f'''
<div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
  <a href="/admin/students"
     style="padding:7px 14px;border-radius:9px;background:white;border:1px solid #e2e8f0;
            color:#64748b;text-decoration:none;font-size:.8rem;font-weight:600;
            display:flex;align-items:center;gap:5px">
    <i class="fas fa-arrow-left"></i> Back</a>
  <h4 style="margin:0;font-size:1rem;font-weight:700;color:#1e293b">Student Detail</h4>
</div>

<div class="hero d-flex align-items-center gap-4 flex-wrap mb-4">
  <div style="width:56px;height:56px;background:linear-gradient(135deg,#2563eb,#7c3aed);
              border-radius:14px;display:flex;align-items:center;justify-content:center;
              color:white;font-weight:800;font-size:1.3rem;flex-shrink:0">{av}</div>
  <div style="flex:1">
    <h3 style="font-weight:800;margin:0 0 3px;font-size:1.2rem">{s["full_name"]}</h3>
    <p style="color:rgba(255,255,255,.5);margin:0;font-size:.82rem">{s["email"]}</p>
    {f'<span style="background:rgba(255,255,255,.12);color:white;padding:3px 11px;border-radius:11px;font-size:.7rem;font-weight:600;margin-top:6px;display:inline-block">{s["learning_style"]}</span>' if s.get("learning_style") else ''}
  </div>
  <div style="text-align:right">
    <div style="font-size:.68rem;color:rgba(255,255,255,.4)">Joined</div>
    <div style="font-size:.85rem;color:white;font-weight:600">{joined}</div>
    <div style="font-size:.7rem;color:rgba(255,255,255,.4);margin-top:3px">
      {s.get("education_category","") or ""} • {s.get("skill_level","") or ""}</div>
  </div>
</div>

<div class="row g-3 mb-4">
  <div class="col-6 col-md-3">
    <div style="background:white;border-radius:12px;padding:14px;border:1px solid #e2e8f0;text-align:center">
      <div style="font-size:1.5rem;font-weight:800;color:#2563eb">{len(watched)}</div>
      <div style="font-size:.7rem;color:#94a3b8;margin-top:3px">Videos Watched</div>
    </div>
  </div>
  <div class="col-6 col-md-3">
    <div style="background:white;border-radius:12px;padding:14px;border:1px solid #e2e8f0;text-align:center">
      <div style="font-size:1.5rem;font-weight:800;color:#059669">{len(quizzes)}</div>
      <div style="font-size:.7rem;color:#94a3b8;margin-top:3px">Quizzes Taken</div>
    </div>
  </div>
  <div class="col-6 col-md-3">
    <div style="background:white;border-radius:12px;padding:14px;border:1px solid #e2e8f0;text-align:center">
      <div style="font-size:1.5rem;font-weight:800;color:#d97706">{avg}%</div>
      <div style="font-size:.7rem;color:#94a3b8;margin-top:3px">Avg Score</div>
    </div>
  </div>
  <div class="col-6 col-md-3">
    <div style="background:white;border-radius:12px;padding:14px;border:1px solid #e2e8f0;text-align:center">
      <div style="font-size:1.5rem;font-weight:800;color:#dc2626">{len(weak)}</div>
      <div style="font-size:.7rem;color:#94a3b8;margin-top:3px">Weak Topics</div>
    </div>
  </div>
</div>

<div class="row g-4">
  <div class="col-lg-8">
    <div class="cb mb-3">
      <div class="ch">
        <div style="font-size:.86rem;font-weight:700;color:#1e293b;
                    display:flex;align-items:center;gap:7px">
          <i class="fas fa-clipboard-check" style="color:#059669"></i> Quiz History
          <span style="background:#eff6ff;color:#2563eb;padding:2px 8px;
                       border-radius:9px;font-size:.67rem;font-weight:700">{len(quizzes)}</span>
        </div>
      </div>
      <div style="overflow-x:auto">
        <table class="dt">
          <thead><tr><th>#</th><th>Topic</th><th>Video</th><th>Score</th><th>%</th><th>Date</th></tr></thead>
          <tbody>{quiz_rows}</tbody>
        </table>
      </div>
    </div>
    <div class="cb">
      <div class="ch">
        <div style="font-size:.86rem;font-weight:700;color:#1e293b;
                    display:flex;align-items:center;gap:7px">
          <i class="fas fa-play-circle" style="color:#2563eb"></i> Watched Videos
          <span style="background:#eff6ff;color:#2563eb;padding:2px 8px;
                       border-radius:9px;font-size:.67rem;font-weight:700">{len(watched)}</span>
        </div>
      </div>
      <div style="overflow-x:auto">
        <table class="dt">
          <thead><tr><th>#</th><th>Title</th><th>Topic</th><th>Date</th></tr></thead>
          <tbody>{watch_rows}</tbody>
        </table>
      </div>
    </div>
  </div>
  <div class="col-lg-4">
    {f'<div class="cb mb-3"><div class="ch"><div style="font-size:.86rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:7px"><i class="fas fa-brain" style="color:#2563eb"></i> Cognitive Profile</div><span style="background:#eff6ff;color:#2563eb;padding:2px 8px;border-radius:9px;font-size:.67rem;font-weight:700">{s["cog"]}/10</span></div><div style="padding:14px 16px">{cog_html}</div></div>' if s['cog'] is not None else ''}
    <div class="cb">
      <div class="ch">
        <div style="font-size:.86rem;font-weight:700;color:#1e293b;
                    display:flex;align-items:center;gap:7px">
          <i class="fas fa-exclamation-triangle" style="color:#d97706"></i> Weak Topics
        </div>
        <span style="background:#fef2f2;color:#dc2626;padding:2px 8px;
                     border-radius:9px;font-size:.67rem;font-weight:700">{len(weak)}</span>
      </div>
      <div style="padding:10px 14px">{wk_html}</div>
    </div>
  </div>
</div>'''

    return make_response(page(s['full_name'], 'students', body))


# ── Delete student ────────────────────────────────────────
@admin_bp.route('/admin/delete/<int:sid>', methods=['POST'])
@admin_required
def admin_delete(sid):
    execute_query("DELETE FROM users WHERE id=%s AND role='student'", (sid,))
    return redirect('/admin/students')


# ============================================================
# CATEGORIES MANAGEMENT
# ============================================================
@admin_bp.route('/admin/categories')
@admin_required
def admin_categories():
    cats   = execute_query("SELECT * FROM educational_categories ORDER BY display_order", fetch=True) or []
    depts  = execute_query("SELECT * FROM university_departments ORDER BY display_order", fetch=True) or []
    fields = execute_query(
        """SELECT f.*, d.name as dept_name FROM university_fields_of_study f
           JOIN university_departments d ON d.id=f.department_id
           ORDER BY f.department_id, f.display_order""", fetch=True
    ) or []

    cnt_map = {}
    for r in (execute_query("SELECT education_category, COUNT(*) as c FROM users WHERE role='student' GROUP BY education_category", fetch=True) or []):
        cnt_map[r['education_category']] = r['c']

    cat_rows = ''
    for c in cats:
        cnt = cnt_map.get(c['name'], 0)
        cat_rows += f'''<tr>
<td style="font-weight:600">{c["name"]}</td>
<td style="color:#94a3b8;font-size:.8rem">{c["description"] or ""}</td>
<td><code style="font-size:.75rem;background:#f1f5f9;padding:2px 7px;border-radius:4px">{c["icon"]}</code></td>
<td style="text-align:center"><strong>{c["display_order"]}</strong></td>
<td style="text-align:center"><span style="background:#eff6ff;color:#2563eb;
   padding:2px 8px;border-radius:9px;font-size:.67rem;font-weight:700">{cnt}</span></td>
<td><form method="POST" action="/admin/categories/delete/{c["id"]}"
         onsubmit="return confirm('Delete {c["name"]}?')" style="display:inline">
  <button class="btn-sm" style="background:#fef2f2;color:#dc2626;border:1px solid #fecaca"
          type="submit"><i class="fas fa-trash"></i></button>
</form></td>
</tr>'''

    dept_rows = ''
    for d in depts:
        dept_rows += f'''<tr>
<td style="font-weight:600">{d["name"]}</td>
<td><code style="font-size:.75rem;background:#f1f5f9;padding:2px 7px;border-radius:4px">{d["icon"] or ""}</code></td>
<td style="text-align:center"><strong>{d["display_order"]}</strong></td>
<td><form method="POST" action="/admin/dept/delete/{d["id"]}"
         onsubmit="return confirm('Delete {d["name"]}?')" style="display:inline">
  <button class="btn-sm" style="background:#fef2f2;color:#dc2626;border:1px solid #fecaca"
          type="submit"><i class="fas fa-trash"></i></button>
</form></td>
</tr>'''

    dept_opts = ''.join(f'<option value="{d["id"]}">{d["name"]}</option>' for d in depts)

    field_rows = ''
    for f in fields:
        field_rows += f'''<tr>
<td style="color:#94a3b8;font-size:.75rem">{f["dept_name"]}</td>
<td style="font-weight:600">{f["field_name"]}</td>
<td style="text-align:center"><strong>{f["display_order"]}</strong></td>
<td><form method="POST" action="/admin/field/delete/{f["id"]}"
         onsubmit="return confirm('Delete?')" style="display:inline">
  <button class="btn-sm" style="background:#fef2f2;color:#dc2626;border:1px solid #fecaca"
          type="submit"><i class="fas fa-trash"></i></button>
</form></td>
</tr>'''

    body = f'''
<div class="hero mb-4">
  <h3 style="font-weight:900;font-size:1.2rem;margin:0 0 3px">🗂️ Categories Management</h3>
  <p style="color:rgba(255,255,255,.5);margin:0;font-size:.82rem">
    Manage education categories, university departments and fields</p>
</div>

<div class="row g-4">
  <div class="col-lg-6">
    <div class="cb mb-4">
      <div class="ch">
        <div style="font-size:.87rem;font-weight:700;color:#1e293b;
                    display:flex;align-items:center;gap:8px">
          <i class="fas fa-layer-group" style="color:#2563eb"></i>
          Education Categories
          <span style="background:#eff6ff;color:#2563eb;padding:2px 8px;
                       border-radius:9px;font-size:.67rem;font-weight:700">{len(cats)}</span>
        </div>
      </div>
      <div style="overflow-x:auto">
        <table class="dt">
          <thead><tr><th>Name</th><th>Description</th><th>Icon</th><th>Order</th><th>Students</th><th>Del</th></tr></thead>
          <tbody>{cat_rows}</tbody>
        </table>
      </div>
      <div style="padding:14px 16px;border-top:1px solid #f1f5f9;background:#f8fafc">
        <div style="font-size:.78rem;font-weight:700;color:#1e293b;margin-bottom:10px">
          ➕ Add Category</div>
        <form method="POST" action="/admin/categories/add"
              style="display:grid;grid-template-columns:1fr 1fr;gap:7px">
          <input type="text" name="name" class="inp" placeholder="Name" required>
          <input type="text" name="description" class="inp" placeholder="Description">
          <input type="text" name="icon" class="inp" placeholder="fas fa-book" value="fas fa-book">
          <div style="display:flex;gap:7px">
            <input type="number" name="display_order" class="inp" placeholder="Order" value="99" style="width:80px">
            <button type="submit" class="btn-sm"
                    style="background:linear-gradient(135deg,#2563eb,#7c3aed);color:white;flex:1">
              Add</button>
          </div>
        </form>
      </div>
    </div>
  </div>

  <div class="col-lg-6">
    <div class="cb mb-4">
      <div class="ch">
        <div style="font-size:.87rem;font-weight:700;color:#1e293b;
                    display:flex;align-items:center;gap:8px">
          <i class="fas fa-university" style="color:#7c3aed"></i>
          University Departments
          <span style="background:#faf5ff;color:#7c3aed;padding:2px 8px;
                       border-radius:9px;font-size:.67rem;font-weight:700">{len(depts)}</span>
        </div>
      </div>
      <div style="overflow-x:auto">
        <table class="dt">
          <thead><tr><th>Name</th><th>Icon</th><th>Order</th><th>Del</th></tr></thead>
          <tbody>{dept_rows}</tbody>
        </table>
      </div>
      <div style="padding:14px 16px;border-top:1px solid #f1f5f9;background:#f8fafc">
        <div style="font-size:.78rem;font-weight:700;color:#1e293b;margin-bottom:10px">
          ➕ Add Department</div>
        <form method="POST" action="/admin/dept/add"
              style="display:grid;grid-template-columns:1fr 1fr;gap:7px">
          <input type="text" name="name" class="inp" placeholder="Department name" required>
          <input type="text" name="icon" class="inp" placeholder="fas fa-university">
          <input type="number" name="display_order" class="inp" placeholder="Order" value="99">
          <button type="submit" class="btn-sm"
                  style="background:linear-gradient(135deg,#7c3aed,#2563eb);color:white">
            Add Department</button>
        </form>
      </div>
    </div>

    <div class="cb">
      <div class="ch">
        <div style="font-size:.87rem;font-weight:700;color:#1e293b;
                    display:flex;align-items:center;gap:8px">
          <i class="fas fa-book" style="color:#059669"></i>
          Fields of Study
          <span style="background:#f0fdf4;color:#059669;padding:2px 8px;
                       border-radius:9px;font-size:.67rem;font-weight:700">{len(fields)}</span>
        </div>
      </div>
      <div style="max-height:260px;overflow-y:auto">
        <table class="dt">
          <thead><tr><th>Dept</th><th>Field Name</th><th>Order</th><th>Del</th></tr></thead>
          <tbody>{field_rows}</tbody>
        </table>
      </div>
      <div style="padding:14px 16px;border-top:1px solid #f1f5f9;background:#f8fafc">
        <div style="font-size:.78rem;font-weight:700;color:#1e293b;margin-bottom:10px">
          ➕ Add Field</div>
        <form method="POST" action="/admin/field/add"
              style="display:grid;grid-template-columns:1fr 1fr;gap:7px">
          <select name="department_id" class="inp" required>
            <option value="">Select Department</option>
            {dept_opts}
          </select>
          <input type="text" name="field_name" class="inp" placeholder="Field name" required>
          <input type="number" name="display_order" class="inp" placeholder="Order" value="99">
          <button type="submit" class="btn-sm"
                  style="background:linear-gradient(135deg,#059669,#0891b2);color:white">
            Add Field</button>
        </form>
      </div>
    </div>
  </div>
</div>'''

    return make_response(page('Categories', 'categories', body))


# ── Category CRUD ─────────────────────────────────────────
@admin_bp.route('/admin/categories/add', methods=['POST'])
@admin_required
def cat_add():
    n,d,ic,o = request.form.get('name','').strip(), request.form.get('description','').strip(), request.form.get('icon','fas fa-book').strip(), request.form.get('display_order',99)
    if n:
        execute_query("INSERT INTO educational_categories (name,description,icon,display_order) VALUES(%s,%s,%s,%s)",(n,d,ic,o))
    return redirect('/admin/categories')

@admin_bp.route('/admin/categories/delete/<int:cid>', methods=['POST'])
@admin_required
def cat_delete(cid):
    execute_query("DELETE FROM educational_categories WHERE id=%s",(cid,))
    return redirect('/admin/categories')

@admin_bp.route('/admin/dept/add', methods=['POST'])
@admin_required
def dept_add():
    n,ic,o = request.form.get('name','').strip(), request.form.get('icon','fas fa-university').strip(), request.form.get('display_order',99)
    if n:
        execute_query("INSERT INTO university_departments (name,icon,display_order) VALUES(%s,%s,%s)",(n,ic,o))
    return redirect('/admin/categories')

@admin_bp.route('/admin/dept/delete/<int:did>', methods=['POST'])
@admin_required
def dept_delete(did):
    execute_query("DELETE FROM university_departments WHERE id=%s",(did,))
    return redirect('/admin/categories')

@admin_bp.route('/admin/field/add', methods=['POST'])
@admin_required
def field_add():
    did,fn,o = request.form.get('department_id'), request.form.get('field_name','').strip(), request.form.get('display_order',99)
    if fn and did:
        execute_query("INSERT INTO university_fields_of_study (department_id,field_name,display_order) VALUES(%s,%s,%s)",(did,fn,o))
    return redirect('/admin/categories')

@admin_bp.route('/admin/field/delete/<int:fid>', methods=['POST'])
@admin_required
def field_delete(fid):
    execute_query("DELETE FROM university_fields_of_study WHERE id=%s",(fid,))
    return redirect('/admin/categories')


# ============================================================
# REPORTS & ANALYTICS
# ============================================================
@admin_bp.route('/admin/reports')
@admin_required
def admin_reports():
    top_students = execute_query(
        """SELECT u.full_name, u.education_category, u.field_of_interest,
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

    top_rows = ''
    for i,s in enumerate(top_students,1):
        sc   = float(s['avg_score'] or 0)
        sclr = '#059669' if sc>=70 else '#d97706' if sc>=40 else '#dc2626'
        top_rows += f'<tr><td style="color:#94a3b8">{i}</td><td style="font-weight:600">{s["full_name"]}</td><td><span style="background:#eff6ff;color:#2563eb;padding:2px 7px;border-radius:7px;font-size:.67rem">{s["education_category"] or "—"}</span></td><td style="font-size:.78rem;color:#64748b">{s["field_of_interest"] or "—"}</td><td><span style="font-weight:700;color:{sclr}">{sc}%</span></td><td style="text-align:center;color:#94a3b8">{s["qc"]}</td></tr>'
    if not top_rows:
        top_rows = '<tr><td colspan="6" style="text-align:center;padding:20px;color:#94a3b8">No data yet</td></tr>'

    weak_rows = ''
    for w in weak_agg:
        weak_rows += f'<tr><td style="font-weight:600;color:#92400e">⚠️ {w["topic"]}</td><td style="text-align:center"><span style="background:#fef2f2;color:#dc2626;padding:2px 8px;border-radius:9px;font-size:.68rem;font-weight:700">{w["tf"]} fails</span></td><td style="text-align:center;color:#94a3b8">{w["st"]} students</td></tr>'
    if not weak_rows:
        weak_rows = '<tr><td colspan="3" style="text-align:center;padding:20px;color:#94a3b8">No weak topics</td></tr>'

    chart_daily_labels = json.dumps([str(r['day']) for r in daily])
    chart_daily_quiz   = json.dumps([r['quizzes'] for r in daily])
    chart_daily_score  = json.dumps([float(r['avg_score'] or 0) for r in daily])
    chart_level_labels = json.dumps([r['skill_level'] for r in level_dist])
    chart_level_data   = json.dumps([r['cnt'] for r in level_dist])
    chart_topic_labels = json.dumps([r['topic'][:15] for r in topic_perf])
    chart_topic_scores = json.dumps([float(r['avg_score'] or 0) for r in topic_perf])

    extra = '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>'

    body = f'''
<div class="hero mb-4">
  <h3 style="font-weight:900;font-size:1.2rem;margin:0 0 3px">📈 Reports & Analytics</h3>
  <p style="color:rgba(255,255,255,.5);margin:0;font-size:.82rem">
    Detailed learning analytics and performance reports</p>
</div>

<div class="row g-4 mb-4">
  <div class="col-lg-8">
    <div class="cb">
      <div class="ch">
        <div style="font-size:.87rem;font-weight:700;color:#1e293b;
                    display:flex;align-items:center;gap:8px">
          <i class="fas fa-chart-line" style="color:#2563eb"></i>
          Daily Quiz Activity (Last 14 days)
        </div>
      </div>
      <div style="padding:16px"><div class="chart-wrap"><canvas id="dailyChart"></canvas></div></div>
    </div>
  </div>
  <div class="col-lg-4">
    <div class="cb">
      <div class="ch">
        <div style="font-size:.87rem;font-weight:700;color:#1e293b;
                    display:flex;align-items:center;gap:8px">
          <i class="fas fa-chart-pie" style="color:#7c3aed"></i>
          Level Distribution
        </div>
      </div>
      <div style="padding:16px"><div class="chart-wrap"><canvas id="levelChart"></canvas></div></div>
    </div>
  </div>
</div>

<div class="row g-4 mb-4">
  <div class="col-lg-6">
    <div class="cb">
      <div class="ch">
        <div style="font-size:.87rem;font-weight:700;color:#1e293b;
                    display:flex;align-items:center;gap:8px">
          <i class="fas fa-trophy" style="color:#d97706"></i>
          Top Performing Students
        </div>
      </div>
      <div style="overflow-x:auto">
        <table class="dt">
          <thead><tr><th>#</th><th>Student</th><th>Category</th><th>Field</th><th>Avg Score</th><th>Quizzes</th></tr></thead>
          <tbody>{top_rows}</tbody>
        </table>
      </div>
    </div>
  </div>
  <div class="col-lg-6">
    <div class="cb">
      <div class="ch">
        <div style="font-size:.87rem;font-weight:700;color:#1e293b;
                    display:flex;align-items:center;gap:8px">
          <i class="fas fa-exclamation-triangle" style="color:#d97706"></i>
          Hardest Topics (Most Fails)
        </div>
      </div>
      <div style="overflow-x:auto">
        <table class="dt">
          <thead><tr><th>Topic</th><th>Total Fails</th><th>Affected Students</th></tr></thead>
          <tbody>{weak_rows}</tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<div class="cb">
  <div class="ch">
    <div style="font-size:.87rem;font-weight:700;color:#1e293b;
                display:flex;align-items:center;gap:8px">
      <i class="fas fa-chart-bar" style="color:#059669"></i>
      Topic Average Scores (Weakest First)
    </div>
    <span style="font-size:.72rem;color:#94a3b8">Lower score = needs more help</span>
  </div>
  <div style="padding:16px"><div class="chart-wrap" style="height:200px">
    <canvas id="topicChart"></canvas>
  </div></div>
</div>

<script>
var dlabels = {chart_daily_labels};
var dquiz   = {chart_daily_quiz};
var dscore  = {chart_daily_score};
var llabels = {chart_level_labels};
var ldata   = {chart_level_data};
var tlabels = {chart_topic_labels};
var tscores = {chart_topic_scores};

new Chart(document.getElementById('dailyChart'),{{
  type:'bar',
  data:{{
    labels:dlabels.length?dlabels:['No data'],
    datasets:[
      {{label:'Quizzes',data:dquiz,backgroundColor:'rgba(37,99,235,.7)',borderRadius:4,yAxisID:'y'}},
      {{label:'Avg Score %',data:dscore,backgroundColor:'rgba(124,58,237,.7)',borderRadius:4,yAxisID:'y1',type:'line',borderColor:'#7c3aed',pointRadius:3}}
    ]
  }},
  options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{labels:{{font:{{size:11}}}}}}}},
    scales:{{
      y:{{beginAtZero:true,grid:{{color:'#f1f5f9'}},ticks:{{font:{{size:10}}}}}},
      y1:{{beginAtZero:true,max:100,position:'right',grid:{{display:false}},
           ticks:{{callback:v=>v+'%',font:{{size:10}}}}}},
      x:{{ticks:{{font:{{size:10}}}},grid:{{display:false}}}}
    }}
  }}
}});

new Chart(document.getElementById('levelChart'),{{
  type:'doughnut',
  data:{{
    labels:llabels.length?llabels:['No data'],
    datasets:[{{data:ldata,backgroundColor:['#059669','#d97706','#7c3aed'],borderWidth:2,borderColor:'white'}}]
  }},
  options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{position:'bottom',labels:{{font:{{size:11}}}}}}}}
  }}
}});

new Chart(document.getElementById('topicChart'),{{
  type:'bar',
  data:{{
    labels:tlabels.length?tlabels:['No data'],
    datasets:[{{label:'Avg Score %',data:tscores,
      backgroundColor:tscores.map(s=>s<40?'rgba(220,38,38,.75)':s<60?'rgba(217,119,6,.75)':'rgba(34,197,94,.75)'),
      borderRadius:4}}]
  }},
  options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{display:false}}}},
    scales:{{
      x:{{min:0,max:100,ticks:{{callback:v=>v+'%',font:{{size:10}}}},grid:{{color:'#f1f5f9'}}}},
      y:{{ticks:{{font:{{size:10}}}},grid:{{display:false}}}}
    }}
  }}
}});
</script>'''

    return make_response(page('Reports', 'reports', body, extra))


# ============================================================
# MOE EVALUATION (same as before — kept intact)
# ============================================================
@admin_bp.route('/admin/moe-evaluation')
@admin_required
def moe_evaluation():
    students = execute_query("SELECT id, full_name FROM users WHERE role='student'", fetch=True) or []
    user_metrics = []
    all_p, all_r, all_n, all_h, all_l = [], [], [], [], []

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
            from app.ai.moe_engine import TransformerMoE
            moe       = TransformerMoE(uid)
            recs      = moe.get_recommendations()
            rec_topics= [r['topic'].lower() for r in recs]
            weights   = moe.weights
        except Exception:
            rec_topics = []
            weights    = {'weak_topic':0.33,'performance':0.33,'history':0.34}

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
        prec    = round(hits/k,4) if k else 0
        rec_v   = round(hits/len(rel_set),4) if rel_set else 0
        dcg     = sum(1/math.log2(i+2) for i,t in enumerate(rec_k) if t in rel_set)
        idcg    = sum(1/math.log2(i+2) for i in range(_min(len(rel_set),k)))
        ndcg    = round(dcg/idcg,4) if idcg else 0
        hr      = 1 if any(t in rel_set for t in rec_k) else 0
        lir     = 0.0
        if len(shist) >= 2:
            first  = float(shist[0]['pct']  or 0)
            latest = float(shist[-1]['pct'] or 0)
            lir    = round(((latest-first)/first)*100,1) if first>0 else 0.0

        user_metrics.append({
            'name':s['full_name'],'precision':prec,'recall':rec_v,
            'ndcg':ndcg,'hit_rate':hr,'lir':lir,'weights':weights,
            'rel_count':len(relevant),'quizzes':len(perf),'watched':len(watched)
        })
        all_p.append(prec); all_r.append(rec_v); all_n.append(ndcg)
        all_h.append(hr);   all_l.append(lir)

    def avg(lst): return round(sum(lst)/len(lst),4) if lst else 0
    sp=avg(all_p); sr=avg(all_r); sn=avg(all_n); sh=avg(all_h); sl=avg(all_l)

    import random
    all_topics=['python programming','web development','machine learning','data science',
                'javascript','database sql','algorithms','flask framework']
    rpl = []
    for m in user_metrics:
        if m['rel_count']==0: continue
        rpl.append(len(random.sample(all_topics,_min(10,len(all_topics))))/10)
    rp  = avg(rpl) if rpl else 0.10
    mvr = round(((sp-rp)/max(rp,0.001))*100,1)

    topic_perf = execute_query(
        "SELECT topic, ROUND(AVG(score/total*100),1) as avg_score FROM video_quizzes WHERE attempted=1 AND total>0 GROUP BY topic ORDER BY avg_score ASC LIMIT 10",
        fetch=True
    ) or []

    score_dist = execute_query(
        """SELECT SUM(CASE WHEN score/total*100<40 THEN 1 ELSE 0 END) as vl,
             SUM(CASE WHEN score/total*100>=40 AND score/total*100<60 THEN 1 ELSE 0 END) as lo,
             SUM(CASE WHEN score/total*100>=60 AND score/total*100<75 THEN 1 ELSE 0 END) as me,
             SUM(CASE WHEN score/total*100>=75 AND score/total*100<90 THEN 1 ELSE 0 END) as hi,
             SUM(CASE WHEN score/total*100>=90 THEN 1 ELSE 0 END) as ex
           FROM video_quizzes WHERE attempted=1 AND total>0""", fetch=True
    )
    dist = score_dist[0] if score_dist else {}

    ww = avg([m['weights'].get('weak_topic',0.33)  for m in user_metrics])
    wp = avg([m['weights'].get('performance',0.33) for m in user_metrics])
    wh = avg([m['weights'].get('history',0.34)     for m in user_metrics])

    def badge(v,t1,t2):
        if v>=t1: return "<span style='background:#f0fdf4;color:#059669;padding:2px 9px;border-radius:20px;font-size:.67rem;font-weight:700'>Excellent</span>"
        if v>=t2: return "<span style='background:#fffbeb;color:#d97706;padding:2px 9px;border-radius:20px;font-size:.67rem;font-weight:700'>Good</span>"
        return "<span style='background:#fef2f2;color:#dc2626;padding:2px 9px;border-radius:20px;font-size:.67rem;font-weight:700'>Low</span>"

    user_rows = ''
    for m in user_metrics:
        pc = '#059669' if m['precision']>=.6 else '#d97706' if m['precision']>=.4 else '#dc2626'
        nc = '#059669' if m['ndcg']>=.6      else '#d97706' if m['ndcg']>=.4      else '#dc2626'
        lc = '#059669' if m['lir']>10        else '#d97706' if m['lir']>=0        else '#dc2626'
        status_badge = "<span style='color:#059669;font-weight:700'>Hit</span>" if m['hit_rate'] else "<span style='color:#dc2626'>Miss</span>"
        lir_text = ("+" + str(m['lir'])) if m['lir'] > 0 else str(m['lir'])
        user_rows += f'<tr><td><div style="display:flex;align-items:center;gap:7px"><div style="width:26px;height:26px;background:linear-gradient(135deg,#2563eb,#7c3aed);border-radius:7px;display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:.7rem">{m["name"][0].upper()}</div><span style="font-size:.79rem;font-weight:600;color:#1e293b">{m["name"]}</span></div></td><td><span style="font-weight:700;color:{pc}">{round(m["precision"]*100)}%</span></td><td><span style="font-weight:700;color:#2563eb">{round(m["recall"]*100)}%</span></td><td><span style="font-weight:700;color:{nc}">{round(m["ndcg"]*100)}%</span></td><td>{status_badge}</td><td><span style="font-weight:700;color:{lc}">{lir_text}%</span></td><td style="color:#94a3b8">{m["quizzes"]}</td><td style="color:#94a3b8">{m["watched"]}</td></tr>'
    if not user_rows:
        user_rows = '<tr><td colspan="8" style="text-align:center;padding:30px;color:#94a3b8">No quiz data yet</td></tr>'

    cu  = json.dumps([m['name'].split()[0] for m in user_metrics])
    cp  = json.dumps([round(m['precision']*100,1) for m in user_metrics])
    cn  = json.dumps([round(m['ndcg']*100,1) for m in user_metrics])
    cl  = json.dumps([m['lir'] for m in user_metrics])
    ctl = json.dumps([t['topic'][:15] for t in topic_perf])
    cts = json.dumps([float(t['avg_score'] or 0) for t in topic_perf])
    cd  = json.dumps([int(dist.get('vl') or 0),int(dist.get('lo') or 0),int(dist.get('me') or 0),int(dist.get('hi') or 0),int(dist.get('ex') or 0)])

    extra = '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>'

    body = f'''
<div class="hero mb-4">
  <h3 style="font-weight:900;font-size:1.2rem;margin:0 0 3px">🤖 MoE Evaluation</h3>
  <p style="color:rgba(255,255,255,.5);margin:0;font-size:.82rem">
    Mixture of Experts — Performance Metrics &amp; Graphs
    &nbsp;|&nbsp; <strong style="color:white">{len(user_metrics)}</strong> users evaluated</p>
</div>

<div class="row g-3 mb-4">
  <div class="col-6 col-md-3"><div class="sc s1">
    <div style="font-size:.67rem;color:#94a3b8;font-weight:600;text-transform:uppercase;margin-bottom:7px">Precision@10</div>
    <div style="font-size:1.9rem;font-weight:900;color:#0f172a;line-height:1">{round(sp*100)}%</div>
    <div style="margin-top:6px">{badge(sp,.7,.5)}</div>
  </div></div>
  <div class="col-6 col-md-3"><div class="sc s2">
    <div style="font-size:.67rem;color:#94a3b8;font-weight:600;text-transform:uppercase;margin-bottom:7px">Recall@10</div>
    <div style="font-size:1.9rem;font-weight:900;color:#0f172a;line-height:1">{round(sr*100)}%</div>
    <div style="margin-top:6px">{badge(sr,.6,.4)}</div>
  </div></div>
  <div class="col-6 col-md-3"><div class="sc s4">
    <div style="font-size:.67rem;color:#94a3b8;font-weight:600;text-transform:uppercase;margin-bottom:7px">NDCG@10</div>
    <div style="font-size:1.9rem;font-weight:900;color:#0f172a;line-height:1">{round(sn*100)}%</div>
    <div style="margin-top:6px">{badge(sn,.7,.5)}</div>
  </div></div>
  <div class="col-6 col-md-3"><div class="sc s3">
    <div style="font-size:.67rem;color:#94a3b8;font-weight:600;text-transform:uppercase;margin-bottom:7px">Hit Rate</div>
    <div style="font-size:1.9rem;font-weight:900;color:#0f172a;line-height:1">{round(sh*100)}%</div>
    <div style="margin-top:6px">{badge(sh,.8,.6)}</div>
  </div></div>
  <div class="col-6 col-md-3"><div class="sc s2">
    <div style="font-size:.67rem;color:#94a3b8;font-weight:600;text-transform:uppercase;margin-bottom:7px">LIR</div>
    <div style="font-size:1.9rem;font-weight:900;color:#0f172a;line-height:1">{("+"+str(sl)) if sl>0 else str(sl)}%</div>
    <div style="margin-top:6px">{"<span style='background:#f0fdf4;color:#059669;padding:2px 9px;border-radius:20px;font-size:.67rem;font-weight:700'>Improving</span>" if sl>0 else "<span style='background:#fef2f2;color:#dc2626;padding:2px 9px;border-radius:20px;font-size:.67rem;font-weight:700'>Need Data</span>"}</div>
  </div></div>
  <div class="col-6 col-md-3"><div class="sc s1">
    <div style="font-size:.67rem;color:#94a3b8;font-weight:600;text-transform:uppercase;margin-bottom:7px">MoE vs Random</div>
    <div style="font-size:1.9rem;font-weight:900;color:#0f172a;line-height:1">{("+"+str(mvr)) if mvr>0 else str(mvr)}%</div>
    <div style="margin-top:6px">{"<span style='background:#f0fdf4;color:#059669;padding:2px 9px;border-radius:20px;font-size:.67rem;font-weight:700'>Better</span>" if mvr>0 else "<span style='background:#fef2f2;color:#dc2626;padding:2px 9px;border-radius:20px;font-size:.67rem;font-weight:700'>Below</span>"}</div>
  </div></div>
  <div class="col-6 col-md-3"><div class="sc s5">
    <div style="font-size:.67rem;color:#94a3b8;font-weight:600;text-transform:uppercase;margin-bottom:7px">Expert 1 Weight</div>
    <div style="font-size:1.9rem;font-weight:900;color:#0f172a;line-height:1">{round(ww*100)}%</div>
    <div style="margin-top:6px"><span style="background:#fef2f2;color:#dc2626;padding:2px 9px;border-radius:20px;font-size:.67rem;font-weight:700">Weak Topics</span></div>
  </div></div>
  <div class="col-6 col-md-3"><div class="sc s2">
    <div style="font-size:.67rem;color:#94a3b8;font-weight:600;text-transform:uppercase;margin-bottom:7px">Expert 2 Weight</div>
    <div style="font-size:1.9rem;font-weight:900;color:#0f172a;line-height:1">{round(wp*100)}%</div>
    <div style="margin-top:6px"><span style="background:#f0fdf4;color:#059669;padding:2px 9px;border-radius:20px;font-size:.67rem;font-weight:700">Performance</span></div>
  </div></div>
</div>

<div class="row g-4 mb-4">
  <div class="col-lg-7">
    <div class="cb">
      <div class="ch"><div style="font-size:.87rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px"><i class="fas fa-chart-bar" style="color:#2563eb"></i> Precision &amp; NDCG per User</div></div>
      <div style="padding:16px"><div class="chart-wrap"><canvas id="pnChart"></canvas></div></div>
    </div>
  </div>
  <div class="col-lg-5">
    <div class="cb">
      <div class="ch"><div style="font-size:.87rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px"><i class="fas fa-chart-pie" style="color:#7c3aed"></i> Score Distribution</div></div>
      <div style="padding:16px"><div class="chart-wrap"><canvas id="distChart"></canvas></div></div>
    </div>
  </div>
</div>

<div class="row g-4 mb-4">
  <div class="col-lg-6">
    <div class="cb">
      <div class="ch"><div style="font-size:.87rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px"><i class="fas fa-exclamation-triangle" style="color:#d97706"></i> Topic Scores (Weakest First)</div></div>
      <div style="padding:16px"><div class="chart-wrap"><canvas id="tChart"></canvas></div></div>
    </div>
  </div>
  <div class="col-lg-6">
    <div class="cb">
      <div class="ch"><div style="font-size:.87rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px"><i class="fas fa-chart-line" style="color:#059669"></i> LIR per User</div></div>
      <div style="padding:16px"><div class="chart-wrap"><canvas id="lirChart"></canvas></div></div>
    </div>
  </div>
</div>

<div class="row g-4 mb-4">
  <div class="col-lg-6">
    <div class="cb">
      <div class="ch"><div style="font-size:.87rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px"><i class="fas fa-sliders" style="color:#7c3aed"></i> Expert Attention Weights</div></div>
      <div style="padding:16px">
        {''.join([
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px"><div style="font-size:.78rem;font-weight:600;color:#1e293b;width:130px;flex-shrink:0">{lbl}</div><div style="flex:1;height:10px;background:#f1f5f9;border-radius:5px;overflow:hidden"><div style="width:{round(val*100)}%;height:100%;background:{clr};border-radius:5px"></div></div><div style="font-size:.75rem;font-weight:700;color:{clr};width:38px;text-align:right">{round(val*100)}%</div></div>'
            for lbl,val,clr in [("Expert 1 — Weak",ww,"#dc2626"),("Expert 2 — Perf",wp,"#059669"),("Expert 3 — Pref",wh,"#7c3aed")]
        ])}
        <div style="background:#f8fafc;border-radius:10px;padding:13px;margin-top:8px;border:1px solid #f1f5f9">
          <div style="font-size:.74rem;font-weight:700;color:#1e293b;margin-bottom:8px">vs Random Baseline</div>
          <div style="display:flex;gap:14px">
            <div><div style="font-size:1.3rem;font-weight:900;color:#2563eb">{round(sp*100)}%</div><div style="font-size:.64rem;color:#94a3b8">MoE</div></div>
            <div><div style="font-size:1.3rem;font-weight:900;color:#94a3b8">{round(rp*100)}%</div><div style="font-size:.64rem;color:#94a3b8">Random</div></div>
            <div><div style="font-size:1.3rem;font-weight:900;color:{'#059669' if mvr>0 else '#dc2626'}">{("+"+str(mvr)) if mvr>0 else str(mvr)}%</div><div style="font-size:.64rem;color:#94a3b8">Improvement</div></div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div class="col-lg-6">
    <div class="cb">
      <div class="ch"><div style="font-size:.87rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px"><i class="fas fa-circle-nodes" style="color:#7c3aed"></i> System Radar</div></div>
      <div style="padding:16px"><div class="chart-wrap"><canvas id="radarChart"></canvas></div></div>
    </div>
  </div>
</div>

<div class="cb">
  <div class="ch"><div style="font-size:.87rem;font-weight:700;color:#1e293b;display:flex;align-items:center;gap:8px"><i class="fas fa-table" style="color:#2563eb"></i> Per-User Breakdown</div></div>
  <div style="overflow-x:auto">
    <table class="dt">
      <thead><tr><th>User</th><th>Precision@10</th><th>Recall@10</th><th>NDCG@10</th><th>Hit Rate</th><th>LIR</th><th>Quizzes</th><th>Watched</th></tr></thead>
      <tbody>{user_rows}</tbody>
    </table>
  </div>
</div>

<script>
var cu={cu}; var cp={cp}; var cn={cn}; var cl={cl};
var ctl={ctl}; var cts={cts}; var cd={cd};
var sp={round(sp*100,1)}; var sr={round(sr*100,1)};
var sn={round(sn*100,1)}; var sh={round(sh*100,1)};
var sl=Math.max(0,{round(_min(_abs(sl)/50*100,100),1)});
var smvr=Math.max(0,{round(_min(_abs(mvr)/100*100,100),1)});

new Chart(document.getElementById('pnChart'),{{type:'bar',data:{{labels:cu.length?cu:['No data'],datasets:[{{label:'Precision@10 (%)',data:cp,backgroundColor:'rgba(37,99,235,.75)',borderRadius:4}},{{label:'NDCG@10 (%)',data:cn,backgroundColor:'rgba(124,58,237,.75)',borderRadius:4}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{font:{{size:11}}}}}}}},scales:{{y:{{min:0,max:100,ticks:{{callback:v=>v+'%',font:{{size:10}}}},grid:{{color:'#f1f5f9'}}}},x:{{ticks:{{font:{{size:10}}}},grid:{{display:false}}}}}}}}}});
new Chart(document.getElementById('distChart'),{{type:'doughnut',data:{{labels:['<40%','40-60%','60-75%','75-90%','90%+'],datasets:[{{data:cd,backgroundColor:['#ef4444','#f97316','#eab308','#22c55e','#3b82f6'],borderWidth:2,borderColor:'white'}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'right',labels:{{font:{{size:10}},padding:8}}}}}}}}}});
new Chart(document.getElementById('tChart'),{{type:'bar',data:{{labels:ctl.length?ctl:['No data'],datasets:[{{label:'Avg Score',data:cts,backgroundColor:cts.map(s=>s<40?'rgba(220,38,38,.75)':s<60?'rgba(217,119,6,.75)':'rgba(34,197,94,.75)'),borderRadius:4}}]}},options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{min:0,max:100,ticks:{{callback:v=>v+'%',font:{{size:10}}}},grid:{{color:'#f1f5f9'}}}},y:{{ticks:{{font:{{size:10}}}},grid:{{display:false}}}}}}}}}});
new Chart(document.getElementById('lirChart'),{{type:'bar',data:{{labels:cu.length?cu:['No data'],datasets:[{{label:'LIR (%)',data:cl,backgroundColor:cl.map(l=>l>20?'rgba(34,197,94,.75)':l>0?'rgba(234,179,8,.75)':'rgba(220,38,38,.75)'),borderRadius:4}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{y:{{ticks:{{callback:v=>v+'%',font:{{size:10}}}},grid:{{color:'#f1f5f9'}}}},x:{{ticks:{{font:{{size:10}}}},grid:{{display:false}}}}}}}}}});
new Chart(document.getElementById('radarChart'),{{type:'radar',data:{{labels:['Precision','Recall','NDCG','Hit Rate','LIR','MoE Gain'],datasets:[{{label:'MoE',data:[sp,sr,sn,sh,sl,smvr],backgroundColor:'rgba(124,58,237,.15)',borderColor:'#7c3aed',pointBackgroundColor:'#7c3aed',pointRadius:4,borderWidth:2}},{{label:'Baseline',data:[{round(rp*100,1)},0,0,0,0,0],backgroundColor:'rgba(148,163,184,.1)',borderColor:'#94a3b8',pointBackgroundColor:'#94a3b8',pointRadius:3,borderWidth:1.5}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{font:{{size:10}}}}}}}},scales:{{r:{{min:0,max:100,ticks:{{stepSize:20,font:{{size:9}}}},grid:{{color:'#e2e8f0'}},pointLabels:{{font:{{size:10}}}}}}}}}}}});
</script>'''

    return make_response(page('MoE Evaluation', 'moe', body, extra))