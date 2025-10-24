# Twin Sun Bot - Discord Monetization Bot

A comprehensive Discord bot for Mongolian communities featuring role-based subscriptions, QPay payment integration, AI-powered analytics, and automated membership management.

## 🌟 Features

### Payment & Monetization
- **QPay Integration**: Secure payment processing via QPay Mongolia
- **Role-Based Subscriptions**: Users purchase roles with automatic expiry
- **Multi-Role Support**: Users can hold multiple paid roles simultaneously
- **Flexible Purchases**: Both admin-posted paywalls and user-initiated purchases
- **Automatic Renewals**: DM notifications with renewal options before expiry

### Membership Management
- **Automatic Role Assignment**: Roles granted immediately upon payment
- **Expiry System**: Roles automatically removed when membership expires
- **Soft-Delete Plans**: Historical data preserved even when plans are deleted
- **Multi-Guild Support**: Works across multiple Discord servers

### Analytics & Insights
- **AI-Powered Analytics**: GPT-4o provides business insights and recommendations
- **Growth Dashboard**: Visual charts showing revenue trends and member growth
- **Top Members Tracking**: See your highest spenders overall and per plan
- **Weekly Reports**: Automated Monday reports sent to admins
- **Real-Time Stats**: Track revenue, active members, and plan performance

### Admin Features
- **Bot Subscription System**: Admins rent the bot (Basic/Pro/Premium plans)
- **Revenue Collection**: Collect earnings with 3% platform fee
- **Plan Descriptions**: Add marketing copy to role plans
- **Manager Roles**: Delegate plan management to non-admin roles
- **Setup Verification**: `/checksetup` ensures correct permissions

### Developer Tools
- **AI Developer Assistant**: Owner-only `/devchat` command for development help
- **Full Code Analysis**: AI scans entire codebase for expert guidance
- **Direct OpenAI Integration**: Cost-optimized to minimize API expenses

## 📋 Requirements

- Python 3.11+
- Discord Bot Token
- QPay Mongolia Account (username, password, invoice code)
- OpenAI API Key (for AI features)
- PostgreSQL (automatically provided by Replit)

## 🚀 Quick Start

### 1. Environment Setup

Set these secrets in your Replit environment:

```bash
DISCORD_TOKEN=your_discord_bot_token
QPAY_USERNAME=your_qpay_username
QPAY_PASSWORD=your_qpay_password
QPAY_INVOICE_CODE=your_qpay_invoice_code
OPENAI_API_KEY=your_openai_api_key
OWNER_DISCORD_ID=your_discord_user_id
OWNER_ID=your_discord_user_id  # For /devchat command
```

Optional subscription pricing (defaults are for testing):
```bash
SUB_BASIC_PRICE=100      # 30 days
SUB_PRO_PRICE=200        # 90 days  
SUB_PREMIUM_PRICE=300    # 180 days
```

### 2. Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Enable these Privileged Gateway Intents:
   - Server Members Intent
   - Message Content Intent
4. Invite bot with these permissions:
   - Manage Roles
   - Send Messages
   - Use Slash Commands

### 3. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python main.py
```

### 4. Server Setup (First Time)

1. Run `/setup` to subscribe to the bot
2. Run `/checksetup` to verify permissions
3. **IMPORTANT**: Drag bot role ABOVE all paid roles in Server Settings → Roles
4. Run `/plan_add` to create your first paid role
5. Use `/paywall` to post purchase buttons in a channel

## 📚 Commands

### Admin Commands
- `/setup` - Subscribe to bot (Basic/Pro/Premium)
- `/plan_add` - Create a paid role plan
- `/plan_list` - View all role plans
- `/plan_toggle` - Enable/disable a plan
- `/plan_delete` - Soft-delete a plan (preserves analytics)
- `/edit_plan_description` - Add marketing copy to plans
- `/paywall` - Post payment buttons in a channel
- `/checksetup` - Verify bot permissions and role position

### Analytics Commands (Admin)
- `/status` - Financial dashboard + Collect button
- `/growth` - Visual charts + AI business insights
- `/topmembers` - See top spenders and statistics
- `/bot_info` - Show all commands and features guide

### User Commands
- `/buy` - Purchase any available role
- `/myplan` - Check all active memberships with expiry timers
- `/verifypayment` - Backup command to verify payments manually

### Manager Commands
- `/set_manager_role` - Allow a role to manage plans
- `/view_manager_role` - Check manager role
- `/remove_manager_role` - Remove manager permissions

### Owner Commands
- `/devchat` - AI development assistant (reads entire codebase)
- `/review` - Send feedback to bot developer

## 🏗️ Architecture

### Tech Stack
- **Framework**: discord.py (Python)
- **Database**: SQLite (file-based, reliable)
- **Payment API**: QPay Mongolia
- **AI Model**: OpenAI GPT-4o
- **Charts**: QuickChart.io

### Project Structure
```
.
├── main.py                      # Bot entry point
├── database.py                  # Database operations
├── cogs/
│   ├── admin.py                 # Admin commands
│   ├── payment.py               # Payment processing
│   ├── membership.py            # User commands
│   ├── status.py                # Financial dashboard
│   ├── analytics.py             # Growth analytics
│   ├── subscription_checker.py  # Background expiry checks
│   ├── weekly_reports.py        # Automated reports
│   ├── owner.py                 # Owner commands
│   └── devchat.py              # AI developer assistant
├── utils/
│   ├── qpay.py                 # QPay API integration
│   ├── charts.py               # Chart generation
│   └── helpers.py              # Utility functions
└── requirements.txt            # Python dependencies
```

### Database Schema
- `subscriptions` - Bot rental subscriptions
- `role_plans` - Paid role configurations
- `users` - Discord user records
- `memberships` - User access records
- `payments` - Payment transactions
- `payouts` - Collection requests
- `ledger` - Financial audit trail
- `manager_roles` - Delegated permissions

### Background Tasks
- **Expiry Checker** (every 1 hour): Removes expired roles
- **Subscription Checker** (every 1 hour): Deactivates expired bot subscriptions
- **Weekly Reports** (Mondays): Sends AI-powered analytics to admins
- **Renewal Warnings** (every 12 hours): Warns admins 3 days before expiry

## 🔒 Security

- Secrets stored in environment variables (never committed)
- SQL injection prevention (parameterized queries)
- Permission checks on all admin commands
- Owner-only commands for sensitive operations
- QPay API authentication with Bearer tokens
- Database foreign key constraints enabled

## 💡 Key Design Decisions

### Why SQLite?
- No external dependencies required
- Simple, reliable, file-based storage
- Perfect for Discord bot scale
- Easy backups (just copy database.db)

### Why Soft-Delete?
- Preserves historical analytics data
- Shows deleted plans in revenue reports
- Prevents data loss from admin mistakes
- Maintains payment history integrity

### Why GPT-4o?
- Best balance of cost, speed, and quality
- Excellent at data analysis and recommendations
- Lower cost than GPT-4 Turbo
- Perfect for weekly reports and analytics

### Why Direct OpenAI API?
- Minimizes costs (bypasses Replit Agent fees)
- Full control over prompts and context
- Cost-effective for owner-only dev assistance

## 📊 Revenue Model

- **Bot Subscription**: Admins rent the bot (30/90/180 days)
- **Platform Fee**: 3% deducted from all role sales
- **Minimum Collection**: 100,000₮ to withdraw earnings
- **Payment Flow**: QPay → Database → Role Grant → Commission tracking

## 🐛 Troubleshooting

### Bot can't assign roles
**Solution**: Drag bot role ABOVE paid roles in Server Settings → Roles

### Payments not working
**Solution**: Run `/checksetup` and verify QPay credentials in Secrets

### Users not getting DMs
**Solution**: Normal - some users have DMs disabled. Use `/verifypayment` as backup

### Background tasks not running
**Solution**: Bot must stay online 24/7. Use Replit Always On or similar service

## 📝 License

This project is proprietary software developed for Mongolian Discord communities.

## 🤝 Support

For bugs or feature requests, use `/review` command in Discord or contact the bot owner.

## 🚀 Deployment

### Replit (Recommended)
1. Import this repository to Replit
2. Set all secrets in Replit Secrets
3. Click "Run" - bot auto-deploys!

### Self-Hosting
1. Clone the repository
2. Create `.env` file with all required variables
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `python main.py`
5. Keep the process running 24/7 (use `screen`, `tmux`, or systemd)

## ⚡ Performance

- Handles multiple guilds concurrently
- Background tasks run independently
- Efficient database queries (indexed lookups)
- API rate limiting handled by discord.py
- Automatic reconnection on connection loss

---

**Made with ❤️ for Mongolian Discord communities**
