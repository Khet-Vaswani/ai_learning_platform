# ============================================================
# youtube.py — YouTube Search with Caching & Quota Management
# ============================================================


from flask import Blueprint, request, jsonify, session
from app.utils.auth_helpers import login_required
from app.utils.db import execute_query
from googleapiclient.discovery import build
import os, time

youtube_bp = Blueprint('youtube', __name__)

# ── In-memory cache ───────────────────────────────────────
_cache       = {}
CACHE_EXPIRY = 3600  # 1 hour

# ── Fallback videos (when quota exceeded) ─────────────────
FALLBACK_VIDEOS = {
    'python': [
        {'video_id':'_uQrJ0TkZlc', 'title':'Python Full Course for Beginners', 'channel':'Programming with Mosh', 'thumbnail':'https://img.youtube.com/vi/_uQrJ0TkZlc/mqdefault.jpg', 'description':'Learn Python basics'},
        {'video_id':'rfscVS0vtbw', 'title':'Learn Python in 4 Hours', 'channel':'freeCodeCamp', 'thumbnail':'https://img.youtube.com/vi/rfscVS0vtbw/mqdefault.jpg', 'description':'Python tutorial'},
        {'video_id':'eWRfhZUzrAc', 'title':'Python for Everybody', 'channel':'Dr. Chuck', 'thumbnail':'https://img.youtube.com/vi/eWRfhZUzrAc/mqdefault.jpg', 'description':'Python course'},
        {'video_id':'kqtD5dpn9C8', 'title':'Python Tutorial for Beginners', 'channel':'Telusko', 'thumbnail':'https://img.youtube.com/vi/kqtD5dpn9C8/mqdefault.jpg', 'description':'Python basics'},
    ],
    'machine learning': [
        {'video_id':'GwIo3gDZCVQ', 'title':'Machine Learning Full Course', 'channel':'Simplilearn', 'thumbnail':'https://img.youtube.com/vi/GwIo3gDZCVQ/mqdefault.jpg', 'description':'ML course'},
        {'video_id':'aircAruvnKk', 'title':'Neural Networks explained', 'channel':'3Blue1Brown', 'thumbnail':'https://img.youtube.com/vi/aircAruvnKk/mqdefault.jpg', 'description':'Neural networks'},
        {'video_id':'i_LwzRVP7bg', 'title':'Machine Learning for Beginners', 'channel':'freeCodeCamp', 'thumbnail':'https://img.youtube.com/vi/i_LwzRVP7bg/mqdefault.jpg', 'description':'ML basics'},
    ],
    'web development': [
        {'video_id':'G3e-cpL7ofc', 'title':'HTML CSS JavaScript Full Course', 'channel':'SuperSimpleDev', 'thumbnail':'https://img.youtube.com/vi/G3e-cpL7ofc/mqdefault.jpg', 'description':'Web development'},
        {'video_id':'nu_pCVPKzTk', 'title':'Flask Tutorial', 'channel':'Tech With Tim', 'thumbnail':'https://img.youtube.com/vi/nu_pCVPKzTk/mqdefault.jpg', 'description':'Flask web framework'},
        {'video_id':'Z1RJmh_OqeA', 'title':'Learn Flask in 1 Hour', 'channel':'Programming with Mosh', 'thumbnail':'https://img.youtube.com/vi/Z1RJmh_OqeA/mqdefault.jpg', 'description':'Flask tutorial'},
    ],
    'javascript': [
        {'video_id':'W6NZfCO5SIk', 'title':'JavaScript Tutorial for Beginners', 'channel':'Programming with Mosh', 'thumbnail':'https://img.youtube.com/vi/W6NZfCO5SIk/mqdefault.jpg', 'description':'JS basics'},
        {'video_id':'PkZNo7MFNFg', 'title':'Learn JavaScript Full Course', 'channel':'freeCodeCamp', 'thumbnail':'https://img.youtube.com/vi/PkZNo7MFNFg/mqdefault.jpg', 'description':'JavaScript course'},
    ],
    'data science': [
        {'video_id':'ua-CiDNNj30', 'title':'Data Science Full Course', 'channel':'freeCodeCamp', 'thumbnail':'https://img.youtube.com/vi/ua-CiDNNj30/mqdefault.jpg', 'description':'Data science'},
        {'video_id':'LHBE6Q9XlzI', 'title':'Python for Data Science', 'channel':'freeCodeCamp', 'thumbnail':'https://img.youtube.com/vi/LHBE6Q9XlzI/mqdefault.jpg', 'description':'Data science with Python'},
    ],
    'algorithms': [
        {'video_id':'8hly31xKli0', 'title':'Algorithms and Data Structures', 'channel':'freeCodeCamp', 'thumbnail':'https://img.youtube.com/vi/8hly31xKli0/mqdefault.jpg', 'description':'Algorithms course'},
        {'video_id':'BBpAmxU_NQo', 'title':'Data Structures Easy to Advanced', 'channel':'freeCodeCamp', 'thumbnail':'https://img.youtube.com/vi/BBpAmxU_NQo/mqdefault.jpg', 'description':'Data structures'},
    ],
    'default': [
        {'video_id':'_uQrJ0TkZlc', 'title':'Python Full Course for Beginners', 'channel':'Programming with Mosh', 'thumbnail':'https://img.youtube.com/vi/_uQrJ0TkZlc/mqdefault.jpg', 'description':'Python course'},
        {'video_id':'rfscVS0vtbw', 'title':'Learn Python in 4 Hours', 'channel':'freeCodeCamp', 'thumbnail':'https://img.youtube.com/vi/rfscVS0vtbw/mqdefault.jpg', 'description':'Python tutorial'},
        {'video_id':'G3e-cpL7ofc', 'title':'HTML CSS JavaScript Full Course', 'channel':'SuperSimpleDev', 'thumbnail':'https://img.youtube.com/vi/G3e-cpL7ofc/mqdefault.jpg', 'description':'Web dev'},
        {'video_id':'GwIo3gDZCVQ', 'title':'Machine Learning Full Course', 'channel':'Simplilearn', 'thumbnail':'https://img.youtube.com/vi/GwIo3gDZCVQ/mqdefault.jpg', 'description':'ML course'},
        {'video_id':'8hly31xKli0', 'title':'Algorithms and Data Structures', 'channel':'freeCodeCamp', 'thumbnail':'https://img.youtube.com/vi/8hly31xKli0/mqdefault.jpg', 'description':'Algorithms'},
        {'video_id':'nu_pCVPKzTk', 'title':'Flask Tutorial', 'channel':'Tech With Tim', 'thumbnail':'https://img.youtube.com/vi/nu_pCVPKzTk/mqdefault.jpg', 'description':'Flask'},
    ]
}


def get_yt():
    return build(
        'youtube', 'v3',
        developerKey=os.getenv('YOUTUBE_API_KEY')
    )


def get_cache(key):
    """Get from cache if not expired"""
    if key in _cache:
        data, timestamp = _cache[key]
        if time.time() - timestamp < CACHE_EXPIRY:
            return data
        del _cache[key]
    return None


def set_cache(key, data):
    """Save to cache"""
    _cache[key] = (data, time.time())


def get_fallback(query):
    """Return fallback videos based on query keywords"""
    q = query.lower()
    for keyword, videos in FALLBACK_VIDEOS.items():
        if keyword in q:
            return videos
    return FALLBACK_VIDEOS['default']


def is_quota_error(e):
    """Check if error is quota exceeded"""
    return '403' in str(e) or 'quota' in str(e).lower()


# ============================================================
# SEARCH VIDEOS
# ============================================================
@youtube_bp.route('/youtube/search')
@login_required
def search_videos():
    query = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 50))

    if not query:
        return jsonify({'success': False, 'message': 'Query required'})

    # Check cache first
    cache_key = f"search_{query.lower()}_{limit}"
    cached = get_cache(cache_key)
    if cached:
        print(f"✅ Cache hit: {query}")
        return jsonify({'success': True, 'videos': cached, 'query': query})

    # Try YouTube API
    try:
        res = get_yt().search().list(
            q                 = query + ' tutorial',
            part              = 'snippet',
            maxResults        = min(limit, 50),
            type              = 'video',
            relevanceLanguage = 'en',
            safeSearch        = 'strict'
        ).execute()

        videos = []
        for i in res.get('items', []):
            videos.append({
                'video_id'   : i['id']['videoId'],
                'title'      : i['snippet']['title'],
                'thumbnail'  : i['snippet']['thumbnails']['medium']['url'],
                'channel'    : i['snippet']['channelTitle'],
                'description': i['snippet']['description'][:120],
                'published'  : i['snippet']['publishedAt'][:10]
            })

        # Save to cache
        set_cache(cache_key, videos)
        print(f"✅ YouTube search: {query} ({len(videos)} results)")

        return jsonify({
            'success': True,
            'videos' : videos,
            'query'  : query,
            'total'  : len(videos)
        })

    except Exception as e:
        if is_quota_error(e):
            print(f"⚠️ YouTube quota exceeded — using fallback for: {query}")
            fallback = get_fallback(query)
            return jsonify({
                'success' : True,
                'videos'  : fallback,
                'query'   : query,
                'total'   : len(fallback),
                'fallback': True
            })
        else:
            print(f"❌ YouTube error: {e}")
            return jsonify({'success': False, 'message': str(e)})


# ============================================================
# VIDEO DETAILS
# ============================================================
@youtube_bp.route('/youtube/video-details')
@login_required
def video_details():
    video_id = request.args.get('video_id', '').strip()
    if not video_id:
        return jsonify({'success': False})

    # Check cache
    cache_key = f"details_{video_id}"
    cached = get_cache(cache_key)
    if cached:
        return jsonify({'success': True, 'video': cached})

    try:
        res = get_yt().videos().list(
            part = 'snippet,statistics',
            id   = video_id
        ).execute()

        items = res.get('items', [])
        if not items:
            return jsonify({'success': False})

        item    = items[0]
        snippet = item['snippet']
        stats   = item.get('statistics', {})

        video_data = {
            'video_id'     : video_id,
            'title'        : snippet.get('title', ''),
            'description'  : snippet.get('description', '')[:500],
            'channel_title': snippet.get('channelTitle', ''),
            'published_at' : snippet.get('publishedAt', ''),
            'view_count'   : stats.get('viewCount', '0'),
            'like_count'   : stats.get('likeCount', '0'),
            'comment_count': stats.get('commentCount', '0'),
        }

        set_cache(cache_key, video_data)
        return jsonify({'success': True, 'video': video_data})

    except Exception as e:
        if is_quota_error(e):
            # Return basic info without API call
            return jsonify({
                'success': True,
                'video'  : {
                    'video_id'     : video_id,
                    'title'        : '',
                    'description'  : 'Video details unavailable (quota exceeded)',
                    'channel_title': 'YouTube',
                    'published_at' : '',
                    'view_count'   : '0',
                    'like_count'   : '0',
                    'comment_count': '0',
                }
            })
        print(f"❌ Video details error: {e}")
        return jsonify({'success': False, 'message': str(e)})


# ============================================================
# SAVE WATCHED
# ============================================================
@youtube_bp.route('/youtube/watched', methods=['POST'])
@login_required
def save_watched():
    data    = request.get_json()
    user_id = session['user_id']

    video_id    = data.get('video_id', '')
    video_title = data.get('title', '')
    topic       = data.get('topic', 'General')

    if not video_id:
        return jsonify({'success': False})

    execute_query(
        """INSERT IGNORE INTO watched_videos
           (user_id, video_id, video_title, topic)
           VALUES (%s,%s,%s,%s)""",
        (user_id, video_id, video_title, topic)
    )
    return jsonify({'success': True})


# ============================================================
# WATCH HISTORY
# ============================================================
@youtube_bp.route('/youtube/history')
@login_required
def watch_history():
    user_id = session['user_id']
    history = execute_query(
        """SELECT video_id, video_title, topic, watched_at
           FROM watched_videos WHERE user_id=%s
           ORDER BY watched_at DESC LIMIT 20""",
        (user_id,), fetch=True
    )
    return jsonify({'success': True, 'history': history or []})

@youtube_bp.route('/youtube/related')
@login_required
def related_videos():
    topic    = request.args.get('topic', '').strip()
    video_id = request.args.get('video_id', '').strip()

    if not topic:
        return jsonify({'success': False})

    cache_key = f"related_{topic.lower()}"
    cached    = get_cache(cache_key)
    if cached:
        return jsonify({'success': True, 'videos': cached})

    try:
        res = get_yt().search().list(
            q                 = topic + ' tutorial',
            part              = 'snippet',
            maxResults        = 8,
            type              = 'video',
            relevanceLanguage = 'en',
            safeSearch        = 'strict'
        ).execute()

        videos = []
        for i in res.get('items', []):
            vid = i['id']['videoId']
            if vid != video_id:  # Skip current video
                videos.append({
                    'video_id' : vid,
                    'title'    : i['snippet']['title'],
                    'thumbnail': i['snippet']['thumbnails']['medium']['url'],
                    'channel'  : i['snippet']['channelTitle']
                })

        set_cache(cache_key, videos)
        return jsonify({'success': True, 'videos': videos})

    except Exception as e:
        if is_quota_error(e):
            fallback = get_fallback(topic)
            filtered = [v for v in fallback if v['video_id'] != video_id]
            return jsonify({'success': True, 'videos': filtered})
        return jsonify({'success': False, 'message': str(e)})
    
# ============================================================
# Transcript Route — Add this to your app/routes/youtube.py
# ============================================================
# pip install youtube-transcript-api --break-system-packages
# ============================================================


# ── Add this route inside youtube.py ─────────────────────
# (Keep all your existing routes, just ADD this one)

# ============================================================
# ADD THIS ROUTE TO app/routes/youtube.py
# Paste inside youtube.py (after imports, with other routes)
# ============================================================

@youtube_bp.route('/youtube/transcript')
@login_required
def get_transcript():
    """
    Extract transcript from YouTube video.
    Priority:
    1. DB cache (instant)
    2. YouTube captions API
    3. Video description fallback
    """
    video_id = request.args.get('video_id', '').strip()
    if not video_id:
        return jsonify({'success': False, 'message': 'video_id required'})

    # ── Step 1: Check DB cache ────────────────────────────
    try:
        cached = execute_query(
            """SELECT transcript_text, source, word_count
               FROM video_transcripts
               WHERE video_id = %s""",
            (video_id,), fetch=True
        )
        if cached and cached[0]['transcript_text']:
            print(f"✅ Transcript from DB cache: {video_id}")
            return jsonify({
                'success'   : True,
                'transcript': cached[0]['transcript_text'],
                'source'    : cached[0]['source'],
                'length'    : cached[0]['word_count'],
                'cached'    : True,
            })
    except Exception as e:
        print(f"⚠️ Cache check error: {e}")

    # ── Step 2: YouTube captions ──────────────────────────
    try:
        from youtube_transcript_api import (
            YouTubeTranscriptApi,
            TranscriptsDisabled,
            NoTranscriptFound,
        )

        transcript_text = ''
        source          = 'youtube_captions'

        try:
            # Try manual captions first (more accurate)
            segments = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=['en', 'en-US', 'en-GB', 'en-IN']
            )
            transcript_text = ' '.join(s['text'] for s in segments)

        except NoTranscriptFound:
            # Try auto-generated captions
            try:
                all_t    = YouTubeTranscriptApi.list_transcripts(video_id)
                auto     = all_t.find_generated_transcript(['en'])
                segments = auto.fetch()
                transcript_text = ' '.join(s['text'] for s in segments)
                source   = 'youtube_auto_captions'
            except Exception:
                pass

        if transcript_text and len(transcript_text) > 100:
            # Clean transcript
            import re
            cleaned = re.sub(r'\[.*?\]', '', transcript_text)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()

            word_count = len(cleaned.split())

            # Save to cache
            _save_transcript_cache(video_id, cleaned, source, word_count)

            print(f"✅ YouTube transcript: {word_count} words ({source})")
            return jsonify({
                'success'   : True,
                'transcript': cleaned,
                'source'    : source,
                'length'    : word_count,
                'cached'    : False,
            })

    except ImportError:
        print("⚠️ youtube-transcript-api not installed")
        print("   Run: pip install youtube-transcript-api")
    except TranscriptsDisabled:
        print(f"⚠️ Transcripts disabled for: {video_id}")
    except Exception as e:
        print(f"⚠️ Caption extraction failed: {e}")

    # ── Step 3: Video description fallback ───────────────
    try:
        yt = build('youtube', 'v3',
                   developerKey=os.getenv('YOUTUBE_API_KEY'))
        resp = yt.videos().list(
            part='snippet',
            id  = video_id
        ).execute()

        if resp.get('items'):
            snippet = resp['items'][0]['snippet']
            desc    = snippet.get('description', '')
            title   = snippet.get('title', '')
            tags    = ', '.join(snippet.get('tags', [])[:10])

            if desc and len(desc) > 100:
                fallback_text = (
                    f"Video Title: {title}\n\n"
                    f"Description: {desc[:2000]}\n\n"
                    f"Tags: {tags}"
                )
                word_count = len(fallback_text.split())
                _save_transcript_cache(video_id, fallback_text, 'description', word_count)

                print(f"✅ Description fallback: {word_count} words")
                return jsonify({
                    'success'   : True,
                    'transcript': fallback_text,
                    'source'    : 'description',
                    'length'    : word_count,
                    'cached'    : False,
                })
    except Exception as e:
        print(f"⚠️ Description fallback error: {e}")

    # ── Nothing worked ────────────────────────────────────
    print(f"❌ No transcript available for: {video_id}")
    return jsonify({
        'success'   : False,
        'transcript': '',
        'source'    : 'none',
        'length'    : 0,
        'message'   : 'Transcript not available for this video',
    })


def _save_transcript_cache(
    video_id  : str,
    text      : str,
    source    : str,
    word_count: int
):
    """Save transcript to DB cache."""
    try:
        execute_query(
            """INSERT INTO video_transcripts
               (video_id, transcript_text, source, word_count)
               VALUES (%s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               transcript_text = VALUES(transcript_text),
               source          = VALUES(source),
               word_count      = VALUES(word_count),
               created_at      = NOW()""",
            (video_id, text, source, word_count)
        )
    except Exception as e:
        print(f"⚠️ Transcript cache save error: {e}")