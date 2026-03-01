import sqlite3
import json
import uuid
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_name="admissions_data.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        """Initializes the database with Users and Candidates tables."""
        with self.conn:
            # 1. Users Table (For Authentication)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password TEXT NOT NULL
                )
            """)
            
            # 2. Candidates Table (For Application Data & PDFs)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS candidates (
                    candidate_id TEXT PRIMARY KEY,
                    username TEXT,
                    created_at TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    program TEXT,
                    user_data_json TEXT,
                    transcript_report TEXT,
                    chat_history_json TEXT,
                    audit_logs_json TEXT,
                    final_verdict_json TEXT,
                    status TEXT,
                    pdf_blob BLOB,
                    FOREIGN KEY(username) REFERENCES users(username)
                )
            """)

    # ==========================================
    # AUTHENTICATION LOGIC
    # ==========================================
    def create_account(self, username, password):
        """Attempts to register a new user. Fails if username is taken."""
        try:
            with self.conn:
                self.conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            return True, "Account created successfully!"
        except sqlite3.IntegrityError:
            return False, "Username already exists. Please choose another."

    def verify_login(self, username, password):
        """Checks if the username and password match."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        if result and result[0] == password:
            return True
        return False
    

    def get_application_by_username(self, username):
        """Fetches a user's application to prevent retakes or resume abandoned sessions."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM candidates WHERE username = ? ORDER BY created_at DESC LIMIT 1", (username,))
        row = cursor.fetchone()
        if row:
            columns = [column[0] for column in cursor.description]
            return dict(zip(columns, row))
        return None

    # ==========================================
    # APPLICATION LOGIC
    # ==========================================
    def create_candidate_record(self, user_data, transcript_report, audit_logs):
        """Creates the initial application row, linked to the logged-in username."""
        candidate_id = str(uuid.uuid4())[:8].upper()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.conn:
            self.conn.execute("""
                INSERT INTO candidates (
                    candidate_id, username, created_at, first_name, last_name, program, 
                    user_data_json, transcript_report, audit_logs_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                candidate_id, 
                user_data.get('username'), # Links the app to the user
                created_at, 
                user_data['first_name'], 
                user_data['last_name'], 
                user_data['degree'], 
                json.dumps(user_data), 
                transcript_report, 
                json.dumps(audit_logs), 
                "interviewing"
            ))
        return candidate_id

    def sync_to_db(self, candidate_id, chat_display, audit_logs):
        """Saves the chat and AI reasoning silently."""
        clean_history = [{"role": msg[0], "content": msg[1]} for msg in chat_display]
        with self.conn:
            self.conn.execute("""
                UPDATE candidates 
                SET chat_history_json = ?, audit_logs_json = ? 
                WHERE candidate_id = ?
            """, (json.dumps(clean_history), json.dumps(audit_logs), candidate_id))

    def update_final_verdict(self, candidate_id, final_verdict, audit_logs, pdf_bytes):
        """Saves the scorecard and the actual PDF file directly into the DB."""
        with self.conn:
            self.conn.execute("""
                UPDATE candidates 
                SET final_verdict_json = ?, audit_logs_json = ?, status = 'evaluated', pdf_blob = ?
                WHERE candidate_id = ?
            """, (json.dumps(final_verdict), json.dumps(audit_logs), pdf_bytes, candidate_id))

    def get_all_candidates(self):
        """Fetches all candidates for the Admin view."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM candidates ORDER BY created_at DESC")
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]