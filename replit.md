# Replit.md

## Overview

This is a Discord bot designed for community management with integrated payment processing and leader commission tracking. The bot handles user registration, payment confirmations through QPay API integration, and manages leader balances with commission-based rewards. It's built using Python with Discord.py for bot functionality and SQLite for data persistence.

## Recent Changes (October 3, 2025)

### New Features
- **Growth Analytics Dashboard**: Admins can view comprehensive revenue analytics with `/growth`
  - Beautiful visual charts showing 30-day revenue trends (line chart)
  - Revenue breakdown by role plan (pie chart with percentages)
  - Growth percentage calculation comparing last 30 days vs previous 30 days
  - Total revenue, available balance (after 3% fee), and active member count
  - Top 5 role plans with payment counts
  - Charts generated via QuickChart.io API (no installation needed)
  - Handles edge cases: new growth, zero revenue, positive/negative trends
- **Subscription Renewal System**: Automatic expiry warnings and flexible payment options
  - DM sent to all admins 3 days before subscription expires
  - Two renewal options: QPay or Pay with Collected Balance
  - Accurate money tracking - collected balance deducted and recorded in payouts table
  - Automatic subscription activation after payment
  - Bot stops working when subscription expires with helpful messages to members
- **Top Members Dashboard**: Admins can view member spending statistics with `/topmembers`
  - Shows top 10 overall spenders across all plans with medals (🥇🥈🥉)
  - Displays top 3 spenders for each individual role plan
  - Total revenue summary at the top
  - Beautiful dashboard embeds with member names and payment counts
- **Plan Descriptions**: Admins can now add custom marketing descriptions to role plans explaining benefits, perks, and what members get
  - `/plan_add` command opens a modal to add descriptions when creating plans
  - `/edit_plan_description` command allows updating descriptions anytime
  - Descriptions appear in `/buy` and `/paywall` embeds, payment confirmations, and renewal DMs
  - Graceful fallbacks for plans without descriptions
- **Dual Purchase System**: Users can now buy roles in two ways:
  - `/paywall` command (Admin posts payment buttons in channel)
  - `/buy` command (Any user can call directly, ephemeral message)
- **Bot Information Command**: Enhanced `/bot_info` with critical warnings and detailed guide button
  - Shows critical warnings first (bot role positioning, permissions)
  - Quick reference of all commands
  - "Detailed Guide" button for comprehensive information
  - Covers setup workflow, payment flow, analytics, troubleshooting

### Payout Rules & Confirmations
- **Minimum Collection Amount**: 100,000₮ required to request payout
  - Status command shows warning if balance below minimum
  - Collect button displays helpful message with amount needed
  - Only sends DM to owner when balance meets minimum requirement
  - Prevents small payouts to reduce bank transfer fees
- **Payout Confirmation System**: Detailed DMs sent when owner marks payout as done
  - **Admin Confirmation DM**: Sent to admin with collection details, bank account info, request/completion dates, revenue breakdown, and payout ID
  - **Owner Checkpoint DM**: Permanent record sent to owner with server info, admin details, amount sent, bank details, transaction breakdown, and timeline - serves as proof for future verification and bank reconciliation

### Critical Bug Fixes
- **Button Interaction Timeout Fix** (Oct 7, 2025): Added `/verifypayment` slash command as reliable alternative to buttons - buttons in DMs can timeout/fail after bot restarts, new command always works
- **Membership Renewal Payment Verification** (Oct 7, 2025): Fixed missing "Check Payment" button in membership expiry renewal DMs - users can now verify payment and restore role after paying renewal fee
- **Subscription Renewal Fee Bug** (Oct 3, 2025): Fixed incorrect fee calculation in balance-based renewal - admins now pay exact amount (100₮/200₮/300₮) without inflated 3% deduction
- **Payment Record Corruption** (Oct 3, 2025): Fixed parameter order in membership expiry renewal flow - prevents data corruption in payment records
- **Payment Confirmation Fixed**: Added proper interaction response handling to prevent crashes during payment verification
- **Database Integrity**: Removed plan ID resequencing to prevent foreign key corruption when deleting plans
- **Payout System**: Fixed bank account data saving to correctly store user input instead of TextInput objects
- **Null Safety**: Added comprehensive null checks for guild, member, role, and plan lookups across all commands
- **QPay Validation**: Added startup validation for QPay credentials with clear error messaging
- **Discord.py Compatibility**: Updated cog_unload methods to async for compatibility with latest Discord.py

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Database Design
- **SQLite Database**: Uses a local SQLite database (`database.db`) for data persistence
- **Relational Schema**: Three main tables with foreign key relationships:
  - Users table: Stores Discord user information with leader associations
  - Leaders table: Manages leader profiles, commission rates, and balances
  - Payments table: Tracks payment transactions and status updates
- **Data Integrity**: Foreign key constraints enabled to maintain referential integrity

### Bot Architecture
- **Discord.py Framework**: Built on the Discord.py library with command prefix "!"
- **Intent Configuration**: Configured with message content and member intents for full functionality
- **Modular Design**: Database operations separated into dedicated modules for maintainability

### Payment Processing
- **Real QPay Integration**: Live payment processing through QPay Mongolia API
- **Secure Authentication**: Token-based authentication using stored credentials (QPAY_USERNAME, QPAY_PASSWORD, QPAY_INVOICE_CODE)
- **Invoice Creation**: Automatic QPay invoice generation with real payment URLs
- **Status Verification**: Real-time payment status checking directly from QPay API
- **Role Automation**: Automatic Discord role assignment upon payment confirmation

### Commission System
- **Leader-based Structure**: Users are associated with leaders who earn commissions
- **Balance Management**: Automatic balance updates for leaders based on confirmed payments
- **Rate-based Calculations**: Configurable commission rates per leader

### Development Tools
- **Database Viewer**: Dedicated utility (`view_db.py`) for database inspection and debugging
- **Environment Configuration**: Secure token management through environment variables

## External Dependencies

### APIs and Services
- **Discord API**: Core bot functionality through Discord.py library
- **QPay Payment API**: External payment processing and confirmation service

### Python Libraries
- **discord.py**: Discord bot framework and API wrapper
- **sqlite3**: Built-in Python SQLite database interface
- **requests**: HTTP client for external API calls
- **datetime**: Date and time handling utilities

### Infrastructure
- **Environment Variables**: Secure configuration management for sensitive tokens and environment-specific settings
- **SQLite Database**: Local file-based database storage (`database.db` and `community_bot.db`)
- **Multi-Environment Support**: Separate configurations for test (Replit) and production (Railway) environments

### Environment Variables Configuration

**Required Variables (All Environments):**
- `DISCORD_TOKEN`: Discord bot authentication token
- `QPAY_USERNAME`, `QPAY_PASSWORD`, `QPAY_INVOICE_CODE`: QPay API credentials
- `OWNER_DISCORD_ID`: Bot owner's Discord ID

**Environment-Specific Variables:**

| Variable | Replit (Test) | Railway (Production) | Purpose |
|----------|---------------|----------------------|---------|
| `DB_NAME` | Not set (uses `database.db`) | `production.db` | Database file name |
| `SUB_BASIC_PRICE` | Not set (uses 100) | `59900` | Basic subscription price |
| `SUB_PRO_PRICE` | Not set (uses 200) | `149900` | Pro subscription price |
| `SUB_PREMIUM_PRICE` | Not set (uses 300) | `279900` | Premium subscription price |

**Why This Matters:**
- Replit uses low test prices (100₮, 200₮, 300₮) for easy testing
- Railway uses real production prices (59,900₮, 149,900₮, 279,900₮) automatically
- No risk of accidentally pushing test prices to production - controlled by environment variables
- Same codebase works perfectly in both environments