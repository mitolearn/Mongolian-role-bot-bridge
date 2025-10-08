# Railway PostgreSQL Setup Guide

## 🚂 Step 1: Add PostgreSQL to Your Railway Project

### 1.1 Open Your Railway Dashboard
- Go to: https://railway.app
- Open your bot project (where your Discord bot is deployed)

### 1.2 Add PostgreSQL Database
1. Click **"+ New"** button in your project
2. Select **"Database"** → **"PostgreSQL"**
3. Railway creates it instantly (free $5/month credit included)
4. Wait 10-20 seconds for database to provision

### 1.3 Get Connection Details
1. Click on the PostgreSQL service
2. Go to **"Connect"** tab
3. Copy the **"Postgres Connection URL"** 
   - It looks like: `postgresql://user:password@host:port/database`
   - Keep this URL safe - you'll need it!

---

## 📦 Step 2: Update Your Bot Code on Railway

### 2.1 Add PostgreSQL Package
Add to your `requirements.txt`:
```
discord-py
requests
psycopg2-binary
```

### 2.2 Replace database.py
1. Rename current `database.py` to `database_sqlite.py` (backup)
2. Rename `database_postgres.py` to `database.py`
3. Your bot will now use PostgreSQL

### 2.3 Add Environment Variable
In Railway project settings:
1. Click on your Discord bot service
2. Go to **"Variables"** tab
3. Add new variable:
   - **Name**: `DATABASE_URL`
   - **Value**: [paste the Postgres Connection URL from Step 1.3]
4. Click **"Save"**

---

## 🔄 Step 3: Deploy & Test

### 3.1 Deploy Changes
1. Git push your changes:
   ```bash
   git add .
   git commit -m "feat: Switch to PostgreSQL for production"
   git push
   ```
2. Railway automatically deploys
3. Wait 1-2 minutes for build to complete

### 3.2 Check Logs
1. Click on your bot service in Railway
2. Go to **"Deployments"** tab
3. Click latest deployment → View logs
4. Look for: `✅ PostgreSQL connection pool initialized`
5. Look for: `✅ PostgreSQL database schema initialized`

### 3.3 Test Bot
1. Go to your Discord server
2. Run `/bot_info` to verify bot is working
3. Try creating a plan with `/plan_add`
4. Everything should work normally

---

## 🌐 Step 4: Share Database with Website

### 4.1 Get Connection Details for Website Developer
In Railway PostgreSQL service → "Connect" tab, copy these:

```
Host: [shown in Railway]
Port: [shown in Railway]  
Database: [shown in Railway]
Username: [shown in Railway]
Password: [shown in Railway]
```

### 4.2 Send to Website Developer
Create a message like this:

```
PostgreSQL Database Connection Details:

Full URL: postgresql://user:pass@host:port/dbname
(OR separate details:)
Host: abc.railway.internal
Port: 5432
Database: railway
Username: postgres
Password: [your password]

Tables in database:
- subscriptions
- guild_config
- role_plans
- users
- memberships
- payments
- leaders
- ledger
- payouts
- manager_roles

Your website can connect directly to read data.
For actions (create/edit), call bot API endpoints (we'll set those up next).
```

---

## ✅ Verification Checklist

- [ ] PostgreSQL added to Railway project
- [ ] `DATABASE_URL` environment variable set
- [ ] `requirements.txt` includes `psycopg2-binary`
- [ ] `database.py` uses PostgreSQL version
- [ ] Code pushed to git and deployed
- [ ] Bot logs show PostgreSQL connection success
- [ ] Bot commands work in Discord
- [ ] Connection details shared with website developer

---

## 💰 Cost Estimate

**Railway Free Tier:**
- $5 credit per month
- PostgreSQL charges: ~$0.20/day for small database
- Discord bot: ~$0.30/day
- **Total**: ~$15/month (you pay ~$10 after free credit)

**For your production bot:**
- Multiple servers = more database activity
- Estimated: $20-30/month
- Still much cheaper than managed hosting elsewhere!

---

## 🆘 Troubleshooting

### "Connection refused"
- Check if `DATABASE_URL` is set correctly in Railway variables
- Make sure PostgreSQL service is running (green status)

### "Permission denied"
- Railway PostgreSQL requires `psycopg2-binary` package
- Make sure it's in requirements.txt

### "Table doesn't exist"
- Check bot logs - `init_db()` should run on startup
- Manually run init if needed through Railway shell

### Website can't connect
- Make sure website has correct connection details
- Railway internal network vs external - use the public URL for external website

---

## 🎉 Success!

Your bot now uses production-grade PostgreSQL that:
- ✅ Supports bot + website simultaneously
- ✅ Handles multiple connections properly
- ✅ Scales with your growth
- ✅ No file corruption issues
- ✅ Better performance than SQLite

Next step: Set up API endpoints for website integration!
