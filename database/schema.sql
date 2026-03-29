-- ============================================================
-- AI Learning Platform — Complete Database Schema
-- ============================================================

CREATE DATABASE IF NOT EXISTS ai_learning_platform;
USE ai_learning_platform;

-- TABLE 1: users
CREATE TABLE IF NOT EXISTS users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    full_name       VARCHAR(100) NOT NULL,
    email           VARCHAR(100) NOT NULL UNIQUE,
    password        VARCHAR(255) NOT NULL,
    role            ENUM('student','admin') DEFAULT 'student',
    profile_pic     VARCHAR(255) DEFAULT 'default.png',
    onboarding_done TINYINT(1) DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- TABLE 2: cognitive_categories
CREATE TABLE IF NOT EXISTS cognitive_categories (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    icon        VARCHAR(50)
);

-- TABLE 3: cognitive_questions
CREATE TABLE IF NOT EXISTS cognitive_questions (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    category_id    INT NOT NULL,
    question_text  TEXT NOT NULL,
    option_a       VARCHAR(255) NOT NULL,
    option_b       VARCHAR(255) NOT NULL,
    option_c       VARCHAR(255) NOT NULL,
    option_d       VARCHAR(255) NOT NULL,
    correct_answer ENUM('A','B','C','D') NOT NULL,
    difficulty     ENUM('Easy','Medium','Hard') DEFAULT 'Medium',
    time_limit     INT DEFAULT 30,
    FOREIGN KEY (category_id)
        REFERENCES cognitive_categories(id)
);

-- TABLE 4: cognitive_results
CREATE TABLE IF NOT EXISTS cognitive_results (
    id                    INT AUTO_INCREMENT PRIMARY KEY,
    user_id               INT NOT NULL UNIQUE,
    logical_score         INT DEFAULT 0,
    numerical_score       INT DEFAULT 0,
    verbal_score          INT DEFAULT 0,
    problem_solving_score INT DEFAULT 0,
    total_score           INT DEFAULT 0,
    learning_style        VARCHAR(100),
    time_taken            INT DEFAULT 0,
    attempted_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- TABLE 5: watched_videos
CREATE TABLE IF NOT EXISTS watched_videos (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    video_id    VARCHAR(50) NOT NULL,
    video_title VARCHAR(255),
    topic       VARCHAR(100),
    watched_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_watch (user_id, video_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- TABLE 6: video_notes
CREATE TABLE IF NOT EXISTS video_notes (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL,
    video_id     VARCHAR(50) NOT NULL,
    notes        TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_notes (user_id, video_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- TABLE 7: video_quizzes
CREATE TABLE IF NOT EXISTS video_quizzes (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    video_id    VARCHAR(50) NOT NULL,
    video_title VARCHAR(255),
    topic       VARCHAR(100),
    questions   LONGTEXT,
    score       INT DEFAULT 0,
    total       INT DEFAULT 0,
    attempted   TINYINT(1) DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- TABLE 8: weak_topics
CREATE TABLE IF NOT EXISTS weak_topics (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL,
    topic         VARCHAR(100) NOT NULL,
    fail_count    INT DEFAULT 1,
    last_detected TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                  ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_weak (user_id, topic),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);