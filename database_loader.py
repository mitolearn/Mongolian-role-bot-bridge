# database_loader.py - Smart database loader
import os

# Check if PostgreSQL is available and DATABASE_URL is set for Railway
database_url = os.getenv("DATABASE_URL")
use_postgres = False

if database_url:
    try:
        import psycopg2
        # PostgreSQL module available - use it!
        print("🔄 Using PostgreSQL (Railway production)")
        from database_postgres import *
        use_postgres = True
    except ImportError:
        # PostgreSQL not available - fallback to SQLite
        print("⚠️ DATABASE_URL set but psycopg2 not installed - using SQLite")
        from database import *

if not use_postgres and not database_url:
    print("🔄 Using SQLite (Replit testing)")
    from database import *
