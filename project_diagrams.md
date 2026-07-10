# 📊 AI Learning Platform — System Architecture, Flowchart & ER Diagram

This document outlines a simplified system architecture, user flowchart, and database Entity-Relationship (ER) diagram for the **AI-Powered Personalized Learning Platform**.

---

## 1. System Architecture

The application is designed using a multi-tiered architecture consisting of the Presentation (Frontend), Logic (Flask backend), AI & Adaptive Engine, and Database layers.

```mermaid
graph TB
    subgraph Client ["Client Layer (Frontend)"]
        UI["Modern Web Interface<br>(HTML5, CSS3, JS, Chart.js)"]
    end

    subgraph Backend ["Flask Application Server (Backend)"]
        Route["App Routes & Blueprints<br>(Auth, Onboarding, Dashboard, Video, Quiz)"]
        YT["YouTube Helper & Search Cache"]
    end

    subgraph AI ["AI & Adaptive Engine"]
        Gemini["Gemini AI<br>(Notes & Quiz Generation)"]
        Recommender["Adaptive Recommendation Engine<br>(Mixture of Experts)"]
        Tracker["Weak Topic & Curve Tracker"]
    end

    subgraph DB ["Database Layer"]
        MySQL[("MySQL Database")]
    end

    %% Connections
    UI <-->|HTTP / AJAX| Route
    Route <--> YT
    Route <--> Gemini
    Route <--> Recommender
    Route <--> Tracker
    
    %% DB Connections
    Route <--> MySQL
    Recommender <--> MySQL
    Tracker <--> MySQL
    
    classDef client fill:#3c3489,stroke:#afa9ec,color:#fff;
    classDef backend fill:#085041,stroke:#5dcaa1,color:#fff;
    classDef ai fill:#633806,stroke:#ef9f27,color:#fff;
    classDef db fill:#2c3e50,stroke:#34495e,color:#fff;
    
    class UI client;
    class Route,YT backend;
    class Gemini,Recommender,Tracker ai;
    class MySQL db;
```

---

## 2. User & System Flowchart

A streamlined look at the core user lifecycle:

```mermaid
flowchart TD
    Start([User Registration & Auth]) --> Onboarding["Category-Based Onboarding<br>(Grade & Level Setup)"]
    Onboarding --> Dashboard["Personalized Dashboard<br>(MoE Video Recommendations)"]
    Dashboard --> Learn["Watch Video & Learn"]
    
    Learn --> Action{Choose Action}
    Action -->|"Study"| Notes["Generate AI Study Notes"]
    Action -->|"Assessment"| Quiz["Take AI-Generated Quiz"]
    
    Notes --> Learn
    
    Quiz --> Grade["AI Auto-Grading"]
    Grade --> AdaptiveLevel["Adaptive Level Adjustment<br>(Updates difficulty & marks weak topics)"]
    
    AdaptiveLevel --> Dashboard
```

---

## 3. Database Entity-Relationship (ER) Diagram

A high-level ER Diagram showing the core tables, primary/foreign keys, and relationships.

```mermaid
erDiagram
    users {
        int id PK
        varchar email UK
        int educational_category_id FK
        enum learning_level
    }

    educational_categories {
        int id PK
        varchar name UK
    }

    cognitive_results {
        int id PK
        int user_id FK
        int total_score
        varchar learning_style
    }

    watched_videos {
        int id PK
        int user_id FK
        varchar video_id
        varchar topic
    }

    video_quizzes {
        int id PK
        int user_id FK
        varchar video_id
        longtext questions
    }

    quiz_attempts {
        int id PK
        int user_id FK
        int quiz_id FK
        int score
    }

    weak_topics {
        int id PK
        int user_id FK
        varchar topic
        int fail_count
    }

    learning_curves {
        int id PK
        int user_id FK
        varchar topic
        enum curve_stage
        enum difficulty_level
    }

    %% Relationships
    users }o--|| educational_categories : "categorized_under"
    cognitive_results ||--|| users : "belongs_to"
    watched_videos }o--|| users : "watched_by"
    video_quizzes }o--|| users : "created_for"
    weak_topics }o--|| users : "tracked_for"
    learning_curves }o--|| users : "tracked_for"
    quiz_attempts }o--|| users : "attempted_by"
    quiz_attempts }o--|| video_quizzes : "attempts_details"
```
