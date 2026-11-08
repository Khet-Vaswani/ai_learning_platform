# ============================================================
# notifications.py — Real Student Notifications System
# ============================================================

from app.utils.db import execute_query
from datetime import datetime, date

_table_ready = False


def ensure_notifications_table():
    """Ensure user_notifications table exists (checked once per server start, not per request)"""
    global _table_ready
    if _table_ready:
        return
    sql = """
    CREATE TABLE IF NOT EXISTS user_notifications (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        title VARCHAR(150) NOT NULL,
        message TEXT NOT NULL,
        type VARCHAR(50) DEFAULT 'info',
        icon VARCHAR(50) DEFAULT 'fa-bell',
        is_read TINYINT(1) DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_user (user_id)
    )
    """
    try:
        _table_ready = execute_query(sql, fetch=False) is not False
    except Exception as e:
        print(f"[WARN] Notifications table check: {e}")


def create_notification(user_id, title, message, notif_type='info', icon='fa-bell'):
    """Insert a real notification for a student"""
    if not user_id:
        return False
    ensure_notifications_table()
    try:
        sql = """
        INSERT INTO user_notifications (user_id, title, message, type, icon, is_read)
        VALUES (%s, %s, %s, %s, %s, 0)
        """
        return execute_query(sql, (user_id, title, message, notif_type, icon), fetch=False)
    except Exception as e:
        print(f"[WARN] create_notification error: {e}")
        return False


def format_relative_time(dt):
    """Format datetime into friendly relative string like '5 mins ago'"""
    if not dt:
        return "Recently"
    now = datetime.now()
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
        except Exception:
            return "Recently"
    
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        mins = seconds // 60
        return f"{mins} min{'s' if mins > 1 else ''} ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif seconds < 172800:
        return "Yesterday"
    else:
        days = seconds // 86400
        return f"{days} days ago"


def seed_contextual_notifications(user_id):
    """
    If user has 0 notifications, seed real personalized notifications
    derived from their real student history (quizzes, watched videos, streak).
    """
    ensure_notifications_table()
    count_row = execute_query(
        "SELECT COUNT(*) as cnt FROM user_notifications WHERE user_id=%s",
        (user_id,), fetch=True
    )
    if count_row and count_row[0]['cnt'] > 0:
        return

    # 1. Check user profile
    user = execute_query(
        "SELECT full_name, field_of_interest, skill_level FROM users WHERE id=%s",
        (user_id,), fetch=True
    )
    field = user[0].get('field_of_interest') if user else 'General'
    level = user[0].get('skill_level') if user else 'Beginner'

    # Notification 1: Welcome & Path
    create_notification(
        user_id,
        "Welcome to AI Learning!",
        f"Your learning track is tailored for {field} at {level} level.",
        notif_type="welcome",
        icon="fa-graduation-cap"
    )

    # 2. Check recent quiz
    recent_quiz = execute_query(
        """SELECT topic, score, total, created_at 
           FROM video_quizzes 
           WHERE user_id=%s AND attempted=1 
           ORDER BY created_at DESC LIMIT 1""",
        (user_id,), fetch=True
    )
    if recent_quiz:
        q = recent_quiz[0]
        pct = round((q['score'] / q['total'] * 100), 1) if q['total'] else 0
        create_notification(
            user_id,
            f"Quiz Completed: {q['topic']}",
            f"You scored {pct}% on your {q['topic']} interactive quiz.",
            notif_type="quiz",
            icon="fa-check-circle"
        )

    # 3. Check weak topics
    weak = execute_query(
        "SELECT topic, fail_count FROM weak_topics WHERE user_id=%s ORDER BY fail_count DESC LIMIT 1",
        (user_id,), fetch=True
    )
    if weak:
        create_notification(
            user_id,
            "AI Review Recommendation",
            f"Topic '{weak[0]['topic']}' needs attention. Practice video recommendations are ready.",
            notif_type="weak_topic",
            icon="fa-exclamation-triangle"
        )

    # 4. Check study streak
    streak = execute_query(
        """SELECT COUNT(DISTINCT activity_date) as days FROM (
            SELECT session_date as activity_date FROM study_sessions WHERE user_id=%s
            UNION
            SELECT DATE(watched_at) as activity_date FROM watched_videos WHERE user_id=%s
        ) as act""",
        (user_id, user_id), fetch=True
    )
    days = streak[0]['days'] if streak and streak[0]['days'] else 0
    if days > 0:
        create_notification(
            user_id,
            "Streak Maintained! 🔥",
            f"You have active study records across {days} day{'s' if days > 1 else ''}. Keep the momentum going!",
            notif_type="streak",
            icon="fa-fire"
        )


def get_user_notifications(user_id, limit=10):
    """Retrieve formatted notifications and unread count for user"""
    ensure_notifications_table()
    seed_contextual_notifications(user_id)

    rows = execute_query(
        """SELECT id, title, message, type, icon, is_read, created_at
           FROM user_notifications
           WHERE user_id=%s
           ORDER BY created_at DESC
           LIMIT %s""",
        (user_id, limit), fetch=True
    ) or []

    unread_row = execute_query(
        "SELECT COUNT(*) as unread FROM user_notifications WHERE user_id=%s AND is_read=0",
        (user_id,), fetch=True
    )
    unread_count = unread_row[0]['unread'] if unread_row else 0

    results = []
    for r in rows:
        results.append({
            'id': r['id'],
            'title': r['title'],
            'message': r['message'],
            'type': r.get('type') or 'info',
            'icon': r.get('icon') or 'fa-bell',
            'is_read': bool(r['is_read']),
            'time_ago': format_relative_time(r['created_at'])
        })

    return {
        'notifications': results,
        'unread_count': unread_count
    }


def mark_notifications_as_read(user_id, notif_id=None):
    """Mark all or specific notification as read"""
    ensure_notifications_table()
    if notif_id:
        return execute_query(
            "UPDATE user_notifications SET is_read=1 WHERE id=%s AND user_id=%s",
            (notif_id, user_id), fetch=False
        )
    else:
        return execute_query(
            "UPDATE user_notifications SET is_read=1 WHERE user_id=%s",
            (user_id,), fetch=False
        )


def dismiss_notification(user_id, notif_id):
    """Delete or dismiss a notification"""
    ensure_notifications_table()
    return execute_query(
        "DELETE FROM user_notifications WHERE id=%s AND user_id=%s",
        (notif_id, user_id), fetch=False
    )
