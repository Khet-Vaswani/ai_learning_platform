#!/usr/bin/env python3
"""
create_admin.py — Create or Reset an Admin Account for LearnNova

Usage:
    python create_admin.py
    python create_admin.py admin@platform.com Admin@123 "System Administrator"
"""

import sys
import os
import bcrypt
from dotenv import load_dotenv

load_dotenv()

import mysql.connector

def create_or_update_admin(email="admin@platform.com", password="Admin@123", full_name="System Administrator"):
    host = os.getenv('DB_HOST', 'localhost')
    port = int(os.getenv('DB_PORT', 3306))
    user = os.getenv('DB_USER', 'root')
    db_pass = os.getenv('DB_PASSWORD', '')
    database = os.getenv('DB_NAME', 'ai_learning_platform')

    print(f"Connecting to MySQL ({host}:{port}, DB: {database})...")
    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=db_pass,
            database=database,
            connection_timeout=5
        )
    except mysql.connector.Error as err:
        print(f"\n[ERROR] Could not connect to MySQL server: {err}")
        print("\nPlease ensure:")
        print("  1. MySQL / XAMPP / MariaDB is actively running.")
        print("  2. DB_HOST, DB_PORT, DB_USER, DB_PASSWORD in .env match your configuration.")
        return False

    cursor = conn.cursor(dictionary=True)
    try:
        pass_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        email = email.strip().lower()

        cursor.execute("SELECT id, email, role FROM users WHERE email = %s", (email,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE users
                SET password = %s, role = 'admin', full_name = %s, onboarding_done = 1
                WHERE id = %s
            """, (pass_hash, full_name, existing['id']))
            conn.commit()
            print(f"\n[OK] Updated existing user '{email}' to Role: ADMIN.")
        else:
            cursor.execute("""
                INSERT INTO users (full_name, email, password, role, onboarding_done)
                VALUES (%s, %s, %s, 'admin', 1)
            """, (full_name, email, pass_hash))
            conn.commit()
            print(f"\n[OK] Successfully created new Admin account for '{email}'.")

        print("=" * 55)
        print("ADMIN CREDENTIALS:")
        print(f"  Login URL : http://localhost:5000/admin")
        print(f"  Email     : {email}")
        print(f"  Password  : {password}")
        print(f"  Role      : admin")
        print("=" * 55)
        return True

    except Exception as e:
        print(f"\n[ERROR] Failed to save admin account: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@platform.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "Admin@123"
    name = sys.argv[3] if len(sys.argv) > 3 else "System Administrator"
    create_or_update_admin(email, password, name)
