#!/usr/bin/env python3
"""
Direct SQL execution to create schema
Run this script to apply all database migrations
"""

import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def run_migrations():
    try:
        conn = mysql.connector.connect(
            host               = os.getenv('DB_HOST',     'localhost'),
            port               = int(os.getenv('DB_PORT', 3306)),
            user               = os.getenv('DB_USER',     'root'),
            password           = os.getenv('DB_PASSWORD', ''),
            database           = os.getenv('DB_NAME',     'ai_learning_platform'),
            connection_timeout = 3
        )
        cursor = conn.cursor()
        print("[OK] Database connected")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False

    # Execute statements
    try:
        print("\n" + "=" * 60)
        print("EXECUTING DATABASE MIGRATIONS...")
        print("=" * 60)
        
        for i, statement in enumerate(sql_statements, 1):
            cursor.execute(statement)
            print(f"[OK] Step {i}/{len(sql_statements)}")
        
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
