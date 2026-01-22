"""
Database module for RedditListener
Handles SQLite database operations for storing Reddit threads and summaries
"""
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

DATABASE_PATH = 'reddit_threads.db'

def init_database():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create threads table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT UNIQUE,
            subreddit TEXT NOT NULL,
            title TEXT NOT NULL,
            author TEXT,
            created_date TEXT,
            posted_time TEXT,
            flair TEXT,
            content TEXT,
            url TEXT,
            summary TEXT,
            downloaded_at TEXT NOT NULL,
            summarized_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully")

def insert_thread(thread_data: Dict) -> bool:
    """Insert a new thread into the database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO threads 
            (thread_id, subreddit, title, author, created_date, posted_time, 
             flair, content, url, downloaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            thread_data.get('thread_id'),
            thread_data.get('subreddit'),
            thread_data.get('title'),
            thread_data.get('author'),
            thread_data.get('created_date'),
            thread_data.get('posted_time'),
            thread_data.get('flair'),
            thread_data.get('content'),
            thread_data.get('url'),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error inserting thread: {e}")
        return False

def get_all_threads() -> List[Dict]:
    """Retrieve all threads from the database"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM threads 
        ORDER BY downloaded_at DESC
    ''')
    
    rows = cursor.fetchall()
    threads = [dict(row) for row in rows]
    
    conn.close()
    return threads

def get_thread_by_id(thread_id: int) -> Optional[Dict]:
    """Retrieve a specific thread by its database ID"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM threads WHERE id = ?', (thread_id,))
    row = cursor.fetchone()
    
    conn.close()
    return dict(row) if row else None

def update_thread_summary(thread_id: int, summary: str) -> bool:
    """Update the summary for a specific thread"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE threads 
            SET summary = ?, summarized_at = ?
            WHERE id = ?
        ''', (summary, datetime.now().isoformat(), thread_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating summary: {e}")
        return False

def get_threads_without_summary() -> List[Dict]:
    """Get all threads that don't have summaries yet"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM threads 
        WHERE summary IS NULL OR summary = ""
        ORDER BY downloaded_at DESC
    ''')
    
    rows = cursor.fetchall()
    threads = [dict(row) for row in rows]
    
    conn.close()
    return threads

def clear_all_threads() -> bool:
    """Clear all threads from the database (for testing)"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM threads')
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error clearing threads: {e}")
        return False
