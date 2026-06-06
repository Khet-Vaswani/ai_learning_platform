#!/usr/bin/env python3
"""
Direct SQL execution to create schema
Run this script to apply all database migrations
"""

import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection
try:
    conn = mysql.connector.connect(
        host     = os.getenv('DB_HOST',     'localhost'),
        port     = int(os.getenv('DB_PORT', 3306)),
        user     = os.getenv('DB_USER',     'root'),
        password = os.getenv('DB_PASSWORD', ''),
        database = os.getenv('DB_NAME',     'ai_learning_platform')
    )
    cursor = conn.cursor()
    print("✓ Database connected")
except Exception as e:
    print(f"✗ Connection failed: {e}")
    exit(1)

# SQL Statements to execute
sql_statements = [
    # Create educational_categories
    """
    CREATE TABLE IF NOT EXISTS educational_categories (
        id              INT AUTO_INCREMENT PRIMARY KEY,
        name            VARCHAR(100) NOT NULL UNIQUE,
        description     VARCHAR(255),
        icon            VARCHAR(50),
        display_order   INT DEFAULT 0
    );
    """,
    
    # Insert categories
    """
    INSERT INTO educational_categories (name, description, icon, display_order) VALUES
    ('Primary', 'Classes 1-5 (Age 5-10)', 'fas fa-book-reader', 1),
    ('Secondary', 'Classes 6-8 (Age 11-13)', 'fas fa-book-open', 2),
    ('Matriculation', 'Classes 9-10 (Age 14-15)', 'fas fa-graduation-cap', 3),
    ('Intermediate', 'Classes 11-12 (Age 16-17)', 'fas fa-laptop-code', 4),
    ('University', 'Bachelor/Masters Level', 'fas fa-university', 5),
    ('Professional', 'Working Professionals & Above', 'fas fa-briefcase', 6)
    ON DUPLICATE KEY UPDATE id = id;
    """,
    
    # Create student_classes
    """
    CREATE TABLE IF NOT EXISTS student_classes (
        id                  INT AUTO_INCREMENT PRIMARY KEY,
        category_id         INT NOT NULL,
        class_label         VARCHAR(50) NOT NULL,
        display_order       INT DEFAULT 0,
        FOREIGN KEY (category_id) REFERENCES educational_categories(id) ON DELETE CASCADE
    );
    """,
    
    # Insert student classes
    """
    INSERT IGNORE INTO student_classes (category_id, class_label, display_order) VALUES
    (1, 'Class 1', 1),
    (1, 'Class 2', 2),
    (1, 'Class 3', 3),
    (1, 'Class 4', 4),
    (1, 'Class 5', 5),
    (2, 'Class 6', 1),
    (2, 'Class 7', 2),
    (2, 'Class 8', 3),
    (3, 'Class 9', 1),
    (3, 'Class 10', 2),
    (4, 'Pre-Medical', 1),
    (4, 'Pre-Engineering', 2),
    (4, 'Commerce', 3),
    (4, 'Arts', 4),
    (4, 'ICS (Computer Science)', 5);
    """,
    
    # Create university_departments
    """
    CREATE TABLE IF NOT EXISTS university_departments (
        id              INT AUTO_INCREMENT PRIMARY KEY,
        name            VARCHAR(100) NOT NULL UNIQUE,
        icon            VARCHAR(50),
        display_order   INT DEFAULT 0
    );
    """,
    
    # Insert departments
    """
    INSERT IGNORE INTO university_departments (name, icon, display_order) VALUES
    ('Computer Science', 'fas fa-laptop-code', 1),
    ('Engineering', 'fas fa-cogs', 2),
    ('Business & Economics', 'fas fa-briefcase', 3),
    ('Law', 'fas fa-gavel', 4),
    ('Medicine & Health Sciences', 'fas fa-stethoscope', 5),
    ('Arts & Humanities', 'fas fa-book', 6),
    ('Education', 'fas fa-chalkboard-teacher', 7),
    ('Social Sciences', 'fas fa-users', 8),
    ('Agriculture & Natural Sciences', 'fas fa-leaf', 9),
    ('Other', 'fas fa-question-circle', 10);
    """,
    
    # Create university_fields_of_study
    """
    CREATE TABLE IF NOT EXISTS university_fields_of_study (
        id              INT AUTO_INCREMENT PRIMARY KEY,
        department_id   INT NOT NULL,
        field_name      VARCHAR(100) NOT NULL,
        display_order   INT DEFAULT 0,
        FOREIGN KEY (department_id) REFERENCES university_departments(id) ON DELETE CASCADE
    );
    """,
    
    # Insert fields
    """
    INSERT IGNORE INTO university_fields_of_study (department_id, field_name, display_order) VALUES
    (1, 'Software Engineering', 1),
    (1, 'Data Science & AI', 2),
    (1, 'Web Development', 3),
    (1, 'Cybersecurity', 4),
    (1, 'Mobile Development', 5),
    (1, 'Database Administration', 6),
    (1, 'Cloud Computing', 7),
    (2, 'Mechanical Engineering', 1),
    (2, 'Electrical Engineering', 2),
    (2, 'Civil Engineering', 3),
    (2, 'Software Engineering', 4),
    (2, 'Chemical Engineering', 5),
    (2, 'Aerospace Engineering', 6),
    (3, 'Finance & Banking', 1),
    (3, 'Marketing', 2),
    (3, 'Human Resources', 3),
    (3, 'Accounting', 4),
    (3, 'International Business', 5),
    (3, 'Entrepreneurship', 6),
    (4, 'Constitutional Law', 1),
    (4, 'Criminal Law', 2),
    (4, 'Commercial Law', 3),
    (4, 'International Law', 4),
    (4, 'Administrative Law', 5),
    (5, 'Medicine', 1),
    (5, 'Nursing', 2),
    (5, 'Pharmacy', 3),
    (5, 'Dentistry', 4),
    (5, 'Public Health', 5),
    (5, 'Physiotherapy', 6),
    (6, 'English Literature', 1),
    (6, 'History', 2),
    (6, 'Philosophy', 3),
    (6, 'Psychology', 4),
    (6, 'Linguistics', 5),
    (7, 'Educational Psychology', 1),
    (7, 'Curriculum Development', 2),
    (7, 'Higher Education', 3),
    (7, 'Special Education', 4),
    (8, 'Sociology', 1),
    (8, 'Political Science', 2),
    (8, 'Economics', 3),
    (8, 'Anthropology', 4),
    (9, 'Agriculture', 1),
    (9, 'Environmental Science', 2),
    (9, 'Biology', 3),
    (9, 'Botany', 4);
    """,
    
    # Create recommendation_history
    """
    CREATE TABLE IF NOT EXISTS recommendation_history (
        id              INT AUTO_INCREMENT PRIMARY KEY,
        user_id         INT NOT NULL,
        video_id        VARCHAR(50) NOT NULL,
        recommended_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reason          VARCHAR(255),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """,
    
    # Create quiz_attempts
    """
    CREATE TABLE IF NOT EXISTS quiz_attempts (
        id              INT AUTO_INCREMENT PRIMARY KEY,
        user_id         INT NOT NULL,
        video_id        VARCHAR(50),
        quiz_id         INT,
        score           INT,
        total_questions INT,
        percentage      DECIMAL(5,2),
        attempted_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """,
]

# Execute statements
try:
    print("\n" + "=" * 60)
    print("EXECUTING DATABASE MIGRATIONS...")
    print("=" * 60)
    
    for i, statement in enumerate(sql_statements, 1):
        cursor.execute(statement)
        print(f"✓ Step {i}/{len(sql_statements)}")
    
    conn.commit()
    print("\n✓ All migrations executed successfully!")
    print("=" * 60)
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    conn.rollback()
    exit(1)
finally:
    cursor.close()
    conn.close()

# Verify
print("\nVerifying schema...")
try:
    conn = mysql.connector.connect(
        host     = os.getenv('DB_HOST',     'localhost'),
        port     = int(os.getenv('DB_PORT', 3306)),
        user     = os.getenv('DB_USER',     'root'),
        password = os.getenv('DB_PASSWORD', ''),
        database = os.getenv('DB_NAME',     'ai_learning_platform')
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
        'quiz_attempts'
    ]
    
    print("\nNew Tables Created:")
    for table in new_tables:
        if table in tables:
            print(f"  ✓ {table}")
        else:
            print(f"  ✗ {table} (MISSING)")
    
    # Check data
    cursor.execute("SELECT COUNT(*) as cnt FROM educational_categories")
    cat_count = cursor.fetchone()['cnt']
    print(f"\n✓ Educational Categories: {cat_count}")
    
    cursor.execute("SELECT COUNT(*) as cnt FROM student_classes")
    class_count = cursor.fetchone()['cnt']
    print(f"✓ Student Classes: {class_count}")
    
    cursor.execute("SELECT COUNT(*) as cnt FROM university_departments")
    dept_count = cursor.fetchone()['cnt']
    print(f"✓ Departments: {dept_count}")
    
    cursor.execute("SELECT COUNT(*) as cnt FROM university_fields_of_study")
    field_count = cursor.fetchone()['cnt']
    print(f"✓ Fields of Study: {field_count}")
    
    print("\n" + "=" * 60)
    print("✓ SCHEMA MIGRATION COMPLETE!")
    print("=" * 60)
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"✗ Verification failed: {e}")
    exit(1)
