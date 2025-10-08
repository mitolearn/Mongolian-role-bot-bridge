# Website Database Integration Guide

## 📊 PostgreSQL Connection Details

### For Website Developer

**Connection Information:**
```
Database Type: PostgreSQL 14+
Connection Method: Direct connection OR REST API

Option 1: Direct PostgreSQL Connection
- Host: [Get from Railway PostgreSQL → Connect tab]
- Port: 5432 (default)
- Database: [Get from Railway]
- Username: [Get from Railway]
- Password: [Get from Railway]
- SSL Mode: require

Option 2: Connection URL (easier)
DATABASE_URL=postgresql://username:password@host:port/database
```

---

## 🗄️ Database Schema Reference

### Tables Overview

#### 1. **subscriptions** - Bot rental subscriptions
```sql
guild_id TEXT PRIMARY KEY          -- Discord server ID
plan_name TEXT                     -- "basic", "pro", "premium"
amount_mnt INTEGER                 -- Price in MNT
invoice_id TEXT                    -- QPay invoice ID
expires_at TIMESTAMP               -- Expiry date
status TEXT                        -- "pending", "active", "expired"
```

#### 2. **role_plans** - Paid role plans (what admins sell)
```sql
plan_id SERIAL PRIMARY KEY         -- Plan ID
guild_id TEXT                      -- Discord server ID
role_id TEXT                       -- Discord role ID
role_name TEXT                     -- Role display name
price_mnt INTEGER                  -- Price in MNT
duration_days INTEGER              -- Access duration
active INTEGER                     -- 1=active, 0=inactive
description TEXT                   -- Marketing description
```

#### 3. **memberships** - User role purchases
```sql
guild_id TEXT                      -- Discord server ID
user_id TEXT                       -- Discord user ID
plan_id INTEGER                    -- Links to role_plans
active INTEGER                     -- 1=active, 0=expired
access_ends_at TIMESTAMP           -- Expiry date
last_payment_id TEXT               -- Links to payments
```

#### 4. **payments** - Payment transactions
```sql
payment_id TEXT PRIMARY KEY        -- QPay invoice ID
guild_id TEXT                      -- Discord server ID
user_id TEXT                       -- Discord user ID
plan_id INTEGER                    -- Links to role_plans
amount_mnt INTEGER                 -- Amount in MNT
status TEXT                        -- "pending", "paid", "refunded"
short_url TEXT                     -- QPay payment URL
created_at TIMESTAMP               -- Payment created
paid_at TIMESTAMP                  -- Payment confirmed
```

#### 5. **payouts** - Admin payout requests
```sql
id SERIAL PRIMARY KEY              -- Payout ID
guild_id TEXT                      -- Discord server ID
gross_mnt INTEGER                  -- Total revenue
fee_mnt INTEGER                    -- Platform fee (3%)
net_mnt INTEGER                    -- Amount to pay admin
account_number TEXT                -- Bank account
account_name TEXT                  -- Account holder name
note TEXT                          -- Additional notes
created_at TIMESTAMP               -- Request date
status TEXT                        -- "pending", "done"
```

#### 6. **manager_roles** - Permission system
```sql
guild_id TEXT PRIMARY KEY          -- Discord server ID
role_id TEXT                       -- Manager role ID
role_name TEXT                     -- Role display name
created_at TIMESTAMP               -- Created date
```

---

## 🔌 Website Integration Patterns

### Pattern 1: Read-Only Direct Access (Recommended for Dashboard)

**Use for:**
- Displaying revenue stats
- Showing member lists
- Analytics charts
- Payment history

**Example (Node.js):**
```javascript
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

// Get server revenue
async function getServerRevenue(guild_id) {
  const result = await pool.query(`
    SELECT COALESCE(SUM(amount_mnt), 0) as total
    FROM payments
    WHERE guild_id = $1 AND status = 'paid'
  `, [guild_id]);
  
  return result.rows[0].total;
}

// Get active members
async function getActiveMembers(guild_id) {
  const result = await pool.query(`
    SELECT COUNT(DISTINCT user_id) as count
    FROM memberships
    WHERE guild_id = $1 AND active = 1
  `, [guild_id]);
  
  return result.rows[0].count;
}
```

### Pattern 2: API-Only Access (Recommended for Actions)

**Use for:**
- Creating plans
- Processing payments
- Requesting payouts
- Any data modifications

**Why:** Bot handles business logic, validation, Discord role updates

**Website calls bot API endpoints** (we'll create these next)

---

## 📋 Common Queries for Website

### 1. Get Server Dashboard Data
```sql
-- Total revenue
SELECT COALESCE(SUM(amount_mnt), 0) as total_revenue
FROM payments
WHERE guild_id = $1 AND status = 'paid';

-- Available balance (after 3% fee and payouts)
SELECT 
  COALESCE(SUM(amount_mnt), 0) * 0.97 - COALESCE(
    (SELECT SUM(net_mnt) FROM payouts WHERE guild_id = $1 AND status = 'done'), 
    0
  ) as available_balance
FROM payments
WHERE guild_id = $1 AND status = 'paid';

-- Active members count
SELECT COUNT(DISTINCT user_id) as members
FROM memberships
WHERE guild_id = $1 AND active = 1;

-- Subscription status
SELECT plan_name, expires_at, status
FROM subscriptions
WHERE guild_id = $1;
```

### 2. Get Role Plans List
```sql
SELECT plan_id, role_name, price_mnt, duration_days, description
FROM role_plans
WHERE guild_id = $1 AND active = 1
ORDER BY price_mnt ASC;
```

### 3. Get Payment History
```sql
SELECT 
  p.payment_id,
  p.user_id,
  p.amount_mnt,
  p.status,
  p.created_at,
  p.paid_at,
  rp.role_name
FROM payments p
LEFT JOIN role_plans rp ON p.plan_id = rp.plan_id
WHERE p.guild_id = $1
ORDER BY p.created_at DESC
LIMIT 50;
```

### 4. Get Top Spenders
```sql
SELECT 
  user_id,
  COUNT(*) as purchase_count,
  SUM(amount_mnt) as total_spent
FROM payments
WHERE guild_id = $1 AND status = 'paid'
GROUP BY user_id
ORDER BY total_spent DESC
LIMIT 10;
```

### 5. Get Revenue Breakdown by Plan
```sql
SELECT 
  rp.role_name,
  COUNT(*) as sales_count,
  SUM(p.amount_mnt) as revenue
FROM payments p
JOIN role_plans rp ON p.plan_id = rp.plan_id
WHERE p.guild_id = $1 AND p.status = 'paid'
GROUP BY rp.plan_id, rp.role_name
ORDER BY revenue DESC;
```

---

## 🔒 Security Recommendations

### For Website Developer:

1. **Never expose database credentials to frontend**
   - Use backend API only
   - Store DATABASE_URL in server environment variables

2. **Validate guild_id ownership**
   - Check if logged-in user is admin of that guild
   - Use Discord OAuth to verify permissions

3. **Read-only queries for dashboard**
   - Use SELECT queries only for displaying data
   - Never UPDATE/DELETE from website directly

4. **Use bot API for modifications**
   - Creating plans → POST /api/plans
   - Processing payments → POST /api/payments
   - Let bot handle Discord role updates

5. **Connection pooling**
   - Use pg.Pool, not individual connections
   - Set max connections: 10-20

---

## 🚀 Quick Start for Website

### Step 1: Install PostgreSQL Client
```bash
npm install pg
# or
pip install psycopg2-binary
```

### Step 2: Set Environment Variable
```bash
DATABASE_URL=postgresql://user:pass@host:port/db
```

### Step 3: Test Connection
```javascript
const { Pool } = require('pg');
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

pool.query('SELECT NOW()', (err, res) => {
  console.log(err ? err : res.rows[0]);
  pool.end();
});
```

### Step 4: Build Dashboard Pages
- `/dashboard` - Show revenue, balance, members
- `/dashboard/plans` - Manage role plans
- `/dashboard/analytics` - Charts and insights
- `/dashboard/payouts` - Request payouts

---

## 📞 What to Share with Website Developer

Copy-paste this message:

```
Hi! Here's the database connection for the Discord bot:

DATABASE_URL: [paste from Railway]

Or separate details:
Host: [host]
Port: 5432
Database: [database]
Username: [username]
Password: [password]
SSL: Required

Database schema: See WEBSITE_DATABASE_GUIDE.md

Important:
1. You can READ data directly (revenue, members, stats)
2. For ACTIONS (create plan, process payment), wait for bot API endpoints
3. Use connection pooling (max 10 connections)
4. Never expose credentials to frontend
5. Validate user permissions with Discord OAuth

Let me know when you're ready for the API endpoint specifications!
```

---

## ✅ Checklist for Website Developer

- [ ] PostgreSQL client library installed
- [ ] DATABASE_URL environment variable set
- [ ] Test connection successful
- [ ] Can query subscriptions table
- [ ] Can query role_plans table
- [ ] Dashboard shows revenue correctly
- [ ] Member count displays properly
- [ ] Payment history loads
- [ ] Connection pooling configured
- [ ] Ready for API endpoint integration

---

Next: Bot API endpoints for payment processing and plan management! 🚀
