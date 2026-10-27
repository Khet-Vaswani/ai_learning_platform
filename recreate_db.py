#!/usr/bin/env python3
"""
recreate_db.py — Automated Database Re-creation Script for AI Learning Platform

This script:
1. Connects to MySQL server (without requiring the database to already exist).
2. Drops any existing/corrupted database and creates a fresh database.
3. Applies database/schema.sql (base tables + study tracker).
4. Applies database/schema_updates.sql (onboarding categories, depts, classes, tracking).
5. Applies database/seed_data.sql (cognitive assessment questions & categories).
6. Seeds a default Admin user so you can log into /admin right away.
7. Validates and reports the status of all tables.
"""

import os
import sys
import mysql.connector
from dotenv import load_dotenv
import bcrypt

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 3306))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'ai_learning_platform')


def split_sql_statements(content: str):
    statements = []
    current = []
    delimiter = ';'

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith('--') or line.startswith('/*'):
            continue
        if line.upper().startswith('DELIMITER'):
            parts = line.split()
            if len(parts) > 1:
                delimiter = parts[1]
            continue

        current.append(raw_line)
        if line.endswith(delimiter):
            stmt = '\n'.join(current).strip()
            if stmt.endswith(delimiter):
                stmt = stmt[:-len(delimiter)].strip()
            if stmt:
                statements.append(stmt)
            current = []

    if current:
        stmt = '\n'.join(current).strip()
        if stmt:
            statements.append(stmt)

    return statements


def execute_sql_file(cursor, file_path: str):
    if not os.path.exists(file_path):
        print(f"  [WARN] File not found: {file_path}")
        return

    print(f"  -> Processing: {os.path.basename(file_path)}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    statements = split_sql_statements(content)
    success_count = 0
    warning_count = 0

    for stmt in statements:
        try:
            cursor.execute(stmt)
            success_count += 1
        except mysql.connector.Error as err:
            # Tolerable errors: duplicate column (1060), duplicate key (1061), table exists (1050)
            if err.errno in (1060, 1061, 1050):
                continue
            # Duplicate entry on insert
            if err.errno == 1062:
                continue
            warning_count += 1
            print(f"     [WARN ({err.errno})]: {err.msg}")

    print(f"  [OK] Completed {os.path.basename(file_path)} ({success_count} statements executed, {warning_count} warnings)")


def recreate_database():
    print("=" * 65)
    print("      AI LEARNING PLATFORM — DATABASE RE-CREATION WIZARD")
    print("=" * 65)
    print(f"Target Server : {DB_HOST}:{DB_PORT}")
    print(f"Target User   : {DB_USER}")
    print(f"Database Name : {DB_NAME}\n")

    # Step 1: Connect to MySQL server without database
    print("[1/5] Connecting to MySQL Server...")
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            autocommit=True
        )
        cursor = conn.cursor()
        print("  [OK] Connected to MySQL successfully!")
    except mysql.connector.Error as err:
        print(f"\n[ERROR] Could not connect to MySQL server: {err}")
        print("\nTroubleshooting tips:")
        print("  - If using XAMPP: Open XAMPP Control Panel and click 'Start' next to MySQL.")
        print("  - If using Windows Services: Run 'net start MySQL80' or 'net start MySQL' as Admin.")
        print("  - Check your .env file credentials (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD).")
        sys.exit(1)

    # Step 2: Drop and recreate database
    print(f"\n[2/5] Resetting database '{DB_NAME}'...")
    try:
        cursor.execute(f"DROP DATABASE IF EXISTS `{DB_NAME}`;")
        cursor.execute(f"CREATE DATABASE `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cursor.execute(f"USE `{DB_NAME}`;")
        print(f"  [OK] Fresh database '{DB_NAME}' created.")
    except mysql.connector.Error as err:
        print(f"  [ERROR] Failed to recreate database: {err}")
        cursor.close()
        conn.close()
        sys.exit(1)

    # Step 3: Run SQL scripts in correct order
    print("\n[3/5] Applying Schema and Migrations...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    schema_file = os.path.join(base_dir, 'database', 'schema.sql')
    updates_file = os.path.join(base_dir, 'database', 'schema_updates.sql')
    seed_file = os.path.join(base_dir, 'database', 'seed_data.sql')

    execute_sql_file(cursor, schema_file)
    execute_sql_file(cursor, updates_file)
    execute_sql_file(cursor, seed_file)

    # Step 4: Seed default Admin and Demo Student account
    print("\n[4/5] Checking/Seeding Default Users...")
    try:
        admin_pass_hash = bcrypt.hashpw(b'Admin@123', bcrypt.gensalt()).decode('utf-8')
        student_pass_hash = bcrypt.hashpw(b'Student@123', bcrypt.gensalt()).decode('utf-8')

        cursor.execute("""
            INSERT INTO users (full_name, email, password, role, onboarding_done)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE role='admin'
        """, ('System Administrator', 'admin@platform.com', admin_pass_hash, 'admin', 1))

        cursor.execute("""
            INSERT INTO users (full_name, email, password, role, onboarding_done, field_of_interest, skill_level)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE full_name=VALUES(full_name)
        """, ('Demo Student', 'student@platform.com', student_pass_hash, 'student', 1, 'Computer Science', 'Beginner'))

        print("  [OK] Default accounts seeded:")
        print("       - Admin   : admin@platform.com   / Password: Admin@123")
        print("       - Student : student@platform.com / Password: Student@123")
    except Exception as e:
        print(f"  [WARN] Could not seed default users: {e}")

    # Step 5: Verification & Summary
    print("\n[5/5] Verifying Database Integrity...")
    cursor.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s", (DB_NAME,))
    tables = [row[0] for row in cursor.fetchall()]

    expected_tables = [
        'users', 'educational_categories', 'student_classes',
        'university_departments', 'university_fields_of_study',
        'cognitive_categories', 'cognitive_questions', 'cognitive_results',
        'watched_videos', 'video_notes', 'video_quizzes', 'weak_topics',
        'video_transcripts', 'search_cache', 'topic_difficulty',
        'learning_curves', 'password_resets', 'recommendation_history',
        'quiz_attempts', 'study_schedule', 'study_sessions'
    ]

    all_ok = True
    print("\n  Table Status:")
    for tbl in expected_tables:
        if tbl in tables:
            cursor.execute(f"SELECT COUNT(*) FROM `{tbl}`")
            cnt = cursor.fetchone()[0]
            print(f"    [OK] {tbl:<30} ({cnt} rows)")
        else:
            all_ok = False
            print(f"    [MISSING] {tbl:<30}")

    cursor.close()
    conn.close()

    print("\n" + "=" * 65)
    if all_ok:
        print("   SUCCESS! DATABASE HAS BEEN FULLY RE-CREATED AND INITIALIZED.")
    else:
        print("   COMPLETED WITH WARNINGS: Some tables were missing.")
    print("=" * 65)


if __name__ == '__main__':
    recreate_database()
