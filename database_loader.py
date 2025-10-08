# database_loader.py - Smart database loader
# Automatically uses PostgreSQL if DATABASE_URL exists, otherwise SQLite
import os

if os.getenv("DATABASE_URL"):
    # PostgreSQL
    from database_postgres import *
    from database_postgres import _conn  # Explicitly export _conn for owner.py
else:
    # SQLite
    from database import *
    from database import _conn  # Explicitly export _conn for owner.py
