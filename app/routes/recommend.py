# ============================================================
# recommend.py — Transformer MoE Recommendation Routes
# ============================================================

from flask import Blueprint, jsonify, session
from app.utils.auth_helpers import login_required
from app.utils.db import execute_query
from app.ai.moe_engine import TransformerMoE
from googleapiclient.discovery import build
import os, time, json

recommend_bp = Blueprint('recommend', __name__)

# ── Cache ─────────────────────────────────────────────────
_cache       = {}
CACHE_EXPIRY = 900  # 15 minutes

# ── Fallback Videos ───────────────────────────────────────
FALLBACK = [
    {'video_id':'_uQrJ0TkZlc', 'title':'Python Full Course',
     'channel':'Programming with Mosh',
     'thumbnail':'https://img.youtube.com/vi/_uQrJ0TkZlc/mqdefault.jpg'},
    {'video_id':'rfscVS0vtbw', 'title':'Learn Python in 4 Hours',
     'channel':'freeCodeCamp',
     'thumbnail':'https://img.youtube.com/vi/rfscVS0vtbw/mqdefault.jpg'},
    {'video_id':'G3e-cpL7ofc', 'title':'HTML CSS JS Full Course',
     'channel':'SuperSimpleDev',
     'thumbnail':'https://img.youtube.com/vi/G3e-cpL7ofc/mqdefault.jpg'},
    {'video_id':'GwIo3gDZCVQ', 'title':'Machine Learning Course',
     'channel':'Simplilearn',
     'thumbnail':'https://img.youtube.com/vi/GwIo3gDZCVQ/mqdefault.jpg'},
    {'video_id':'nu_pCVPKzTk', 'title':'Flask Tutorial',
     'channel':'Tech With Tim',
     'thumbnail':'https://img.youtube.com/vi/nu_pCVPKzTk/mqdefault.jpg'},
    {'video_id':'8hly31xKli0', 'title':'Algorithms & Data Structures',
     'channel':'freeCodeCamp',
     'thumbnail':'https://img.youtube.com/vi/8hly31xKli0/mqdefault.jpg'},
    {'video_id':'W6NZfCO5SIk', 'title':'JavaScript Tutorial',
     'channel':'Programming with Mosh',
     'thumbnail':'https://img.youtube.com/vi/W6NZfCO5SIk/mqdefault.jpg'},
    {'video_id':'ua-CiDNNj30', 'title':'Data Science Full Course',
     'channel':'freeCodeCamp',
     'thumbnail':'https://img.youtube.com/vi/ua-CiDNNj30/mqdefault.jpg'},
]


def get_yt():
    return build(
        'youtube', 'v3',
        developerKey=os.getenv('YOUTUBE_API_KEY')
    )


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


def get_fallback_by_topic(query, reason, expert, score):
    """Return fallback video matching query"""
    q   = query.lower()
    res = []

    topic_map = {
        'python'  : '_uQrJ0TkZlc',
        'flask'   : 'nu_pCVPKzTk',
        'machine' : 'GwIo3gDZCVQ',
        'javascript': 'W6NZfCO5SIk',
        'data'    : 'ua-CiDNNj30',
        'algorithm': '8hly31xKli0',
        'html'    : 'G3e-cpL7ofc',
        'web'     : 'G3e-cpL7ofc',
    }

    matched_id = None
    for keyword, vid_id in topic_map.items():
        if keyword in q:
            matched_id = vid_id
            break

    for fb in FALLBACK:
        if matched_id and fb['video_id'] == matched_id:
            res.append({**fb, 'reason': reason,
                        'expert': expert, 'final_score': score})
            break

    if not res and FALLBACK:
        fb = FALLBACK[0]
        res.append({**fb, 'reason': reason,
                    'expert': expert, 'final_score': score})

    return res


# ============================================================
# RECOMMEND VIDEOS
# ============================================================
@recommend_bp.route('/recommend/videos')
@login_required
def recommend_videos():
    user_id = session['user_id']

    # Check cache
    cache_key = f"rec_{user_id}"
    cached    = get_cache(cache_key)
    if cached:
        print(f"✅ Cache hit: user {user_id}")
        return jsonify({
            'success'        : True,
            'recommendations': cached,
            'cached'         : True
        })

    # Initialize Transformer MoE
    moe     = TransformerMoE(user_id)
    queries = moe.get_recommendations()
    weights = moe.weights

    # Watched IDs to exclude
    watched = execute_query(
        "SELECT video_id FROM watched_videos WHERE user_id=%s",
        (user_id,), fetch=True
    ) or []
    watched_ids = set(w['video_id'] for w in watched)

    recommendations = []
    quota_exceeded  = False

    try:
        yt = get_yt()
    except Exception:
        quota_exceeded = True
        yt = None

    for q in queries[:6]:
        if len(recommendations) >= 20:
            break

        if quota_exceeded or yt is None:
            fb = get_fallback_by_topic(
                q['query'], q['reason'],
                q['expert'], q['final_score']
            )
            for v in fb:
                if v['video_id'] not in watched_ids:
                    recommendations.append(v)
            continue

        # Check DB cache
        db_cached = execute_query(
            """SELECT results FROM search_cache
               WHERE query=%s AND expires_at > NOW()""",
            (q['query'].lower(),), fetch=True
        )

        if db_cached:
            try:
                videos = json.loads(db_cached[0]['results'])
                for v in videos[:3]:
                    if v['video_id'] not in watched_ids:
                        recommendations.append({
                            'video_id'   : v['video_id'],
                            'title'      : v['title'],
                            'thumbnail'  : v['thumbnail'],
                            'channel'    : v['channel'],
                            'reason'     : q['reason'],
                            'expert'     : q['expert'],
                            'final_score': q['final_score'],
                            'priority'   : q.get('priority','medium'),
                            'weight_used': q.get('weight_used', 0)
                        })
            except:
                pass
            continue

        # YouTube API
        try:
            res = yt.search().list(
                q                 = q['query'],
                part              = 'snippet',
                maxResults        = 5,
                type              = 'video',
                relevanceLanguage = 'en',
                safeSearch        = 'strict'
            ).execute()

            items = res.get('items', [])

            # Cache results
            cache_data = [{
                'video_id' : i['id']['videoId'],
                'title'    : i['snippet']['title'],
                'thumbnail': i['snippet']['thumbnails']['medium']['url'],
                'channel'  : i['snippet']['channelTitle']
            } for i in items]

            execute_query(
                """INSERT INTO search_cache (query, results)
                   VALUES (%s,%s)
                   ON DUPLICATE KEY UPDATE
                   results=%s, created_at=NOW(),
                   expires_at=(NOW() + INTERVAL 24 HOUR)""",
                (q['query'].lower(),
                 json.dumps(cache_data),
                 json.dumps(cache_data))
            )

            for item in items:
                vid_id = item['id']['videoId']
                if vid_id not in watched_ids:
                    recommendations.append({
                        'video_id'   : vid_id,
                        'title'      : item['snippet']['title'],
                        'thumbnail'  : item['snippet']['thumbnails']['medium']['url'],
                        'channel'    : item['snippet']['channelTitle'],
                        'reason'     : q['reason'],
                        'expert'     : q['expert'],
                        'final_score': q['final_score'],
                        'priority'   : q.get('priority','medium'),
                        'weight_used': q.get('weight_used', 0)
                    })

        except Exception as e:
            if is_quota_err(e):
                print(f"⚠️ Quota exceeded")
                quota_exceeded = True
                fb = get_fallback_by_topic(
                    q['query'], q['reason'],
                    q['expert'], q['final_score']
                )
                for v in fb:
                    if v['video_id'] not in watched_ids:
                        recommendations.append(v)
            else:
                print(f"YouTube error: {e}")
            continue

    # Remove duplicates + sort
    seen  = set()
    final = []
    for r in recommendations:
        if r['video_id'] not in seen:
            seen.add(r['video_id'])
            final.append(r)

    final.sort(key=lambda x: x['final_score'], reverse=True)
    result = final[:20]

    # Cache result
    if result:
        set_cache(cache_key, result)

    print(f"\n✅ Final: {len(result)} recommendations")
    print(f"   Attention Weights Used:")
    print(f"   weak={weights['weak_topic']:.3f} "
          f"perf={weights['performance']:.3f} "
          f"hist={weights['history']:.3f}")

    return jsonify({
        'success'        : True,
        'recommendations': result,
        'total'          : len(result),
        'weights'        : weights,
        'quota_exceeded' : quota_exceeded
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

    return jsonify({
        'success' : True,
        'analysis': analysis
    })
