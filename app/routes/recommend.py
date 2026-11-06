# ============================================================
# recommend.py — MoE Recommendation Routes (Robust & Resilient)
# ============================================================

from flask import Blueprint, jsonify, session, request
from app.utils.auth_helpers import login_required
from app.utils.db import execute_query
from app.ai.moe_engine import TransformerMoE, FIELD_TOPICS, get_topics_for_field
from app.routes.youtube import is_entertainment_query, filter_educational_videos
from googleapiclient.discovery import build
import os, time, json, re

recommend_bp = Blueprint('recommend', __name__)

_cache       = {}
CACHE_EXPIRY = 900  # 15 min


# ════════════════════════════════════════════════════════════
# DOMAIN-SPECIFIC FALLBACK VIDEO CATALOG
# ════════════════════════════════════════════════════════════
FALLBACK_CATALOG = {
    # ── Computer Science & Programming ───────────────────────
    'software': [
        {'video_id': '8hly31xKli0', 'title': 'Software Engineering & System Design', 'channel': 'freeCodeCamp', 'thumbnail': 'https://img.youtube.com/vi/8hly31xKli0/mqdefault.jpg'},
        {'video_id': '_uQrJ0TkZlc', 'title': 'Python Full Course for Beginners', 'channel': 'Programming with Mosh', 'thumbnail': 'https://img.youtube.com/vi/_uQrJ0TkZlc/mqdefault.jpg'},
    ],
    'computer': [
        {'video_id': '_uQrJ0TkZlc', 'title': 'Python Programming & CS Foundations', 'channel': 'Programming with Mosh', 'thumbnail': 'https://img.youtube.com/vi/_uQrJ0TkZlc/mqdefault.jpg'},
        {'video_id': '8hly31xKli0', 'title': 'Algorithms & Data Structures Full Course', 'channel': 'freeCodeCamp', 'thumbnail': 'https://img.youtube.com/vi/8hly31xKli0/mqdefault.jpg'},
    ],
    'python': [
        {'video_id': '_uQrJ0TkZlc', 'title': 'Python Full Course for Beginners', 'channel': 'Programming with Mosh', 'thumbnail': 'https://img.youtube.com/vi/_uQrJ0TkZlc/mqdefault.jpg'},
        {'video_id': 'rfscVS0vtbw', 'title': 'Learn Python in 4 Hours', 'channel': 'freeCodeCamp', 'thumbnail': 'https://img.youtube.com/vi/rfscVS0vtbw/mqdefault.jpg'},
    ],
    'javascript': [
        {'video_id': 'W6NZfCO5SIk', 'title': 'JavaScript Tutorial for Beginners', 'channel': 'Programming with Mosh', 'thumbnail': 'https://img.youtube.com/vi/W6NZfCO5SIk/mqdefault.jpg'},
        {'video_id': 'PkZNo7MFNFg', 'title': 'Learn JavaScript Full Course', 'channel': 'freeCodeCamp', 'thumbnail': 'https://img.youtube.com/vi/PkZNo7MFNFg/mqdefault.jpg'},
    ],
    'web': [
        {'video_id': 'G3e-cpL7ofc', 'title': 'HTML CSS JS Full Course', 'channel': 'SuperSimpleDev', 'thumbnail': 'https://img.youtube.com/vi/G3e-cpL7ofc/mqdefault.jpg'},
        {'video_id': 'nu_pCVPKzTk', 'title': 'Flask Web Development Tutorial', 'channel': 'Tech With Tim', 'thumbnail': 'https://img.youtube.com/vi/nu_pCVPKzTk/mqdefault.jpg'},
    ],
    'algorithm': [
        {'video_id': '8hly31xKli0', 'title': 'Algorithms & Data Structures Full Course', 'channel': 'freeCodeCamp', 'thumbnail': 'https://img.youtube.com/vi/8hly31xKli0/mqdefault.jpg'},
        {'video_id': 'BBpAmxU_NQo', 'title': 'Data Structures Easy to Advanced', 'channel': 'freeCodeCamp', 'thumbnail': 'https://img.youtube.com/vi/BBpAmxU_NQo/mqdefault.jpg'},
    ],
    'machine learning': [
        {'video_id': 'GwIo3gDZCVQ', 'title': 'Machine Learning Full Course', 'channel': 'Simplilearn', 'thumbnail': 'https://img.youtube.com/vi/GwIo3gDZCVQ/mqdefault.jpg'},
        {'video_id': 'aircAruvnKk', 'title': 'Neural Networks Explained Visually', 'channel': '3Blue1Brown', 'thumbnail': 'https://img.youtube.com/vi/aircAruvnKk/mqdefault.jpg'},
    ],
    'data': [
        {'video_id': 'ua-CiDNNj30', 'title': 'Data Science Full Course for Beginners', 'channel': 'freeCodeCamp', 'thumbnail': 'https://img.youtube.com/vi/ua-CiDNNj30/mqdefault.jpg'},
        {'video_id': 'LHBE6Q9XlzI', 'title': 'Python for Data Science Tutorial', 'channel': 'freeCodeCamp', 'thumbnail': 'https://img.youtube.com/vi/LHBE6Q9XlzI/mqdefault.jpg'},
    ],
    'database': [
        {'video_id': 'HXV3zeRR3h4', 'title': 'SQL Tutorial - Full Database Course', 'channel': 'freeCodeCamp', 'thumbnail': 'https://img.youtube.com/vi/HXV3zeRR3h4/mqdefault.jpg'},
        {'video_id': '7S_tz1z_5bA', 'title': 'MySQL Full Course for Beginners', 'channel': 'Programming with Mosh', 'thumbnail': 'https://img.youtube.com/vi/7S_tz1z_5bA/mqdefault.jpg'},
    ],
    'cloud': [
        {'video_id': 'ulprqHHWlng', 'title': 'AWS Certified Cloud Practitioner Course', 'channel': 'freeCodeCamp', 'thumbnail': 'https://img.youtube.com/vi/ulprqHHWlng/mqdefault.jpg'},
        {'video_id': 'fqMOX6JJhGo', 'title': 'Docker Tutorial for Beginners', 'channel': 'Programming with Mosh', 'thumbnail': 'https://img.youtube.com/vi/fqMOX6JJhGo/mqdefault.jpg'},
    ],
    'cybersecurity': [
        {'video_id': 'inWWhr5tnEA', 'title': 'Cyber Security Full Course for Beginners', 'channel': 'Simplilearn', 'thumbnail': 'https://img.youtube.com/vi/inWWhr5tnEA/mqdefault.jpg'},
    ],

    # ── Medicine & Biology ───────────────────────────────────
    'medicine': [
        {'video_id': 'uBGl2BujkPQ', 'title': 'Human Anatomy & Physiology Introduction', 'channel': 'CrashCourse', 'thumbnail': 'https://img.youtube.com/vi/uBGl2BujkPQ/mqdefault.jpg'},
        {'video_id': 'fR3NxCR9z2U', 'title': 'Cellular Respiration and Biology Basics', 'channel': 'Amoeba Sisters', 'thumbnail': 'https://img.youtube.com/vi/fR3NxCR9z2U/mqdefault.jpg'},
    ],
    'anatomy': [
        {'video_id': 'uBGl2BujkPQ', 'title': 'Human Anatomy Overview', 'channel': 'CrashCourse', 'thumbnail': 'https://img.youtube.com/vi/uBGl2BujkPQ/mqdefault.jpg'},
    ],
    'biology': [
        {'video_id': 'QnQe0xW_JY4', 'title': 'Introduction to Biology', 'channel': 'CrashCourse', 'thumbnail': 'https://img.youtube.com/vi/QnQe0xW_JY4/mqdefault.jpg'},
        {'video_id': '8IlzKri08kk', 'title': 'DNA Structure and Replication', 'channel': 'Amoeba Sisters', 'thumbnail': 'https://img.youtube.com/vi/8IlzKri08kk/mqdefault.jpg'},
    ],

    # ── Engineering & Physical Sciences ─────────────────────
    'physics': [
        {'video_id': 'ZM8ECpBvc0I', 'title': 'Physics Mechanics: Motion & Newton\'s Laws', 'channel': 'CrashCourse', 'thumbnail': 'https://img.youtube.com/vi/ZM8ECpBvc0I/mqdefault.jpg'},
        {'video_id': 'ihNZlp7iUHE', 'title': 'Electric Charge and Circuit Theory', 'channel': 'CrashCourse', 'thumbnail': 'https://img.youtube.com/vi/ihNZlp7iUHE/mqdefault.jpg'},
    ],
    'chemistry': [
        {'video_id': 'FSyAehMdpyI', 'title': 'The Nucleus: Chemistry Crash Course', 'channel': 'CrashCourse', 'thumbnail': 'https://img.youtube.com/vi/FSyAehMdpyI/mqdefault.jpg'},
        {'video_id': 'bka20Q9TN6M', 'title': 'Periodic Table & Chemical Bonds', 'channel': 'CrashCourse', 'thumbnail': 'https://img.youtube.com/vi/bka20Q9TN6M/mqdefault.jpg'},
    ],
    'math': [
        {'video_id': 'WSstjN89q4w', 'title': 'Calculus 1 Full Course', 'channel': 'freeCodeCamp', 'thumbnail': 'https://img.youtube.com/vi/WSstjN89q4w/mqdefault.jpg'},
        {'video_id': 'fNk_zzaMoSs', 'title': 'Essence of Linear Algebra', 'channel': '3Blue1Brown', 'thumbnail': 'https://img.youtube.com/vi/fNk_zzaMoSs/mqdefault.jpg'},
    ],
    'engineering': [
        {'video_id': 'btGYcizV0iI', 'title': 'Introduction to Mechanical Engineering', 'channel': 'The Engineering Mindset', 'thumbnail': 'https://img.youtube.com/vi/btGYcizV0iI/mqdefault.jpg'},
        {'video_id': 'mc979OhitAg', 'title': 'How Electricity Works - Circuit Basics', 'channel': 'The Engineering Mindset', 'thumbnail': 'https://img.youtube.com/vi/mc979OhitAg/mqdefault.jpg'},
    ],

    # ── Business & Economics ─────────────────────────────────
    'business': [
        {'video_id': 'd8u3CN5v078', 'title': 'Principles of Management & Business', 'channel': 'CrashCourse', 'thumbnail': 'https://img.youtube.com/vi/d8u3CN5v078/mqdefault.jpg'},
        {'video_id': 'y8Tr4JgWvT4', 'title': 'Accounting Principles & Bookkeeping Basics', 'channel': 'Accounting Stuff', 'thumbnail': 'https://img.youtube.com/vi/y8Tr4JgWvT4/mqdefault.jpg'},
    ],
    'finance': [
        {'video_id': 'y8Tr4JgWvT4', 'title': 'Financial Accounting Fundamentals', 'channel': 'Accounting Stuff', 'thumbnail': 'https://img.youtube.com/vi/y8Tr4JgWvT4/mqdefault.jpg'},
    ],
    'economics': [
        {'video_id': '3ez10ADR_gM', 'title': 'Intro to Economics: Crash Course Econ #1', 'channel': 'CrashCourse', 'thumbnail': 'https://img.youtube.com/vi/3ez10ADR_gM/mqdefault.jpg'},
    ],

    # ── Law & Social Sciences ────────────────────────────────
    'law': [
        {'video_id': 'mIXGDn67rXo', 'title': 'Introduction to Law & Legal Systems', 'channel': 'CrashCourse', 'thumbnail': 'https://img.youtube.com/vi/mIXGDn67rXo/mqdefault.jpg'},
        {'video_id': '0b0ax374hsI', 'title': 'Constitutional Law Principles', 'channel': 'CrashCourse', 'thumbnail': 'https://img.youtube.com/vi/0b0ax374hsI/mqdefault.jpg'},
    ],
    'psychology': [
        {'video_id': 'vo4pMVb0R6M', 'title': 'Intro to Psychology: Crash Course', 'channel': 'CrashCourse', 'thumbnail': 'https://img.youtube.com/vi/vo4pMVb0R6M/mqdefault.jpg'},
    ],

    # ── School & Test Prep ───────────────────────────────────
    'school': [
        {'video_id': 'fNk_zzaMoSs', 'title': 'General Mathematics Concepts', 'channel': 'Khan Academy', 'thumbnail': 'https://img.youtube.com/vi/fNk_zzaMoSs/mqdefault.jpg'},
        {'video_id': 'ZM8ECpBvc0I', 'title': 'General Science Foundations', 'channel': 'CrashCourse', 'thumbnail': 'https://img.youtube.com/vi/ZM8ECpBvc0I/mqdefault.jpg'},
    ],
    'english': [
        {'video_id': 'hC_24rB5U2M', 'title': 'English Grammar & Essay Writing Masterclass', 'channel': 'Learn English Lab', 'thumbnail': 'https://img.youtube.com/vi/hC_24rB5U2M/mqdefault.jpg'},
    ],
    'css': [
        {'video_id': 'mIXGDn67rXo', 'title': 'Pakistan Affairs & Governance Analysis', 'channel': 'World Affairs', 'thumbnail': 'https://img.youtube.com/vi/mIXGDn67rXo/mqdefault.jpg'},
    ],
}

DEFAULT_FALLBACK = [
    {'video_id': '_uQrJ0TkZlc', 'title': 'Python Full Course for Beginners', 'channel': 'Programming with Mosh', 'thumbnail': 'https://img.youtube.com/vi/_uQrJ0TkZlc/mqdefault.jpg'},
    {'video_id': 'G3e-cpL7ofc', 'title': 'HTML CSS JS Full Course', 'channel': 'SuperSimpleDev', 'thumbnail': 'https://img.youtube.com/vi/G3e-cpL7ofc/mqdefault.jpg'},
    {'video_id': 'GwIo3gDZCVQ', 'title': 'Machine Learning Course', 'channel': 'Simplilearn', 'thumbnail': 'https://img.youtube.com/vi/GwIo3gDZCVQ/mqdefault.jpg'},
    {'video_id': '8hly31xKli0', 'title': 'Algorithms & Data Structures', 'channel': 'freeCodeCamp', 'thumbnail': 'https://img.youtube.com/vi/8hly31xKli0/mqdefault.jpg'},
]


def get_fallback_for_topic(topic, field=''):
    """Return relevant fallback educational videos matching a topic or field."""
    text = f"{topic} {field}".lower()
    for kw, videos in FALLBACK_CATALOG.items():
        if kw in text:
            return [{**v, 'topic': topic} for v in videos]
    return [{**v, 'topic': topic} for v in DEFAULT_FALLBACK[:2]]


def fallback_for_query(query, reason, expert, score, topic=''):
    """Return a single fallback item for recommendation engine."""
    videos = get_fallback_for_topic(topic or query, query)
    fb = videos[0] if videos else DEFAULT_FALLBACK[0]
    return {
        **fb,
        'topic'      : topic or fb.get('topic', ''),
        'reason'     : reason or '🎯 Recommended based on your field',
        'expert'     : expert or 'history',
        'final_score': score or 0.85,
    }


def get_yt():
    key = os.getenv('YOUTUBE_API_KEY')
    if not key:
        return None
    return build('youtube', 'v3', developerKey=key)


def is_quota_err(e):
    # Only the daily limit. Other 403s (a blocked or wrong key) are not quota
    # errors and must show up in the logs instead of silently stopping searches.
    msg = str(e).lower()
    return 'quota' in msg or 'dailylimitexceeded' in msg or 'ratelimitexceeded' in msg


def get_cache(key):
    if key in _cache:
        data, ts = _cache[key]
        if time.time() - ts < CACHE_EXPIRY:
            return data
        del _cache[key]
    return None


def set_cache(key, data):
    _cache[key] = (data, time.time())


def search_youtube(yt, query, limit=5):
    """
    Search YouTube with educational filtering.
    Does not restrict to Category 27 upfront because most university/tech
    courses are under Science & Tech (Cat 28) or others.
    """
    if is_entertainment_query(query):
        return []
    try:
        # Search educational keywords
        res = yt.search().list(
            q=query + ' tutorial lecture',
            part='snippet',
            maxResults=limit,
            type='video',
            relevanceLanguage='en',
            safeSearch='strict'
        ).execute()

        items = [{
            'video_id'   : i['id']['videoId'],
            'title'      : i['snippet']['title'],
            'thumbnail'  : i['snippet']['thumbnails']['medium']['url'],
            'channel'    : i['snippet']['channelTitle'],
            'description': i['snippet'].get('description', ''),
        } for i in res.get('items', []) if i.get('id', {}).get('videoId')]

        filtered = filter_educational_videos(items)
        if filtered:
            return filtered
        if items:
            return items

        # Simpler retry if 0 results
        res2 = yt.search().list(
            q=query, part='snippet', maxResults=limit,
            type='video', relevanceLanguage='en', safeSearch='strict'
        ).execute()
        items2 = [{
            'video_id'   : i['id']['videoId'],
            'title'      : i['snippet']['title'],
            'thumbnail': i['snippet']['thumbnails']['medium']['url'],
            'channel'    : i['snippet']['channelTitle'],
            'description': i['snippet'].get('description', ''),
        } for i in res2.get('items', []) if i.get('id', {}).get('videoId')]
        return filter_educational_videos(items2) or items2

    except Exception as e:
        print(f"[YouTube Search] Notice: {e}")
        if is_quota_err(e):
            raise e
        return []


def get_db_cache(query):
    cached = execute_query(
        "SELECT results FROM search_cache WHERE query=%s AND expires_at > NOW()",
        (query.lower(),), fetch=True
    )
    if cached and cached[0].get('results'):
        try:
            data = json.loads(cached[0]['results'])
            if data and len(data) > 0:
                return data
        except Exception:
            pass
    return None


def save_db_cache(query, videos):
    if not videos or len(videos) == 0:
        return  # Never cache empty lists
    try:
        execute_query(
            """INSERT INTO search_cache (query, results)
               VALUES (%s,%s)
               ON DUPLICATE KEY UPDATE
               results=%s, created_at=NOW(),
               expires_at=(NOW() + INTERVAL 24 HOUR)""",
            (query.lower(), json.dumps(videos), json.dumps(videos))
        )
    except Exception:
        pass


# ============================================================
# RECOMMEND VIDEOS — Main MoE Route
# ============================================================
@recommend_bp.route('/recommend/videos')
@login_required
def recommend_videos():
    user_id = session['user_id']

    # Cache check
    cache_key = f"rec_{user_id}"
    cached    = None if request.args.get('refresh') == '1' else get_cache(cache_key)
    if cached and len(cached) > 0:
        return jsonify({'success': True, 'recommendations': cached, 'cached': True,
                        'weights': get_cache(f"recw_{user_id}")})

    moe     = TransformerMoE(user_id)
    queries = moe.get_recommendations()
    weights = moe.weights

    watched_ids = {
        w['video_id'] for w in
        (execute_query("SELECT video_id FROM watched_videos WHERE user_id=%s",
                       (user_id,), fetch=True) or [])
    }
    # Videos the student marked "Not for me" are never shown again
    watched_ids |= {
        r['video_id'] for r in
        (execute_query("""SELECT video_id FROM recommendation_history
                          WHERE user_id=%s AND feedback='not_for_me'""",
                       (user_id,), fetch=True) or [])
    }

    recommendations = []
    quota_exceeded  = False
    got_real_videos = False   # from YouTube or its saved results, not the backup list
    # Spread the 20 slots across queries/topics so every goal row gets picks
    PER_QUERY, PER_TOPIC = 3, 4
    topic_count = {}

    try:
        yt = get_yt()
    except Exception:
        quota_exceeded = True
        yt = None

    for q in queries[:8]:
        if len(recommendations) >= 20:
            break

        q_topic = q.get('topic', '')
        q_videos = []

        if quota_exceeded or yt is None:
            v = fallback_for_query(q['query'], q['reason'], q['expert'], q['final_score'], q_topic)
            if v['video_id'] not in watched_ids:
                recommendations.append(v)
            continue

        # DB cache
        db_videos = get_db_cache(q['query'])
        if db_videos and len(db_videos) > 0:
            q_videos = db_videos[:3]

        # YouTube API
        if not q_videos and not quota_exceeded:
            try:
                yt_videos = search_youtube(yt, q['query'], 5)
                if yt_videos and len(yt_videos) > 0:
                    q_videos = yt_videos[:PER_QUERY]
                    save_db_cache(q['query'], yt_videos)
            except Exception as e:
                if is_quota_err(e):
                    quota_exceeded = True

        # Fallback if YouTube search yielded no videos
        if not q_videos:
            v = fallback_for_query(q['query'], q['reason'], q['expert'], q['final_score'], q_topic)
            if v['video_id'] not in watched_ids:
                recommendations.append(v)
            continue

        got_real_videos = True
        for v in q_videos:
            if topic_count.get(q_topic, 0) >= PER_TOPIC:
                break
            if v['video_id'] not in watched_ids:
                topic_count[q_topic] = topic_count.get(q_topic, 0) + 1
                recommendations.append({
                    **v,
                    'topic'       : q_topic,   # MoE topic, so watch/quiz history is logged under it
                    'topic_score' : q.get('topic_score'),
                    'reason'      : q['reason'],
                    'expert'      : q['expert'],
                    'final_score' : q['final_score'],
                    'priority'    : q.get('priority', 'medium'),
                    'weight_used' : q.get('weight_used', 0),
                })

    # Deduplicate + sort
    seen, final = set(), []
    for r in recommendations:
        if r['video_id'] not in seen:
            seen.add(r['video_id'])
            final.append(r)

    # Safety: Guarantee at least default fallback if empty
    if not final:
        default_fb = get_fallback_for_topic(moe.data.get('field', ''), '')
        for fb in default_fb:
            final.append(fallback_for_query(fb.get('title', ''), 'Recommended for your field', 'history', 0.90))

    final.sort(key=lambda x: x['final_score'], reverse=True)
    result = final[:20]

    # Don't keep a backup-only list: once YouTube works again, the next visit should use it
    if result and got_real_videos:
        set_cache(cache_key, result)
        set_cache(f"recw_{user_id}", weights)
    elif not got_real_videos:
        print("[Recommend] YouTube returned no videos; showing the backup list (not cached)")

    return jsonify({
        'success'        : True,
        'recommendations': result,
        'total'          : len(result),
        'weights'        : weights,
        'quota_exceeded' : quota_exceeded,
    })


# ============================================================
# FEEDBACK — "Helpful" / "I know this" / "Not for me" on a card
# ============================================================
FEEDBACK_TYPES = ('helpful', 'known', 'not_for_me')

@recommend_bp.route('/recommend/feedback', methods=['POST'])
@login_required
def recommendation_feedback():
    data     = request.get_json(silent=True) or {}
    video_id = str(data.get('video_id', '')).strip()[:50]
    feedback = data.get('feedback')
    if not video_id or feedback not in FEEDBACK_TYPES:
        return jsonify({'success': False, 'message': 'Invalid feedback.'}), 400

    saved = execute_query(
        """INSERT INTO recommendation_history
           (user_id, video_id, reason, topic, expert, feedback)
           VALUES (%s,%s,%s,%s,%s,%s)""",
        (session['user_id'], video_id,
         str(data.get('reason', ''))[:255],
         str(data.get('topic', ''))[:150],
         str(data.get('expert', ''))[:30],
         feedback)
    )
    if saved is False:
        return jsonify({'success': False, 'message': 'Could not save feedback.'}), 500

    # Next load should reflect the feedback
    _cache.pop(f"rec_{session['user_id']}", None)
    return jsonify({'success': True})


# ============================================================
# PREFERENCE VIDEOS — New user initial recommendations
# ============================================================
@recommend_bp.route('/recommend/preference-videos')
@login_required
def preference_videos():
    user_id = session['user_id']

    user_prefs = execute_query(
        "SELECT field_of_interest, education_category, skill_level FROM users WHERE id=%s",
        (user_id,), fetch=True
    )

    field     = ''
    skill_lvl = 'Beginner'

    if user_prefs:
        field     = user_prefs[0].get('field_of_interest') or user_prefs[0].get('education_category') or ''
        skill_lvl = user_prefs[0].get('skill_level') or 'Beginner'

    if not field:
        field = session.get('field_of_interest') or session.get('education_category') or 'Computer Science'

    topics = get_topics_for_field(field)
    if not topics:
        topics = ['Computer Science', 'Web Development', 'Python Programming', 'General Knowledge']

    suffix_map = {
        'Beginner'    : 'complete beginners tutorial',
        'Intermediate': 'intermediate tutorial',
        'Advanced'    : 'advanced tutorial',
    }
    suffix = suffix_map.get(skill_lvl, 'tutorial')

    cache_key = f"pref_{user_id}_{field}_{skill_lvl}"
    cached    = get_cache(cache_key)
    if cached and len(cached) > 0:
        return jsonify({
            'success'    : True,
            'videos'     : cached,
            'field'      : field,
            'skill_level': skill_lvl,
            'total'      : len(cached),
        })

    videos          = []
    quota_exceeded  = False
    got_real_videos = False

    try:
        yt = get_yt()
    except Exception:
        quota_exceeded = True
        yt = None

    for topic in topics[:4]:
        if len(videos) >= 12:
            break

        query        = f"{topic} {suffix}"
        topic_videos = []

        # 1. DB cache check (only non-empty results)
        db_videos = get_db_cache(query)
        if db_videos and len(db_videos) > 0:
            topic_videos = [v for v in db_videos if isinstance(v, dict) and v.get('video_id')][:3]

        # 2. YouTube API search
        if not topic_videos and not quota_exceeded and yt is not None:
            try:
                yt_videos = search_youtube(yt, query, 3)
                if yt_videos and len(yt_videos) > 0:
                    topic_videos = yt_videos
                    save_db_cache(query, yt_videos)
            except Exception as e:
                if is_quota_err(e):
                    quota_exceeded = True

        # 3. Domain-specific fallback if YouTube API unavailable, empty or failed
        if topic_videos:
            got_real_videos = True
        else:
            topic_videos = get_fallback_for_topic(topic, field)

        for v in topic_videos:
            videos.append({**v, 'topic': topic})

    # Deduplicate
    seen, final = set(), []
    for v in videos:
        if v.get('video_id') and v['video_id'] not in seen:
            seen.add(v['video_id'])
            final.append(v)

    # Guaranteed fallback if still empty
    if not final:
        for fb in get_fallback_for_topic(field, field):
            final.append({**fb, 'topic': field})

    if final and got_real_videos:
        set_cache(cache_key, final)

    return jsonify({
        'success'    : True,
        'videos'     : final[:12],
        'field'      : field,
        'skill_level': skill_lvl,
        'total'      : len(final),
    })


# ============================================================
# WEAK TOPICS
# ============================================================
@recommend_bp.route('/recommend/weak-topics')
@login_required
def get_weak_topics():
    user_id = session['user_id']
    weak    = execute_query(
        """SELECT topic, fail_count, last_detected
           FROM weak_topics WHERE user_id=%s
           ORDER BY fail_count DESC""",
        (user_id,), fetch=True
    )
    return jsonify({'success': True, 'weak_topics': weak or []})


# ============================================================
# MOE ANALYSIS
# ============================================================
@recommend_bp.route('/recommend/moe-analysis')
@login_required
def moe_analysis():
    user_id  = session['user_id']
    moe      = TransformerMoE(user_id)
    analysis = moe.get_analysis()
    return jsonify({'success': True, 'analysis': analysis})