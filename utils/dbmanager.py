import sqlite3
import json
import uuid
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_name="admissions_data.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        """Initializes the database with all application and reference tables."""
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
                    transcript_blob BLOB,  
                    ielts_blob BLOB,       
                    FOREIGN KEY(username) REFERENCES users(username)
                )
            """)

            # 3. Referees Table (Referee Authentication)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS referees (
                    email TEXT PRIMARY KEY,
                    password TEXT NOT NULL
                )
            """)

            # 4. Reference Requests Table (The Relational Link)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS reference_requests (
                    id TEXT PRIMARY KEY,
                    candidate_id TEXT,
                    referee_email TEXT,
                    referee_name TEXT,
                    referee_designation TEXT,
                    status TEXT DEFAULT 'pending',
                    chat_history_json TEXT,
                    created_at TEXT,
                    FOREIGN KEY(candidate_id) REFERENCES candidates(candidate_id),
                    FOREIGN KEY(referee_email) REFERENCES referees(email)
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
        """Checks if the username and password match, providing specific error messages."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        
        if not result:
            return False, "Username not found. Please click 'Create Account' to register."
        if result[0] == password:
            return True, "Login successful!"
            
        return False, "Incorrect password. Please try again."
    
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
    def create_candidate_record(self, user_data, transcript_report, audit_logs, transcript_bytes=None, ielts_bytes=None):
        """Creates the initial application row, linked to the logged-in username."""
        candidate_id = str(uuid.uuid4())[:8].upper()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.conn:
            self.conn.execute("""
                INSERT INTO candidates (
                    candidate_id, username, created_at, first_name, last_name, program, 
                    user_data_json, transcript_report, audit_logs_json, status, transcript_blob, ielts_blob
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                candidate_id, 
                user_data.get('username'), 
                created_at, 
                user_data['first_name'], 
                user_data['last_name'], 
                user_data['degree'], 
                json.dumps(user_data), 
                transcript_report, 
                json.dumps(audit_logs), 
                "interviewing",
                transcript_bytes,
                ielts_bytes 
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

    def update_admin_decision(self, candidate_id, final_status):
        """Saves the human Admin's final admissions decision."""
        with self.conn:
            self.conn.execute("""
                UPDATE candidates 
                SET status = ? 
                WHERE candidate_id = ?
            """, (final_status, candidate_id))

    def update_candidate_status(self, candidate_id, status):
        """Allows us to set a student to 'pending_references' without a final verdict yet."""
        with self.conn:
            self.conn.execute("UPDATE candidates SET status = ? WHERE candidate_id = ?", (status, candidate_id))

    def get_all_candidates(self):
        """Fetches all candidates for the Admin view."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM candidates ORDER BY created_at DESC")
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    # ==========================================
    # REFEREE AUTHENTICATION
    # ==========================================
    def create_referee_account(self, email, password):
        try:
            with self.conn:
                self.conn.execute("INSERT INTO referees (email, password) VALUES (?, ?)", (email.lower(), password))
            return True, "Referee account created successfully!"
        except sqlite3.IntegrityError:
            return False, "An account with this email already exists."

    def verify_referee_login(self, email, password):
        cursor = self.conn.cursor()
        cursor.execute("SELECT password FROM referees WHERE email = ?", (email.lower(),))
        result = cursor.fetchone()
        if not result:
            return False, "Email not found. Please click 'Create Account' to register."
        if result[0] == password:
            return True, "Login successful!"
        return False, "Incorrect password. Please try again."

    # ==========================================
    # REFERENCE REQUEST LOGIC
    # ==========================================
    def create_reference_request(self, candidate_id, referee_email, referee_name, referee_designation):
        """Creates a pending request linked to both the candidate and the referee's email."""
        req_id = f"REF-{str(uuid.uuid4())[:6].upper()}"
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.conn:
            self.conn.execute("""
                INSERT INTO reference_requests (
                    id, candidate_id, referee_email, referee_name, referee_designation, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (req_id, candidate_id, referee_email.lower(), referee_name, referee_designation, created_at))
        return req_id

    def get_references_by_email(self, email):
        """Joins the request table with the candidates table so the Referee UI has the context."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT r.id, r.candidate_id, r.referee_name, r.referee_designation, r.status,
                   c.first_name || ' ' || c.last_name as candidate_name,
                   c.program as candidate_program, c.transcript_report
            FROM reference_requests r
            JOIN candidates c ON r.candidate_id = c.candidate_id
            WHERE r.referee_email = ?
            ORDER BY r.created_at DESC
        """, (email.lower(),))
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def complete_reference(self, request_id, chat_display):
        """Saves the referee interview transcript and marks the request as completed."""
        clean_history = [{"role": msg[0], "content": msg[1]} for msg in chat_display]
        with self.conn:
            self.conn.execute("""
                UPDATE reference_requests 
                SET chat_history_json = ?, status = 'completed'
                WHERE id = ?
            """, (json.dumps(clean_history), request_id))

    def check_references_completed(self, candidate_id):
        """Checks if all references for a candidate are completed and returns them."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT status, chat_history_json 
            FROM reference_requests 
            WHERE candidate_id = ?
        """, (candidate_id,))
        requests = cursor.fetchall()
        
        # If there are no requests, or any are still pending, return False
        if not requests or any(req[0] == 'pending' for req in requests):
            return False, []
            
        # If all are complete, return True and the chat logs
        chat_logs = [json.loads(req[1]) for req in requests if req[1]]
        return True, chat_logs

    def get_candidate_for_evaluation(self, candidate_id):
        """Pulls the full candidate record so the Evaluation Engine can run."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,))
        row = cursor.fetchone()
        if row:
            columns = [column[0] for column in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def get_references_by_candidate(self, candidate_id):
        """Fetches all reference data for a specific candidate."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT referee_name, referee_designation, referee_email, status, chat_history_json
            FROM reference_requests
            WHERE candidate_id = ?
        """, (candidate_id,))
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]