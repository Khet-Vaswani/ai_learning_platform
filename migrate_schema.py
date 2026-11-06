#!/usr/bin/env python3
"""
Direct SQL execution to create schema
Run this script to apply all database migrations
"""

import hashlib
import re
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def _load_sql_file(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    statements = []
    for stmt in content.split(';'):
        stmt = stmt.strip()
        # Filter out comments-only or empty statements
        cleaned = '\n'.join([line for line in stmt.splitlines() if not line.strip().startswith('--')])
        # The database comes from DB_NAME (e.g. "defaultdb" on a hosted database),
        # so the files' own CREATE DATABASE / USE lines are skipped
        if re.match(r'^\s*(USE|CREATE DATABASE)\b', cleaned, re.I):
            continue
        if cleaned.strip():
            statements.append(stmt + ';')
    return statements


# MariaDB-only syntax; MySQL 8 (e.g. Aiven) rejects it, so it is run as a check + plain ALTER
_ADD_COLUMN_IF_MISSING = re.compile(
    r'^ALTER TABLE\s+`?(\w+)`?\s+ADD COLUMN IF NOT EXISTS\s+`?(\w+)`?\s+(.+?);?$', re.I | re.S)


def _execute(cursor, statement):
    m = _ADD_COLUMN_IF_MISSING.match(statement.strip())
    if not m:
        cursor.execute(statement)
        return
    table, column, definition = m.groups()
    cursor.execute(
        """SELECT 1 FROM information_schema.COLUMNS
           WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s""",
        (table, column))
    if not cursor.fetchall():
        cursor.execute(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}")


def run_migrations():
    db_name = os.getenv('DB_NAME', 'ai_learning_platform')
    try:
        conn = mysql.connector.connect(
            host               = os.getenv('DB_HOST',     'localhost'),
            port               = int(os.getenv('DB_PORT', 3306)),
            user               = os.getenv('DB_USER',     'root'),
            password           = os.getenv('DB_PASSWORD', ''),
            connection_timeout = 3
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`;")
        cursor.execute(f"USE `{db_name}`;")
        print(f"[OK] Database '{db_name}' ready & connected")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False

    base_dir = os.path.dirname(__file__)
    schema_path = os.path.join(base_dir, 'database', 'schema.sql')
    updates_path = os.path.join(base_dir, 'database', 'schema_updates.sql')
    seed_path = os.path.join(base_dir, 'database', 'seed_data.sql')

    sql_statements = _load_sql_file(schema_path) + _load_sql_file(updates_path) + _load_sql_file(seed_path)

    # Skip the whole run when the SQL files haven't changed since the last
    # successful run (keeps every server start fast, especially on hosted databases)
    files_hash = hashlib.sha256(''.join(sql_statements).encode('utf-8')).hexdigest()
    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS schema_version (
                              id INT PRIMARY KEY, files_hash VARCHAR(64) NOT NULL)""")
        cursor.execute("SELECT files_hash FROM schema_version WHERE id = 1")
        row = cursor.fetchone()
        if row and row[0] == files_hash:
            print("[OK] Database schema is up to date")
            cursor.close()
            conn.close()
            return True
    except mysql.connector.Error as e:
        print(f"[WARN] Could not read schema version: {e}")

    # Execute statements
    try:
        print("\n" + "=" * 60)
        print("EXECUTING DATABASE MIGRATIONS...")
        print("=" * 60)
        
        for i, statement in enumerate(sql_statements, 1):
            try:
                _execute(cursor, statement)
                print(f"[OK] Step {i}/{len(sql_statements)}")
            except mysql.connector.Error as stmt_err:
                # Ignore duplicate column / table / constraint errors during re-runs
                if stmt_err.errno in (1060, 1061, 1050):
                    continue
                print(f"[WARN] Migration step {i} warning: {stmt_err}")
        
        # No default admin is created here: a password written in the code is public.
        # Create one with:  python create_admin.py <email> <password> "<name>"

        cursor.execute(
            """INSERT INTO schema_version (id, files_hash) VALUES (1, %s)
               ON DUPLICATE KEY UPDATE files_hash = %s""", (files_hash, files_hash))
        conn.commit()
        print("\n[OK] All migrations executed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

    # Verify
    print("\nVerifying schema...")
    try:
        conn = mysql.connector.connect(
            host               = os.getenv('DB_HOST',     'localhost'),
            port               = int(os.getenv('DB_PORT', 3306)),
            user               = os.getenv('DB_USER',     'root'),
            password           = os.getenv('DB_PASSWORD', ''),
            database           = os.getenv('DB_NAME',     'ai_learning_platform'),
            connection_timeout = 3
        )
        cursor = conn.cursor(dictionary=True)
        
        # Check tables
        cursor.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s", (db_name,))
        tables = [row['TABLE_NAME'] for row in cursor.fetchall()]
        
        new_tables = [
            'educational_categories',
            'student_classes',
            'university_departments',
            'university_fields_of_study',
            'recommendation_history',
            'quiz_attempts',
            'password_resets'
        ]
        
        print("\nNew Tables Created:")
        for table in new_tables:
            if table in tables:
                print(f"  [OK] {table}")
            else:
                print(f"  [ERROR] {table} (MISSING)")
        
        # Check data
        cursor.execute("SELECT COUNT(*) as cnt FROM educational_categories")
        cat_count = cursor.fetchone()['cnt']
        print(f"\n[OK] Educational Categories: {cat_count}")
        
        cursor.execute("SELECT COUNT(*) as cnt FROM student_classes")
        class_count = cursor.fetchone()['cnt']
        print(f"[OK] Student Classes: {class_count}")
        
        cursor.execute("SELECT COUNT(*) as cnt FROM university_departments")
        dept_count = cursor.fetchone()['cnt']
        print(f"[OK] Departments: {dept_count}")
        
        cursor.execute("SELECT COUNT(*) as cnt FROM university_fields_of_study")
        field_count = cursor.fetchone()['cnt']
        print(f"[OK] Fields of Study: {field_count}")
        
        print("\n" + "=" * 60)
        print("[OK] SCHEMA MIGRATION COMPLETE!")
        print("=" * 60)
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Verification failed: {e}")
        return False


if __name__ == '__main__':
    run_migrations()
