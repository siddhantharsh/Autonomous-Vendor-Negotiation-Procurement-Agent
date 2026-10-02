import sqlite3
import json
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "negotiations.db")

class NegotiationDB:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS negotiations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vendor_email TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    target_price TEXT,
                    current_offer TEXT,
                    status TEXT NOT NULL,
                    history TEXT NOT NULL,
                    last_updated TIMESTAMP NOT NULL
                )
            ''')
            conn.commit()

    def create_negotiation(self, vendor_email, product_name, target_price, initial_message):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            history = [{"role": "assistant", "content": initial_message, "timestamp": datetime.now().isoformat()}]
            cursor.execute('''
                INSERT INTO negotiations (vendor_email, product_name, target_price, current_offer, status, history, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (vendor_email, product_name, target_price, "None", "AWAITING_REPLY", json.dumps(history), datetime.now().isoformat()))
            conn.commit()
            return cursor.lastrowid

    def get_negotiation_by_email(self, vendor_email):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, vendor_email, product_name, target_price, current_offer, status, history, last_updated
                FROM negotiations
                WHERE vendor_email = ? AND status NOT IN ('ACCEPTED', 'REJECTED')
                ORDER BY last_updated DESC LIMIT 1
            ''', (vendor_email,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "vendor_email": row[1],
                    "product_name": row[2],
                    "target_price": row[3],
                    "current_offer": row[4],
                    "status": row[5],
                    "history": json.loads(row[6]),
                    "last_updated": row[7]
                }
            return None

    def update_negotiation(self, neg_id, status, current_offer, new_message=None, role="user"):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Fetch existing history
            cursor.execute('SELECT history FROM negotiations WHERE id = ?', (neg_id,))
            row = cursor.fetchone()
            if not row:
                return False
                
            history = json.loads(row[0])
            if new_message is not None:
                history.append({
                    "role": role,
                    "content": new_message,
                    "timestamp": datetime.now().isoformat()
                })
                
            cursor.execute('''
                UPDATE negotiations
                SET status = ?, current_offer = ?, history = ?, last_updated = ?
                WHERE id = ?
            ''', (status, current_offer, json.dumps(history), datetime.now().isoformat(), neg_id))
            conn.commit()
            return True
