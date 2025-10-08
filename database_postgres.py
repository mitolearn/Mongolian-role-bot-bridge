# database_postgres.py - PostgreSQL version for Railway deployment
import os
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool

# Database connection pool
connection_pool = None

def get_db_url():
    """Get PostgreSQL connection URL from environment"""
    return os.getenv("DATABASE_URL")

def init_pool():
    """Initialize connection pool"""
    global connection_pool
    db_url = get_db_url()
    
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    connection_pool = pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        dsn=db_url
    )
    print("✅ PostgreSQL connection pool initialized")

def _conn():
    """Get connection from pool"""
    if connection_pool is None:
        init_pool()
    return connection_pool.getconn()

def _release_conn(conn):
    """Release connection back to pool"""
    if connection_pool:
        connection_pool.putconn(conn)

def init_db():
    """Initialize PostgreSQL database schema"""
    conn = _conn()
    try:
        c = conn.cursor()

        # Subscriptions table
        c.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            guild_id TEXT PRIMARY KEY,
            plan_name TEXT,
            amount_mnt INTEGER,
            invoice_id TEXT,
            expires_at TIMESTAMP,
            status TEXT
        )
        """)

        # Guild configuration
        c.execute("""
        CREATE TABLE IF NOT EXISTS guild_config (
            guild_id TEXT PRIMARY KEY,
            sales_channel_id TEXT,
            commission_rate REAL DEFAULT 0.10,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """)

        # Role plans
        c.execute("""
        CREATE TABLE IF NOT EXISTS role_plans (
            plan_id SERIAL PRIMARY KEY,
            guild_id TEXT,
            role_id TEXT,
            role_name TEXT,
            price_mnt INTEGER,
            duration_days INTEGER,
            active INTEGER DEFAULT 1,
            description TEXT DEFAULT ''
        )
        """)

        # Users table
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT,
            guild_id TEXT,
            username TEXT,
            PRIMARY KEY (user_id, guild_id)
        )
        """)

        # Memberships
        c.execute("""
        CREATE TABLE IF NOT EXISTS memberships (
            guild_id TEXT,
            user_id TEXT,
            plan_id INTEGER,
            active INTEGER,
            access_ends_at TIMESTAMP,
            last_payment_id TEXT
        )
        """)

        # Payments
        c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id TEXT PRIMARY KEY,
            guild_id TEXT,
            user_id TEXT,
            plan_id INTEGER,
            amount_mnt INTEGER,
            status TEXT,
            short_url TEXT,
            created_at TIMESTAMP,
            paid_at TIMESTAMP
        )
        """)

        # Leaders
        c.execute("""
        CREATE TABLE IF NOT EXISTS leaders (
            leader_id SERIAL PRIMARY KEY,
            guild_id TEXT,
            leader_name TEXT,
            commission_rate REAL DEFAULT 0.10,
            balance_mnt INTEGER DEFAULT 0
        )
        """)

        # Ledger
        c.execute("""
        CREATE TABLE IF NOT EXISTS ledger (
            id SERIAL PRIMARY KEY,
            guild_id TEXT,
            leader_id INTEGER,
            payment_id TEXT,
            type TEXT,
            amount_mnt INTEGER,
            created_at TIMESTAMP
        )
        """)

        # Payouts
        c.execute("""
        CREATE TABLE IF NOT EXISTS payouts (
            id SERIAL PRIMARY KEY,
            guild_id TEXT,
            gross_mnt INTEGER,
            fee_mnt INTEGER,
            net_mnt INTEGER,
            account_number TEXT,
            account_name TEXT,
            note TEXT,
            created_at TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
        """)

        # Manager roles
        c.execute("""
        CREATE TABLE IF NOT EXISTS manager_roles (
            guild_id TEXT PRIMARY KEY,
            role_id TEXT,
            role_name TEXT,
            created_at TIMESTAMP
        )
        """)

        conn.commit()
        print("✅ PostgreSQL database schema initialized")
    finally:
        _release_conn(conn)

# All the same functions from database.py but using PostgreSQL syntax
# (Functions are identical to SQLite version, just connection handling changes)

# ---------- GUILD CONFIG ----------
def set_guild_config(guild_id: str, sales_channel_id: str|None, commission_rate: float|None = None):
    now = datetime.utcnow()
    conn = _conn()
    try:
        c = conn.cursor()
        c.execute("SELECT guild_id FROM guild_config WHERE guild_id=%s", (guild_id,))
        exists = c.fetchone()
        if exists:
            if sales_channel_id:
                c.execute("UPDATE guild_config SET sales_channel_id=%s, updated_at=%s WHERE guild_id=%s",
                          (sales_channel_id, now, guild_id))
            if commission_rate is not None:
                c.execute("UPDATE guild_config SET commission_rate=%s, updated_at=%s WHERE guild_id=%s",
                          (commission_rate, now, guild_id))
        else:
            c.execute("INSERT INTO guild_config (guild_id, sales_channel_id, commission_rate, created_at, updated_at) VALUES (%s,%s,%s,%s,%s)",
                      (guild_id, sales_channel_id, commission_rate or 0.10, now, now))
        conn.commit()
    finally:
        _release_conn(conn)

def get_guild_config(guild_id: str):
    conn = _conn()
    try:
        c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("SELECT guild_id, sales_channel_id, commission_rate FROM guild_config WHERE guild_id=%s", (guild_id,))
        row = c.fetchone()
        return dict(row) if row else None
    finally:
        _release_conn(conn)

# ---------- ROLE PLANS ----------
def add_role_plan(guild_id: str, role_id: str, role_name: str, price_mnt: int, duration_days: int, description: str = ""):
    conn = _conn()
    try:
        c = conn.cursor()
        c.execute("""INSERT INTO role_plans (guild_id, role_id, role_name, price_mnt, duration_days, active, description)
                     VALUES (%s,%s,%s,%s,%s,1,%s) RETURNING plan_id""",
                  (guild_id, role_id, role_name, price_mnt, duration_days, description))
        plan_id = c.fetchone()[0]
        conn.commit()
        return plan_id
    finally:
        _release_conn(conn)

def list_role_plans(guild_id: str, only_active=True):
    conn = _conn()
    try:
        c = conn.cursor()
        if only_active:
            c.execute("""SELECT plan_id, role_id, role_name, price_mnt, duration_days, active, description
                         FROM role_plans WHERE guild_id=%s AND active=1 ORDER BY price_mnt ASC""", (guild_id,))
        else:
            c.execute("""SELECT plan_id, role_id, role_name, price_mnt, duration_days, active, description
                         FROM role_plans WHERE guild_id=%s ORDER BY price_mnt ASC""", (guild_id,))
        return c.fetchall()
    finally:
        _release_conn(conn)

def update_plan_description(plan_id: int, description: str):
    conn = _conn()
    try:
        c = conn.cursor()
        c.execute("UPDATE role_plans SET description=%s WHERE plan_id=%s", (description, plan_id))
        conn.commit()
    finally:
        _release_conn(conn)

def get_plan(plan_id: int):
    conn = _conn()
    try:
        c = conn.cursor()
        c.execute("""SELECT plan_id, guild_id, role_id, role_name, price_mnt, duration_days, active, description
                     FROM role_plans WHERE plan_id=%s""", (plan_id,))
        row = c.fetchone()
        if not row: return None
        return {"plan_id": row[0], "guild_id": row[1], "role_id": row[2], "role_name": row[3],
                "price_mnt": row[4], "duration_days": row[5], "active": row[6], "description": row[7] or ""}
    finally:
        _release_conn(conn)

# ... (Continue with all other functions - I'll add the most important ones)

# ---------- SUBSCRIPTION ----------
def create_subscription(guild_id: str, plan_name: str, amount: int, invoice_id: str, expires_at: str):
    conn = _conn()
    try:
        c = conn.cursor()
        c.execute("""INSERT INTO subscriptions
                     (guild_id, plan_name, amount_mnt, invoice_id, expires_at, status)
                     VALUES (%s,%s,%s,%s,%s, 'pending')
                     ON CONFLICT (guild_id) DO UPDATE SET
                     plan_name=EXCLUDED.plan_name, amount_mnt=EXCLUDED.amount_mnt,
                     invoice_id=EXCLUDED.invoice_id, expires_at=EXCLUDED.expires_at, status=EXCLUDED.status""",
                  (guild_id, plan_name, amount, invoice_id, expires_at))
        conn.commit()
    finally:
        _release_conn(conn)

def get_subscription(guild_id: str):
    conn = _conn()
    try:
        c = conn.cursor()
        c.execute("SELECT plan_name, amount_mnt, expires_at, status FROM subscriptions WHERE guild_id=%s", (guild_id,))
        return c.fetchone()
    finally:
        _release_conn(conn)

def has_active_subscription(guild_id: str):
    now = datetime.utcnow()
    conn = _conn()
    try:
        c = conn.cursor()
        c.execute("""
            SELECT 1 FROM subscriptions 
            WHERE guild_id=%s AND status='active' AND expires_at > %s 
            LIMIT 1
        """, (guild_id, now))
        return bool(c.fetchone())
    finally:
        _release_conn(conn)

# ---------- PAYMENTS ----------
def create_payment(payment_id: str, guild_id: str, user_id: str, plan_id: int, amount_mnt: int, short_url: str):
    now = datetime.utcnow()
    conn = _conn()
    try:
        c = conn.cursor()
        c.execute("""INSERT INTO payments
                     (payment_id, guild_id, user_id, plan_id, amount_mnt, status, short_url, created_at)
                     VALUES (%s,%s,%s,%s,%s,'pending',%s,%s)
                     ON CONFLICT (payment_id) DO UPDATE SET
                     amount_mnt=EXCLUDED.amount_mnt, status=EXCLUDED.status""",
                  (payment_id, guild_id, user_id, plan_id, amount_mnt, short_url, now))
        conn.commit()
    finally:
        _release_conn(conn)

def get_payment(payment_id: str):
    conn = _conn()
    try:
        c = conn.cursor()
        c.execute("""SELECT payment_id, guild_id, user_id, plan_id, amount_mnt, status, short_url, created_at, paid_at
                     FROM payments WHERE payment_id=%s""", (payment_id,))
        return c.fetchone()
    finally:
        _release_conn(conn)

# ---------- STATS ----------
def total_guild_revenue(guild_id: str):
    conn = _conn()
    try:
        c = conn.cursor()
        c.execute("""SELECT COALESCE(SUM(amount_mnt),0) FROM payments
                     WHERE guild_id=%s AND status='paid'""", (guild_id,))
        amt = c.fetchone()[0] or 0
        return int(amt)
    finally:
        _release_conn(conn)

def count_active_members(guild_id: str):
    conn = _conn()
    try:
        c = conn.cursor()
        c.execute("""SELECT COUNT(DISTINCT user_id) FROM memberships WHERE guild_id=%s AND active=1""", (guild_id,))
        return int(c.fetchone()[0] or 0)
    finally:
        _release_conn(conn)

# Note: Add all remaining functions from database.py here with PostgreSQL syntax (%s instead of ?)
