# app/database.py

import sqlite3
from typing import List
from .schemas import FinalBrief

DB_NAME = "research_final_history.db"

def init_db():
    """Initializes the database and creates the briefs table if it doesn't exist."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS briefs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                brief_json TEXT NOT NULL
            )
        """)
        conn.commit()
    print("Database initialized.")

def save_brief(user_id: str, brief: FinalBrief):
    """Saves a research brief to the database for a specific user."""
    brief_json = brief.model_dump_json()
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO briefs (user_id, topic, brief_json) VALUES (?, ?, ?)",
            (user_id, brief.topic, brief_json)
        )
        conn.commit()
    print(f"Brief for topic '{brief.topic}' saved for user '{user_id}'.")


def get_briefs_by_user(user_id: str) -> List[FinalBrief]:
    """Retrieves all research briefs for a specific user from the database."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT brief_json FROM briefs WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        
        briefs = []
        for row in rows:
            brief_json = row[0]
            brief_object = FinalBrief.model_validate_json(brief_json)
            briefs.append(brief_object)
        
        print(f"Found {len(briefs)} previous briefs for user '{user_id}'.")
        return briefs