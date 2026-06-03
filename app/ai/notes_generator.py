# ============================================================
# ai/notes_generator.py — AI-Powered Notes Generation
# ============================================================

import json
import re
from typing import Dict, List, Optional
import google.generativeai as genai
from app.utils.db import execute_query, fetch_query

class NotesGenerator:
    """Generate structured study notes from video transcripts using Gemini AI"""
    
    def __init__(self, api_key: str = None):
        """Initialize with Gemini API key"""
        if api_key:
            genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    async def generate_notes(self, 
                            video_id: str,
                            transcript: str,
                            topic: str,
                            learning_level: str = 'Beginner') -> Dict:
        """
        Generate comprehensive study notes from video transcript.
        
        Args:
            video_id: YouTube video ID
            transcript: Full video transcript
            topic: Topic/subject of the video
            learning_level: Beginner/Intermediate/Advanced
            
        Returns:
            Dictionary with structured notes
        """
        
        # Chunk the transcript if too long
        chunks = self._chunk_transcript(transcript, chunk_size=3000)
        
        # Generate summary for each chunk
        chunk_summaries = []
        for chunk in chunks:
            summary = await self._summarize_chunk(chunk)
            chunk_summaries.append(summary)
        
        # Combine summaries and generate full notes
        combined = '\n\n'.join(chunk_summaries)
        
        prompt = f"""
        Given the following video transcript chunks about "{topic}", generate comprehensive study notes.
        
        TRANSCRIPT:
        {combined}
        
        Generate notes in the following JSON format:
        {{
            "topic_heading": "Clear topic title",
            "learning_objectives": ["objective 1", "objective 2", ...],
            "key_concepts": [
                {{
                    "concept_name": "Name of concept",
                    "explanation": "Detailed explanation",
                    "bullet_points": ["point 1", "point 2", ...],
                    "example": "Real-world example"
                }},
                ...
            ],
            "important_formulas": [
                {{"formula": "Formula", "explanation": "What it means"}}
            ],
            "summary": "Concise summary of the topic",
            "practice_questions": [
                {{"question": "Q?", "answer": "A", "difficulty": "Easy/Medium/Hard"}}
            ]
        }}
        
        Generate notes appropriate for {learning_level} level learners.
        Ensure accuracy and clarity.
        """
        
        response = self.model.generate_content(prompt)
        
        try:
            notes_json = self._extract_json(response.text)
            return {
                'success': True,
                'notes': notes_json,
                'generated_at': __import__('datetime').datetime.now().isoformat(),
                'source': 'AI-Generated from Transcript'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'raw_notes': response.text
            }
    
    async def _summarize_chunk(self, chunk: str) -> str:
        """Summarize a transcript chunk"""
        prompt = f"""
        Summarize the following video transcript section concisely, extracting key concepts:
        
        {chunk}
        
        Provide a clear, structured summary.
        """
        response = self.model.generate_content(prompt)
        return response.text
    
    def _chunk_transcript(self, transcript: str, chunk_size: int = 3000) -> List[str]:
        """Break transcript into manageable chunks"""
        chunks = []
        for i in range(0, len(transcript), chunk_size):
            chunks.append(transcript[i:i + chunk_size])
        return chunks
    
    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from AI response"""
        # Try to find JSON block
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json.loads(json_match.group())
        raise ValueError("No JSON found in response")
    
    def save_notes(self, user_id: int, video_id: str, notes: Dict) -> bool:
        """Save generated notes to database"""
        try:
            execute_query(
                """INSERT INTO video_notes 
                   (user_id, video_id, notes)
                   VALUES (%s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                   notes = VALUES(notes)""",
                (user_id, video_id, json.dumps(notes))
            )
            return True
        except Exception as e:
            print(f"Error saving notes: {e}")
            return False
    
    def format_notes_html(self, notes: Dict) -> str:
        """Format notes for HTML display"""
        
        html = f"""
        <div class="notes-container">
            <h1>{notes.get('topic_heading', 'Study Notes')}</h1>
            
            <section class="learning-objectives">
                <h2>📚 Learning Objectives</h2>
                <ul>
                    {''.join(f'<li>{obj}</li>' for obj in notes.get('learning_objectives', []))}
                </ul>
            </section>
            
            <section class="key-concepts">
                <h2>🎯 Key Concepts</h2>
        """
        
        for concept in notes.get('key_concepts', []):
            html += f"""
                <div class="concept-block">
                    <h3>{concept.get('concept_name', 'Concept')}</h3>
                    <p><strong>Explanation:</strong> {concept.get('explanation', '')}</p>
                    <ul>
                        {''.join(f"<li>{point}</li>" for point in concept.get('bullet_points', []))}
                    </ul>
                    {f'<p><strong>Example:</strong> {concept.get("example", "")}</p>' if concept.get('example') else ''}
                </div>
            """
        
        html += """
            </section>
        """
        
        # Add formulas if present
        if notes.get('important_formulas'):
            html += """
                <section class="formulas">
                    <h2>📐 Important Formulas</h2>
            """
            for formula in notes['important_formulas']:
                html += f"""
                    <div class="formula-item">
                        <code>{formula.get('formula', '')}</code>
                        <p>{formula.get('explanation', '')}</p>
                    </div>
                """
            html += "</section>"
        
        # Add summary
        html += f"""
            <section class="summary">
                <h2>✅ Summary</h2>
                <p>{notes.get('summary', '')}</p>
            </section>
            
            <section class="practice">
                <h2>🧠 Practice Questions</h2>
        """
        
        for q in notes.get('practice_questions', []):
            html += f"""
                <div class="question-item">
                    <p><strong>Q:</strong> {q.get('question', '')}</p>
                    <p><strong>A:</strong> {q.get('answer', '')}</p>
                    <span class="difficulty">{q.get('difficulty', 'Medium')}</span>
                </div>
            """
        
        html += """
            </section>
        </div>
        """
        
        return html


# ============================================================
# Helper function for async usage in Flask
# ============================================================

def generate_notes_sync(video_id: str, transcript: str, topic: str, level: str = 'Beginner') -> Dict:
    """Synchronous wrapper for notes generation"""
    import asyncio
    
    generator = NotesGenerator()
    
    # Generate notes synchronously
    transcript_limited = transcript[:5000]

    prompt = f"""
    Given the following video transcript about "{topic}", generate comprehensive study notes.

    TRANSCRIPT:
    {transcript_limited}

    Generate notes in the following JSON format:
    {{
        "topic_heading": "Clear topic title",
        "learning_objectives": ["objective 1", "objective 2"],
        "key_concepts": [
            {{
                "concept_name": "Name of concept",
                "explanation": "Detailed explanation",
                "bullet_points": ["point 1", "point 2"],
                "example": "Real-world example"
            }}
        ],
        "important_formulas": [
            {{"formula": "Formula", "explanation": "What it means"}}
        ],
        "summary": "Concise summary of the topic",
        "practice_questions": [
            {{"question": "Q?", "answer": "A", "difficulty": "Easy"}}
        ]
    }}

    Ensure accuracy and clarity. Generate for {level} level learners.
    """
    
    try:
        response = generator.model.generate_content(prompt)
        notes_json = generator._extract_json(response.text)
        return {
            'success': True,
            'notes': notes_json,
            'generated_at': __import__('datetime').datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
