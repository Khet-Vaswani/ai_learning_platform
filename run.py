import sys
import io

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import os

# Vercel's TiDB Cloud integration sets TIDB_* variables; the app reads DB_*.
# Settings you add yourself as DB_* always win.
for _db, _tidb in (('DB_HOST', 'TIDB_HOST'), ('DB_PORT', 'TIDB_PORT'), ('DB_USER', 'TIDB_USER'),
                   ('DB_PASSWORD', 'TIDB_PASSWORD'), ('DB_NAME', 'TIDB_DATABASE')):
    if not os.getenv(_db) and os.getenv(_tidb):
        os.environ[_db] = os.environ[_tidb]

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)