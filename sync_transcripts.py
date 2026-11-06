#!/usr/bin/env python3
"""
sync_transcripts.py — Fetch YouTube transcripts on this computer and save them
into the database the live site uses.

YouTube often blocks caption requests from cloud servers such as Vercel, but
not from a home connection. Transcripts saved in the database are used by the
live site directly (it checks the saved copy first), so its notes, quizzes and
"ask about a video" answers work for these videos.

Usage (PowerShell, with the hosted database's details for this window only):
    $env:DB_HOST="..."; $env:DB_PORT="..."; $env:DB_USER="..."; $env:DB_PASSWORD="..."; $env:DB_NAME="defaultdb"
    python sync_transcripts.py                  # videos the site has shown or students watched
    python sync_transcripts.py --limit 100
    python sync_transcripts.py VIDEO_ID_OR_URL ...   # specific videos
"""

import argparse
import json
import os
import re
import sys

from dotenv import load_dotenv

load_dotenv()   # does not override DB_* already set in the terminal

from app.utils.db import execute_query
from app.ai.transcript_extractor import (
    VALID_TRANSCRIPT_SOURCES, extract_transcript_full_pipeline, get_cached_transcript)

VIDEO_ID = re.compile(r'(?:v=|youtu\.be/|shorts/|embed/)?([A-Za-z0-9_-]{11})(?:[?&#].*)?$')


def _video_id(text):
    m = VIDEO_ID.search(text.strip())
    return m.group(1) if m else None


def _videos_the_site_uses(limit):
    """Most recent videos students watched or were recommended or searched, newest first."""
    ids = []

    def add(vid):
        if vid and vid not in ids:
            ids.append(vid)

    for r in execute_query("SELECT video_id FROM watched_videos ORDER BY watched_at DESC LIMIT 500") or []:
        add(r['video_id'])
    for r in execute_query("SELECT video_id FROM recommendation_history ORDER BY recommended_at DESC LIMIT 500") or []:
        add(r['video_id'])
    for r in execute_query("SELECT results FROM search_cache ORDER BY created_at DESC LIMIT 200") or []:
        try:
            for v in json.loads(r['results'] or '[]'):
                add(v.get('video_id') if isinstance(v, dict) else None)
        except ValueError:
            pass
    return ids[:limit]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('videos', nargs='*', help='video IDs or YouTube links (default: videos the site uses)')
    parser.add_argument('--limit', type=int, default=50, help='how many videos to check (default 50)')
    parser.add_argument('--whisper', action='store_true',
                        help='also transcribe videos without captions from their audio (slow)')
    args = parser.parse_args()

    host = os.getenv('DB_HOST', 'localhost')
    print(f"Database: {host} / {os.getenv('DB_NAME', 'ai_learning_platform')}")
    if host in ('localhost', '127.0.0.1'):
        print("Note: this is your local database. Set DB_* to the hosted database to fill the live site's.")

    if args.videos:
        ids = [v for v in (_video_id(a) for a in args.videos) if v]
    else:
        ids = _videos_the_site_uses(args.limit)
    if not ids:
        print("No videos found. Watch or open some videos on the site first, or pass video IDs.")
        return 1

    saved = already = failed = 0
    for i, vid in enumerate(ids, 1):
        if get_cached_transcript(vid):
            already += 1
            continue
        result = extract_transcript_full_pipeline(video_id=vid, use_whisper=args.whisper)
        if result.get('transcript') and result.get('source') in VALID_TRANSCRIPT_SOURCES:
            saved += 1
            print(f"[{i}/{len(ids)}] saved {vid} ({len(result['transcript'].split())} words)")
        else:
            failed += 1
            print(f"[{i}/{len(ids)}] no transcript for {vid}")

    print(f"\nDone: {saved} saved, {already} already saved, {failed} without a transcript.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
