-- ============================================================
-- AI Learning Platform — Schema Updates for Category-Based Flow
-- ============================================================

USE ai_learning_platform;

-- ============================================================
-- TABLE: educational_categories
-- ============================================================
CREATE TABLE IF NOT EXISTS educational_categories (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE,
    description     VARCHAR(255),
    icon            VARCHAR(50),
    display_order   INT DEFAULT 0
);

INSERT INTO educational_categories (name, description, icon, display_order) VALUES
('Primary', 'Classes 1-5 (Age 5-10)', 'fas fa-book-reader', 1),
('Secondary', 'Classes 6-8 (Age 11-13)', 'fas fa-book-open', 2),
('Matriculation', 'Classes 9-10 (Age 14-15)', 'fas fa-graduation-cap', 3),
('Intermediate', 'Classes 11-12 (Age 16-17)', 'fas fa-laptop-code', 4),
('University', 'Bachelor/Masters Level', 'fas fa-university', 5),
('Professional', 'Working Professionals & Above', 'fas fa-briefcase', 6)
ON DUPLICATE KEY UPDATE id = id;

-- ============================================================
-- TABLE: student_classes
-- ============================================================
CREATE TABLE IF NOT EXISTS student_classes (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    category_id         INT NOT NULL,
    class_label         VARCHAR(50) NOT NULL,
    display_order       INT DEFAULT 0,
    UNIQUE KEY uq_cat_class (category_id, class_label),
    FOREIGN KEY (category_id) REFERENCES educational_categories(id) ON DELETE CASCADE
);

-- Primary: Classes 1-5
INSERT IGNORE INTO student_classes (category_id, class_label, display_order) VALUES
(1, 'Class 1', 1),
(1, 'Class 2', 2),
(1, 'Class 3', 3),
(1, 'Class 4', 4),
(1, 'Class 5', 5);

-- Secondary: Classes 6-8
INSERT IGNORE INTO student_classes (category_id, class_label, display_order) VALUES
(2, 'Class 6', 1),
(2, 'Class 7', 2),
(2, 'Class 8', 3);

-- Matriculation: Classes 9-10
INSERT IGNORE INTO student_classes (category_id, class_label, display_order) VALUES
(3, 'Class 9', 1),
(3, 'Class 10', 2);

-- Intermediate: Streams
INSERT IGNORE INTO student_classes (category_id, class_label, display_order) VALUES
(4, 'Pre-Medical', 1),
(4, 'Pre-Engineering', 2),
(4, 'Commerce', 3),
(4, 'Arts', 4),
(4, 'ICS (Computer Science)', 5);

-- ============================================================
-- TABLE: university_departments
-- ============================================================
CREATE TABLE IF NOT EXISTS university_departments (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE,
    icon            VARCHAR(50),
    display_order   INT DEFAULT 0
);

INSERT INTO university_departments (name, icon, display_order) VALUES
('Computer Science', 'fas fa-laptop-code', 1),
('Engineering', 'fas fa-cogs', 2),
('Business & Economics', 'fas fa-briefcase', 3),
('Law', 'fas fa-gavel', 4),
('Medicine & Health Sciences', 'fas fa-stethoscope', 5),
('Arts & Humanities', 'fas fa-book', 6),
('Education', 'fas fa-chalkboard-teacher', 7),
('Social Sciences', 'fas fa-users', 8),
('Agriculture & Natural Sciences', 'fas fa-leaf', 9),
('Other', 'fas fa-question-circle', 10)
ON DUPLICATE KEY UPDATE id = id;

-- ============================================================
-- TABLE: university_fields_of_study
-- ============================================================
CREATE TABLE IF NOT EXISTS university_fields_of_study (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    department_id   INT NOT NULL,
    field_name      VARCHAR(100) NOT NULL,
    display_order   INT DEFAULT 0,
    UNIQUE KEY uq_dept_field (department_id, field_name),
    FOREIGN KEY (department_id) REFERENCES university_departments(id) ON DELETE CASCADE
);

-- Computer Science fields
INSERT IGNORE INTO university_fields_of_study (department_id, field_name, display_order) VALUES
(1, 'Software Engineering', 1),
(1, 'Data Science & AI', 2),
(1, 'Web Development', 3),
(1, 'Cybersecurity', 4),
(1, 'Mobile Development', 5),
(1, 'Database Administration', 6),
(1, 'Cloud Computing', 7);

-- Engineering fields
INSERT IGNORE INTO university_fields_of_study (department_id, field_name, display_order) VALUES
(2, 'Mechanical Engineering', 1),
(2, 'Electrical Engineering', 2),
(2, 'Civil Engineering', 3),
(2, 'Software Engineering', 4),
(2, 'Chemical Engineering', 5),
(2, 'Aerospace Engineering', 6);

-- Business fields
INSERT IGNORE INTO university_fields_of_study (department_id, field_name, display_order) VALUES
(3, 'Finance & Banking', 1),
(3, 'Marketing', 2),
(3, 'Human Resources', 3),
(3, 'Accounting', 4),
(3, 'International Business', 5),
(3, 'Entrepreneurship', 6);

-- Law fields
INSERT IGNORE INTO university_fields_of_study (department_id, field_name, display_order) VALUES
(4, 'Constitutional Law', 1),
(4, 'Criminal Law', 2),
(4, 'Commercial Law', 3),
(4, 'International Law', 4),
(4, 'Administrative Law', 5);

-- Medicine fields
INSERT IGNORE INTO university_fields_of_study (department_id, field_name, display_order) VALUES
(5, 'Medicine', 1),
(5, 'Nursing', 2),
(5, 'Pharmacy', 3),
(5, 'Dentistry', 4),
(5, 'Public Health', 5),
(5, 'Physiotherapy', 6);

-- Arts fields
INSERT IGNORE INTO university_fields_of_study (department_id, field_name, display_order) VALUES
(6, 'English Literature', 1),
(6, 'History', 2),
(6, 'Philosophy', 3),
(6, 'Psychology', 4),
(6, 'Linguistics', 5);

-- Education fields
INSERT IGNORE INTO university_fields_of_study (department_id, field_name, display_order) VALUES
(7, 'Educational Psychology', 1),
(7, 'Curriculum Development', 2),
(7, 'Higher Education', 3),
(7, 'Special Education', 4);

-- Social Sciences fields
INSERT IGNORE INTO university_fields_of_study (department_id, field_name, display_order) VALUES
(8, 'Sociology', 1),
(8, 'Political Science', 2),
(8, 'Economics', 3),
(8, 'Anthropology', 4);

-- Agricultural fields
INSERT IGNORE INTO university_fields_of_study (department_id, field_name, display_order) VALUES
(9, 'Agriculture', 1),
(9, 'Environmental Science', 2),
(9, 'Biology', 3),
(9, 'Botany', 4);

-- ============================================================
-- UPDATE users TABLE
-- ============================================================
ALTER TABLE users ADD COLUMN IF NOT EXISTS educational_category_id INT DEFAULT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS student_class_id INT DEFAULT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS university_department_id INT DEFAULT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS university_field_id INT DEFAULT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS learning_level ENUM('Beginner','Intermediate','Advanced') DEFAULT 'Beginner';
-- Denormalized names used by onboarding, dashboard, settings, admin and MoE engine
ALTER TABLE users ADD COLUMN IF NOT EXISTS education_category VARCHAR(100) DEFAULT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR(150) DEFAULT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_pic VARCHAR(255) DEFAULT 'default.png';
UPDATE users u JOIN educational_categories c ON c.id = u.educational_category_id
    SET u.education_category = c.name
    WHERE u.education_category IS NULL;

ALTER TABLE users ADD CONSTRAINT fk_user_category 
    FOREIGN KEY (educational_category_id) REFERENCES educational_categories(id);
ALTER TABLE users ADD CONSTRAINT fk_user_class 
    FOREIGN KEY (student_class_id) REFERENCES student_classes(id);
ALTER TABLE users ADD CONSTRAINT fk_user_dept 
    FOREIGN KEY (university_department_id) REFERENCES university_departments(id);
ALTER TABLE users ADD CONSTRAINT fk_user_field 
    FOREIGN KEY (university_field_id) REFERENCES university_fields_of_study(id);

-- ============================================================
-- TRACKING TABLE: recommendation_history
-- ============================================================
CREATE TABLE IF NOT EXISTS recommendation_history (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    video_id        VARCHAR(50) NOT NULL,
    recommended_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason          VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================
-- TRACKING TABLE: quiz_attempts
-- ============================================================
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    video_id        VARCHAR(50) NOT NULL,
    quiz_id         INT,
    score           INT,
    total_questions INT,
    percentage      DECIMAL(5,2),
    attempted_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (quiz_id) REFERENCES video_quizzes(id) ON DELETE SET NULL
);

-- ============================================================
-- INDEXES for Performance
-- ============================================================
CREATE INDEX idx_user_category ON users(educational_category_id);
CREATE INDEX idx_user_class ON users(student_class_id);
CREATE INDEX idx_recommend_history ON recommendation_history(user_id, recommended_at);
CREATE INDEX idx_quiz_attempts ON quiz_attempts(user_id, attempted_at);
CREATE INDEX idx_weak_topics ON weak_topics(user_id, last_detected);

-- ============================================================
-- ALTER video_quizzes
-- ============================================================
ALTER TABLE video_quizzes ADD COLUMN IF NOT EXISTS notes_source VARCHAR(50) DEFAULT 'transcript';
ALTER TABLE video_quizzes ADD COLUMN IF NOT EXISTS transcript_length INT DEFAULT 0;

-- ============================================================
-- Verification Queries (Run to verify)
-- ============================================================
-- SELECT * FROM educational_categories;
-- SELECT * FROM student_classes;
-- SELECT * FROM university_departments;
-- SELECT * FROM university_fields_of_study;
