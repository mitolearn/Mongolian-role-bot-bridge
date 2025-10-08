# Railway PostgreSQL Database Connection Guide

## 🎯 Overview

Your Discord bot now uses **PostgreSQL** on both environments:
- **Replit (Test)**: Separate PostgreSQL database for testing
- **Railway (Production)**: Shared PostgreSQL database with your bot AND website

## 📊 Database Schema

### Tables

#### 1. **subscriptions** - Bot rental subscriptions
```sql
CREATE TABLE subscriptions (
    guild_id VARCHAR PRIMARY KEY,
    plan_name VARCHAR,
    amount_mnt INTEGER,
    invoice_id VARCHAR,
    expires_at TIMESTAMP,
    status VARCHAR
)
```

#### 2. **role_plans** - Paid role configurations
```sql
CREATE TABLE role_plans (
    plan_id SERIAL PRIMARY KEY,
    guild_id VARCHAR,
    role_id VARCHAR,
    role_name VARCHAR,
    price_mnt INTEGER,
    duration_days INTEGER,
    active INTEGER DEFAULT 1,
    description TEXT DEFAULT ''
)
```

#### 3. **users** - Discord users
```sql
CREATE TABLE users (
    user_id VARCHAR,
    guild_id VARCHAR,
    username VARCHAR,
    PRIMARY KEY (user_id, guild_id)
)
```

#### 4. **memberships** - Active role memberships
```sql
CREATE TABLE memberships (
    guild_id VARCHAR,
    user_id VARCHAR,
    plan_id INTEGER,
    active INTEGER,
    access_ends_at TIMESTAMP,
    last_payment_id VARCHAR
)
```

#### 5. **payments** - Payment transactions
```sql
CREATE TABLE payments (
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
```

#### 6. **payouts** - Admin collection requests
```sql
CREATE TABLE payouts (
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
```

#### 7. **manager_roles** - Manager role configurations
```sql
CREATE TABLE manager_roles (
    guild_id VARCHAR PRIMARY KEY,
    role_id VARCHAR,
    role_name VARCHAR,
    created_at TIMESTAMP
)
```

#### 8. **guild_config** - Server configurations
```sql
CREATE TABLE guild_config (
    guild_id VARCHAR PRIMARY KEY,
    sales_channel_id VARCHAR,
    commission_rate REAL DEFAULT 0.10,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

## 🔌 How to Connect Your Website

### Option 1: Direct PostgreSQL Connection (Recommended)

**Railway provides the DATABASE_URL environment variable automatically.**

#### Python Example (Flask/Django):
```python
import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Example query
cursor.execute("SELECT * FROM role_plans WHERE guild_id = %s", (guild_id,))
plans = cursor.fetchall()
```

#### Node.js Example (Express):
```javascript
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

// Example query
const result = await pool.query('SELECT * FROM role_plans WHERE guild_id = $1', [guildId]);
```

### Option 2: Environment Variables (Manual Connection)

Railway provides these environment variables:
- `PGHOST` - Database host
- `PGPORT` - Database port (usually 5432)
- `PGUSER` - Database username
- `PGPASSWORD` - Database password
- `PGDATABASE` - Database name

#### Python Example:
```python
import psycopg2

conn = psycopg2.connect(
    host=os.getenv("PGHOST"),
    port=os.getenv("PGPORT"),
    user=os.getenv("PGUSER"),
    password=os.getenv("PGPASSWORD"),
    database=os.getenv("PGDATABASE")
)
```

## 📝 Common Queries for Website

### Get Server's Active Role Plans
```sql
SELECT plan_id, role_name, price_mnt, duration_days, description
FROM role_plans
WHERE guild_id = 'YOUR_GUILD_ID' AND active = 1
ORDER BY price_mnt ASC
```

### Get Server's Revenue Statistics
```sql
SELECT 
    COALESCE(SUM(amount_mnt), 0) as total_revenue,
    COUNT(*) as total_payments
FROM payments
WHERE guild_id = 'YOUR_GUILD_ID' AND status = 'paid'
```

### Get Active Members Count
```sql
SELECT COUNT(DISTINCT user_id) as active_members
FROM memberships
WHERE guild_id = 'YOUR_GUILD_ID' AND active = 1
```

### Get User's Active Memberships
```sql
SELECT m.plan_id, m.access_ends_at, rp.role_name, rp.price_mnt
FROM memberships m
JOIN role_plans rp ON m.plan_id = rp.plan_id
WHERE m.guild_id = 'YOUR_GUILD_ID' 
  AND m.user_id = 'USER_DISCORD_ID' 
  AND m.active = 1
```

### Get Payment History
```sql
SELECT p.payment_id, p.amount_mnt, p.status, p.created_at, p.paid_at,
       u.username, rp.role_name
FROM payments p
JOIN users u ON p.user_id = u.user_id AND p.guild_id = u.guild_id
JOIN role_plans rp ON p.plan_id = rp.plan_id
WHERE p.guild_id = 'YOUR_GUILD_ID' AND p.status = 'paid'
ORDER BY p.created_at DESC
LIMIT 50
```

### Get Subscription Status
```sql
SELECT plan_name, amount_mnt, expires_at, status
FROM subscriptions
WHERE guild_id = 'YOUR_GUILD_ID'
```

## 🚀 Deployment Steps

### Step 1: Get Railway DATABASE_URL

1. Go to your Railway project dashboard
2. Navigate to your PostgreSQL database service
3. Click "Variables" tab
4. Copy the `DATABASE_URL` value (format: `postgresql://user:password@host:port/database`)

### Step 2: Add to Your Website Environment

**If deploying on Railway:**
- Railway automatically injects `DATABASE_URL` into your website service
- Just use `os.getenv("DATABASE_URL")` in your code

**If deploying elsewhere (Vercel, Heroku, etc.):**
- Add `DATABASE_URL` as an environment variable manually
- Use the value from Railway PostgreSQL

### Step 3: Install PostgreSQL Library

**Python:**
```bash
pip install psycopg2-binary
```

**Node.js:**
```bash
npm install pg
```

## ⚠️ Important Notes

1. **Read-Only Recommended**: Website should mainly READ data, bot handles WRITES
2. **Connection Pooling**: Use connection pools for better performance
3. **Error Handling**: Always handle database connection errors gracefully
4. **Security**: Never expose DATABASE_URL in frontend code
5. **Timezone**: All timestamps are in UTC (use `.utcnow()` in Python)

## 🔐 Security Best Practices

1. **Use Parameterized Queries** (prevent SQL injection):
   ```python
   # ✅ GOOD
   cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
   
   # ❌ BAD
   cursor.execute(f"SELECT * FROM users WHERE user_id = '{user_id}'")
   ```

2. **Close Connections**:
   ```python
   try:
       conn = psycopg2.connect(DATABASE_URL)
       # ... queries ...
   finally:
       conn.close()
   ```

3. **Use Environment Variables**: Never hardcode database credentials

## 📞 Need Help?

If you have questions about:
- Database schema structure
- Specific queries
- Connection issues
- Data relationships

Just ask! I can help you write the exact queries your website needs.

---

## 🎯 Quick Start Example (Python Flask)

```python
from flask import Flask, jsonify
import psycopg2
import os

app = Flask(__name__)

def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

@app.route('/api/server/<guild_id>/plans')
def get_plans(guild_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT plan_id, role_name, price_mnt, duration_days, description
        FROM role_plans
        WHERE guild_id = %s AND active = 1
        ORDER BY price_mnt ASC
    """, (guild_id,))
    plans = cursor.fetchall()
    conn.close()
    
    return jsonify([{
        'plan_id': row[0],
        'role_name': row[1],
        'price': row[2],
        'duration_days': row[3],
        'description': row[4]
    } for row in plans])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

This creates an API endpoint that your website frontend can call to get role plans!
