import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host     = os.getenv('DB_HOST',     'localhost'),
            port     = int(os.getenv('DB_PORT', 3306)),
            user     = os.getenv('DB_USER',     'root'),
            password = os.getenv('DB_PASSWORD', ''),
            database = os.getenv('DB_NAME',     'ai_learning_platform')
        )
        return conn
    except mysql.connector.Error as e:
        print(f"❌ DB connection failed: {e}")
        return None


def execute_query(query, params=None, fetch=True):
    conn = get_db_connection()
    if not conn:
        return False

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())
        
        # If query has no result set (e.g., INSERT, UPDATE, DELETE),
        # commit and return lastrowid (or rowcount or True if lastrowid is not set)
        if cursor.description is None:
            conn.commit()
            return cursor.lastrowid if cursor.lastrowid else True

        if fetch:
            return cursor.fetchall()
        else:
            conn.commit()
            return cursor.lastrowid

    except mysql.connector.Error as e:
        print(f"❌ Query failed: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


def fetch_query(query, params=None):
    """Execute a SQL query and fetch all results."""
    return execute_query(query, params, fetch=True)
