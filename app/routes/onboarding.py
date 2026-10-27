# ============================================================
# onboarding.py — FINAL FIXED VERSION
# Database-Driven: educational_categories, university_departments,
#                  university_fields_of_study
# ============================================================

from flask import (Blueprint, render_template, request,
                   redirect, url_for, session, jsonify)
from app.utils.auth_helpers import login_required
from app.utils.db import execute_query

onboarding_bp = Blueprint('onboarding', __name__)

# ── Static class data for non-university categories ───────
CATEGORY_CLASSES = {
    'Primary': [
        {'id': 'class_1', 'label': 'Class 1', 'emoji': '⭐', 'color': '#059669',
         'topics': ['English Basics', 'Urdu Basics', 'Maths Class 1', 'General Knowledge']},
        {'id': 'class_2', 'label': 'Class 2', 'emoji': '⭐', 'color': '#059669',
         'topics': ['English Class 2', 'Urdu Class 2', 'Maths Class 2', 'Science Class 2']},
        {'id': 'class_3', 'label': 'Class 3', 'emoji': '⭐', 'color': '#0891b2',
         'topics': ['English Class 3', 'Urdu Class 3', 'Maths Class 3', 'Science Class 3']},
        {'id': 'class_4', 'label': 'Class 4', 'emoji': '⭐', 'color': '#0891b2',
         'topics': ['English Class 4', 'Urdu Class 4', 'Maths Class 4', 'Social Studies']},
        {'id': 'class_5', 'label': 'Class 5', 'emoji': '⭐', 'color': '#7c3aed',
         'topics': ['English Class 5', 'Urdu Class 5', 'Maths Class 5', 'Science Class 5', 'Islamiat']},
    ],
    'Secondary': [
        {'id': 'class_6', 'label': 'Class 6', 'emoji': '📗', 'color': '#0891b2',
         'topics': ['English Class 6', 'Urdu Class 6', 'Mathematics Class 6', 'General Science', 'Islamiat']},
        {'id': 'class_7', 'label': 'Class 7', 'emoji': '📗', 'color': '#0891b2',
         'topics': ['English Class 7', 'Urdu Class 7', 'Mathematics Class 7', 'General Science', 'History']},
        {'id': 'class_8', 'label': 'Class 8', 'emoji': '📗', 'color': '#7c3aed',
         'topics': ['English Class 8', 'Urdu Class 8', 'Mathematics Class 8', 'Science Class 8', 'Pakistan Studies']},
    ],
    'Matriculation': [
        {'id': 'c9_sci',  'label': 'Class 9 — Science',  'emoji': '🔬', 'color': '#7c3aed',
         'topics': ['Physics Class 9', 'Chemistry Class 9', 'Biology Class 9', 'Mathematics Class 9', 'English Class 9']},
        {'id': 'c10_sci', 'label': 'Class 10 — Science', 'emoji': '🔬', 'color': '#7c3aed',
         'topics': ['Physics Class 10', 'Chemistry Class 10', 'Biology Class 10', 'Mathematics Class 10', 'English Class 10']},
        {'id': 'c9_arts', 'label': 'Class 9 — Arts',    'emoji': '🎨', 'color': '#d97706',
         'topics': ['General Math Class 9', 'Urdu Class 9', 'English Class 9', 'Pakistan Studies', 'Islamiat']},
        {'id': 'c10_arts','label': 'Class 10 — Arts',   'emoji': '🎨', 'color': '#d97706',
         'topics': ['General Math Class 10', 'Urdu Class 10', 'English Class 10', 'Pakistan Studies', 'Civics']},
        {'id': 'c9_com',  'label': 'Class 9 — Commerce','emoji': '💼', 'color': '#059669',
         'topics': ['Principles of Accounting', 'Commercial Geography', 'Urdu', 'English', 'Pakistan Studies']},
        {'id': 'c10_com', 'label': 'Class 10 — Commerce','emoji': '💼', 'color': '#059669',
         'topics': ['Principles of Accounting', 'Principles of Commerce', 'Urdu', 'English', 'Pakistan Studies']},
    ],
    'Intermediate': [
        {'id': 'pre_med', 'label': 'Pre-Medical (FSc)',      'emoji': '🏥', 'color': '#dc2626',
         'topics': ['Biology FSc', 'Chemistry FSc', 'Physics FSc', 'English FSc', 'Urdu FSc']},
        {'id': 'pre_eng', 'label': 'Pre-Engineering (FSc)',  'emoji': '⚙️', 'color': '#7c3aed',
         'topics': ['Mathematics FSc', 'Physics FSc', 'Chemistry FSc', 'English FSc', 'Urdu FSc']},
        {'id': 'ics',     'label': 'ICS — Computer Science', 'emoji': '💻', 'color': '#2563eb',
         'topics': ['Computer Science ICS', 'Mathematics ICS', 'Physics ICS', 'English ICS']},
        {'id': 'icom',    'label': 'ICom — Commerce',        'emoji': '💹', 'color': '#059669',
         'topics': ['Accounting ICom', 'Business Mathematics', 'Economics', 'English ICom']},
        {'id': 'fa',      'label': 'FA — Arts',              'emoji': '📜', 'color': '#d97706',
         'topics': ['Urdu FA', 'English FA', 'Islamic Studies', 'History', 'Civics']},
    ],
    'Professional': [
        {'id': 'css_pms',  'label': 'CSS / PMS',    'emoji': '🏛️', 'color': '#4f46e5',
         'topics': ['Pakistan Affairs', 'Current Affairs', 'Islamiat', 'English Essay', 'General Knowledge']},
        {'id': 'mdcat',    'label': 'MDCAT',         'emoji': '🩺', 'color': '#dc2626',
         'topics': ['Biology MDCAT', 'Chemistry MDCAT', 'Physics MDCAT', 'English MDCAT']},
        {'id': 'ecat',     'label': 'ECAT',          'emoji': '📐', 'color': '#7c3aed',
         'topics': ['Mathematics ECAT', 'Physics ECAT', 'Chemistry ECAT']},
        {'id': 'nts_gat',  'label': 'NTS / GAT',    'emoji': '📋', 'color': '#2563eb',
         'topics': ['Verbal Reasoning', 'Quantitative Reasoning', 'Analytical Reasoning']},
        {'id': 'ielts',    'label': 'IELTS / TOEFL', 'emoji': '🌍', 'color': '#0891b2',
         'topics': ['IELTS Reading', 'IELTS Writing', 'IELTS Listening', 'IELTS Speaking']},
        {'id': 'ppsc_fpsc','label': 'PPSC / FPSC',  'emoji': '🏢', 'color': '#d97706',
         'topics': ['General Knowledge', 'Pakistan Studies', 'Islamic Studies', 'Current Affairs']},
    ],
}

LEVELS = [
    {'id': 'Beginner',     'label': 'Beginner',     'emoji': '🌱', 'color': '#059669',
     'desc': 'New to this, need basics explained'},
    {'id': 'Intermediate', 'label': 'Intermediate', 'emoji': '🔥', 'color': '#d97706',
     'desc': 'Know some basics, want to go deeper'},
    {'id': 'Advanced',     'label': 'Advanced',     'emoji': '🚀', 'color': '#7c3aed',
     'desc': 'Strong foundation, need advanced content'},
]


# ── Load categories from DB ───────────────────────────────
def get_categories():
    rows = execute_query(
        "SELECT id, name, description, icon FROM educational_categories ORDER BY display_order",
        fetch=True
    ) or []
    emoji_map = {
        'Primary': '📚', 'Secondary': '🏫', 'Matriculation': '📖',
        'Intermediate': '🎓', 'University': '🏛️', 'Professional': '🏆'
    }
    color_map = {
        'Primary': '#059669', 'Secondary': '#0891b2', 'Matriculation': '#7c3aed',
        'Intermediate': '#d97706', 'University': '#2563eb', 'Professional': '#dc2626'
    }
    result = []
    for r in rows:
        name = r['name']
        result.append({
            'id'   : r['id'],
            'name' : name,
            'desc' : r['description'] or '',
            'icon' : r['icon'] or 'fas fa-book',
            'emoji': emoji_map.get(name, '📚'),
            'color': color_map.get(name, '#2563eb'),
        })
    return result


# ── Load university departments ───────────────────────────
def get_departments():
    rows = execute_query(
        "SELECT id, name, icon FROM university_departments ORDER BY display_order",
        fetch=True
    ) or []
    return [{'id': r['id'], 'name': r['name'], 'icon': r.get('icon', '')} for r in rows]


# ── Load fields for a department ─────────────────────────
def get_fields(dept_id):
    rows = execute_query(
        "SELECT MIN(id) as id, field_name FROM university_fields_of_study WHERE department_id=%s GROUP BY field_name ORDER BY MIN(display_order), MIN(id)",
        (dept_id,), fetch=True
    ) or []
    return [{'id': r['id'], 'field_name': r['field_name']} for r in rows]


# ============================================================
# ONBOARDING PAGE
# ============================================================
@onboarding_bp.route('/onboarding/preferences', methods=['GET'])
@login_required
def preferences():
    if session.get('onboarding_done'):
        return redirect(url_for('dashboard.index'))

    categories  = get_categories()
    departments = get_departments()

    # University category ID from DB
    uni_cat_id = next((c['id'] for c in categories if c['name'] == 'University'), 5)

    return render_template(
        'onboarding.html',
        categories       = categories,
        category_classes = CATEGORY_CLASSES,
        departments      = departments,
        levels           = LEVELS,
        uni_cat_id       = uni_cat_id,
        user_name        = session.get('user_name', ''),
    )


# ============================================================
# GET FIELDS FOR DEPARTMENT (AJAX)
# ============================================================
@onboarding_bp.route('/onboarding/get-fields/<int:dept_id>')
@login_required
def get_fields_ajax(dept_id):
    fields = get_fields(dept_id)
    return jsonify({'success': True, 'fields': fields})


# ============================================================
# SAVE PREFERENCES
# ============================================================
@onboarding_bp.route('/onboarding/save', methods=['POST'])
@login_required
def save_preferences():
    data        = request.get_json()
    user_id     = session['user_id']

    cat_id      = data.get('category_id')
    cat_name    = data.get('category_name', '')
    class_id    = data.get('class_id', '')
    class_label = data.get('class_label', '')
    dept_id     = data.get('dept_id')
    dept_name   = data.get('dept_name', '')
    field_id    = data.get('field_id')
    field_name  = data.get('field_name', '')
    level       = data.get('level', 'Beginner')

    if not cat_id:
        return jsonify({'success': False, 'message': 'Category required'})

    # Field of interest
    if cat_name == 'University':
        field_of_interest = field_name or dept_name
        topics = []
    else:
        field_of_interest = class_label
        topics = []
        for c in CATEGORY_CLASSES.get(cat_name, []):
            if c['id'] == class_id:
                topics = c.get('topics', [])
                break

    diff_map   = {'Beginner': 'Easy', 'Intermediate': 'Medium', 'Advanced': 'Hard'}
    difficulty = diff_map.get(level, 'Easy')

    # Save (execute_query returns False on failure instead of raising)
    saved = execute_query(
        """UPDATE users
           SET education_category       = %s,
               educational_category_id  = %s,
               field_of_interest        = %s,
               skill_level              = %s,
               difficulty_level         = %s,
               department               = %s,
               university_department_id = %s,
               university_field_id      = %s,
               onboarding_done          = 1
           WHERE id = %s""",
        (cat_name, cat_id, field_of_interest, level, difficulty,
         dept_name or None, dept_id or None, field_id or None, user_id)
    )
    if saved is False:
        # Fallback without new columns
        execute_query(
            """UPDATE users
               SET field_of_interest = %s,
                   skill_level       = %s,
                   difficulty_level  = %s,
                   onboarding_done   = 1
               WHERE id = %s""",
            (field_of_interest, level, difficulty, user_id)
        )

    # Seed topic_difficulty
    for topic in topics:
        execute_query(
            """INSERT INTO topic_difficulty
               (user_id, topic, difficulty_level, last_score, attempts)
               VALUES (%s,%s,%s,0,0)
               ON DUPLICATE KEY UPDATE difficulty_level=VALUES(difficulty_level)""",
            (user_id, topic, difficulty)
        )

    session['onboarding_done']    = 1
    session['education_category'] = cat_name
    session['field_of_interest']  = field_of_interest
    session['skill_level']        = level

    return jsonify({'success': True, 'redirect_url': '/dashboard'})


# ============================================================
# SKIP
# ============================================================
@onboarding_bp.route('/onboarding/skip', methods=['POST'])
@login_required
def skip():
    execute_query("UPDATE users SET onboarding_done=1 WHERE id=%s", (session['user_id'],))
    session['onboarding_done'] = 1
    return jsonify({'success': True, 'redirect_url': '/dashboard'})


# ── Helper for recommend.py ───────────────────────────────
def get_field_queries(field_label, skill_level):
    suffix = {'Beginner': 'beginners tutorial', 'Intermediate': 'intermediate',
               'Advanced': 'advanced'}.get(skill_level, 'tutorial')
    return [f"{field_label} {suffix}", f"{field_label} lecture", f"{field_label} course"]