# database_loader.py - Smart database loader (forced to SQLite)
# Always uses SQLite (production.db), ignores DATABASE_URL unless explicitly forced

import os

# ✅ Always prefer SQLite unless FORCE_POSTGRES=true is set
USE_POSTGRES = os.getenv("FORCE_POSTGRES", "false").lower() == "true"
DB_NAME = os.getenv("DB_NAME", "database.db")

if USE_POSTGRES:
    print("🐘 Using PostgreSQL database (FORCE_POSTGRES=true)")
    from database_postgres import *
    from database_postgres import _conn  # Export for owner.py
else:
    print(f"🗄️ Using SQLite database: {DB_NAME}")
    from database import *
    from database import _conn  # Export for owner.py