# ============================================================
# cognitive.py — AI Generated Cognitive Assessment
# ============================================================

from flask import (Blueprint, render_template, request,
                   jsonify, session, redirect, url_for)
from app.utils.auth_helpers import login_required
from app.utils.db import execute_query
from groq import Groq
import os, json, time

cognitive_bp = Blueprint('cognitive', __name__)

groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))

GROQ_MODELS = [
    'groq/compound-mini',
    'groq/compound',
    'openai/gpt-oss-120b',
    'qwen/qwen3.8-27b',
]


def generate_ai(prompt, max_tokens=2000):
    last_error = None
    for model in GROQ_MODELS:
        try:
            response = groq_client.chat.completions.create(
                model      = model,
                messages   = [{"role":"user","content":prompt}],
                max_tokens = max_tokens,
                temperature= 0.8
            )
            result = response.choices[0].message.content.strip()
            print(f"✅ Cognitive AI: {model}")
            return result
        except Exception as e:
            err = str(e)
            last_error = err
            if '429' in err or 'rate' in err.lower():
                print(f"⚠️ Rate limit: {model}")
                time.sleep(2)
                continue
            elif '401' in err or 'invalid_api_key' in err.lower():
                break
            continue

    # Gemini fallback
    GEMINI_MODELS = ['gemini-3.6-flash', 'gemini-3.5-flash', 'gemini-flash-latest']
    try:
        from google import genai
        gc = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        for model in GEMINI_MODELS:
            try:
                resp = gc.models.generate_content(model=model, contents=prompt)
                print(f"✅ Cognitive AI via Gemini fallback: {model}")
                return resp.text.strip()
            except Exception as ge:
                err = str(ge)
                if '429' in err or 'quota' in err.lower():
                    time.sleep(2); continue
                continue
    except Exception as e:
        raise Exception(f"All AI models failed. Last: {last_error} | Gemini: {e}")
    raise Exception(f"All AI models failed. Last: {last_error}")


# ============================================================
# GENERATE COGNITIVE QUESTIONS VIA AI
# ============================================================
def generate_cognitive_questions():
    prompt = """Generate exactly 10 multiple choice questions for a cognitive assessment test.

Categories (must include ALL 4):
- Logical Reasoning: 3 questions (pattern recognition, sequences, deduction)
- Numerical Ability: 3 questions (math, calculations, number patterns)
- Verbal Ability: 2 questions (vocabulary, comprehension, analogies)
- Problem Solving: 2 questions (puzzles, critical thinking, scenarios)

Rules:
- Questions must be DIFFERENT every time (randomize)
- Medium difficulty level
- Clear, unambiguous questions
- 4 options each (A, B, C, D)
- Only ONE correct answer

Return ONLY valid JSON array, no other text:
[
  {
    "question": "Question text here?",
    "category": "Logical Reasoning",
    "options": {"A": "option1", "B": "option2", "C": "option3", "D": "option4"},
    "correct": "A",
    "explanation": "Why this is correct"
  }
]"""

    try:
        raw   = generate_ai(prompt)
        raw   = raw.replace('```json','').replace('```','').strip()
        start = raw.find('[')
        end   = raw.rfind(']') + 1
        if start != -1 and end > start:
            raw = raw[start:end]
        questions = json.loads(raw)

        # Ensure exactly 10
        questions = questions[:10]
        print(f"✅ Generated {len(questions)} cognitive questions")
        return questions

    except Exception as e:
        print(f"❌ Cognitive generation error: {e}")
        return get_fallback_questions()


def get_fallback_questions():
    """Fallback questions if AI fails"""
    return [
        {
            "question": "What comes next in the sequence: 2, 4, 8, 16, ?",
            "category": "Logical Reasoning",
            "options": {"A": "24", "B": "32", "C": "28", "D": "20"},
            "correct": "B",
            "explanation": "Each number doubles: 16 × 2 = 32"
        },
        {
            "question": "If all cats are animals, and some animals are pets, which is definitely true?",
            "category": "Logical Reasoning",
            "options": {
                "A": "All cats are pets",
                "B": "Some cats are pets",
                "C": "All cats are animals",
                "D": "No cats are pets"
            },
            "correct": "C",
            "explanation": "The first statement directly states all cats are animals"
        },
        {
            "question": "Find the odd one out: 144, 169, 196, 225, 250",
            "category": "Logical Reasoning",
            "options": {"A": "144", "B": "196", "C": "250", "D": "225"},
            "correct": "C",
            "explanation": "250 is not a perfect square. Others are: 12², 13², 14², 15²"
        },
        {
            "question": "What is 15% of 240?",
            "category": "Numerical Ability",
            "options": {"A": "36", "B": "24", "C": "48", "D": "32"},
            "correct": "A",
            "explanation": "15% × 240 = 0.15 × 240 = 36"
        },
        {
            "question": "A train travels 120km in 2 hours. How long for 300km?",
            "category": "Numerical Ability",
            "options": {"A": "4 hours", "B": "5 hours", "C": "6 hours", "D": "3 hours"},
            "correct": "B",
            "explanation": "Speed = 60km/h. Time = 300/60 = 5 hours"
        },
        {
            "question": "If 5 workers complete a job in 12 days, how many days for 3 workers?",
            "category": "Numerical Ability",
            "options": {"A": "15", "B": "18", "C": "20", "D": "24"},
            "correct": "C",
            "explanation": "5×12 = 60 worker-days. 60÷3 = 20 days"
        },
        {
            "question": "Choose the word most similar to 'ELOQUENT':",
            "category": "Verbal Ability",
            "options": {"A": "Silent", "B": "Articulate", "C": "Confused", "D": "Boring"},
            "correct": "B",
            "explanation": "Eloquent means fluent and persuasive speech, similar to articulate"
        },
        {
            "question": "BOOK is to LIBRARY as PAINTING is to:",
            "category": "Verbal Ability",
            "options": {"A": "Artist", "B": "Canvas", "C": "Gallery", "D": "Museum"},
            "correct": "C",
            "explanation": "Books are stored in libraries; paintings are displayed in galleries"
        },
        {
            "question": "A farmer has 17 sheep. All but 9 die. How many are left?",
            "category": "Problem Solving",
            "options": {"A": "8", "B": "9", "C": "17", "D": "0"},
            "correct": "B",
            "explanation": "'All but 9' means 9 survive"
        },
        {
            "question": "You have 3 boxes: Apples, Oranges, Mixed. All labels are wrong. You pick one fruit from Mixed box — it's an apple. How do you label all boxes correctly?",
            "category": "Problem Solving",
            "options": {
                "A": "Mixed=Apples, Apples=Oranges, Oranges=Mixed",
                "B": "Mixed=Apples, Oranges=Mixed, Apples=Oranges",
                "C": "Cannot determine",
                "D": "Need more information"
            },
            "correct": "B",
            "explanation": "Since Mixed box had apple → it's Apples. Apples box must be Oranges (wrong label). Oranges box must be Mixed"
        }
    ]


# ============================================================
# COGNITIVE TEST PAGE
# ============================================================
@cognitive_bp.route('/cognitive-test')
@login_required
def cognitive_test():
    user_id = session['user_id']

    # Check if already done
    existing = execute_query(
        "SELECT id FROM cognitive_results WHERE user_id=%s",
        (user_id,), fetch=True
    )

    if existing:
        return redirect(url_for('dashboard.index'))

    return render_template('cognitive_test.html')


# ============================================================
# GET QUESTIONS — AI Generated
# ============================================================
@cognitive_bp.route('/cognitive/get-questions')
@login_required
def get_questions():
    try:
        questions = generate_cognitive_questions()
        return jsonify({
            'success'  : True,
            'questions': questions,
            'total'    : len(questions)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })


# ============================================================
# SUBMIT COGNITIVE TEST
# ============================================================
@cognitive_bp.route('/cognitive/submit', methods=['POST'])
@login_required
def submit_cognitive():
    data    = request.get_json()
    user_id = session['user_id']
    answers = data.get('answers', {})
    questions = data.get('questions', [])

    if not questions:
        return jsonify({
            'success': False,
            'message': 'No questions found'
        })

    # Category scores
    scores = {
        'Logical Reasoning': {'correct': 0, 'total': 0},
        'Numerical Ability' : {'correct': 0, 'total': 0},
        'Verbal Ability'    : {'correct': 0, 'total': 0},
        'Problem Solving'   : {'correct': 0, 'total': 0},
    }

    for i, q in enumerate(questions):
        category = q.get('category', 'Logical Reasoning')
        correct  = q.get('correct', '')
        user_ans = answers.get(str(i), '')

        if category in scores:
            scores[category]['total'] += 1
            if user_ans == correct:
                scores[category]['correct'] += 1

    logical   = scores['Logical Reasoning']['correct']
    numerical = scores['Numerical Ability']['correct']
    verbal    = scores['Verbal Ability']['correct']
    problem   = scores['Problem Solving']['correct']
    total     = logical + numerical + verbal + problem

    # Detect learning style
    learning_style = detect_learning_style(
        logical, numerical, verbal, problem, total
    )

    # Save to DB
    execute_query(
        """INSERT INTO cognitive_results
           (user_id, logical_score, numerical_score,
            verbal_score, problem_solving_score,
            total_score, learning_style)
           VALUES (%s,%s,%s,%s,%s,%s,%s)
           ON DUPLICATE KEY UPDATE
           logical_score          = %s,
           numerical_score        = %s,
           verbal_score           = %s,
           problem_solving_score  = %s,
           total_score            = %s,
           learning_style         = %s""",
        (user_id, logical, numerical, verbal, problem,
         total, learning_style,
         logical, numerical, verbal, problem,
         total, learning_style)
    )

    execute_query(
        "UPDATE users SET onboarding_done=1 WHERE id=%s",
        (user_id,)
    )

    session['onboarding_done'] = 1

    return jsonify({
        'success'       : True,
        'scores'        : {
            'logical'  : logical,
            'numerical': numerical,
            'verbal'   : verbal,
            'problem'  : problem,
            'total'    : total
        },
        'learning_style': learning_style,
        'redirect'      : '/dashboard'
    })


def detect_learning_style(logical, numerical, verbal,
                           problem, total):
    if total >= 9:
        return 'Advanced Learner'
    elif total <= 3:
        return 'Developing Learner'
    elif logical >= 3 and numerical >= 3:
        return 'Analytical Learner'
    elif verbal >= 2 and problem >= 2:
        return 'Creative Learner'
    elif problem >= 2 and logical >= 2:
        return 'Strategic Learner'
    else:
        return 'Balanced Learner'