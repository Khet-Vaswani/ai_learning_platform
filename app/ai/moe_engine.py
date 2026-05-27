# ============================================================
# moe_engine.py — Intelligent Adaptive Recommendation Engine
# ============================================================

import math
from app.utils.db import execute_query


# ── Field → Topics (BOTH id and label keys) ───────────────
FIELD_TOPICS = {
    # ── IT ────────────────────────────────────────────────
    'computer_science'       : ['Python Programming', 'Algorithms', 'Data Structures', 'Object Oriented Programming', 'Web Development'],
    'Computer Science'       : ['Python Programming', 'Algorithms', 'Data Structures', 'Object Oriented Programming', 'Web Development'],
    'data_science'           : ['Machine Learning', 'Data Analysis', 'Deep Learning', 'Statistics', 'Python for Data Science'],
    'Data Science & AI'      : ['Machine Learning', 'Data Analysis', 'Deep Learning', 'Statistics', 'Python for Data Science'],
    'web_development'        : ['HTML CSS', 'JavaScript', 'React', 'Flask Framework', 'Node.js'],
    'Web Development'        : ['HTML CSS', 'JavaScript', 'React', 'Flask Framework', 'Node.js'],
    'database'               : ['Database SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'Database Design'],
    'Database & Backend'     : ['Database SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'Database Design'],
    'mobile_dev'             : ['React Native', 'Flutter', 'Android Development', 'iOS Development'],
    'Mobile Development'     : ['React Native', 'Flutter', 'Android Development', 'iOS Development'],
    'cybersecurity'          : ['Network Security', 'Ethical Hacking', 'Cryptography', 'Cyber Forensics'],
    'Cybersecurity'          : ['Network Security', 'Ethical Hacking', 'Cryptography', 'Cyber Forensics'],
    'cloud_devops'           : ['AWS', 'Docker', 'Linux', 'CI/CD', 'Kubernetes'],
    'Cloud & DevOps'         : ['AWS', 'Docker', 'Linux', 'CI/CD', 'Kubernetes'],

    # ── Business ──────────────────────────────────────────
    'business_admin'         : ['Business Management', 'Marketing Strategy', 'Financial Management', 'Entrepreneurship', 'Business Analytics'],
    'BBA / Business Admin'   : ['Business Management', 'Marketing Strategy', 'Financial Management', 'Entrepreneurship', 'Business Analytics'],
    'Business Administration (BBA)' : ['Business Management', 'Marketing Strategy', 'Financial Management', 'Entrepreneurship', 'Business Analytics'],
    'accounting'             : ['Financial Accounting', 'Managerial Accounting', 'Taxation', 'Auditing', 'Cost Accounting'],
    'Accounting & Finance'   : ['Financial Accounting', 'Managerial Accounting', 'Taxation', 'Auditing', 'Cost Accounting'],
    'marketing'              : ['Digital Marketing', 'Brand Management', 'Sales Strategy', 'Market Research', 'Social Media Marketing'],
    'Marketing & Sales'      : ['Digital Marketing', 'Brand Management', 'Sales Strategy', 'Market Research', 'Social Media Marketing'],
    'hr_management'          : ['HR Management', 'Recruitment', 'Employee Relations', 'Training and Development', 'Performance Management'],
    'Human Resources'        : ['HR Management', 'Recruitment', 'Employee Relations', 'Training and Development', 'Performance Management'],

    # ── Law ───────────────────────────────────────────────
    'law'                    : ['Constitutional Law', 'Criminal Law', 'Contract Law', 'International Law', 'Legal Research'],
    'Law & Legal Studies'    : ['Constitutional Law', 'Criminal Law', 'Contract Law', 'International Law', 'Legal Research'],
    'criminal_justice'       : ['Criminal Justice System', 'Forensic Science', 'Law Enforcement', 'Criminology', 'Corrections'],
    'Criminal Justice'       : ['Criminal Justice System', 'Forensic Science', 'Law Enforcement', 'Criminology', 'Corrections'],

    # ── CSS/PMS ───────────────────────────────────────────
    'css_exam'               : ['Pakistan Affairs', 'Islamic Studies', 'Current Affairs', 'Essay Writing', 'General Knowledge'],
    'CSS / PMS Exam Prep'    : ['Pakistan Affairs', 'Islamic Studies', 'Current Affairs', 'Essay Writing', 'General Knowledge'],

    # ── Social Sciences ───────────────────────────────────
    'political_science'      : ['Political Theory', 'International Relations', 'Public Policy', 'Comparative Politics'],
    'Political Science'      : ['Political Theory', 'International Relations', 'Public Policy', 'Comparative Politics'],
    'psychology'             : ['Clinical Psychology', 'Cognitive Psychology', 'Developmental Psychology', 'Social Psychology'],
    'Psychology'             : ['Clinical Psychology', 'Cognitive Psychology', 'Developmental Psychology', 'Social Psychology'],
    'sociology'              : ['Social Theory', 'Criminology', 'Urban Sociology', 'Social Research'],
    'Sociology'              : ['Social Theory', 'Criminology', 'Urban Sociology', 'Social Research'],
    'economics'              : ['Microeconomics', 'Macroeconomics', 'International Economics', 'Development Economics'],
    'Economics'              : ['Microeconomics', 'Macroeconomics', 'International Economics', 'Development Economics'],

    # ── Science ───────────────────────────────────────────
    'engineering'            : ['Mechanical Engineering', 'Electrical Engineering', 'Civil Engineering', 'Thermodynamics'],
    'Engineering'            : ['Mechanical Engineering', 'Electrical Engineering', 'Civil Engineering', 'Thermodynamics'],
    'mathematics'            : ['Calculus', 'Linear Algebra', 'Statistics', 'Discrete Mathematics', 'Probability'],
    'Mathematics'            : ['Calculus', 'Linear Algebra', 'Statistics', 'Discrete Mathematics', 'Probability'],
    'physics'                : ['Classical Physics', 'Quantum Physics', 'Thermodynamics', 'Electromagnetism'],
    'Physics'                : ['Classical Physics', 'Quantum Physics', 'Thermodynamics', 'Electromagnetism'],
    'chemistry'              : ['Organic Chemistry', 'Inorganic Chemistry', 'Physical Chemistry', 'Analytical Chemistry'],
    'Chemistry'              : ['Organic Chemistry', 'Inorganic Chemistry', 'Physical Chemistry', 'Analytical Chemistry'],
    'biology'                : ['Molecular Biology', 'Genetics', 'Ecology', 'Microbiology'],
    'Biology'                : ['Molecular Biology', 'Genetics', 'Ecology', 'Microbiology'],

    # ── Health ────────────────────────────────────────────
    'medicine'               : ['Anatomy', 'Physiology', 'Pharmacology', 'Clinical Medicine', 'Pathology'],
    'Medicine & Healthcare'  : ['Anatomy', 'Physiology', 'Pharmacology', 'Clinical Medicine', 'Pathology'],
    'nursing'                : ['Nursing Fundamentals', 'Medical-Surgical Nursing', 'Pediatric Nursing', 'Mental Health Nursing'],
    'Nursing'                : ['Nursing Fundamentals', 'Medical-Surgical Nursing', 'Pediatric Nursing', 'Mental Health Nursing'],
    'pharmacy'               : ['Pharmaceutical Chemistry', 'Pharmacology', 'Clinical Pharmacy', 'Pharmacy Practice'],
    'Pharmacy'               : ['Pharmaceutical Chemistry', 'Pharmacology', 'Clinical Pharmacy', 'Pharmacy Practice'],

    # ── Arts ──────────────────────────────────────────────
    'english_literature'     : ['American Literature', 'British Literature', 'World Literature', 'Literary Theory'],
    'English Literature'     : ['American Literature', 'British Literature', 'World Literature', 'Literary Theory'],
    'history'                : ['World History', 'Pakistani History', 'European History', 'Asian History'],
    'History'                : ['World History', 'Pakistani History', 'European History', 'Asian History'],
    'philosophy'             : ['Western Philosophy', 'Eastern Philosophy', 'Ethics', 'Logic'],
    'Philosophy'             : ['Western Philosophy', 'Eastern Philosophy', 'Ethics', 'Logic'],
    'art_design'             : ['Visual Arts', 'Graphic Design', 'Art History', 'Digital Art'],
    'Art & Design'           : ['Visual Arts', 'Graphic Design', 'Art History', 'Digital Art'],

    # ── Education / Media ─────────────────────────────────
    'education'              : ['Educational Psychology', 'Curriculum Development', 'Teaching Methods', 'Educational Technology'],
    'Education'              : ['Educational Psychology', 'Curriculum Development', 'Teaching Methods', 'Educational Technology'],
    'journalism'             : ['News Writing', 'Broadcast Journalism', 'Digital Media', 'Media Ethics'],
    'Journalism & Media'     : ['News Writing', 'Broadcast Journalism', 'Digital Media', 'Media Ethics'],
    'hospitality'            : ['Hotel Management', 'Tourism Management', 'Event Planning', 'Food and Beverage'],
    'Hospitality & Tourism'  : ['Hotel Management', 'Tourism Management', 'Event Planning', 'Food and Beverage'],

    # ── Design ────────────────────────────────────────────
    'design'                 : ['Figma', 'UI Design', 'UX Research', 'Graphic Design', 'Prototyping'],
    'UI/UX Design'           : ['Figma', 'UI Design', 'UX Research', 'Graphic Design', 'Prototyping'],
}


def get_topics_for_field(field):
    """
    Resolve topics for any field label or id.
    Tries exact match first, then case-insensitive,
    then partial match — never falls through to IT topics.
    """
    if not field:
        return []

    # 1. Exact match
    if field in FIELD_TOPICS:
        return FIELD_TOPICS[field]

    # 2. Case-insensitive exact match
    field_lower = field.lower().strip()
    for key, topics in FIELD_TOPICS.items():
        if key.lower().strip() == field_lower:
            return topics

    # 3. Partial match (field label contains a known key or vice versa)
    for key, topics in FIELD_TOPICS.items():
        if field_lower in key.lower() or key.lower() in field_lower:
            return topics

    # 4. Return empty — do NOT fallback to IT topics
    print(f"⚠️ No topics found for field: '{field}'")
    return []


# ── Learning path ─────────────────────────────────────────
TOPIC_PATH = {
    'Python Programming'             : 'Object Oriented Programming',
    'Object Oriented Programming'    : 'Data Structures',
    'Data Structures'                : 'Algorithms',
    'Algorithms'                     : 'Web Development',
    'HTML CSS'                       : 'JavaScript',
    'JavaScript'                     : 'React',
    'React'                          : 'Node.js',
    'Node.js'                        : 'Database SQL',
    'Machine Learning'               : 'Deep Learning',
    'Deep Learning'                  : 'Neural Networks',
    'Data Analysis'                  : 'Machine Learning',
    'Statistics'                     : 'Data Analysis',
    'Database SQL'                   : 'MySQL',
    'MySQL'                          : 'PostgreSQL',
    'Network Security'               : 'Ethical Hacking',
    'Ethical Hacking'                : 'Cryptography',
    'Calculus'                       : 'Linear Algebra',
    'Linear Algebra'                 : 'Statistics',
    'Business Management'            : 'Marketing Strategy',
    'Marketing Strategy'             : 'Financial Management',
    'Financial Accounting'           : 'Managerial Accounting',
    'Constitutional Law'             : 'Criminal Law',
    'Criminal Law'                   : 'Contract Law',
    'Pakistan Affairs'               : 'Current Affairs',
    'Current Affairs'                : 'Essay Writing',
    'Microeconomics'                 : 'Macroeconomics',
    'Anatomy'                        : 'Physiology',
    'Physiology'                     : 'Pharmacology',
    'Political Theory'               : 'International Relations',
    'Clinical Psychology'            : 'Cognitive Psychology',
    'Mechanical Engineering'         : 'Electrical Engineering',
    'Figma'                          : 'UI Design',
    'UI Design'                      : 'UX Research',
}


LEVEL_SUFFIX = {
    'Beginner'    : 'complete beginners tutorial step by step',
    'Intermediate': 'intermediate concepts with examples',
    'Advanced'    : 'advanced deep dive expert level',
    'Easy'        : 'complete beginners tutorial step by step',
    'Medium'      : 'intermediate concepts with examples',
    'Hard'        : 'advanced deep dive expert level',
}


# ============================================================
# ATTENTION ROUTER
# ============================================================
class AttentionRouter:

    def __init__(self, student_context):
        self.context = student_context

    def _softmax(self, scores):
        if all(s == 0 for s in scores):
            n = len(scores)
            return [1.0/n for _ in scores]
        max_s = max(scores)
        exp_s = [math.exp(s - max_s) for s in scores]
        total = sum(exp_s)
        return [e / total for e in exp_s]

    def compute_weights(self):
        ctx      = self.context
        is_new   = ctx.get('is_new_user', False)

        # New user — preference expert takes over completely
        if is_new:
            return {
                'weak_topic' : 0.05,
                'performance': 0.05,
                'history'    : 0.90,
            }

        weak_signal  = min(ctx['weak_count']  * 0.3,  1.0)
        quiz_signal  = min(ctx['quiz_count']  * 0.1,  1.0)
        watch_signal = min(ctx['watch_count'] * 0.05, 1.0)
        avg_perf     = ctx['avg_score'] / 100.0

        k_weak = weak_signal * 0.5 + (1 - avg_perf) * 0.3 + quiz_signal * 0.2
        k_perf = quiz_signal * 0.5 + avg_perf * 0.3 + weak_signal * 0.2
        k_hist = watch_signal * 0.5 + (1 - watch_signal) * 0.3 + (1 - weak_signal) * 0.2

        d_k     = math.sqrt(3)
        raw     = [
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


# ============================================================
# TRANSFORMER MOE
# ============================================================
class TransformerMoE:

    def __init__(self, user_id):
        self.user_id = user_id
        self.data    = self._load_student_data()
        self.context = self._build_context()
        self.router  = AttentionRouter(self.context)
        self.weights = self.router.compute_weights()

        state = 'NEW USER' if self.context['is_new_user'] else 'RETURNING'
        print(f"\n🤖 MoE [{state}] user={user_id} "
              f"field='{self.data['field']}' "
              f"weak={self.context['weak_count']} "
              f"quiz={self.context['quiz_count']} "
              f"watched={self.context['watch_count']} "
              f"avg={self.context['avg_score']}%")
        print(f"   Weights: weak={self.weights['weak_topic']:.3f} "
              f"perf={self.weights['performance']:.3f} "
              f"pref={self.weights['history']:.3f}")

    # ── Load student data ──────────────────────────────────
    def _load_student_data(self):
        user_row = execute_query(
            """SELECT field_of_interest, skill_level, onboarding_done
               FROM users WHERE id=%s""",
            (self.user_id,), fetch=True
        )

        field     = user_row[0]['field_of_interest'] if user_row else None
        skill_lvl = (user_row[0]['skill_level'] or 'Beginner') if user_row else 'Beginner'

        # Use robust resolver — never falls back to IT
        preferred_topics = get_topics_for_field(field)
        print(f"   Field resolved: '{field}' → {preferred_topics}")

        # Weak topics (real failures only)
        weak = execute_query(
            """SELECT topic, fail_count FROM weak_topics
               WHERE user_id=%s AND fail_count > 0
               ORDER BY fail_count DESC""",
            (self.user_id,), fetch=True
        ) or []

        # Quiz performance
        performance = execute_query(
            """SELECT topic,
                      ROUND(AVG(score/total*100), 1) as avg_score,
                      COUNT(*) as attempts,
                      MAX(ROUND(score/total*100, 1)) as best_score,
                      MIN(ROUND(score/total*100, 1)) as worst_score
               FROM video_quizzes
               WHERE user_id=%s AND attempted=1 AND total>0
               GROUP BY topic ORDER BY avg_score ASC""",
            (self.user_id,), fetch=True
        ) or []

        # Watch history
        watched = execute_query(
            "SELECT DISTINCT video_id, topic FROM watched_videos WHERE user_id=%s",
            (self.user_id,), fetch=True
        ) or []

        # Learning curves
        curves = execute_query(
            """SELECT topic, curve_stage, current_score,
                      predicted_next, difficulty_level, learning_rate
               FROM learning_curves WHERE user_id=%s""",
            (self.user_id,), fetch=True
        ) or []

        # Avg score
        avg = execute_query(
            """SELECT ROUND(AVG(score/total*100), 1) as avg
               FROM video_quizzes
               WHERE user_id=%s AND attempted=1 AND total>0""",
            (self.user_id,), fetch=True
        )
        avg_score = float(avg[0]['avg'] or 0) if avg else 0.0

        return {
            'weak'            : weak,
            'performance'     : performance,
            'watched'         : watched,
            'curves'          : curves,
            'avg_score'       : avg_score,
            'field'           : field,
            'skill_level'     : skill_lvl,
            'preferred_topics': preferred_topics,
        }

    def _build_context(self):
        d = self.data
        return {
            'weak_count' : len(d['weak']),
            'quiz_count' : len(d['performance']),
            'watch_count': len(d['watched']),
            'avg_score'  : d['avg_score'],
            # New user = no watch history AND no quiz attempts
            'is_new_user': len(d['watched']) == 0 and len(d['performance']) == 0,
        }

    # ── Expert 1: Weak Topic ───────────────────────────────
    def expert_weak_topics(self):
        queries = []
        weak    = self.data['weak']
        curves  = {c['topic']: c for c in self.data['curves']}

        # Only triggers after quizzes attempted
        if self.context['quiz_count'] == 0 or not weak:
            return queries

        for wt in weak[:5]:
            topic      = wt['topic']
            fail_count = wt['fail_count']

            topic_perf = next(
                (p for p in self.data['performance'] if p['topic'] == topic),
                None
            )
            avg   = float(topic_perf['avg_score']) if topic_perf else 0.0
            curve = curves.get(topic)
            stage = curve['curve_stage'] if curve else ''

            if avg < 30 or stage == 'Struggling':
                base  = 1.0
                query = f"{topic} absolute beginners complete guide from zero"
                reason= f"🔴 Very weak in {topic} ({avg:.0f}%) — back to basics"
            elif avg < 50:
                base  = 0.85
                query = f"{topic} basics explained simply step by step"
                reason= f"⚠️ Struggling in {topic} ({avg:.0f}%) — need basics"
            else:
                base  = 0.70
                query = f"{topic} practice exercises solved examples"
                reason= f"📊 Below average in {topic} ({avg:.0f}%) — more practice"

            final = round(base * self.weights['weak_topic'], 4)
            queries.append({
                'query'       : query,
                'topic'       : topic,
                'expert'      : 'weak_topic',
                'expert_score': base,
                'final_score' : final,
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
                # STRONG → advance + unlock next topic
                expert_score = 0.85
                query        = f"{topic} advanced expert techniques projects"
                reason       = f"🏆 Strong in {topic} ({avg:.0f}%) — advancing!"

                next_t = TOPIC_PATH.get(topic)
                if next_t:
                    suffix = LEVEL_SUFFIX.get(skill_lvl, 'tutorial')
                    queries.append({
                        'query'       : f"{next_t} introduction {suffix}",
                        'topic'       : next_t,
                        'expert'      : 'performance',
                        'expert_score': 0.80,
                        'final_score' : round(0.80 * self.weights['performance'], 4),
                        'reason'      : f"➡️ Unlock next: {next_t}",
                        'priority'    : 'high',
                        'weight_used' : round(self.weights['performance'], 3),
                        'curve_stage' : stage,
                    })

            elif avg >= 60:
                expert_score = 0.65
                query        = f"{topic} intermediate deep dive concepts"
                reason       = f"📈 Progressing in {topic} ({avg:.0f}%)"
            elif avg >= 40:
                expert_score = 0.80
                query        = f"{topic} practice problems step by step solutions"
                reason       = f"📊 Need practice in {topic} ({avg:.0f}%)"
            else:
                expert_score = 0.95
                query        = f"{topic} fundamentals basics beginners easy"
                reason       = f"📉 Very low in {topic} ({avg:.0f}%) — fundamentals"

            if attempts >= 3 and avg < 60:
                expert_score = min(expert_score + 0.10, 1.0)

            final = round(expert_score * self.weights['performance'], 4)
            queries.append({
                'query'       : query,
                'topic'       : topic,
                'expert'      : 'performance',
                'expert_score': expert_score,
                'final_score' : final,
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
        suffix         = LEVEL_SUFFIX.get(skill_lvl, 'tutorial')
        is_new         = self.context['is_new_user']

        if not preferred:
            print(f"   ⚠️ No preferred topics for expert_history")

        # Preferred field topics (new user → all show, returning → unwatched only)
        for topic in preferred:
            t_lower = topic.lower()
            if not is_new and t_lower in watched_topics:
                continue
            if t_lower in weak_set:
                continue   # Weak topics handled by Expert 1

            expert_score = 0.90 if is_new else 0.65
            queries.append({
                'query'       : f"{topic} {suffix}",
                'topic'       : topic,
                'expert'      : 'history',
                'expert_score': expert_score,
                'final_score' : round(expert_score * self.weights['history'], 4),
                'reason'      : f"🎯 {'Your field' if not is_new else 'Recommended for you'}: {topic}",
                'priority'    : 'high',
                'weight_used' : round(self.weights['history'], 3),
            })

        # General fallback ONLY if no preferred topics resolved
        if not queries:
            fallback_topics = [
                ('Python Programming',  'python programming complete beginners course'),
                ('Web Development',     'web development html css javascript full course'),
                ('Machine Learning',    'machine learning beginners complete guide'),
                ('Data Science',        'data science python complete tutorial'),
                ('JavaScript',          'javascript complete course beginners'),
                ('Database SQL',        'sql mysql database complete tutorial'),
                ('Algorithms',          'data structures algorithms complete course'),
            ]
            for topic_name, query in fallback_topics:
                t_lower = topic_name.lower()
                if t_lower in watched_topics or t_lower in weak_set:
                    continue
                queries.append({
                    'query'       : query,
                    'topic'       : topic_name,
                    'expert'      : 'history',
                    'expert_score': 0.40,
                    'final_score' : round(0.40 * self.weights['history'], 4),
                    'reason'      : f"📺 Explore: {topic_name}",
                    'priority'    : 'low',
                    'weight_used' : round(self.weights['history'], 3),
                })

        return queries[:6]

    # ── Router ─────────────────────────────────────────────
    def get_recommendations(self):
        e1    = self.expert_weak_topics()
        e2    = self.expert_performance()
        e3    = self.expert_history()
        all_q = e1 + e2 + e3

        print(f"   E1(Weak)={len(e1)} E2(Perf)={len(e2)} E3(Pref)={len(e3)}")

        all_q.sort(key=lambda x: x['final_score'], reverse=True)

        seen, unique = set(), []
        for q in all_q:
            key = q['query'][:35].lower()
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
            'experts': {
                'weak_topic': {
                    'name'  : 'Weak Topic Expert',
                    'weight': round(self.weights['weak_topic'], 3),
                    'data'  : len(self.data['weak']),
                },
                'performance': {
                    'name'  : 'Performance Expert',
                    'weight': round(self.weights['performance'], 3),
                    'data'  : len(self.data['performance']),
                },
                'history': {
                    'name'  : 'Preference Expert',
                    'weight': round(self.weights['history'], 3),
                    'data'  : len(self.data['watched']),
                },
            },
        }