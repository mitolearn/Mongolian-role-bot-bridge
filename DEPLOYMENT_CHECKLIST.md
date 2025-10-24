# 🚀 Deployment Checklist - Twin Sun Bot

## Pre-Launch Verification

### ✅ 1. Environment Variables
- [ ] `DISCORD_TOKEN` - Discord bot token set
- [ ] `QPAY_USERNAME` - QPay username set
- [ ] `QPAY_PASSWORD` - QPay password set
- [ ] `QPAY_INVOICE_CODE` - QPay invoice code set
- [ ] `OPENAI_API_KEY` - OpenAI API key set
- [ ] `OWNER_DISCORD_ID` - Your Discord user ID set
- [ ] `OWNER_ID` - Same as OWNER_DISCORD_ID (for /devchat)
- [ ] `SUB_BASIC_PRICE` - Optional (default: 100₮)
- [ ] `SUB_PRO_PRICE` - Optional (default: 200₮)
- [ ] `SUB_PREMIUM_PRICE` - Optional (default: 300₮)

### ✅ 2. Discord Bot Configuration
- [ ] Bot invited to server with Manage Roles permission
- [ ] Server Members Intent enabled
- [ ] Message Content Intent enabled
- [ ] Bot role positioned ABOVE all paid roles

### ✅ 3. Code Verification
- [x] All Python files have proper error handling
- [x] Database migrations are idempotent
- [x] QPay integration tested
- [x] Background tasks configured correctly
- [x] No hardcoded secrets in code
- [x] Temporary files cleaned up

### ✅ 4. Database
- [x] SQLite database initialized
- [x] All tables created with proper schema
- [x] Soft-delete column added to role_plans
- [x] Foreign keys enabled
- [x] Migrations tested

### ✅ 5. Features Verification

#### Payment System
- [ ] `/setup` - Bot subscription works
- [ ] `/buy` - User can purchase roles
- [ ] QPay invoice generation works
- [ ] Payment verification works
- [ ] Role granted immediately after payment
- [ ] `/verifypayment` backup command works

#### Membership Management
- [ ] Roles assigned automatically
- [ ] Multiple roles supported
- [ ] Expiry system works (test with short duration)
- [ ] Renewal DMs sent 3 days before expiry
- [ ] Deleted plans preserved in analytics

#### Admin Features
- [ ] `/plan_add` - Create role plans
- [ ] `/plan_list` - View all plans
- [ ] `/plan_delete` - Soft-delete preserves data
- [ ] `/edit_plan_description` - Add marketing copy
- [ ] `/paywall` - Post purchase buttons
- [ ] `/checksetup` - Verify permissions

#### Analytics
- [ ] `/status` - Shows correct revenue breakdown
- [ ] `/status` - Shows bot subscription expiry
- [ ] `/growth` - AI insights working
- [ ] `/topmembers` - Shows Discord names (not IDs)
- [ ] `/topmembers` - Includes deleted plans
- [ ] Weekly reports send on Mondays

#### Owner Commands
- [ ] `/devchat` - AI assistant works
- [ ] `/review` - Feedback system works

### ✅ 6. Background Tasks
- [x] Subscription checker runs every 1 hour
- [x] Membership expiry checker runs every 1 hour
- [x] Renewal warnings run every 12 hours
- [x] Weekly reports run every Monday
- [x] All tasks wait for bot.wait_until_ready()

### ✅ 7. Error Handling
- [x] Try/except blocks on all Discord API calls
- [x] Try/except blocks on all database operations
- [x] Try/except blocks on all QPay API calls
- [x] Try/except blocks on all OpenAI API calls
- [x] Proper error messages to users
- [x] Console logging for debugging

### ✅ 8. Security
- [x] No secrets in code
- [x] SQL injection prevention (parameterized queries)
- [x] Permission checks on admin commands
- [x] Owner-only checks on sensitive commands
- [x] Manager role permissions working

## Launch Procedure

### Step 1: Code Push
```bash
git init
git add .
git commit -m "Initial commit - Twin Sun Bot v1.0"
git remote add origin <your-repo-url>
git push -u origin main
```

### Step 2: Replit Setup
1. Import repository to Replit
2. Configure all secrets
3. Click "Run"
4. Verify bot comes online

### Step 3: Server Setup
1. Run `/setup` as admin
2. Pay for bot subscription
3. Run `/checksetup`
4. Fix any permission issues
5. Verify bot role position

### Step 4: Create First Plan
1. Run `/plan_add role:@YourRole display_name:"Premium Member" price_mnt:1000 duration_days:30`
2. Add description with `/edit_plan_description`
3. Post paywall with `/paywall`

### Step 5: Test Purchase
1. Purchase as test user
2. Verify payment flow
3. Check role assignment
4. Verify database records

### Step 6: Monitor
1. Check console logs for errors
2. Test `/status` command
3. Verify analytics show data
4. Wait 1 hour and check background tasks ran

## Post-Launch Monitoring

### Daily Checks
- [ ] Bot is online
- [ ] No errors in console
- [ ] Payments processing
- [ ] Roles being assigned/removed

### Weekly Checks
- [ ] Review `/status` dashboard
- [ ] Check `/growth` analytics
- [ ] Verify weekly reports sent
- [ ] Review any `/review` feedback

### Monthly Checks
- [ ] Database backup
- [ ] Review subscription renewals
- [ ] Check revenue collection
- [ ] Update prices if needed

## Troubleshooting

### Bot Offline
1. Check Replit logs
2. Verify DISCORD_TOKEN
3. Check Discord API status
4. Restart bot

### Payments Not Working
1. Verify QPay credentials
2. Check QPay account status
3. Test with `/verifypayment`
4. Check console for QPay errors

### Roles Not Assigned
1. Run `/checksetup`
2. Verify bot role position
3. Check Manage Roles permission
4. Check console for Discord errors

### Background Tasks Not Running
1. Check console for task start messages
2. Verify bot stayed online
3. Check for exceptions in logs
4. Restart bot if needed

## Success Criteria

✅ Bot online 24/7
✅ Payments processing successfully  
✅ Roles assigned/removed automatically
✅ Analytics showing accurate data
✅ Weekly reports sending
✅ No critical errors in logs
✅ Users can purchase and renew
✅ Admins can collect revenue

## Rollback Plan

If critical issues occur:
1. Stop accepting new payments
2. Message all admins
3. Fix issues in development environment
4. Test thoroughly
5. Deploy fixed version
6. Resume normal operation

## Version History

- **v1.0** - Initial production release
  - Payment processing via QPay
  - Role-based subscriptions
  - AI-powered analytics
  - Automated membership management
  - Soft-delete plan system
  - Bot subscription tracking
  - Developer AI assistant

---

**Deployment Date**: _To be filled_  
**Deployed By**: _To be filled_  
**Production URL**: _To be filled_
