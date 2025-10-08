# database_postgres.py - PostgreSQL implementation
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime, timedelta

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL environment variable not set!")

print(f"🗄️ Using PostgreSQL database")

def _conn():
    """Create database connection"""
    return psycopg2.connect(DATABASE_URL)

def init_db():
    """Initialize all database tables"""
    conn = _conn()
    c = conn.cursor()

    # Subscriptions table
    c.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        guild_id VARCHAR PRIMARY KEY,
        plan_name VARCHAR,
        amount_mnt INTEGER,
        invoice_id VARCHAR,
        expires_at TIMESTAMP,
        status VARCHAR
    )
    """)

    # Guild configuration (per server)
    c.execute("""
    CREATE TABLE IF NOT EXISTS guild_config (
        guild_id VARCHAR PRIMARY KEY,
        sales_channel_id VARCHAR,
        commission_rate REAL DEFAULT 0.10,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    )
    """)

    # Role plans (multiple paid roles per server)
    c.execute("""
    CREATE TABLE IF NOT EXISTS role_plans (
        plan_id SERIAL PRIMARY KEY,
        guild_id VARCHAR,
        role_id VARCHAR,
        role_name VARCHAR,
        price_mnt INTEGER,
        duration_days INTEGER,
        active INTEGER DEFAULT 1,
        description TEXT DEFAULT ''
    )
    """)

    # Check and add description column if missing
    c.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name='role_plans' AND column_name='description'
    """)
    if not c.fetchone():
        c.execute("ALTER TABLE role_plans ADD COLUMN description TEXT DEFAULT ''")

    # Users with guild support
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id VARCHAR,
        guild_id VARCHAR,
        username VARCHAR,
        PRIMARY KEY (user_id, guild_id)
    )
    """)

    # Memberships (who has access until when)
    c.execute("""
    CREATE TABLE IF NOT EXISTS memberships (
        guild_id VARCHAR,
        user_id VARCHAR,
        plan_id INTEGER,
        active INTEGER,
        access_ends_at TIMESTAMP,
        last_payment_id VARCHAR
    )
    """)

    # Payments
    c.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        payment_id VARCHAR PRIMARY KEY,
        guild_id VARCHAR,
        user_id VARCHAR,
        plan_id INTEGER,
        amount_mnt INTEGER,
        status VARCHAR,
        short_url VARCHAR,
        created_at TIMESTAMP,
        paid_at TIMESTAMP
    )
    """)

    # Leaders (optional revenue share)
    c.execute("""
    CREATE TABLE IF NOT EXISTS leaders (
        leader_id SERIAL PRIMARY KEY,
        guild_id VARCHAR,
        leader_name VARCHAR,
        commission_rate REAL DEFAULT 0.10,
        balance_mnt INTEGER DEFAULT 0
    )
    """)

    # Ledger (platform_fee, leader_share, sale, payout, etc.)
    c.execute("""
    CREATE TABLE IF NOT EXISTS ledger (
        id SERIAL PRIMARY KEY,
        guild_id VARCHAR,
        leader_id INTEGER,
        payment_id VARCHAR,
        type VARCHAR,
        amount_mnt INTEGER,
        created_at TIMESTAMP
    )
    """)

    # Payouts (collection requests)
    c.execute("""
    CREATE TABLE IF NOT EXISTS payouts (
        id SERIAL PRIMARY KEY,
        guild_id VARCHAR,
        gross_mnt INTEGER,
        fee_mnt INTEGER,
        net_mnt INTEGER,
        account_number VARCHAR,
        account_name VARCHAR,
        note TEXT,
        created_at TIMESTAMP,
        status VARCHAR DEFAULT 'pending'
    )
    """)

    # Manager roles
    c.execute("""
    CREATE TABLE IF NOT EXISTS manager_roles (
        guild_id VARCHAR PRIMARY KEY,
        role_id VARCHAR,
        role_name VARCHAR,
        created_at TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()
    print("✅ PostgreSQL tables initialized")

# ---------- GUILD CONFIG ----------
def set_guild_config(guild_id: str, sales_channel_id: str|None, commission_rate: float|None = None):
    now = datetime.utcnow()
    conn = _conn(); c = conn.cursor()
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
    conn.commit(); conn.close()

def get_guild_config(guild_id: str):
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT guild_id, sales_channel_id, commission_rate FROM guild_config WHERE guild_id=%s", (guild_id,))
    row = c.fetchone(); conn.close()
    if not row: return None
    return {"guild_id": row[0], "sales_channel_id": row[1], "commission_rate": row[2]}

# ---------- ROLE PLANS ----------
def add_role_plan(guild_id: str, role_id: str, role_name: str, price_mnt: int, duration_days: int, description: str = ""):
    conn = _conn(); c = conn.cursor()
    c.execute("""INSERT INTO role_plans (guild_id, role_id, role_name, price_mnt, duration_days, active, description)
                 VALUES (%s,%s,%s,%s,%s,1,%s) RETURNING plan_id""",
              (guild_id, role_id, role_name, price_mnt, duration_days, description))
    plan_id = c.fetchone()[0]
    conn.commit(); conn.close()
    return plan_id

def list_role_plans(guild_id: str, only_active=True):
    conn = _conn(); c = conn.cursor()
    if only_active:
        c.execute("""SELECT plan_id, role_id, role_name, price_mnt, duration_days, active, description
                     FROM role_plans WHERE guild_id=%s AND active=1 ORDER BY price_mnt ASC""", (guild_id,))
    else:
        c.execute("""SELECT plan_id, role_id, role_name, price_mnt, duration_days, active, description
                     FROM role_plans WHERE guild_id=%s ORDER BY price_mnt ASC""", (guild_id,))
    rows = c.fetchall(); conn.close()
    return rows

def update_plan_description(plan_id: int, description: str):
    """Update the description of a role plan"""
    conn = _conn(); c = conn.cursor()
    c.execute("UPDATE role_plans SET description=%s WHERE plan_id=%s", (description, plan_id))
    conn.commit(); conn.close()

def toggle_role_plan(plan_id: int, active: int):
    conn = _conn(); c = conn.cursor()
    c.execute("UPDATE role_plans SET active=%s WHERE plan_id=%s", (active, plan_id))
    conn.commit(); conn.close()

def delete_role_plan(plan_id: int):
    """Permanently delete a role plan from the database"""
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT plan_id FROM role_plans WHERE plan_id=%s", (plan_id,))
    if not c.fetchone():
        conn.close()
        return False
    c.execute("DELETE FROM role_plans WHERE plan_id=%s", (plan_id,))
    conn.commit()
    conn.close()
    return True

def get_plan(plan_id: int):
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT plan_id, guild_id, role_id, role_name, price_mnt, duration_days, active, description
                 FROM role_plans WHERE plan_id=%s""", (plan_id,))
    row = c.fetchone(); conn.close()
    if not row: return None
    return {"plan_id": row[0], "guild_id": row[1], "role_id": row[2], "role_name": row[3],
            "price_mnt": row[4], "duration_days": row[5], "active": row[6], "description": row[7] or ""}

# ---------- USERS ----------
def upsert_user(guild_id: str, user_id: str, username: str):
    conn = _conn(); c = conn.cursor()
    c.execute("""INSERT INTO users (user_id, guild_id, username) VALUES (%s,%s,%s)
                 ON CONFLICT (user_id, guild_id) DO UPDATE SET username=EXCLUDED.username""",
              (user_id, guild_id, username))
    conn.commit(); conn.close()

# ---------- PAYMENTS (REAL QPAY) ----------
def create_payment(payment_id: str, guild_id: str, user_id: str, plan_id: int, amount_mnt: int, short_url: str):
    now = datetime.utcnow()
    conn = _conn(); c = conn.cursor()
    c.execute("""INSERT INTO payments
                 (payment_id, guild_id, user_id, plan_id, amount_mnt, status, short_url, created_at)
                 VALUES (%s,%s,%s,%s,%s,'pending',%s,%s)
                 ON CONFLICT (payment_id) DO UPDATE SET 
                 guild_id=EXCLUDED.guild_id, user_id=EXCLUDED.user_id, plan_id=EXCLUDED.plan_id,
                 amount_mnt=EXCLUDED.amount_mnt, short_url=EXCLUDED.short_url""",
              (payment_id, guild_id, user_id, plan_id, amount_mnt, short_url, now))
    conn.commit(); conn.close()

def mark_payment_paid(payment_id: str):
    now = datetime.utcnow()
    conn = _conn(); c = conn.cursor()
    c.execute("UPDATE payments SET status='paid', paid_at=%s WHERE payment_id=%s", (now, payment_id))
    conn.commit(); conn.close()

def get_payment(payment_id: str):
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT payment_id, guild_id, user_id, plan_id, amount_mnt, status, short_url, created_at, paid_at
                 FROM payments WHERE payment_id=%s""", (payment_id,))
    row = c.fetchone(); conn.close()
    return row

def get_payment_by_user(guild_id: str, user_id: str):
    """Get user's most recent payment (for verify payment command)"""
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT payment_id, guild_id, user_id, plan_id, amount_mnt, status, short_url
                 FROM payments 
                 WHERE guild_id=%s AND user_id=%s 
                 ORDER BY created_at DESC 
                 LIMIT 1""", (guild_id, user_id))
    row = c.fetchone(); conn.close()
    return row

# ---------- MEMBERSHIPS ----------
def grant_membership(guild_id: str, user_id: str, plan_id: int, duration_days: int, last_payment_id: str):
    conn = _conn(); c = conn.cursor()
    
    c.execute("""SELECT access_ends_at FROM memberships
                 WHERE guild_id=%s AND user_id=%s AND plan_id=%s AND active=1""",
              (guild_id, user_id, plan_id))
    existing = c.fetchone()
    
    now = datetime.utcnow()
    
    if existing:
        existing_end = existing[0] if isinstance(existing[0], datetime) else datetime.fromisoformat(str(existing[0]))
        
        if existing_end > now:
            new_end = existing_end + timedelta(days=duration_days)
        else:
            new_end = now + timedelta(days=duration_days)
        
        c.execute("""UPDATE memberships 
                     SET access_ends_at=%s, last_payment_id=%s
                     WHERE guild_id=%s AND user_id=%s AND plan_id=%s AND active=1""",
                  (new_end, last_payment_id, guild_id, user_id, plan_id))
    else:
        new_end = now + timedelta(days=duration_days)
        c.execute("""INSERT INTO memberships (guild_id, user_id, plan_id, active, access_ends_at, last_payment_id)
                     VALUES (%s,%s,%s,%s,%s,%s)""", (guild_id, user_id, plan_id, 1, new_end, last_payment_id))
    
    conn.commit(); conn.close()
    return new_end.isoformat()

def list_expired(guild_id: str):
    now = datetime.utcnow()
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT user_id, plan_id FROM memberships
                 WHERE guild_id=%s AND active=1 AND access_ends_at < %s""", (guild_id, now))
    rows = c.fetchall(); conn.close()
    return rows

def deactivate_membership(guild_id: str, user_id: str, plan_id: int = None):
    """Deactivate specific membership or all memberships for a user"""
    conn = _conn(); c = conn.cursor()
    
    if plan_id is not None:
        c.execute("""UPDATE memberships SET active=0 WHERE guild_id=%s AND user_id=%s AND plan_id=%s""", 
                  (guild_id, user_id, plan_id))
    else:
        c.execute("""UPDATE memberships SET active=0 WHERE guild_id=%s AND user_id=%s""", (guild_id, user_id))
    
    conn.commit(); conn.close()

def get_membership_by_invoice(invoice_id: str):
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT guild_id, user_id, plan_id, active, access_ends_at, last_payment_id
                 FROM memberships WHERE last_payment_id=%s""", (invoice_id,))
    row = c.fetchone(); conn.close()
    return row

def get_user_active_membership(guild_id: str, user_id: str):
    """Get ALL active memberships for a user (supports multiple roles)"""
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT plan_id, access_ends_at FROM memberships
                 WHERE guild_id=%s AND user_id=%s AND active=1""", (guild_id, user_id))
    rows = c.fetchall(); conn.close()
    return rows

# ---------- STATS ----------
def guild_revenue_mnt(guild_id: str, days: int = 30):
    since = datetime.utcnow() - timedelta(days=days)
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT COALESCE(SUM(amount_mnt),0) FROM payments
                 WHERE guild_id=%s AND status='paid' AND created_at>=%s""", (guild_id, since))
    amt = c.fetchone()[0] or 0
    conn.close(); return int(amt)

def count_active_members(guild_id: str):
    """Count UNIQUE active members (not total memberships)"""
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT COUNT(DISTINCT user_id) FROM memberships WHERE guild_id=%s AND active=1""", (guild_id,))
    n = c.fetchone()[0] or 0
    conn.close(); return int(n)

# ---------- LEGACY FUNCTIONS ----------
def add_user(user_id, username, leader_id=None, role_given=None):
    conn = _conn(); c = conn.cursor()
    c.execute("""INSERT INTO users (user_id, guild_id, username) VALUES (%s, %s, %s)
                 ON CONFLICT (user_id, guild_id) DO NOTHING""",
              (user_id, "default", username))
    conn.commit(); conn.close()

def add_leader(leader_id, leader_name, commission_rate=0.1):
    conn = _conn(); c = conn.cursor()
    c.execute("""INSERT INTO leaders (leader_id, guild_id, leader_name, commission_rate, balance_mnt) 
                 VALUES (%s, %s, %s, %s, %s)
                 ON CONFLICT DO NOTHING""",
              (leader_id, "default", leader_name, commission_rate, 0))
    conn.commit(); conn.close()

def add_payment(payment_id, user_id, amount, status="pending", leader_id=None):
    now = datetime.utcnow()
    conn = _conn(); c = conn.cursor()
    c.execute("""INSERT INTO payments (payment_id, guild_id, user_id, plan_id, amount_mnt, status, created_at) 
                 VALUES (%s, %s, %s, %s, %s, %s, %s)
                 ON CONFLICT DO NOTHING""",
              (payment_id, "default", user_id, 1, int(amount), status, now))
    conn.commit(); conn.close()

def update_leader_balance(leader_id, amount):
    conn = _conn(); c = conn.cursor()
    c.execute("UPDATE leaders SET balance_mnt = balance_mnt + %s WHERE leader_id = %s", (int(amount), leader_id))
    conn.commit(); conn.close()

def get_leader_balance(leader_id):
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT balance_mnt FROM leaders WHERE leader_id = %s", (leader_id,))
    result = c.fetchone(); conn.close()
    return result[0] if result else 0

# ---------- SUBSCRIPTION FUNCTIONS ----------
def create_subscription(guild_id: str, plan_name: str, amount: int, invoice_id: str, expires_at: str):
    conn = _conn(); c = conn.cursor()
    expires_dt = datetime.fromisoformat(expires_at) if isinstance(expires_at, str) else expires_at
    c.execute("""INSERT INTO subscriptions
                 (guild_id, plan_name, amount_mnt, invoice_id, expires_at, status)
                 VALUES (%s,%s,%s,%s,%s, 'pending')
                 ON CONFLICT (guild_id) DO UPDATE SET
                 plan_name=EXCLUDED.plan_name, amount_mnt=EXCLUDED.amount_mnt,
                 invoice_id=EXCLUDED.invoice_id, expires_at=EXCLUDED.expires_at, status='pending'""",
              (guild_id, plan_name, amount, invoice_id, expires_dt))
    conn.commit(); conn.close()

def mark_subscription_paid(invoice_id: str):
    conn = _conn(); c = conn.cursor()
    c.execute("UPDATE subscriptions SET status='active' WHERE invoice_id=%s", (invoice_id,))
    conn.commit(); conn.close()

def get_subscription(guild_id: str):
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT plan_name, amount_mnt, expires_at, status FROM subscriptions WHERE guild_id=%s", (guild_id,))
    row = c.fetchone(); conn.close()
    return row

def get_all_subscriptions():
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT guild_id, expires_at FROM subscriptions WHERE status='active'")
    rows = c.fetchall(); conn.close()
    return rows

def get_subscriptions_expiring_soon(days: int = 3):
    """Get subscriptions expiring within specified days"""
    now = datetime.utcnow()
    warning_time = now + timedelta(days=days)
    conn = _conn(); c = conn.cursor()
    c.execute("""
        SELECT guild_id, plan_name, expires_at, amount_mnt 
        FROM subscriptions 
        WHERE status='active' AND expires_at <= %s AND expires_at > %s
    """, (warning_time, now))
    rows = c.fetchall()
    conn.close()
    return rows

def renew_subscription_with_balance(guild_id: str, plan_name: str, duration_days: int, amount: int):
    """Renew subscription by deducting from collected balance"""
    available = available_to_collect(guild_id)
    if available < amount:
        return (False, None, f"Not enough balance. Available: {available:,}₮, Required: {amount:,}₮")
    
    conn = _conn(); c = conn.cursor()
    
    c.execute("SELECT expires_at, status FROM subscriptions WHERE guild_id=%s", (guild_id,))
    existing = c.fetchone()
    
    now = datetime.utcnow()
    
    if existing and existing[1] == 'active':
        existing_expiry = existing[0] if isinstance(existing[0], datetime) else datetime.fromisoformat(str(existing[0]))
        
        if existing_expiry > now:
            new_expiry = existing_expiry + timedelta(days=duration_days)
        else:
            new_expiry = now + timedelta(days=duration_days)
    else:
        new_expiry = now + timedelta(days=duration_days)
    
    c.execute("""UPDATE subscriptions 
                 SET plan_name=%s, amount_mnt=%s, expires_at=%s, status='active'
                 WHERE guild_id=%s""",
              (plan_name, amount, new_expiry, guild_id))
    
    note = f"Auto-deducted for {plan_name} subscription renewal ({duration_days} days)"
    c.execute("""INSERT INTO payouts 
                 (guild_id, gross_mnt, fee_mnt, net_mnt, account_number, account_name, note, created_at, status)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'done')""",
              (guild_id, amount, 0, amount, "SYSTEM", "Bot Subscription Renewal", note, now))
    
    conn.commit()
    conn.close()
    
    return (True, new_expiry.isoformat(), f"Successfully renewed with collected balance. New expiry: {new_expiry.strftime('%Y-%m-%d')}")

def deactivate_subscription(guild_id: str):
    conn = _conn(); c = conn.cursor()
    c.execute("UPDATE subscriptions SET status='expired' WHERE guild_id=%s", (guild_id,))
    conn.commit(); conn.close()

def has_active_subscription(guild_id: str):
    """Check if guild has an active (paid and not expired) subscription"""
    now = datetime.utcnow()
    conn = _conn(); c = conn.cursor()
    c.execute("""
        SELECT 1 FROM subscriptions 
        WHERE guild_id=%s AND status='active' AND expires_at > %s 
        LIMIT 1
    """, (guild_id, now))
    row = c.fetchone()
    conn.close()
    return bool(row)

# ---------- REVENUE FUNCTIONS ----------
def total_guild_revenue(guild_id: str):
    """Get total all-time revenue for a guild"""
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT COALESCE(SUM(amount_mnt),0) FROM payments
                 WHERE guild_id=%s AND status='paid'""", (guild_id,))
    amt = c.fetchone()[0] or 0
    conn.close(); return int(amt)

def available_to_collect(guild_id: str):
    """Get available amount after deducting 3% fee and previous payouts"""
    gross = total_guild_revenue(guild_id)
    fee = int(gross * 0.03)
    
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT COALESCE(SUM(net_mnt),0) FROM payouts
                 WHERE guild_id=%s AND status='done'""", (guild_id,))
    paid_out = c.fetchone()[0] or 0
    conn.close()
    
    return max(0, gross - fee - paid_out)

def get_plans_breakdown(guild_id: str):
    """Get revenue breakdown by plan"""
    conn = _conn(); c = conn.cursor()
    c.execute("""
        SELECT 
            rp.role_name,
            (SELECT COUNT(*) FROM memberships m 
             WHERE m.plan_id = rp.plan_id AND m.active = 1 AND m.guild_id = rp.guild_id) as members,
            (SELECT COALESCE(SUM(p.amount_mnt), 0) FROM payments p 
             WHERE p.plan_id = rp.plan_id AND p.status = 'paid' AND p.guild_id = rp.guild_id) as revenue
        FROM role_plans rp
        WHERE rp.guild_id = %s AND rp.active = 1
        ORDER BY revenue DESC
    """, (guild_id,))
    rows = c.fetchall()
    conn.close()
    return rows

# ---------- PAYOUT FUNCTIONS ----------
def create_payout_record(guild_id: str, gross_mnt: int, fee_mnt: int, net_mnt: int, 
                        account_number: str, account_name: str, note: str = ""):
    """Create a payout request record"""
    now = datetime.utcnow()
    conn = _conn(); c = conn.cursor()
    c.execute("""INSERT INTO payouts 
                 (guild_id, gross_mnt, fee_mnt, net_mnt, account_number, account_name, note, created_at, status)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'pending') RETURNING id""",
              (guild_id, gross_mnt, fee_mnt, net_mnt, account_number, account_name, note, now))
    payout_id = c.fetchone()[0]
    conn.commit()
    conn.close()
    return payout_id

def get_payout(payout_id: int):
    """Get payout details"""
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT id, guild_id, gross_mnt, fee_mnt, net_mnt, account_number, account_name, 
                 note, created_at, status FROM payouts WHERE id=%s""", (payout_id,))
    row = c.fetchone()
    conn.close()
    return row

def mark_payout_done(payout_id: int):
    """Mark payout as completed"""
    conn = _conn(); c = conn.cursor()
    c.execute("UPDATE payouts SET status='done' WHERE id=%s", (payout_id,))
    conn.commit()
    conn.close()

# ---------- ANALYTICS FUNCTIONS ----------
def get_top_members(guild_id: str, limit: int = 10):
    """Get top spending members across all plans"""
    conn = _conn(); c = conn.cursor()
    c.execute("""
        SELECT u.username, u.user_id, COUNT(p.payment_id) as payment_count,
               COALESCE(SUM(p.amount_mnt), 0) as total_spent
        FROM users u
        JOIN payments p ON u.user_id = p.user_id AND u.guild_id = p.guild_id
        WHERE u.guild_id = %s AND p.status = 'paid'
        GROUP BY u.username, u.user_id
        ORDER BY total_spent DESC
        LIMIT %s
    """, (guild_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def set_manager_role(guild_id: str, role_id: str, role_name: str):
    """Set the manager role for a guild"""
    now = datetime.utcnow()
    conn = _conn(); c = conn.cursor()
    c.execute("""INSERT INTO manager_roles (guild_id, role_id, role_name, created_at)
                 VALUES (%s, %s, %s, %s)
                 ON CONFLICT (guild_id) DO UPDATE SET
                 role_id=EXCLUDED.role_id, role_name=EXCLUDED.role_name""",
              (guild_id, role_id, role_name, now))
    conn.commit()
    conn.close()

def get_manager_role(guild_id: str):
    """Get the manager role for a guild"""
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT guild_id, role_id, role_name FROM manager_roles WHERE guild_id=%s", (guild_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {"guild_id": row[0], "role_id": row[1], "role_name": row[2]}

def remove_manager_role(guild_id: str):
    """Remove the manager role for a guild"""
    conn = _conn(); c = conn.cursor()
    c.execute("DELETE FROM manager_roles WHERE guild_id=%s", (guild_id,))
    conn.commit()
    conn.close()

def get_top_members_by_plan(guild_id: str, plan_id: int, limit: int = 5):
    """Get top spenders for a specific plan"""
    conn = _conn(); c = conn.cursor()
    c.execute("""
        SELECT u.username, u.user_id, COUNT(p.payment_id) as payment_count
        FROM users u
        JOIN payments p ON u.user_id = p.user_id AND u.guild_id = p.guild_id
        WHERE u.guild_id = %s AND p.plan_id = %s AND p.status = 'paid'
        GROUP BY u.username, u.user_id
        ORDER BY payment_count DESC
        LIMIT %s
    """, (guild_id, plan_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def get_revenue_by_day(guild_id: str, days: int = 30):
    """Get daily revenue for the last N days"""
    since = datetime.utcnow() - timedelta(days=days)
    conn = _conn(); c = conn.cursor()
    c.execute("""
        SELECT DATE(created_at) as day, COALESCE(SUM(amount_mnt), 0) as revenue
        FROM payments
        WHERE guild_id = %s AND status = 'paid' AND created_at >= %s
        GROUP BY DATE(created_at)
        ORDER BY day ASC
    """, (guild_id, since))
    rows = c.fetchall()
    conn.close()
    return rows

def get_role_revenue_breakdown(guild_id: str):
    """Get revenue breakdown by role for pie chart"""
    conn = _conn(); c = conn.cursor()
    c.execute("""
        SELECT rp.role_name, COALESCE(SUM(p.amount_mnt), 0) as revenue
        FROM role_plans rp
        LEFT JOIN payments p ON rp.plan_id = p.plan_id AND p.status = 'paid'
        WHERE rp.guild_id = %s AND rp.active = 1
        GROUP BY rp.role_name
        HAVING SUM(p.amount_mnt) > 0
        ORDER BY revenue DESC
    """, (guild_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_growth_stats(guild_id: str):
    """Get growth statistics comparing last 30 days vs previous 30 days"""
    now = datetime.utcnow()
    last_30_start = now - timedelta(days=30)
    prev_30_start = now - timedelta(days=60)
    
    conn = _conn(); c = conn.cursor()
    
    # Last 30 days revenue
    c.execute("""
        SELECT COALESCE(SUM(amount_mnt), 0) FROM payments
        WHERE guild_id = %s AND status = 'paid' AND created_at >= %s
    """, (guild_id, last_30_start))
    last_30_revenue = c.fetchone()[0] or 0
    
    # Previous 30 days revenue
    c.execute("""
        SELECT COALESCE(SUM(amount_mnt), 0) FROM payments
        WHERE guild_id = %s AND status = 'paid' 
        AND created_at >= %s AND created_at < %s
    """, (guild_id, prev_30_start, last_30_start))
    prev_30_revenue = c.fetchone()[0] or 0
    
    conn.close()
    
    # Calculate growth percentage
    if prev_30_revenue > 0:
        growth = ((last_30_revenue - prev_30_revenue) / prev_30_revenue) * 100
    else:
        growth = 100 if last_30_revenue > 0 else 0
    
    return {
        "last_30_days": int(last_30_revenue),
        "prev_30_days": int(prev_30_revenue),
        "growth_percent": round(growth, 1)
    }
