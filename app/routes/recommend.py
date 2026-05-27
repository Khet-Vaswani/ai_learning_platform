# ============================================================
# recommend.py — MoE Recommendation Routes
# ============================================================

from flask import Blueprint, jsonify, session
from app.utils.auth_helpers import login_required
from app.utils.db import execute_query
from app.ai.moe_engine import TransformerMoE, FIELD_TOPICS
from googleapiclient.discovery import build
import os, time, json

recommend_bp = Blueprint('recommend', __name__)

_cache       = {}
CACHE_EXPIRY = 900  # 15 min


FALLBACK = [
    {'video_id':'_uQrJ0TkZlc', 'title':'Python Full Course',         'channel':'Programming with Mosh',  'thumbnail':'https://img.youtube.com/vi/_uQrJ0TkZlc/mqdefault.jpg'},
    {'video_id':'rfscVS0vtbw', 'title':'Learn Python in 4 Hours',    'channel':'freeCodeCamp',            'thumbnail':'https://img.youtube.com/vi/rfscVS0vtbw/mqdefault.jpg'},
    {'video_id':'G3e-cpL7ofc', 'title':'HTML CSS JS Full Course',     'channel':'SuperSimpleDev',          'thumbnail':'https://img.youtube.com/vi/G3e-cpL7ofc/mqdefault.jpg'},
    {'video_id':'GwIo3gDZCVQ', 'title':'Machine Learning Course',     'channel':'Simplilearn',             'thumbnail':'https://img.youtube.com/vi/GwIo3gDZCVQ/mqdefault.jpg'},
    {'video_id':'nu_pCVPKzTk', 'title':'Flask Tutorial',             'channel':'Tech With Tim',           'thumbnail':'https://img.youtube.com/vi/nu_pCVPKzTk/mqdefault.jpg'},
    {'video_id':'8hly31xKli0', 'title':'Algorithms & Data Structures','channel':'freeCodeCamp',            'thumbnail':'https://img.youtube.com/vi/8hly31xKli0/mqdefault.jpg'},
    {'video_id':'W6NZfCO5SIk', 'title':'JavaScript Tutorial',        'channel':'Programming with Mosh',  'thumbnail':'https://img.youtube.com/vi/W6NZfCO5SIk/mqdefault.jpg'},
    {'video_id':'ua-CiDNNj30', 'title':'Data Science Full Course',   'channel':'freeCodeCamp',            'thumbnail':'https://img.youtube.com/vi/ua-CiDNNj30/mqdefault.jpg'},
]

FALLBACK_MAP = {
    'python'     : '_uQrJ0TkZlc',
    'flask'      : 'nu_pCVPKzTk',
    'machine'    : 'GwIo3gDZCVQ',
    'javascript' : 'W6NZfCO5SIk',
    'data'       : 'ua-CiDNNj30',
    'algorithm'  : '8hly31xKli0',
    'html'       : 'G3e-cpL7ofc',
    'web'        : 'G3e-cpL7ofc',
}


def get_yt():
    return build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))


def is_quota_err(e):
    return '403' in str(e) or 'quota' in str(e).lower()


def get_cache(key):
    if key in _cache:
        data, ts = _cache[key]
        if time.time() - ts < CACHE_EXPIRY:
            return data
        del _cache[key]
    return None


def set_cache(key, data):
    _cache[key] = (data, time.time())


def fallback_for_query(query, reason, expert, score):
    q = query.lower()
    vid_id = next(
        (v for k, v in FALLBACK_MAP.items() if k in q),
        FALLBACK[0]['video_id']
    )
    fb = next((f for f in FALLBACK if f['video_id'] == vid_id), FALLBACK[0])
    return {**fb, 'reason': reason, 'expert': expert, 'final_score': score}


def search_youtube(yt, query, limit=5):
    """Search YouTube and return video list."""
    res = yt.search().list(
        q=query, part='snippet', maxResults=limit,
        type='video', relevanceLanguage='en', safeSearch='strict'
    ).execute()
    return [{
        'video_id' : i['id']['videoId'],
        'title'    : i['snippet']['title'],
        'thumbnail': i['snippet']['thumbnails']['medium']['url'],
        'channel'  : i['snippet']['channelTitle'],
    } for i in res.get('items', [])]


def get_db_cache(query):
    cached = execute_query(
        "SELECT results FROM search_cache WHERE query=%s AND expires_at > NOW()",
        (query.lower(),), fetch=True
    )
    if cached:
        try:
            return json.loads(cached[0]['results'])
        except:
            pass
    return None


def save_db_cache(query, videos):
    execute_query(
        """INSERT INTO search_cache (query, results)
           VALUES (%s,%s)
           ON DUPLICATE KEY UPDATE
           results=%s, created_at=NOW(),
           expires_at=(NOW() + INTERVAL 24 HOUR)""",
        (query.lower(), json.dumps(videos), json.dumps(videos))
    )


# ============================================================
# RECOMMEND VIDEOS — Main route
# ============================================================
@recommend_bp.route('/recommend/videos')
@login_required
def recommend_videos():
    user_id = session['user_id']

    # Cache check
    cache_key = f"rec_{user_id}"
    cached    = get_cache(cache_key)
    if cached:
        return jsonify({'success': True, 'recommendations': cached, 'cached': True})

    moe     = TransformerMoE(user_id)
    queries = moe.get_recommendations()
    weights = moe.weights

    watched_ids = {
        w['video_id'] for w in
        (execute_query("SELECT video_id FROM watched_videos WHERE user_id=%s",
                       (user_id,), fetch=True) or [])
    }

    recommendations = []
    quota_exceeded  = False

    try:
        yt = get_yt()
    except Exception:
        quota_exceeded = True
        yt = None

    for q in queries[:8]:
        if len(recommendations) >= 20:
            break

        if quota_exceeded or yt is None:
            v = fallback_for_query(q['query'], q['reason'], q['expert'], q['final_score'])
            if v['video_id'] not in watched_ids:
                recommendations.append(v)
            continue

        # DB cache
        db_videos = get_db_cache(q['query'])
        if db_videos:
            for v in db_videos[:3]:
                if v['video_id'] not in watched_ids:
                    recommendations.append({
                        **v,
                        'reason'      : q['reason'],
                        'expert'      : q['expert'],
                        'final_score' : q['final_score'],
                        'priority'    : q.get('priority', 'medium'),
                        'weight_used' : q.get('weight_used', 0),
                    })
            continue

        # YouTube API
        try:
            videos = search_youtube(yt, q['query'], 5)
            save_db_cache(q['query'], videos)
            for v in videos:
                if v['video_id'] not in watched_ids:
                    recommendations.append({
                        **v,
                        'reason'      : q['reason'],
                        'expert'      : q['expert'],
                        'final_score' : q['final_score'],
                        'priority'    : q.get('priority', 'medium'),
                        'weight_used' : q.get('weight_used', 0),
                    })
        except Exception as e:
            if is_quota_err(e):
                quota_exceeded = True
                v = fallback_for_query(q['query'], q['reason'], q['expert'], q['final_score'])
                if v['video_id'] not in watched_ids:
                    recommendations.append(v)

    # Deduplicate + sort
    seen, final = set(), []
    for r in recommendations:
        if r['video_id'] not in seen:
            seen.add(r['video_id'])
            final.append(r)

    final.sort(key=lambda x: x['final_score'], reverse=True)
    result = final[:20]

    if result:
        set_cache(cache_key, result)

    return jsonify({
        'success'        : True,
        'recommendations': result,
        'total'          : len(result),
        'weights'        : weights,
        'quota_exceeded' : quota_exceeded,
    })


# ============================================================
# PREFERENCE VIDEOS — New user initial recommendations
# ============================================================
@recommend_bp.route('/recommend/preference-videos')
@login_required
def preference_videos():
    user_id = session['user_id']

    user_prefs = execute_query(
        "SELECT field_of_interest, skill_level FROM users WHERE id=%s",
        (user_id,), fetch=True
    )

    if not user_prefs or not user_prefs[0]['field_of_interest']:
        return jsonify({'success': False, 'message': 'No preferences set'})

    field     = user_prefs[0]['field_of_interest']
    skill_lvl = user_prefs[0]['skill_level'] or 'Beginner'

    # Use robust resolver
    from app.ai.moe_engine import get_topics_for_field
    topics = get_topics_for_field(field)

    if not topics:
        return jsonify({
            'success'    : False,
            'message'    : f"Field '{field}' not recognized",
            'field'      : field,
        })

    suffix_map = {
        'Beginner'    : 'complete beginners tutorial',
        'Intermediate': 'intermediate tutorial',
        'Advanced'    : 'advanced tutorial',
    }
    suffix = suffix_map.get(skill_lvl, 'tutorial')

    cache_key = f"pref_{user_id}_{field}_{skill_lvl}"
    cached    = get_cache(cache_key)
    if cached:
        return jsonify({
            'success'    : True,
            'videos'     : cached,
            'field'      : field,
            'skill_level': skill_lvl,
        })

    videos         = []
    quota_exceeded = False

    try:
        yt = get_yt()
    except Exception:
        quota_exceeded = True
        yt = None

    for topic in topics[:4]:
        if len(videos) >= 12:
            break

        query = f"{topic} {suffix}"

        if quota_exceeded or yt is None:
            idx = len(videos) % len(FALLBACK)
            videos.append({**FALLBACK[idx], 'topic': topic})
            continue

        db_videos = get_db_cache(query)
        if db_videos:
            for v in db_videos[:3]:
                videos.append({**v, 'topic': topic})
            continue

        try:
            yt_videos = search_youtube(yt, query, 3)
            save_db_cache(query, yt_videos)
            for v in yt_videos:
                videos.append({**v, 'topic': topic})
        except Exception as e:
            if is_quota_err(e):
                quota_exceeded = True
                idx = len(videos) % len(FALLBACK)
                videos.append({**FALLBACK[idx], 'topic': topic})

    # Deduplicate
    seen, final = set(), []
    for v in videos:
        if v['video_id'] not in seen:
            seen.add(v['video_id'])
            final.append(v)

    if final:
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