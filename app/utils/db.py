import mysql.connector.pooling
import os
from dotenv import load_dotenv

load_dotenv()

import mysql.connector
import mysql.connector.pooling

_db_pool = None

def _get_pool():
    global _db_pool
    if _db_pool is None:
        try:
            _db_pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="ai_platform_pool",
                # Keep this small on hosted databases: each server copy opens this many
                pool_size=int(os.getenv('DB_POOL_SIZE', 10)),
                pool_reset_session=True,
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', 3306)),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASSWORD', ''),
                database=os.getenv('DB_NAME', 'ai_learning_platform'),
                connection_timeout=10,
            )
        except Exception as e:
            print(f"[WARN] Connection pool init warning: {e}")
            return None
    return _db_pool

def get_db_connection():
    try:
        pool = _get_pool()
        if pool:
            conn = pool.get_connection()
            # Hosted databases close idle connections; reconnect instead of failing the request
            conn.ping(reconnect=True, attempts=2, delay=0)
            return conn
        return mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'ai_learning_platform'),
            connection_timeout=3
        )
    except mysql.connector.Error as e:
        print(f"[ERROR] DB connection failed: {e}")
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
        print(f"[ERROR] Query failed: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


def fetch_query(query, params=None):
    """Execute a SQL query and fetch all results."""
    return execute_query(query, params, fetch=True)
