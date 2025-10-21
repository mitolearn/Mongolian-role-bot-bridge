# database.py
import sqlite3
import os
from datetime import datetime, timedelta

# Get database name from environment variable (stored in Secrets)
DB_NAME = os.getenv("DB_NAME", "database.db")
print(f"🗄️ Using database: {DB_NAME}")

def _conn():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = _conn()
    c = conn.cursor()

    # Enable foreign keys
    c.execute("PRAGMA foreign_keys = ON")

    c.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        guild_id TEXT PRIMARY KEY,
        plan_name TEXT,
        amount_mnt INTEGER,
        invoice_id TEXT,
        expires_at TEXT,
        status TEXT
    )
    """)

    # Guild configuration (per server)
    c.execute("""
    CREATE TABLE IF NOT EXISTS guild_config (
        guild_id TEXT PRIMARY KEY,
        sales_channel_id TEXT,
        commission_rate REAL DEFAULT 0.10,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    # Role plans (multiple paid roles per server)
    c.execute("""
    CREATE TABLE IF NOT EXISTS role_plans (
        plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id TEXT,
        role_id TEXT,
        role_name TEXT,
        price_mnt INTEGER,
        duration_days INTEGER,
        active INTEGER DEFAULT 1,
        description TEXT DEFAULT '',
        deleted_at TEXT DEFAULT NULL
    )
    """)
    
    # Add description column if it doesn't exist (for existing databases)
    c.execute("PRAGMA table_info(role_plans)")
    role_plan_columns = [row[1] for row in c.fetchall()]
    if 'description' not in role_plan_columns:
        c.execute("ALTER TABLE role_plans ADD COLUMN description TEXT DEFAULT ''")
    
    # Add deleted_at column if it doesn't exist (for soft-delete support)
    if 'deleted_at' not in role_plan_columns:
        c.execute("ALTER TABLE role_plans ADD COLUMN deleted_at TEXT DEFAULT NULL")

    # Check if users table exists and has the correct schema
    c.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in c.fetchall()]

    if 'guild_id' not in columns and columns:
        # Old schema detected, migrate data
        c.execute("ALTER TABLE users ADD COLUMN guild_id TEXT DEFAULT 'default'")

    # Users with new schema
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT,
        guild_id TEXT,
        username TEXT,
        PRIMARY KEY (user_id, guild_id)
    )
    """)

    # Memberships (who has access until when)
    c.execute("""
    CREATE TABLE IF NOT EXISTS memberships (
        guild_id TEXT,
        user_id TEXT,
        plan_id INTEGER,
        active INTEGER,
        access_ends_at TEXT,
        last_payment_id TEXT
    )
    """)

    # Payments (fake for now; status toggled on button)
    c.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        payment_id TEXT PRIMARY KEY,
        guild_id TEXT,
        user_id TEXT,
        plan_id INTEGER,
        amount_mnt INTEGER,
        status TEXT, -- pending|paid|refunded
        short_url TEXT,
        created_at TEXT,
        paid_at TEXT
    )
    """)

    # Leaders (optional revenue share)
    c.execute("""
    CREATE TABLE IF NOT EXISTS leaders (
        leader_id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id TEXT,
        leader_name TEXT,
        commission_rate REAL DEFAULT 0.10,
        balance_mnt INTEGER DEFAULT 0
    )
    """)



    # Ledger (platform_fee, leader_share, sale, payout, etc.)
    c.execute("""
    CREATE TABLE IF NOT EXISTS ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id TEXT,
        leader_id INTEGER,
        payment_id TEXT,
        type TEXT,        -- sale|platform_fee|leader_share|payout
        amount_mnt INTEGER,
        created_at TEXT
    )
    """)

    # Payouts (collection requests)
    c.execute("""
    CREATE TABLE IF NOT EXISTS payouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id TEXT,
        gross_mnt INTEGER,
        fee_mnt INTEGER,
        net_mnt INTEGER,
        account_number TEXT,
        account_name TEXT,
        note TEXT,
        created_at TEXT,
        status TEXT DEFAULT 'pending'
    )
    """)

    # Manager roles (allow non-admins to manage plans)
    c.execute("""
    CREATE TABLE IF NOT EXISTS manager_roles (
        guild_id TEXT PRIMARY KEY,
        role_id TEXT,
        role_name TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()

# ---------- GUILD CONFIG ----------
def set_guild_config(guild_id: str, sales_channel_id: str|None, commission_rate: float|None = None):
    now = datetime.utcnow().isoformat()
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT guild_id FROM guild_config WHERE guild_id=?", (guild_id,))
    exists = c.fetchone()
    if exists:
        if sales_channel_id:
            c.execute("UPDATE guild_config SET sales_channel_id=?, updated_at=? WHERE guild_id=?",
                      (sales_channel_id, now, guild_id))
        if commission_rate is not None:
            c.execute("UPDATE guild_config SET commission_rate=?, updated_at=? WHERE guild_id=?",
                      (commission_rate, now, guild_id))
    else:
        c.execute("INSERT INTO guild_config (guild_id, sales_channel_id, commission_rate, created_at, updated_at) VALUES (?,?,?,?,?)",
                  (guild_id, sales_channel_id, commission_rate or 0.10, now, now))
    conn.commit(); conn.close()

def get_guild_config(guild_id: str):
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT guild_id, sales_channel_id, commission_rate FROM guild_config WHERE guild_id=?", (guild_id,))
    row = c.fetchone(); conn.close()
    if not row: return None
    return {"guild_id": row[0], "sales_channel_id": row[1], "commission_rate": row[2]}

# ---------- ROLE PLANS ----------
def add_role_plan(guild_id: str, role_id: str, role_name: str, price_mnt: int, duration_days: int, description: str = ""):
    conn = _conn(); c = conn.cursor()
    c.execute("""INSERT INTO role_plans (guild_id, role_id, role_name, price_mnt, duration_days, active, description)
                 VALUES (?,?,?,?,?,1,?)""",
              (guild_id, role_id, role_name, price_mnt, duration_days, description))
    plan_id = c.lastrowid
    conn.commit(); conn.close()
    return plan_id

def list_role_plans(guild_id: str, only_active=True):
    conn = _conn(); c = conn.cursor()
    if only_active:
        c.execute("""SELECT plan_id, role_id, role_name, price_mnt, duration_days, active, description
                     FROM role_plans WHERE guild_id=? AND active=1 ORDER BY price_mnt ASC""", (guild_id,))
    else:
        c.execute("""SELECT plan_id, role_id, role_name, price_mnt, duration_days, active, description
                     FROM role_plans WHERE guild_id=? ORDER BY price_mnt ASC""", (guild_id,))
    rows = c.fetchall(); conn.close()
    return rows

def update_plan_description(plan_id: int, description: str):
    """Update the description of a role plan"""
    conn = _conn(); c = conn.cursor()
    c.execute("UPDATE role_plans SET description=? WHERE plan_id=?", (description, plan_id))
    conn.commit(); conn.close()

def toggle_role_plan(plan_id: int, active: int):
    conn = _conn(); c = conn.cursor()
    c.execute("UPDATE role_plans SET active=? WHERE plan_id=?", (active, plan_id))
    conn.commit(); conn.close()

def delete_role_plan(plan_id: int):
    """Soft-delete a role plan (mark as deleted but preserve historical data)"""
    conn = _conn(); c = conn.cursor()

    # First check if plan exists and is not already deleted
    c.execute("SELECT plan_id, deleted_at FROM role_plans WHERE plan_id=?", (plan_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False  # Plan doesn't exist
    
    if row[1]:  # deleted_at is not NULL
        conn.close()
        return False  # Plan already deleted

    # Soft-delete: set deleted_at timestamp
    now = datetime.utcnow().isoformat()
    c.execute("UPDATE role_plans SET deleted_at=? WHERE plan_id=?", (now, plan_id))
    conn.commit()
    conn.close()
    return True  # Successfully soft-deleted

def get_plan(plan_id: int):
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT plan_id, guild_id, role_id, role_name, price_mnt, duration_days, active, description
                 FROM role_plans WHERE plan_id=?""", (plan_id,))
    row = c.fetchone(); conn.close()
    if not row: return None
    return {"plan_id": row[0], "guild_id": row[1], "role_id": row[2], "role_name": row[3],
            "price_mnt": row[4], "duration_days": row[5], "active": row[6], "description": row[7] or ""}

# ---------- USERS ----------
def upsert_user(guild_id: str, user_id: str, username: str):
    conn = _conn(); c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO users (user_id, guild_id, username) VALUES (?,?,?)""",
              (user_id, guild_id, username))
    conn.commit(); conn.close()

# ---------- PAYMENTS (REAL QPAY) ----------
def create_payment(payment_id: str, guild_id: str, user_id: str, plan_id: int, amount_mnt: int, short_url: str):
    now = datetime.utcnow().isoformat()
    conn = _conn(); c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO payments
                 (payment_id, guild_id, user_id, plan_id, amount_mnt, status, short_url, created_at)
                 VALUES (?,?,?,?,?,'pending',?,?)""",
              (payment_id, guild_id, user_id, plan_id, amount_mnt, short_url, now))
    conn.commit(); conn.close()

def mark_payment_paid(payment_id: str):
    now = datetime.utcnow().isoformat()
    conn = _conn(); c = conn.cursor()
    c.execute("UPDATE payments SET status='paid', paid_at=? WHERE payment_id=?", (now, payment_id))
    conn.commit(); conn.close()

def get_payment(payment_id: str):
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT payment_id, guild_id, user_id, plan_id, amount_mnt, status, short_url, created_at, paid_at
                 FROM payments WHERE payment_id=?""", (payment_id,))
    row = c.fetchone(); conn.close()
    return row

def get_payment_by_user(guild_id: str, user_id: str):
    """Get user's most recent payment (for verify payment command)"""
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT payment_id, guild_id, user_id, plan_id, amount_mnt, status, short_url
                 FROM payments 
                 WHERE guild_id=? AND user_id=? 
                 ORDER BY created_at DESC 
                 LIMIT 1""", (guild_id, user_id))
    row = c.fetchone(); conn.close()
    return row

# ---------- MEMBERSHIPS ----------
def grant_membership(guild_id: str, user_id: str, plan_id: int, duration_days: int, last_payment_id: str):
    conn = _conn(); c = conn.cursor()
    
    # Check if user has existing active membership for this plan
    c.execute("""SELECT access_ends_at FROM memberships
                 WHERE guild_id=? AND user_id=? AND plan_id=? AND active=1""",
              (guild_id, user_id, plan_id))
    existing = c.fetchone()
    
    now = datetime.utcnow()
    
    if existing:
        # User has active membership - extend it from existing end date
        existing_end = datetime.fromisoformat(existing[0])
        
        # If existing membership hasn't expired yet, add to it
        if existing_end > now:
            new_end = existing_end + timedelta(days=duration_days)
        else:
            # Expired membership - start from now
            new_end = now + timedelta(days=duration_days)
        
        ends = new_end.isoformat()
        
        # Update existing membership
        c.execute("""UPDATE memberships 
                     SET access_ends_at=?, last_payment_id=?
                     WHERE guild_id=? AND user_id=? AND plan_id=? AND active=1""",
                  (ends, last_payment_id, guild_id, user_id, plan_id))
    else:
        # No existing membership for this plan - create new one from now
        ends = (now + timedelta(days=duration_days)).isoformat()
        
        # Insert new membership (keep other active memberships)
        c.execute("""INSERT INTO memberships (guild_id, user_id, plan_id, active, access_ends_at, last_payment_id)
                     VALUES (?,?,?,?,?,?)""", (guild_id, user_id, plan_id, 1, ends, last_payment_id))
    
    conn.commit(); conn.close()
    return ends

def list_expired(guild_id: str):
    now = datetime.utcnow().isoformat()
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT user_id, plan_id FROM memberships
                 WHERE guild_id=? AND active=1 AND access_ends_at < ?""", (guild_id, now))
    rows = c.fetchall(); conn.close()
    return rows

def deactivate_membership(guild_id: str, user_id: str, plan_id: int = None):
    """Deactivate specific membership or all memberships for a user"""
    conn = _conn(); c = conn.cursor()
    
    if plan_id is not None:
        # Deactivate only specific membership (for multiple role support)
        c.execute("""UPDATE memberships SET active=0 WHERE guild_id=? AND user_id=? AND plan_id=?""", 
                  (guild_id, user_id, plan_id))
    else:
        # Deactivate all memberships (legacy behavior)
        c.execute("""UPDATE memberships SET active=0 WHERE guild_id=? AND user_id=?""", (guild_id, user_id))
    
    conn.commit(); conn.close()

def get_membership_by_invoice(invoice_id: str):
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT guild_id, user_id, plan_id, active, access_ends_at, last_payment_id
                 FROM memberships WHERE last_payment_id=?""", (invoice_id,))
    row = c.fetchone(); conn.close()
    return row

def get_user_active_membership(guild_id: str, user_id: str):
    """Get ALL active memberships for a user (supports multiple roles)"""
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT plan_id, access_ends_at FROM memberships
                 WHERE guild_id=? AND user_id=? AND active=1""", (guild_id, user_id))
    rows = c.fetchall(); conn.close()
    return rows  # Returns list of (plan_id, access_ends_at) tuples

# ---------- STATS ----------
def guild_revenue_mnt(guild_id: str, days: int = 30):
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT COALESCE(SUM(amount_mnt),0) FROM payments
                 WHERE guild_id=? AND status='paid' AND created_at>=?""", (guild_id, since))
    amt = c.fetchone()[0] or 0
    conn.close(); return int(amt)

def count_active_members(guild_id: str):
    """Count UNIQUE active members (not total memberships)"""
    conn = _conn(); c = conn.cursor()
    # Use DISTINCT to count unique users (one user with 2 roles = 1 member, not 2)
    c.execute("""SELECT COUNT(DISTINCT user_id) FROM memberships WHERE guild_id=? AND active=1""", (guild_id,))
    n = c.fetchone()[0] or 0
    conn.close(); return int(n)

# ---------- SIMPLE LEGACY FUNCTIONS (for backward compatibility) ----------
def add_user(user_id, username, leader_id=None, role_given=None):
    # Legacy function for simple bot commands
    conn = _conn(); c = conn.cursor()
    joined_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # For legacy compatibility, use a default guild_id if not provided
    c.execute("INSERT OR IGNORE INTO users (user_id, guild_id, username) VALUES (?, ?, ?)",
              (user_id, "default", username))
    conn.commit(); conn.close()

def add_leader(leader_id, leader_name, commission_rate=0.1):
    # Legacy function for simple bot commands
    conn = _conn(); c = conn.cursor()
    # Check if the new schema exists
    c.execute("PRAGMA table_info(leaders)")
    columns = [row[1] for row in c.fetchall()]

    if 'guild_id' in columns:
        # New schema with guild_id
        c.execute("INSERT OR IGNORE INTO leaders (leader_id, guild_id, leader_name, commission_rate, balance_mnt) VALUES (?, ?, ?, ?, ?)",
                  (leader_id, "default", leader_name, commission_rate, 0))
    else:
        # Old schema without guild_id - use balance instead of balance_mnt
        c.execute("INSERT OR IGNORE INTO leaders (leader_id, leader_name, commission_rate, balance) VALUES (?, ?, ?, ?)",
                  (leader_id, leader_name, commission_rate, 0))
    conn.commit(); conn.close()

def add_payment(payment_id, user_id, amount, status="pending", leader_id=None):
    # Legacy function for simple bot commands
    conn = _conn(); c = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT OR IGNORE INTO payments (payment_id, guild_id, user_id, plan_id, amount_mnt, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (payment_id, "default", user_id, 1, int(amount), status, created_at))
    conn.commit(); conn.close()

def update_leader_balance(leader_id, amount):
    # Legacy function for simple bot commands
    conn = _conn(); c = conn.cursor()
    # Check if the new schema exists
    c.execute("PRAGMA table_info(leaders)")
    columns = [row[1] for row in c.fetchall()]

    if 'balance_mnt' in columns:
        c.execute("UPDATE leaders SET balance_mnt = balance_mnt + ? WHERE leader_id = ?", (int(amount), leader_id))
    else:
        c.execute("UPDATE leaders SET balance = balance + ? WHERE leader_id = ?", (int(amount), leader_id))
    conn.commit(); conn.close()

def get_leader_balance(leader_id):
    # Legacy function for simple bot commands
    conn = _conn(); c = conn.cursor()
    # Check if the new schema exists
    c.execute("PRAGMA table_info(leaders)")
    columns = [row[1] for row in c.fetchall()]

    if 'balance_mnt' in columns:
        c.execute("SELECT balance_mnt FROM leaders WHERE leader_id = ?", (leader_id,))
    else:
        c.execute("SELECT balance FROM leaders WHERE leader_id = ?", (leader_id,))
    result = c.fetchone(); conn.close()
    return result[0] if result else 0

def create_subscription(guild_id: str, plan_name: str, amount: int, invoice_id: str, expires_at: str):
    conn = _conn(); c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO subscriptions
                 (guild_id, plan_name, amount_mnt, invoice_id, expires_at, status)
                 VALUES (?,?,?,?,?, 'pending')""",
              (guild_id, plan_name, amount, invoice_id, expires_at))
    conn.commit(); conn.close()

def mark_subscription_paid(invoice_id: str):
    conn = _conn(); c = conn.cursor()
    c.execute("UPDATE subscriptions SET status='active' WHERE invoice_id=?", (invoice_id,))
    conn.commit(); conn.close()

def get_subscription(guild_id: str):
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT plan_name, amount_mnt, expires_at, status FROM subscriptions WHERE guild_id=?", (guild_id,))
    row = c.fetchone(); conn.close()
    return row

def get_all_subscriptions():
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT guild_id, expires_at FROM subscriptions WHERE status='active'")
    rows = c.fetchall(); conn.close()
    return rows

def get_subscriptions_expiring_soon(days: int = 3):
    """Get subscriptions expiring within specified days"""
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    warning_time = (now + timedelta(days=days)).isoformat()
    conn = _conn(); c = conn.cursor()
    c.execute("""
        SELECT guild_id, plan_name, expires_at, amount_mnt 
        FROM subscriptions 
        WHERE status='active' AND expires_at <= ? AND expires_at > ?
    """, (warning_time, now.isoformat()))
    rows = c.fetchall()
    conn.close()
    return rows

def renew_subscription_with_balance(guild_id: str, plan_name: str, duration_days: int, amount: int):
    """Renew subscription by deducting from collected balance. Returns (success, new_expiry, message)"""
    from datetime import datetime, timedelta
    
    # Check if they have enough balance
    available = available_to_collect(guild_id)
    if available < amount:
        return (False, None, f"Not enough balance. Available: {available:,}₮, Required: {amount:,}₮")
    
    conn = _conn(); c = conn.cursor()
    
    # Get existing subscription
    c.execute("SELECT expires_at, status FROM subscriptions WHERE guild_id=?", (guild_id,))
    existing = c.fetchone()
    
    now = datetime.utcnow()
    
    if existing and existing[1] == 'active':
        # Active subscription exists - extend from existing expiry
        existing_expiry = datetime.fromisoformat(existing[0])
        
        # If still valid, extend from expiry date
        if existing_expiry > now:
            new_expiry = existing_expiry + timedelta(days=duration_days)
        else:
            # Expired - start from now
            new_expiry = now + timedelta(days=duration_days)
    else:
        # No active subscription - start from now
        new_expiry = now + timedelta(days=duration_days)
    
    new_expiry_str = new_expiry.isoformat()
    
    # Update subscription
    c.execute("""UPDATE subscriptions 
                 SET plan_name=?, amount_mnt=?, expires_at=?, status='active'
                 WHERE guild_id=?""",
              (plan_name, amount, new_expiry_str, guild_id))
    
    # Record this as a payout (money used for subscription renewal)
    # No fee calculation needed - admin pays exact amount for subscription
    gross = amount
    fee = 0
    note = f"Auto-deducted for {plan_name} subscription renewal ({duration_days} days)"
    
    c.execute("""INSERT INTO payouts 
                 (guild_id, gross_mnt, fee_mnt, net_mnt, account_number, account_name, note, created_at, status)
                 VALUES (?,?,?,?,?,?,?,?,'done')""",
              (guild_id, gross, fee, amount, "SYSTEM", "Bot Subscription Renewal", note, now.isoformat()))
    
    conn.commit()
    conn.close()
    
    # Note: Admin notification should be sent by the calling function (subscription_checker.py)
    # because database.py doesn't have access to Discord bot instance
    return (True, new_expiry_str, f"Successfully renewed with collected balance. New expiry: {new_expiry_str[:10]}")

def deactivate_subscription(guild_id: str):
    conn = _conn(); c = conn.cursor()
    c.execute("UPDATE subscriptions SET status='expired' WHERE guild_id=?", (guild_id,))
    conn.commit(); conn.close()

def has_active_subscription(guild_id: str):
    """Check if guild has an active (paid and not expired) subscription"""
    from datetime import datetime
    now = datetime.utcnow().isoformat()
    conn = _conn(); c = conn.cursor()
    c.execute("""
        SELECT 1 FROM subscriptions 
        WHERE guild_id=? AND status='active' AND expires_at > ? 
        LIMIT 1
    """, (guild_id, now))
    row = c.fetchone()
    conn.close()
    return bool(row)

def total_guild_revenue(guild_id: str):
    """Get total all-time revenue for a guild"""
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT COALESCE(SUM(amount_mnt),0) FROM payments
                 WHERE guild_id=? AND status='paid'""", (guild_id,))
    amt = c.fetchone()[0] or 0
    conn.close(); return int(amt)

def available_to_collect(guild_id: str):
    """Get available amount after deducting 3% fee and previous payouts"""
    gross = total_guild_revenue(guild_id)
    fee = int(gross * 0.03)  # 3% service fee
    
    # Subtract already paid out amounts
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT COALESCE(SUM(net_mnt),0) FROM payouts
                 WHERE guild_id=? AND status='done'""", (guild_id,))
    paid_out = c.fetchone()[0] or 0
    conn.close()
    
    return max(0, gross - fee - paid_out)

def get_plans_breakdown(guild_id: str):
    """Get revenue breakdown by plan - only shows plans with active members"""
    conn = _conn(); c = conn.cursor()
    c.execute("""
        SELECT 
            rp.role_name,
            (SELECT COUNT(*) FROM memberships m 
             WHERE m.plan_id = rp.plan_id AND m.active = 1 AND m.guild_id = rp.guild_id) as members,
            (SELECT COALESCE(SUM(p.amount_mnt), 0) FROM payments p 
             WHERE p.plan_id = rp.plan_id AND p.status = 'paid' AND p.guild_id = rp.guild_id) as revenue
        FROM role_plans rp
        WHERE rp.guild_id = ?
        AND (SELECT COUNT(*) FROM memberships m 
             WHERE m.plan_id = rp.plan_id AND m.active = 1 AND m.guild_id = rp.guild_id) > 0
        ORDER BY revenue DESC
    """, (guild_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def create_payout_record(guild_id: str, gross_mnt: int, fee_mnt: int, net_mnt: int, 
                        account_number: str, account_name: str, note: str = ""):
    """Create a new payout request"""
    now = datetime.utcnow().isoformat()
    conn = _conn(); c = conn.cursor()
    c.execute("""INSERT INTO payouts 
                 (guild_id, gross_mnt, fee_mnt, net_mnt, account_number, account_name, note, created_at, status)
                 VALUES (?,?,?,?,?,?,?,?,'pending')""",
              (guild_id, gross_mnt, fee_mnt, net_mnt, account_number, account_name, note, now))
    payout_id = c.lastrowid
    conn.commit(); conn.close()
    return payout_id

def get_payout(payout_id: int):
    """Get payout details by ID"""
    conn = _conn(); c = conn.cursor()
    c.execute("""SELECT id, guild_id, gross_mnt, fee_mnt, net_mnt, 
                        account_number, account_name, note, created_at, status
                 FROM payouts WHERE id=?""", (payout_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            'id': row[0],
            'guild_id': row[1],
            'gross_mnt': row[2],
            'fee_mnt': row[3],
            'net_mnt': row[4],
            'account_number': row[5],
            'account_name': row[6],
            'note': row[7],
            'created_at': row[8],
            'status': row[9]
        }
    return None

def mark_payout_done(payout_id: int):
    """Mark a payout as completed"""
    conn = _conn(); c = conn.cursor()
    c.execute("UPDATE payouts SET status='done' WHERE id=?", (payout_id,))
    conn.commit(); conn.close()

def get_top_members(guild_id: str, limit: int = 10):
    """Get top members by total amount spent across all plans"""
    conn = _conn(); c = conn.cursor()
    c.execute("""
        SELECT 
            p.user_id,
            u.username,
            COUNT(DISTINCT p.payment_id) as total_payments,
            SUM(p.amount_mnt) as total_spent
        FROM payments p
        LEFT JOIN users u ON p.user_id = u.user_id AND p.guild_id = u.guild_id
        WHERE p.guild_id = ? AND p.status = 'paid'
        GROUP BY p.user_id, u.username
        ORDER BY total_spent DESC
        LIMIT ?
    """, (guild_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def set_manager_role(guild_id: str, role_id: str, role_name: str):
    """Set the manager role for a guild (allows plan management without admin)"""
    now = datetime.utcnow().isoformat()
    conn = _conn(); c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO manager_roles 
                 (guild_id, role_id, role_name, created_at)
                 VALUES (?,?,?,?)""",
              (guild_id, role_id, role_name, now))
    conn.commit(); conn.close()

def get_manager_role(guild_id: str):
    """Get the manager role for a guild"""
    conn = _conn(); c = conn.cursor()
    c.execute("SELECT role_id, role_name FROM manager_roles WHERE guild_id=?", (guild_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"role_id": row[0], "role_name": row[1]}
    return None

def remove_manager_role(guild_id: str):
    """Remove the manager role for a guild"""
    conn = _conn(); c = conn.cursor()
    c.execute("DELETE FROM manager_roles WHERE guild_id=?", (guild_id,))
    conn.commit(); conn.close()

def get_top_members_by_plan(guild_id: str, plan_id: int, limit: int = 5):
    """Get top members for a specific plan"""
    conn = _conn(); c = conn.cursor()
    c.execute("""
        SELECT 
            p.user_id,
            u.username,
            COUNT(DISTINCT p.payment_id) as purchases,
            SUM(p.amount_mnt) as total_spent
        FROM payments p
        LEFT JOIN users u ON p.user_id = u.user_id AND p.guild_id = u.guild_id
        WHERE p.guild_id = ? AND p.plan_id = ? AND p.status = 'paid'
        GROUP BY p.user_id, u.username
        ORDER BY total_spent DESC
        LIMIT ?
    """, (guild_id, plan_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def get_revenue_by_day(guild_id: str, days: int = 30):
    """Get daily revenue for the last N days"""
    conn = _conn(); c = conn.cursor()
    c.execute("""
        SELECT 
            DATE(paid_at) as day,
            COALESCE(SUM(amount_mnt), 0) as revenue
        FROM payments
        WHERE guild_id = ? AND status = 'paid'
        AND paid_at IS NOT NULL
        AND DATE(paid_at) >= DATE('now', '-' || ? || ' days')
        GROUP BY DATE(paid_at)
        ORDER BY day ASC
    """, (guild_id, days))
    rows = c.fetchall()
    conn.close()
    return rows

def get_role_revenue_breakdown(guild_id: str):
    """Get total revenue breakdown by role plan"""
    conn = _conn(); c = conn.cursor()
    c.execute("""
        SELECT 
            rp.role_name,
            COALESCE(SUM(p.amount_mnt), 0) as revenue,
            COUNT(DISTINCT p.payment_id) as payment_count
        FROM role_plans rp
        LEFT JOIN payments p ON rp.plan_id = p.plan_id 
            AND rp.guild_id = p.guild_id 
            AND p.status = 'paid'
        WHERE rp.guild_id = ?
        GROUP BY rp.plan_id, rp.role_name
        HAVING revenue > 0
        ORDER BY revenue DESC
    """, (guild_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_growth_stats(guild_id: str):
    """Get growth statistics comparing last 30 days vs previous 30 days"""
    conn = _conn(); c = conn.cursor()
    
    # Revenue last 30 days
    c.execute("""
        SELECT COALESCE(SUM(amount_mnt), 0)
        FROM payments
        WHERE guild_id = ? AND status = 'paid'
        AND paid_at >= DATE('now', '-30 days')
    """, (guild_id,))
    last_30_days = c.fetchone()[0] or 0
    
    # Revenue previous 30 days (30-60 days ago)
    c.execute("""
        SELECT COALESCE(SUM(amount_mnt), 0)
        FROM payments
        WHERE guild_id = ? AND status = 'paid'
        AND paid_at >= DATE('now', '-60 days')
        AND paid_at < DATE('now', '-30 days')
    """, (guild_id,))
    prev_30_days = c.fetchone()[0] or 0
    
    # Calculate growth percentage
    if prev_30_days > 0:
        growth_percent = ((last_30_days - prev_30_days) / prev_30_days) * 100
    elif last_30_days > 0:
        growth_percent = None
    else:
        growth_percent = 0.0
    
    # Total members with active subscriptions
    c.execute("""
        SELECT COUNT(DISTINCT user_id)
        FROM memberships
        WHERE guild_id = ? AND active = 1
    """, (guild_id,))
    active_members = c.fetchone()[0] or 0
    
    conn.close()
    
    return {
        'last_30_days': last_30_days,
        'prev_30_days': prev_30_days,
        'growth_percent': growth_percent,
        'active_members': active_members
    }