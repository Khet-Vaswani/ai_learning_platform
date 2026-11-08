import mysql.connector.pooling
import os
from dotenv import load_dotenv

load_dotenv()

import mysql.connector
import mysql.connector.pooling

_db_pool = None

# The app's SQL is written for XAMPP's MariaDB. Hosted MySQL 8 (e.g. Aiven) defaults to
# ANSI_QUOTES / ONLY_FULL_GROUP_BY / STRICT mode, which rejects some of it, so every
# connection uses the same mode as local MariaDB.
SQL_MODE = 'NO_ZERO_IN_DATE,NO_ZERO_DATE,NO_ENGINE_SUBSTITUTION'

def _get_pool():
    global _db_pool
    if _db_pool is None:
        try:
            _db_pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="ai_platform_pool",
                # Keep this small on hosted databases: each server copy opens this many
                pool_size=int(os.getenv('DB_POOL_SIZE', 10)),
                # Every query is its own transaction (autocommit), so a connection goes
                # back to the pool with nothing open: no reads holding locks or seeing
                # old data. That makes the per-query session reset unnecessary, which
                # saves a round trip to the database on every query.
                autocommit=True,
                pool_reset_session=False,
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', 3306)),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASSWORD', ''),
                database=os.getenv('DB_NAME', 'ai_learning_platform'),
                connection_timeout=10,
                sql_mode=SQL_MODE,
            )
        except Exception as e:
            print(f"[WARN] Connection pool init warning: {e}")
            return None
    return _db_pool

def get_db_connection():
    try:
        pool = _get_pool()
        if pool:
            return pool.get_connection()
        return mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'ai_learning_platform'),
            connection_timeout=3,
            sql_mode=SQL_MODE,
            autocommit=True,
        )
    except mysql.connector.Error as e:
        print(f"[ERROR] DB connection failed: {e}")
        return None


# Errors meaning the connection itself was dropped (hosted databases close idle ones)
_DROPPED = {2006, 2013, 2055}


def execute_query(query, params=None, fetch=True):
    conn = get_db_connection()
    if not conn:
        return False

    cursor = conn.cursor(dictionary=True)
    try:
        try:
            cursor.execute(query, params or ())
        except (mysql.connector.errors.OperationalError, mysql.connector.errors.InterfaceError) as e:
            if e.errno not in _DROPPED:
                raise
            # Reconnect and retry once, instead of checking the connection before every query
            cursor.close()
            conn.reconnect(attempts=2, delay=0)
            cursor = conn.cursor(dictionary=True)
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
