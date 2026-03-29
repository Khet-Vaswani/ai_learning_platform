USE ai_learning_platform;

-- Cognitive Categories
INSERT INTO cognitive_categories (name, description, icon) VALUES
('Logical Reasoning',  'Tests pattern recognition', '🔷'),
('Numerical Ability',  'Tests mathematical skills', '🔢'),
('Verbal Ability',     'Tests language skills',     '📝'),
('Problem Solving',    'Tests critical thinking',   '💡');

-- Cognitive Questions
INSERT INTO cognitive_questions
(category_id, question_text,
 option_a, option_b, option_c, option_d,
 correct_answer, difficulty, time_limit)
VALUES
(1, 'What comes next: 2, 4, 8, 16, __?',
 '24','32','18','20','B','Easy',25),

(1, 'If all Roses are Flowers and all Flowers need Water — Roses need?',
 'Sun','Water','Soil','Air','B','Medium',35),

(1, 'Circle→Square→Triangle→Circle→Square→__?',
 'Circle','Square','Triangle','Pentagon','C','Easy',25),

(2, 'Student scores 45 out of 60. Percentage?',
 '70%','75%','80%','65%','B','Easy',30),

(2, 'Train travels 120km in 2 hours. Speed?',
 '40 km/h','80 km/h','60 km/h','100 km/h','C','Medium',35),

(2, '15 + (4x3) - 6/2 = ?',
 '18','24','21','27','C','Medium',40),

(3, 'Opposite of EXPAND?',
 'Grow','Shrink','Stretch','Increase','B','Easy',25),

(3, 'She has been studying __ three hours.',
 'since','from','for','during','C','Medium',30),

(4, 'All labels wrong on 3 boxes. Pick from which box to identify all?',
 'Box A','Box B','Box C Mixed','Any box','C','Hard',45),

(4, 'Bug found 11:45 AM. Fix takes 1hr 30min. Done at?',
 '12:45 PM','1:00 PM','1:15 PM','1:30 PM','C','Medium',35);
