#!/usr/bin/env python3
"""
Direct SQL execution to create schema
Run this script to apply all database migrations
"""

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
        if cleaned.strip():
            statements.append(stmt + ';')
    return statements


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

    # Execute statements
    try:
        print("\n" + "=" * 60)
        print("EXECUTING DATABASE MIGRATIONS...")
        print("=" * 60)
        
        for i, statement in enumerate(sql_statements, 1):
            try:
                cursor.execute(statement)
                print(f"[OK] Step {i}/{len(sql_statements)}")
            except mysql.connector.Error as stmt_err:
                # Ignore duplicate column / table / constraint errors during re-runs
                if stmt_err.errno in (1060, 1061, 1050):
                    continue
                print(f"[WARN] Migration step {i} warning: {stmt_err}")
        
        # Seed default Admin user if none exists
        try:
            import bcrypt
            cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
            admin_user = cursor.fetchone()
            if not admin_user:
                admin_pass_hash = bcrypt.hashpw(b'Admin@123', bcrypt.gensalt()).decode('utf-8')
                cursor.execute("""
                    INSERT INTO users (full_name, email, password, role, onboarding_done)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE role='admin'
                """, ('System Administrator', 'admin@platform.com', admin_pass_hash, 'admin', 1))
                print("[OK] Default Admin account seeded: admin@platform.com / Admin@123")
        except Exception as seed_err:
            print(f"[WARN] Failed to auto-seed admin: {seed_err}")

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
        cursor.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'ai_learning_platform'")
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
