import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Characters table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                description TEXT,
                relationship TEXT,
                personality TEXT,
                intensity INTEGER DEFAULT 3,
                voice_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP,
                total_sessions INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1
            )
        ''')

        # Responses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                tier INTEGER NOT NULL,
                text TEXT NOT NULL,
                audio_path TEXT NOT NULL,
                duration_ms INTEGER,
                times_played INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (character_id) REFERENCES characters(id)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_responses_char_tier ON responses(character_id, tier)')

        # Workout sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workout_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                total_punches INTEGER DEFAULT 0,
                avg_force REAL,
                max_force REAL,
                duration_seconds INTEGER,
                FOREIGN KEY (character_id) REFERENCES characters(id)
            )
        ''')

        # Punches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS punches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                character_id INTEGER NOT NULL,
                response_id INTEGER,
                force_value REAL NOT NULL,
                tier INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                response_latency_ms INTEGER,
                FOREIGN KEY (session_id) REFERENCES workout_sessions(id),
                FOREIGN KEY (character_id) REFERENCES characters(id),
                FOREIGN KEY (response_id) REFERENCES responses(id)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_punches_session ON punches(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_punches_char ON punches(character_id)')

        conn.commit()
        conn.close()

    # Character operations
    def create_character(self, name: str, slug: str, **kwargs) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO characters (name, slug, description, relationship, personality, intensity, voice_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            name,
            slug,
            kwargs.get('description'),
            kwargs.get('relationship'),
            kwargs.get('personality'),
            kwargs.get('intensity', 3),
            kwargs.get('voice_id')
        ))

        character_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return character_id

    def get_character(self, character_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM characters WHERE id = ?', (character_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_characters(self, active_only: bool = True) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        query = 'SELECT * FROM characters'
        if active_only:
            query += ' WHERE is_active = 1'
        query += ' ORDER BY last_used_at DESC, created_at DESC'
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_character_last_used(self, character_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE characters
            SET last_used_at = ?, total_sessions = total_sessions + 1
            WHERE id = ?
        ''', (datetime.now(), character_id))
        conn.commit()
        conn.close()

    def delete_character(self, character_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE characters SET is_active = 0 WHERE id = ?', (character_id,))
        conn.commit()
        conn.close()

    # Response operations
    def create_response(self, character_id: int, tier: int, text: str, audio_path: str, duration_ms: int = 0) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO responses (character_id, tier, text, audio_path, duration_ms)
            VALUES (?, ?, ?, ?, ?)
        ''', (character_id, tier, text, audio_path, duration_ms))

        response_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return response_id

    def get_responses_by_character(self, character_id: int, tier: Optional[int] = None) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()

        if tier is not None:
            cursor.execute('''
                SELECT * FROM responses
                WHERE character_id = ? AND tier = ?
                ORDER BY RANDOM()
            ''', (character_id, tier))
        else:
            cursor.execute('''
                SELECT * FROM responses
                WHERE character_id = ?
                ORDER BY tier, RANDOM()
            ''', (character_id,))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def increment_response_play_count(self, response_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE responses SET times_played = times_played + 1 WHERE id = ?', (response_id,))
        conn.commit()
        conn.close()

    # Session operations
    def create_session(self, character_id: int) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO workout_sessions (character_id)
            VALUES (?)
        ''', (character_id,))

        session_id = cursor.lastrowid
        conn.commit()
        conn.close()

        self.update_character_last_used(character_id)
        return session_id

    def end_session(self, session_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Calculate session stats
        cursor.execute('''
            SELECT COUNT(*) as total, AVG(force_value) as avg_force, MAX(force_value) as max_force
            FROM punches WHERE session_id = ?
        ''', (session_id,))
        stats = cursor.fetchone()

        # Get session start time
        cursor.execute('SELECT started_at FROM workout_sessions WHERE id = ?', (session_id,))
        start_time = cursor.fetchone()['started_at']
        duration = (datetime.now() - datetime.fromisoformat(start_time)).seconds

        # Update session
        cursor.execute('''
            UPDATE workout_sessions
            SET ended_at = ?, total_punches = ?, avg_force = ?, max_force = ?, duration_seconds = ?
            WHERE id = ?
        ''', (datetime.now(), stats['total'], stats['avg_force'], stats['max_force'], duration, session_id))

        conn.commit()
        conn.close()

    def get_session(self, session_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM workout_sessions WHERE id = ?', (session_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    # Punch operations
    def log_punch(self, session_id: int, character_id: int, force_value: float, tier: int,
                  response_id: Optional[int] = None, latency_ms: Optional[int] = None):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO punches (session_id, character_id, force_value, tier, response_id, response_latency_ms)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session_id, character_id, force_value, tier, response_id, latency_ms))

        conn.commit()
        conn.close()

        if response_id:
            self.increment_response_play_count(response_id)

    # Statistics
    def get_character_stats(self, character_id: int) -> Dict[str, Any]:
        conn = self.get_connection()
        cursor = conn.cursor()

        # Overall stats
        cursor.execute('''
            SELECT
                COUNT(DISTINCT ws.id) as total_sessions,
                COUNT(p.id) as total_punches,
                AVG(p.force_value) as avg_force,
                MAX(p.force_value) as max_force,
                SUM(CASE WHEN p.tier = 5 THEN 1 ELSE 0 END) as max_tier_punches
            FROM characters c
            LEFT JOIN workout_sessions ws ON c.id = ws.character_id
            LEFT JOIN punches p ON c.id = p.character_id
            WHERE c.id = ?
        ''', (character_id,))

        stats = dict(cursor.fetchone())

        # Recent sessions
        cursor.execute('''
            SELECT * FROM workout_sessions
            WHERE character_id = ?
            ORDER BY started_at DESC
            LIMIT 10
        ''', (character_id,))

        stats['recent_sessions'] = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return stats
