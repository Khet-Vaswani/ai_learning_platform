# ============================================================
# onboarding.py — User Preferences & Onboarding
# ============================================================

from flask import (Blueprint, render_template, request,
                   redirect, url_for, session, jsonify)
from app.utils.auth_helpers import login_required
from app.utils.db import execute_query

onboarding_bp = Blueprint('onboarding', __name__)

# ── Fields (General — not IT only) ───────────────────────
FIELDS = [
    # Technology
    {'id': 'computer_science',  'label': 'Computer Science',
     'icon': 'fas fa-laptop-code', 'color': '#2563eb',
     'topics': ['Python Programming', 'Algorithms', 'Data Structures', 'Web Development']},
    {'id': 'data_science',      'label': 'Data Science & AI',
     'icon': 'fas fa-brain',       'color': '#7c3aed',
     'topics': ['Machine Learning', 'Data Analysis', 'Deep Learning', 'Statistics']},
    {'id': 'web_development',   'label': 'Web Development',
     'icon': 'fas fa-globe',       'color': '#0891b2',
     'topics': ['HTML CSS', 'JavaScript', 'React', 'Flask Framework']},
    {'id': 'cybersecurity',     'label': 'Cybersecurity',
     'icon': 'fas fa-shield-alt',  'color': '#dc2626',
     'topics': ['Network Security', 'Ethical Hacking', 'Cryptography']},
    {'id': 'mobile_dev',        'label': 'Mobile Development',
     'icon': 'fas fa-mobile-alt',  'color': '#d97706',
     'topics': ['React Native', 'Flutter', 'Android', 'iOS']},

    # Business
    {'id': 'business_admin',    'label': 'BBA / Business Admin',
     'icon': 'fas fa-briefcase',   'color': '#b45309',
     'topics': ['Business Analysis', 'Management', 'Marketing', 'Finance']},
    {'id': 'accounting',        'label': 'Accounting & Finance',
     'icon': 'fas fa-calculator',  'color': '#059669',
     'topics': ['Financial Accounting', 'Taxation', 'Auditing', 'Managerial Accounting']},
    {'id': 'marketing',         'label': 'Marketing & Sales',
     'icon': 'fas fa-bullhorn',    'color': '#d97706',
     'topics': ['Digital Marketing', 'Brand Management', 'Sales Strategy', 'Market Research']},
    {'id': 'hr_management',     'label': 'Human Resources',
     'icon': 'fas fa-users',       'color': '#7c3aed',
     'topics': ['HR Management', 'Recruitment', 'Employee Relations', 'Training']},

    # Law
    {'id': 'law',               'label': 'Law & Legal Studies',
     'icon': 'fas fa-gavel',       'color': '#dc2626',
     'topics': ['Constitutional Law', 'Criminal Law', 'Contract Law', 'International Law']},
    {'id': 'criminal_justice',  'label': 'Criminal Justice',
     'icon': 'fas fa-balance-scale','color': '#2563eb',
     'topics': ['Criminal Justice', 'Forensic Science', 'Law Enforcement']},

    # CSS / Competitive Exams
    {'id': 'css_exam',          'label': 'CSS / PMS Exam Prep',
     'icon': 'fas fa-landmark',    'color': '#4f46e5',
     'topics': ['Pakistan Affairs', 'Islamic Studies', 'Current Affairs', 'Essay Writing',
                'General Knowledge', 'English Composition']},
    {'id': 'political_science', 'label': 'Political Science',
     'icon': 'fas fa-vote-yea',    'color': '#4f46e5',
     'topics': ['Political Theory', 'International Relations', 'Public Policy', 'Comparative Politics']},

    # Social Sciences
    {'id': 'psychology',        'label': 'Psychology',
     'icon': 'fas fa-brain',       'color': '#ec4899',
     'topics': ['Clinical Psychology', 'Cognitive Psychology', 'Developmental Psychology']},
    {'id': 'sociology',         'label': 'Sociology',
     'icon': 'fas fa-users-cog',   'color': '#0891b2',
     'topics': ['Social Theory', 'Criminology', 'Urban Sociology', 'Social Research']},
    {'id': 'economics',         'label': 'Economics',
     'icon': 'fas fa-chart-line',  'color': '#059669',
     'topics': ['Microeconomics', 'Macroeconomics', 'International Economics', 'Development Economics']},

    # Science & Engineering
    {'id': 'engineering',       'label': 'Engineering',
     'icon': 'fas fa-cogs',        'color': '#d97706',
     'topics': ['Mechanical Engineering', 'Electrical Engineering', 'Civil Engineering']},
    {'id': 'mathematics',       'label': 'Mathematics',
     'icon': 'fas fa-square-root-alt','color': '#4f46e5',
     'topics': ['Calculus', 'Linear Algebra', 'Statistics', 'Discrete Mathematics']},
    {'id': 'physics',           'label': 'Physics',
     'icon': 'fas fa-atom',        'color': '#7c3aed',
     'topics': ['Classical Physics', 'Quantum Physics', 'Thermodynamics']},
    {'id': 'chemistry',         'label': 'Chemistry',
     'icon': 'fas fa-flask',       'color': '#dc2626',
     'topics': ['Organic Chemistry', 'Inorganic Chemistry', 'Physical Chemistry']},
    {'id': 'biology',           'label': 'Biology',
     'icon': 'fas fa-dna',         'color': '#059669',
     'topics': ['Molecular Biology', 'Genetics', 'Ecology', 'Microbiology']},

    # Health & Medicine
    {'id': 'medicine',          'label': 'Medicine & Healthcare',
     'icon': 'fas fa-stethoscope', 'color': '#dc2626',
     'topics': ['Anatomy', 'Physiology', 'Pharmacology', 'Clinical Medicine']},
    {'id': 'nursing',           'label': 'Nursing',
     'icon': 'fas fa-user-md',     'color': '#ec4899',
     'topics': ['Nursing Fundamentals', 'Medical-Surgical Nursing', 'Pediatric Nursing']},
    {'id': 'pharmacy',          'label': 'Pharmacy',
     'icon': 'fas fa-pills',       'color': '#0891b2',
     'topics': ['Pharmaceutical Chemistry', 'Pharmacology', 'Clinical Pharmacy']},

    # Arts & Humanities
    {'id': 'english_literature','label': 'English Literature',
     'icon': 'fas fa-book',        'color': '#b45309',
     'topics': ['American Literature', 'British Literature', 'World Literature', 'Literary Theory']},
    {'id': 'history',           'label': 'History',
     'icon': 'fas fa-history',     'color': '#4f46e5',
     'topics': ['World History', 'Pakistani History', 'European History', 'Asian History']},
    {'id': 'philosophy',        'label': 'Philosophy',
     'icon': 'fas fa-brain',       'color': '#7c3aed',
     'topics': ['Western Philosophy', 'Eastern Philosophy', 'Ethics', 'Logic']},
    {'id': 'art_design',        'label': 'Art & Design',
     'icon': 'fas fa-palette',     'color': '#ec4899',
     'topics': ['Visual Arts', 'Graphic Design', 'Art History', 'Digital Art']},

    # Education & Media
    {'id': 'education',         'label': 'Education',
     'icon': 'fas fa-graduation-cap','color': '#0891b2',
     'topics': ['Educational Psychology', 'Curriculum Development', 'Teaching Methods']},
    {'id': 'journalism',        'label': 'Journalism & Media',
     'icon': 'fas fa-newspaper',   'color': '#d97706',
     'topics': ['News Writing', 'Broadcast Journalism', 'Digital Media', 'Media Ethics']},
    {'id': 'hospitality',       'label': 'Hospitality & Tourism',
     'icon': 'fas fa-concierge-bell','color': '#b45309',
     'topics': ['Hotel Management', 'Tourism Management', 'Event Planning']},
]

LEVELS = [
    {'id': 'Beginner',     'label': 'Beginner',
     'desc': 'Bilkul naya hoon, basics seekhna chahta hoon',
     'icon': 'fas fa-seedling', 'color': '#059669'},
    {'id': 'Intermediate', 'label': 'Intermediate',
     'desc': 'Kuch basics pata hai, aur deep jana chahta hoon',
     'icon': 'fas fa-fire',    'color': '#d97706'},
    {'id': 'Advanced',     'label': 'Advanced',
     'desc': 'Achha knowledge hai, advanced topics chahiye',
     'icon': 'fas fa-rocket',  'color': '#7c3aed'},
]

# ── Field → YouTube query map ─────────────────────────────
FIELD_QUERY_MAP = {
    'Computer Science'      : ['python programming tutorial', 'data structures algorithms', 'computer science fundamentals'],
    'Data Science & AI'     : ['machine learning tutorial beginners', 'data science python', 'deep learning course'],
    'Web Development'       : ['html css javascript tutorial', 'web development beginners', 'responsive web design'],
    'Cybersecurity'         : ['cybersecurity tutorial beginners', 'ethical hacking course', 'network security'],
    'Mobile Development'    : ['flutter tutorial beginners', 'react native course', 'android development'],
    'BBA / Business Admin'  : ['business management tutorial', 'business administration course', 'MBA concepts'],
    'Accounting & Finance'  : ['financial accounting tutorial', 'accounting basics', 'finance course beginners'],
    'Marketing & Sales'     : ['digital marketing tutorial', 'marketing strategy course', 'social media marketing'],
    'Human Resources'       : ['hr management course', 'human resources basics', 'recruitment training'],
    'Law & Legal Studies'   : ['law basics tutorial', 'legal studies beginners', 'constitutional law lecture'],
    'Criminal Justice'      : ['criminal justice system', 'forensic science course', 'criminology lecture'],
    'CSS / PMS Exam Prep'   : ['CSS exam preparation', 'Pakistan current affairs', 'general knowledge Pakistan'],
    'Political Science'     : ['political science lecture', 'international relations tutorial', 'political theory'],
    'Psychology'            : ['psychology basics tutorial', 'introduction to psychology', 'cognitive psychology'],
    'Sociology'             : ['sociology introduction', 'social theory lecture', 'criminology basics'],
    'Economics'             : ['economics basics tutorial', 'microeconomics course', 'macroeconomics lecture'],
    'Engineering'           : ['engineering basics tutorial', 'mechanical engineering', 'electrical engineering basics'],
    'Mathematics'           : ['calculus tutorial beginners', 'linear algebra course', 'statistics tutorial'],
    'Physics'               : ['physics basics tutorial', 'classical mechanics', 'quantum physics introduction'],
    'Chemistry'             : ['chemistry basics tutorial', 'organic chemistry', 'chemistry for beginners'],
    'Biology'               : ['biology basics tutorial', 'cell biology lecture', 'genetics introduction'],
    'Medicine & Healthcare' : ['anatomy basics tutorial', 'physiology lecture', 'medical studies basics'],
    'Nursing'               : ['nursing fundamentals', 'nursing basics tutorial', 'clinical nursing'],
    'Pharmacy'              : ['pharmacology tutorial', 'pharmacy basics', 'clinical pharmacy lecture'],
    'English Literature'    : ['english literature analysis', 'literary theory basics', 'poetry analysis'],
    'History'               : ['world history lecture', 'history documentary', 'pakistan history'],
    'Philosophy'            : ['philosophy basics tutorial', 'introduction to philosophy', 'ethics lecture'],
    'Art & Design'          : ['graphic design tutorial', 'digital art basics', 'design principles'],
    'Education'             : ['educational psychology', 'teaching methods tutorial', 'curriculum development'],
    'Journalism & Media'    : ['journalism basics', 'media ethics tutorial', 'digital journalism'],
    'Hospitality & Tourism' : ['hotel management course', 'tourism management basics', 'hospitality industry'],
}


# ============================================================
# SHOW PREFERENCES PAGE
# ============================================================
@onboarding_bp.route('/onboarding/preferences', methods=['GET'])
@login_required
def preferences():
    if session.get('onboarding_done'):
        return redirect(url_for('dashboard.index'))
    return render_template('onboarding.html',
                           fields=FIELDS,
                           levels=LEVELS,
                           user_name=session.get('user_name', ''))


# ============================================================
# SAVE PREFERENCES
# ============================================================
@onboarding_bp.route('/onboarding/save', methods=['POST'])
@login_required
def save_preferences():
    data        = request.get_json()
    user_id     = session['user_id']

    # Support both old and new key names
    field_id    = data.get('field') or data.get('field_of_interest', '')
    skill_level = data.get('level') or data.get('skill_level', 'Beginner')

    if not field_id:
        return jsonify({'success': False, 'message': 'Field required'})

    # Find field label + topics
    field_label  = field_id
    field_topics = []
    for f in FIELDS:
        if f['id'] == field_id:
            field_label  = f['label']
            field_topics = f['topics']
            break

    # Difficulty map
    diff_map = {
        'Beginner'    : 'Easy',
        'Intermediate': 'Medium',
        'Advanced'    : 'Hard'
    }
    difficulty = diff_map.get(skill_level, 'Easy')

    # Save to users table
    execute_query(
        """UPDATE users
           SET field_of_interest = %s,
               skill_level       = %s,
               difficulty_level  = %s,
               onboarding_done   = 1
           WHERE id = %s""",
        (field_label, skill_level, difficulty, user_id)
    )

    # Seed topic_difficulty (NOT weak_topics)
    for topic in field_topics:
        execute_query(
            """INSERT INTO topic_difficulty
               (user_id, topic, difficulty_level, last_score, attempts)
               VALUES (%s, %s, %s, 0, 0)
               ON DUPLICATE KEY UPDATE
               difficulty_level = VALUES(difficulty_level)""",
            (user_id, topic, difficulty)
        )

    # Update session
    session['onboarding_done']   = 1
    session['field_of_interest'] = field_label
    session['skill_level']       = skill_level

    return jsonify({'success': True, 'redirect_url': '/dashboard'})


# ============================================================
# SKIP ONBOARDING
# ============================================================
@onboarding_bp.route('/onboarding/skip', methods=['POST'])
@login_required
def skip():
    user_id = session['user_id']
    execute_query(
        "UPDATE users SET onboarding_done=1 WHERE id=%s",
        (user_id,)
    )
    session['onboarding_done'] = 1
    return jsonify({'success': True, 'redirect_url': '/dashboard'})


# ============================================================
# GET FIELD QUERIES (used by recommend.py)
# ============================================================
def get_field_queries(field_label, skill_level):
    """Return YouTube search queries for a field + skill level"""
    queries  = FIELD_QUERY_MAP.get(field_label, [])
    suffix_map = {
        'Beginner'    : 'for beginners',
        'Intermediate': 'intermediate',
        'Advanced'    : 'advanced',
    }
    suffix = suffix_map.get(skill_level, 'for beginners')

    result = []
    for q in queries[:3]:
        result.append(f"{q} {suffix}".strip())
    return result