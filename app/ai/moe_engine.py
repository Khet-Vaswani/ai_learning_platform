# moe_engine.py — FIXED: Supports ALL educational categories
# Now handles: Primary/Secondary/Matric/Intermediate/University
# ============================================================

import math
from app.utils.db import execute_query


# ══════════════════════════════════════════════════════════
# FIELD → TOPICS MAP (University fields)
# ══════════════════════════════════════════════════════════
FIELD_TOPICS = {
    # ── Computer Science ──────────────────────────────────
    'computer_science'       : ['Python Programming', 'Algorithms', 'Data Structures', 'OOP', 'Web Development'],
    'Computer Science'       : ['Python Programming', 'Algorithms', 'Data Structures', 'OOP', 'Web Development'],
    'Software Engineering'   : ['Software Engineering', 'System Design', 'Algorithms', 'Database Design', 'Web Development'],
    'Data Science & AI'      : ['Machine Learning', 'Data Analysis', 'Deep Learning', 'Statistics', 'Python'],
    'Web Development'        : ['HTML CSS', 'JavaScript', 'React', 'Flask Framework', 'Node.js'],
    'Database & Backend'     : ['Database SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'Database Design'],
    'Mobile Development'     : ['React Native', 'Flutter', 'Android Development', 'iOS Development'],
    'Cybersecurity'          : ['Network Security', 'Ethical Hacking', 'Cryptography', 'Cyber Forensics'],
    'Cloud & DevOps'         : ['AWS', 'Docker', 'Linux', 'CI/CD', 'Kubernetes'],

    # ── Business ──────────────────────────────────────────
    'BBA / Business Admin'   : ['Business Management', 'Marketing Strategy', 'Financial Management', 'Entrepreneurship'],
    'Marketing'              : ['Digital Marketing', 'Brand Management', 'Sales Strategy', 'Market Research'],
    'Finance & Accounting'   : ['Financial Accounting', 'Managerial Accounting', 'Taxation', 'Auditing'],
    'Human Resources'        : ['HR Management', 'Recruitment', 'Employee Relations', 'Training and Development'],
    'International Business' : ['International Trade', 'Global Supply Chain', 'Trade Agreements', 'Export Import'],
    'Entrepreneurship'       : ['Startup Strategy', 'Business Planning', 'Funding', 'Innovation Management'],

    # ── Law ───────────────────────────────────────────────
    'Law & Legal Studies'    : ['Constitutional Law', 'Criminal Law', 'Contract Law', 'International Law'],
    'Constitutional Law'     : ['Constitutional Law', 'Human Rights', 'Administrative Law', 'Federal System'],
    'Criminal Law'           : ['Criminal Law', 'Criminal Procedure', 'Evidence Law', 'Criminology'],
    'Civil Law'              : ['Contract Law', 'Property Law', 'Tort Law', 'Civil Procedure'],
    'International Law'      : ['International Law', 'Treaties', 'Diplomacy', 'Trade Law'],
    'Corporate Law'          : ['Corporate Law', 'Company Law', 'Securities Law', 'Business Contracts'],

    # ── Medicine ──────────────────────────────────────────
    'MBBS / Medicine'        : ['Anatomy', 'Physiology', 'Pharmacology', 'Clinical Medicine', 'Pathology'],
    'Nursing'                : ['Nursing Fundamentals', 'Medical-Surgical Nursing', 'Patient Care', 'Pediatric Nursing'],
    'Pharmacy'               : ['Pharmaceutical Chemistry', 'Pharmacology', 'Clinical Pharmacy', 'Drug Interactions'],
    'Dentistry'              : ['Dental Science', 'Oral Surgery', 'Prosthodontics', 'Orthodontics'],
    'Public Health'          : ['Epidemiology', 'Biostatistics', 'Environmental Health', 'Health Promotion'],
    'Physiotherapy'          : ['Physiotherapy Principles', 'Rehabilitation', 'Therapeutic Exercises'],

    # ── Social Sciences ───────────────────────────────────
    'Psychology'             : ['Clinical Psychology', 'Cognitive Psychology', 'Developmental Psychology', 'Social Psychology'],
    'Sociology'              : ['Social Theory', 'Criminology', 'Urban Sociology', 'Social Research'],
    'Political Science'      : ['Political Theory', 'International Relations', 'Public Policy', 'Comparative Politics'],
    'International Relations': ['International Relations', 'Foreign Policy', 'Geopolitics', 'Diplomacy'],
    'Social Work'            : ['Social Work Practice', 'Community Development', 'Counseling'],

    # ── Natural Sciences ──────────────────────────────────
    'Physics'                : ['Classical Physics', 'Quantum Physics', 'Thermodynamics', 'Electromagnetism'],
    'Chemistry'              : ['Organic Chemistry', 'Inorganic Chemistry', 'Physical Chemistry', 'Analytical Chemistry'],
    'Biology'                : ['Molecular Biology', 'Genetics', 'Ecology', 'Microbiology'],
    'Mathematics'            : ['Calculus', 'Linear Algebra', 'Statistics', 'Discrete Mathematics'],
    'Environmental Science'  : ['Environmental Science', 'Ecology', 'Climate Science', 'Sustainability'],

    # ── Engineering ───────────────────────────────────────
    'Mechanical Engineering' : ['Thermodynamics', 'Fluid Mechanics', 'Machine Design', 'Materials Science'],
    'Electrical Engineering' : ['Circuit Theory', 'Power Systems', 'Electronics', 'Signal Processing'],
    'Civil Engineering'      : ['Structural Design', 'Concrete Design', 'Soil Mechanics', 'Infrastructure'],
    'Chemical Engineering'   : ['Chemical Processes', 'Fluid Mechanics', 'Heat Transfer', 'Process Design'],
    'Aerospace Engineering'  : ['Aerodynamics', 'Aircraft Design', 'Propulsion', 'Flight Mechanics'],
    'Biomedical Engineering' : ['Biomedical Devices', 'Biomaterials', 'Medical Imaging', 'Rehabilitation'],

    # ── Arts & Humanities ─────────────────────────────────
    'English Literature'     : ['American Literature', 'British Literature', 'Literary Theory', 'Poetry Analysis'],
    'History'                : ['World History', 'Pakistani History', 'European History', 'Asian History'],
    'Philosophy'             : ['Western Philosophy', 'Eastern Philosophy', 'Ethics', 'Logic'],
    'Journalism & Media'     : ['News Writing', 'Broadcast Journalism', 'Digital Media', 'Media Ethics'],
    'Art & Design'           : ['Visual Arts', 'Graphic Design', 'Digital Art', 'Art History'],
    'Islamic Studies'        : ['Quran Studies', 'Hadith', 'Islamic History', 'Fiqh', 'Islamic Philosophy'],

    # ── Education ─────────────────────────────────────────
    'Education / Teaching'   : ['Educational Psychology', 'Curriculum Development', 'Teaching Methods', 'Assessment'],
    'Educational Psychology' : ['Learning Theories', 'Behavioral Psychology', 'Cognitive Development'],
    'Curriculum Design'      : ['Curriculum Design', 'Instructional Design', 'Assessment Methods'],

    # ── Economics ─────────────────────────────────────────
    'Economics'              : ['Microeconomics', 'Macroeconomics', 'International Economics', 'Economic Policy'],
    'Development Economics'  : ['Development Economics', 'Poverty Studies', 'Economic Policy', 'Growth Theory'],
    'Islamic Economics'      : ['Islamic Finance', 'Zakat', 'Islamic Banking', 'Halal Economics'],
}


# ══════════════════════════════════════════════════════════
# CLASS → TOPICS MAP (School/College levels)
# ══════════════════════════════════════════════════════════
CLASS_TOPICS = {
    # Primary
    'class_1' : ['English Basics', 'Urdu Basics', 'Maths Class 1', 'General Knowledge'],
    'class_2' : ['English Class 2', 'Urdu Class 2', 'Maths Class 2', 'Science Class 2'],
    'class_3' : ['English Class 3', 'Urdu Class 3', 'Maths Class 3', 'Science Class 3'],
    'class_4' : ['English Class 4', 'Urdu Class 4', 'Maths Class 4', 'Social Studies'],
    'class_5' : ['English Class 5', 'Urdu Class 5', 'Maths Class 5', 'Science Class 5'],

    # Secondary
    'class_6' : ['English Class 6', 'Mathematics Class 6', 'General Science', 'Islamiat', 'Urdu'],
    'class_7' : ['English Class 7', 'Mathematics Class 7', 'General Science', 'History', 'Urdu'],
    'class_8' : ['English Class 8', 'Mathematics Class 8', 'Science Class 8', 'Pakistan Studies', 'Urdu'],

    # Matriculation
    'class_9_sci'  : ['Physics Class 9', 'Chemistry Class 9', 'Biology Class 9', 'Mathematics Class 9'],
    'class_10_sci' : ['Physics Class 10', 'Chemistry Class 10', 'Biology Class 10', 'Mathematics Class 10'],
    'class_9_arts' : ['General Math', 'Urdu', 'English', 'Pakistan Studies', 'Islamiat'],
    'class_10_arts': ['General Math', 'Urdu', 'English', 'Pakistan Studies', 'Civics'],
    'class_9_com'  : ['Principles of Accounting', 'Commercial Geography', 'Urdu', 'English'],
    'class_10_com' : ['Principles of Accounting', 'Principles of Commerce', 'Urdu', 'English'],

    # Intermediate
    'pre_med' : ['Biology FSc', 'Chemistry FSc', 'Physics FSc', 'English FSc'],
    'pre_eng' : ['Mathematics FSc', 'Physics FSc', 'Chemistry FSc', 'English FSc'],
    'ics'     : ['Computer Science ICS', 'Mathematics ICS', 'Physics ICS'],
    'icom'    : ['Accounting ICom', 'Business Mathematics', 'Economics', 'English'],
    'fa'      : ['Urdu FA', 'English FA', 'Islamic Studies', 'History', 'Civics'],

    # Professional/Competitive
    'css_pms'   : ['Pakistan Affairs', 'Current Affairs', 'Islamiat', 'English Essay', 'General Knowledge'],
    'mdcat'     : ['Biology MDCAT', 'Chemistry MDCAT', 'Physics MDCAT', 'English MDCAT'],
    'ecat'      : ['Mathematics ECAT', 'Physics ECAT', 'Chemistry ECAT'],
    'nts_gat'   : ['Verbal Reasoning', 'Quantitative Reasoning', 'Analytical Reasoning'],
    'ielts'     : ['IELTS Reading', 'IELTS Writing', 'IELTS Listening', 'IELTS Speaking'],
    'ppsc_fpsc' : ['General Knowledge', 'Pakistan Studies', 'Islamic Studies', 'Current Affairs'],
}


# ══════════════════════════════════════════════════════════
# SEARCH QUERY MAP — for YouTube searches
# ══════════════════════════════════════════════════════════
TOPIC_SEARCH_QUERIES = {
    # Primary
    'English Basics'          : 'English basics for kids class 1',
    'Urdu Basics'             : 'Urdu basics class 1 for kids',
    'Maths Class 1'           : 'basic maths class 1 addition subtraction',
    'General Knowledge'       : 'general knowledge for kids primary school',
    'English Class 2'         : 'English class 2 grammar basics',
    'Mathematics Class 6'     : 'Mathematics class 6 Pakistan curriculum',
    'General Science'         : 'General science class 6 Pakistan',
    'Physics Class 9'         : 'Physics class 9 Pakistan lecture',
    'Chemistry Class 9'       : 'Chemistry class 9 Pakistan tutorial',
    'Biology Class 9'         : 'Biology class 9 Pakistan tutorial',
    'Mathematics Class 9'     : 'Mathematics class 9 algebra geometry',
    'Biology FSc'             : 'FSc Biology Part 1 lecture',
    'Chemistry FSc'           : 'FSc Chemistry Part 1 tutorial',
    'Physics FSc'             : 'FSc Physics mechanics tutorial',
    'Mathematics FSc'         : 'FSc Mathematics calculus tutorial',
    'Computer Science ICS'    : 'ICS Computer Science programming tutorial',
    'Accounting ICom'         : 'ICom Accounting principles tutorial',
    'Pakistan Affairs'        : 'Pakistan affairs CSS preparation',
    'Current Affairs'         : 'current affairs Pakistan 2024',
    'Biology MDCAT'           : 'MDCAT Biology preparation',
    'IELTS Reading'           : 'IELTS reading skills practice',
}


# ══════════════════════════════════════════════════════════
# CATEGORY → GENERIC SEARCH (fallback)
# ══════════════════════════════════════════════════════════
CATEGORY_SEARCH = {
    'Primary'      : 'educational videos for kids primary school',
    'Secondary'    : 'middle school education Pakistan curriculum',
    'Matriculation': 'matric class Pakistan science arts',
    'Intermediate' : 'FSc intermediate Pakistan lecture',
    'University'   : 'university education lecture tutorial',
    'Professional' : 'competitive exam preparation Pakistan',
}


def get_topics_for_field(field):
    """
    Get topics for any field_of_interest value.
    Handles:
    - University fields: "Python Programming", "Constitutional Law", etc.
    - Class labels: "Class 9 — Science", "Pre-Medical (FSc)", etc.
    - Class IDs: "class_9_sci", "pre_med", etc.
    - Category names: "Primary", "Secondary", etc.
    Never returns empty for known categories.
    """
    if not field:
        return _get_general_topics()

    # Exact matches first
    if field in FIELD_TOPICS:
        return FIELD_TOPICS[field]
    if field in CLASS_TOPICS:
        return CLASS_TOPICS[field]

    field_lower = field.lower().strip()

    # Label-to-key mappings for school, college, and professional test prep
    label_to_key = {
        'class 1': 'class_1',
        'class 2': 'class_2',
        'class 3': 'class_3',
        'class 4': 'class_4',
        'class 5': 'class_5',
        'class 6': 'class_6',
        'class 7': 'class_7',
        'class 8': 'class_8',
        'class 9 science': 'class_9_sci',
        'class 9 — science': 'class_9_sci',
        'class 9 - science': 'class_9_sci',
        'class 10 science': 'class_10_sci',
        'class 10 — science': 'class_10_sci',
        'class 10 - science': 'class_10_sci',
        'class 9 arts': 'class_9_arts',
        'class 9 — arts': 'class_9_arts',
        'class 9 - arts': 'class_9_arts',
        'class 10 arts': 'class_10_arts',
        'class 10 — arts': 'class_10_arts',
        'class 10 - arts': 'class_10_arts',
        'class 9 commerce': 'class_9_com',
        'class 9 — commerce': 'class_9_com',
        'class 9 - commerce': 'class_9_com',
        'class 10 commerce': 'class_10_com',
        'class 10 — commerce': 'class_10_com',
        'class 10 - commerce': 'class_10_com',
        'pre-medical': 'pre_med',
        'pre medical': 'pre_med',
        'pre-engineering': 'pre_eng',
        'pre engineering': 'pre_eng',
        'ics': 'ics',
        'icom': 'icom',
        'fa': 'fa',
        'css': 'css_pms',
        'pms': 'css_pms',
        'mdcat': 'mdcat',
        'ecat': 'ecat',
        'nts': 'nts_gat',
        'gat': 'nts_gat',
        'ielts': 'ielts',
        'toefl': 'ielts',
        'ppsc': 'ppsc_fpsc',
        'fpsc': 'ppsc_fpsc',
    }

    # Normalize input field for matching
    cleaned = field_lower.replace('—', ' ').replace('-', ' ').replace('/', ' ').replace('&', ' ').replace('(', '').replace(')', '')
    cleaned = ' '.join(cleaned.split())

    # 1. Substring matching against predefined mappings
    for label_pattern, target_key in label_to_key.items():
        if label_pattern in cleaned:
            return CLASS_TOPICS[target_key]

    # 2. Case-insensitive substring match in FIELD_TOPICS
    for key, topics in FIELD_TOPICS.items():
        k_clean = key.lower().replace('&', ' ').replace('/', ' ')
        k_clean = ' '.join(k_clean.split())
        if k_clean in cleaned or cleaned in k_clean:
            return topics

    # 3. Case-insensitive substring match in CLASS_TOPICS
    for key, topics in CLASS_TOPICS.items():
        k_clean = key.replace('_', ' ')
        if k_clean in cleaned or cleaned in k_clean:
            return topics

    # 4. Fallback to category fallback
    return _category_fallback_topics(field)


def _label_matches_key(label, key):
    """Match class label to CLASS_TOPICS key."""
    label_l = label.lower()
    key_l   = key.lower()
    mappings = {
        'class 1': 'class_1', 'class 2': 'class_2', 'class 3': 'class_3',
        'class 4': 'class_4', 'class 5': 'class_5', 'class 6': 'class_6',
        'class 7': 'class_7', 'class 8': 'class_8',
        'class 9': 'class_9', 'class 10': 'class_10',
        'science': 'sci', 'arts': 'arts', 'commerce': 'com',
        'pre-medical': 'pre_med', 'pre-engineering': 'pre_eng',
        'ics': 'ics', 'icom': 'icom', 'fa': 'fa',
        'css': 'css_pms', 'mdcat': 'mdcat', 'ecat': 'ecat',
    }
    for lbl, k in mappings.items():
        if lbl in label_l and k in key_l:
            return True
    return False


def _category_fallback_topics(category):
    """Return generic topics for a broad category."""
    cat_lower = category.lower()
    if 'primary' in cat_lower:
        return ['English Basics', 'Urdu Basics', 'Maths Class 1', 'General Knowledge', 'Science Basics']
    elif 'secondary' in cat_lower:
        return ['English Class 6', 'Mathematics Class 6', 'General Science', 'Islamiat', 'Pakistan Studies']
    elif 'matric' in cat_lower:
        return ['Physics Class 9', 'Chemistry Class 9', 'Biology Class 9', 'Mathematics Class 9', 'English']
    elif 'intermediate' in cat_lower or 'fsc' in cat_lower:
        return ['Biology FSc', 'Chemistry FSc', 'Physics FSc', 'Mathematics FSc', 'English FSc']
    elif 'university' in cat_lower:
        return ['Python Programming', 'Data Structures', 'Algorithms', 'Web Development', 'Database Design']
    elif 'professional' in cat_lower or 'css' in cat_lower:
        return ['Pakistan Affairs', 'Current Affairs', 'Islamiat', 'English Essay', 'General Knowledge']
    else:
        return _get_general_topics()


def _get_general_topics():
    return ['English Language', 'Mathematics', 'Science Basics', 'General Knowledge', 'Pakistan Studies']


def get_search_query_for_topic(topic, skill_level='Beginner'):
    """Build YouTube search query for a topic."""
    # Check custom query map first
    if topic in TOPIC_SEARCH_QUERIES:
        base = TOPIC_SEARCH_QUERIES[topic]
    else:
        base = topic

    suffix_map = {
        'Beginner'    : 'beginners tutorial',
        'Intermediate': 'intermediate level',
        'Advanced'    : 'advanced concepts',
        'Easy'        : 'beginners tutorial',
        'Medium'      : 'intermediate level',
        'Hard'        : 'advanced concepts',
    }
    suffix = suffix_map.get(skill_level, 'tutorial')
    return f"{base} {suffix}"


# ══════════════════════════════════════════════════════════
# LEARNING PATH
# ══════════════════════════════════════════════════════════
TOPIC_PATH = {
    'Python Programming'      : 'Object Oriented Programming',
    'Object Oriented Programming': 'Data Structures',
    'Data Structures'         : 'Algorithms',
    'Algorithms'              : 'Web Development',
    'HTML CSS'                : 'JavaScript',
    'JavaScript'              : 'React',
    'React'                   : 'Node.js',
    'Node.js'                 : 'Database SQL',
    'Machine Learning'        : 'Deep Learning',
    'Data Analysis'           : 'Machine Learning',
    'Statistics'              : 'Data Analysis',
    'Calculus'                : 'Linear Algebra',
    'Linear Algebra'          : 'Statistics',
    'Business Management'     : 'Marketing Strategy',
    'Marketing Strategy'      : 'Financial Management',
    'Financial Accounting'    : 'Managerial Accounting',
    'Constitutional Law'      : 'Criminal Law',
    'Criminal Law'            : 'Contract Law',
    'Pakistan Affairs'        : 'Current Affairs',
    'Current Affairs'         : 'Essay Writing',
    'Anatomy'                 : 'Physiology',
    'Physiology'              : 'Pharmacology',
    'Political Theory'        : 'International Relations',
    'Clinical Psychology'     : 'Cognitive Psychology',
    'Mechanical Engineering'  : 'Electrical Engineering',
    # School progression
    'Physics Class 9'         : 'Physics Class 10',
    'Chemistry Class 9'       : 'Chemistry Class 10',
    'Biology Class 9'         : 'Biology Class 10',
    'Mathematics Class 9'     : 'Mathematics Class 10',
    'English Class 6'         : 'English Class 7',
    'Mathematics Class 6'     : 'Mathematics Class 7',
}

LEVEL_SUFFIX = {
    'Beginner'    : 'complete beginners tutorial step by step',
    'Intermediate': 'intermediate concepts with examples',
    'Advanced'    : 'advanced deep dive expert level',
    'Easy'        : 'complete beginners tutorial step by step',
    'Medium'      : 'intermediate concepts with examples',
    'Hard'        : 'advanced deep dive expert level',
}


# ══════════════════════════════════════════════════════════
# ATTENTION ROUTER
# ══════════════════════════════════════════════════════════
class AttentionRouter:

    def __init__(self, student_context):
        self.context = student_context

    def _softmax(self, scores):
        if all(s == 0 for s in scores):
            n = len(scores)
            return [1.0 / n for _ in scores]
        max_s = max(scores)
        exp_s = [math.exp(s - max_s) for s in scores]
        total = sum(exp_s)
        return [e / total for e in exp_s]

    def compute_weights(self):
        ctx    = self.context
        is_new = ctx.get('is_new_user', False)

        if is_new:
            return {'weak_topic': 0.05, 'performance': 0.05, 'history': 0.90}

        weak_signal  = min(ctx['weak_count']  * 0.3,  1.0)
        quiz_signal  = min(ctx['quiz_count']  * 0.1,  1.0)
        watch_signal = min(ctx['watch_count'] * 0.05, 1.0)
        avg_perf     = ctx['avg_score'] / 100.0

        k_weak = weak_signal * 0.5 + (1 - avg_perf) * 0.3 + quiz_signal * 0.2
        k_perf = quiz_signal * 0.5 + avg_perf * 0.3 + weak_signal * 0.2
        k_hist = watch_signal * 0.5 + (1 - watch_signal) * 0.3 + (1 - weak_signal) * 0.2

        d_k    = math.sqrt(3)
        raw    = [
            (weak_signal  * k_weak) / d_k,
            (quiz_signal  * k_perf) / d_k,
            (watch_signal * k_hist) / d_k,
        ]
        weights = self._softmax(raw)
        return {
            'weak_topic' : weights[0],
            'performance': weights[1],
            'history'    : weights[2],
        }


# ══════════════════════════════════════════════════════════
# TRANSFORMER MOE ENGINE
# ══════════════════════════════════════════════════════════
class TransformerMoE:

    def __init__(self, user_id):
        self.user_id = user_id
        self.data    = self._load_student_data()
        self.context = self._build_context()
        self.router  = AttentionRouter(self.context)
        self.weights = self.router.compute_weights()

        state = 'NEW' if self.context['is_new_user'] else 'RETURNING'
        print(f"\n🤖 MoE [{state}] user={user_id} "
              f"field='{self.data['field']}' "
              f"cat='{self.data['education_category']}' "
              f"weak={self.context['weak_count']} "
              f"quiz={self.context['quiz_count']} "
              f"watched={self.context['watch_count']} "
              f"avg={self.context['avg_score']}%")

    def _load_student_data(self):
        user_row = execute_query(
            """SELECT field_of_interest, skill_level, onboarding_done,
                      education_category, learning_level
               FROM users WHERE id=%s""",
            (self.user_id,), fetch=True
        )

        field      = ''
        skill_lvl  = 'Beginner'
        edu_cat    = ''

        if user_row:
            field     = user_row[0]['field_of_interest'] or ''
            skill_lvl = user_row[0]['skill_level'] or user_row[0].get('learning_level') or 'Beginner'
            edu_cat   = user_row[0].get('education_category') or ''

        # Get topics — tries field first, then category
        preferred_topics = get_topics_for_field(field)
        if not preferred_topics and edu_cat:
            preferred_topics = _category_fallback_topics(edu_cat)

        print(f"   Field: '{field}' → {len(preferred_topics)} topics")

        weak = execute_query(
            """SELECT topic, fail_count FROM weak_topics
               WHERE user_id=%s AND fail_count > 0
               ORDER BY fail_count DESC""",
            (self.user_id,), fetch=True
        ) or []

        performance = execute_query(
            """SELECT topic,
                      ROUND(AVG(score/total*100), 1) as avg_score,
                      COUNT(*) as attempts
               FROM video_quizzes
               WHERE user_id=%s AND attempted=1 AND total>0
               GROUP BY topic ORDER BY avg_score ASC""",
            (self.user_id,), fetch=True
        ) or []

        watched = execute_query(
            "SELECT DISTINCT video_id, topic FROM watched_videos WHERE user_id=%s",
            (self.user_id,), fetch=True
        ) or []

        curves = execute_query(
            """SELECT topic, curve_stage, current_score,
                      predicted_next, difficulty_level
               FROM learning_curves WHERE user_id=%s""",
            (self.user_id,), fetch=True
        ) or []

        avg = execute_query(
            """SELECT ROUND(AVG(score/total*100), 1) as avg
               FROM video_quizzes WHERE user_id=%s AND attempted=1 AND total>0""",
            (self.user_id,), fetch=True
        )
        avg_score = float(avg[0]['avg'] or 0) if avg else 0.0

        return {
            'weak'               : weak,
            'performance'        : performance,
            'watched'            : watched,
            'curves'             : curves,
            'avg_score'          : avg_score,
            'field'              : field,
            'skill_level'        : skill_lvl,
            'education_category' : edu_cat,
            'preferred_topics'   : preferred_topics,
        }

    def _build_context(self):
        d = self.data
        return {
            'weak_count' : len(d['weak']),
            'quiz_count' : len(d['performance']),
            'watch_count': len(d['watched']),
            'avg_score'  : d['avg_score'],
            'is_new_user': len(d['watched']) == 0 and len(d['performance']) == 0,
        }

    # ── Expert 1: Weak Topic ───────────────────────────────
    def expert_weak_topics(self):
        queries = []
        weak    = self.data['weak']
        curves  = {c['topic']: c for c in self.data['curves']}

        if self.context['quiz_count'] == 0 or not weak:
            return queries

        for wt in weak[:5]:
            topic      = wt['topic']
            topic_perf = next((p for p in self.data['performance'] if p['topic'] == topic), None)
            avg        = float(topic_perf['avg_score']) if topic_perf else 0.0
            curve      = curves.get(topic)
            stage      = curve['curve_stage'] if curve else ''

            if avg < 30 or stage == 'Struggling':
                base   = 1.0
                query  = get_search_query_for_topic(topic, 'Beginner')
                reason = f"🔴 Very weak in {topic} ({avg:.0f}%) — back to basics"
            elif avg < 50:
                base   = 0.85
                query  = f"{topic} basics explained simply step by step"
                reason = f"⚠️ Struggling in {topic} ({avg:.0f}%)"
            else:
                base   = 0.70
                query  = f"{topic} practice exercises solved examples"
                reason = f"📊 Need more practice in {topic} ({avg:.0f}%)"

            queries.append({
                'query'       : query,
                'topic'       : topic,
                'expert'      : 'weak_topic',
                'expert_score': base,
                'final_score' : round(base * self.weights['weak_topic'], 4),
                'reason'      : reason,
                'priority'    : 'high',
                'weight_used' : round(self.weights['weak_topic'], 3),
            })
        return queries

    # ── Expert 2: Performance ──────────────────────────────
    def expert_performance(self):
        queries     = []
        performance = self.data['performance']
        curves      = {c['topic']: c for c in self.data['curves']}
        skill_lvl   = self.data['skill_level']

        if not performance:
            return queries

        for perf in performance[:6]:
            topic    = perf['topic']
            avg      = float(perf['avg_score'] or 0)
            attempts = perf['attempts']
            curve    = curves.get(topic)
            stage    = curve['curve_stage'] if curve else ''

            if avg >= 75 or stage == 'Mastery':
                expert_score = 0.85
                query        = f"{topic} advanced expert techniques"
                reason       = f"🏆 Strong in {topic} ({avg:.0f}%) — advancing!"
                next_t       = TOPIC_PATH.get(topic)
                if next_t:
                    suffix = LEVEL_SUFFIX.get(skill_lvl, 'tutorial')
                    queries.append({
                        'query'       : f"{next_t} {suffix}",
                        'topic'       : next_t,
                        'expert'      : 'performance',
                        'expert_score': 0.80,
                        'final_score' : round(0.80 * self.weights['performance'], 4),
                        'reason'      : f"➡️ Next up: {next_t}",
                        'priority'    : 'high',
                        'weight_used' : round(self.weights['performance'], 3),
                        'curve_stage' : stage,
                    })
            elif avg >= 60:
                expert_score = 0.65
                query        = f"{topic} intermediate concepts"
                reason       = f"📈 Progressing in {topic} ({avg:.0f}%)"
            elif avg >= 40:
                expert_score = 0.80
                query        = f"{topic} practice problems step by step"
                reason       = f"📊 Need practice in {topic} ({avg:.0f}%)"
            else:
                expert_score = 0.95
                query        = get_search_query_for_topic(topic, 'Beginner')
                reason       = f"📉 Very low in {topic} ({avg:.0f}%) — fundamentals"

            if attempts >= 3 and avg < 60:
                expert_score = min(expert_score + 0.10, 1.0)

            queries.append({
                'query'       : query,
                'topic'       : topic,
                'expert'      : 'performance',
                'expert_score': expert_score,
                'final_score' : round(expert_score * self.weights['performance'], 4),
                'reason'      : reason,
                'priority'    : 'high' if avg < 60 else 'medium',
                'weight_used' : round(self.weights['performance'], 3),
                'curve_stage' : stage,
            })
        return queries

    # ── Expert 3: Preference / History ────────────────────
    def expert_history(self):
        queries        = []
        watched_topics = {w['topic'].lower() for w in self.data['watched'] if w['topic']}
        weak_set       = {w['topic'].lower() for w in self.data['weak']}
        preferred      = self.data['preferred_topics']
        skill_lvl      = self.data['skill_level']
        is_new         = self.context['is_new_user']

        for topic in preferred:
            t_lower = topic.lower()
            if not is_new and t_lower in watched_topics:
                continue
            if t_lower in weak_set:
                continue

            expert_score = 0.90 if is_new else 0.65
            query        = get_search_query_for_topic(topic, skill_lvl)

            queries.append({
                'query'       : query,
                'topic'       : topic,
                'expert'      : 'history',
                'expert_score': expert_score,
                'final_score' : round(expert_score * self.weights['history'], 4),
                'reason'      : f"🎯 {'Start learning' if is_new else 'Continue'}: {topic}",
                'priority'    : 'high',
                'weight_used' : round(self.weights['history'], 3),
            })

        # If no preferred topics — use category fallback
        if not queries:
            cat     = self.data['education_category']
            cat_q   = CATEGORY_SEARCH.get(cat, 'educational videos tutorial')
            queries.append({
                'query'       : cat_q,
                'topic'       : cat or 'Education',
                'expert'      : 'history',
                'expert_score': 0.50,
                'final_score' : round(0.50 * self.weights['history'], 4),
                'reason'      : f"📺 Educational content for {cat or 'you'}",
                'priority'    : 'medium',
                'weight_used' : round(self.weights['history'], 3),
            })

        return queries[:6]

    # ── Router ─────────────────────────────────────────────
    def get_recommendations(self):
        e1    = self.expert_weak_topics()
        e2    = self.expert_performance()
        e3    = self.expert_history()
        all_q = e1 + e2 + e3

        print(f"   E1={len(e1)} E2={len(e2)} E3={len(e3)} total={len(all_q)}")

        all_q.sort(key=lambda x: x['final_score'], reverse=True)

        seen, unique = set(), []
        for q in all_q:
            key = q['query'][:40].lower()
            if key not in seen:
                seen.add(key)
                unique.append(q)
        return unique

    def get_analysis(self):
        return {
            'weights': self.weights,
            'context': self.context,
            'is_new' : self.context['is_new_user'],
            'field'  : self.data['field'],
            'level'  : self.data['skill_level'],
            'category': self.data['education_category'],
            'experts': {
                'weak_topic' : {
                    'name'  : 'Weak Topic Expert',
                    'weight': round(self.weights['weak_topic'], 3),
                    'data'  : len(self.data['weak']),
                },
                'performance': {
                    'name'  : 'Performance Expert',
                    'weight': round(self.weights['performance'], 3),
                    'data'  : len(self.data['performance']),
                },
                'history'    : {
                    'name'  : 'Preference Expert',
                    'weight': round(self.weights['history'], 3),
                    'data'  : len(self.data['watched']),
                },
            },
        }