# Replit.md

## Recent Changes

### October 21, 2025 - AI Developer Assistant Integration
- **New Feature**: Added `/devchat` command for owner-only AI-powered development assistance
- **Direct OpenAI Integration**: Integrated GPT-4o model to provide code analysis and development advice
- **Cost Optimization**: Direct API calls to OpenAI (bypassing Replit Agent) to minimize development costs
- **Full Codebase Access**: AI reads ALL Python files (main, cogs, utils) plus documentation files for comprehensive understanding
- **Replit Agent-Level Capabilities**: Enhanced system prompt enables expert-level development assistance comparable to Replit Agent
- **Security**: Command restricted to bot owner via OWNER_ID environment variable
- **Technical Implementation**: 
  - Created `cogs/devchat.py` with full codebase scanning functionality
  - Updated OpenAI library to version 2.6.0 for modern API support
  - Added OWNER_ID secret management
  - AI receives complete project context: all .py files, replit.md, requirements.txt, and setup documentation
  - 4000 token output limit for comprehensive responses

## Overview

This Discord bot facilitates community management, integrating payment processing and leader commission tracking. It handles user registration, payment confirmations via QPay, and manages leader balances with a commission-based reward system. The bot is developed in Python using `discord.py` with SQLite for data persistence. Its purpose is to streamline community operations, automate payment handling, and provide valuable insights through AI-powered analytics. The project aims to enable efficient monetization and growth for Discord communities.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions
- **Interactive Buttons**: Extensive use of Discord buttons for payment, renewal, and navigation.
- **Rich Embeds**: Visually appealing and informative embeds for commands like `/myplan`, `/growth`, `/topmembers`, and `/bot_info`.
- **Color-Coded Status**: Visual cues (e.g., 🟢, 🟡, 🔴) for membership status in `/myplan`.
- **Modals for Input**: Utilizes Discord modals for multi-line text input, such as plan descriptions.
- **Chart Visualization**: Integration with QuickChart.io for generating visual growth and revenue charts.

### Technical Implementations
- **Modular Python**: Codebase structured with separate modules for database operations (`database.py`), bot commands (cogs), and utilities.
- **SQLite Database**: Simple, reliable file-based database with no external dependencies.
- **Asynchronous Operations**: Leverages `asyncio` with `discord.py` for non-blocking I/O and efficient handling of concurrent requests.
- **Robust Error Handling**: Includes comprehensive null checks and error handling for Discord API interactions, database operations, and external API calls.
- **Environment Variable Configuration**: Uses environment variables for sensitive credentials (Discord token, QPay keys) and configuration settings.

### Feature Specifications
- **Payment System**:
    - **QPay Integration**: Direct integration with QPay Mongolia for invoice generation and payment verification.
    - **Dual Purchase System**: Users can buy roles via `/paywall` (admin-posted) or `/buy` (user-initiated ephemeral).
    - **Multi-Role Support**: Users can hold multiple roles simultaneously, each with independent expiry.
    - **Subscription Renewal**: Automated expiry warnings, flexible renewal options (QPay or collected balance), and proper time extension logic.
    - **Universal Payment Backup**: `/verifypayment` command to manually verify payments if automated checks fail.
- **Commission & Payout System**:
    - **Leader Associations**: Tracks user payments linked to specific leaders.
    - **Automated Commissions**: Calculates and updates leader balances based on confirmed payments.
    - **Minimum Payouts**: Enforces a minimum collection amount (100,000₮) before allowing payout requests.
    - **Detailed Payout Confirmations**: Sends DMs to admins and owners with comprehensive transaction details upon payout completion.
- **Analytics & Reporting**:
    - **AI-Powered Weekly Reports**: Automated weekly reports to server admins with comprehensive growth data and GPT-4o powered business recommendations.
    - **Growth Analytics Dashboard**: `/growth` command provides admins with revenue trends, role plan breakdowns, active member count, and AI-driven insights.
    - **Top Members Dashboard**: `/topmembers` command displays top spenders overall and per plan.
- **Community Management**:
    - **Plan Descriptions**: Admins can add marketing descriptions to role plans.
    - **Role Automation**: Automatic Discord role assignment/removal based on payment status and expiry.
    - **Bot Information**: `/bot_info` command provides critical warnings, command list, and a detailed guide.
- **Developer Tools**:
    - **AI Developer Assistant**: `/devchat` command (owner-only) provides GPT-4o powered development advice with complete codebase access
    - **Full Code Analysis**: Scans ALL Python files (main.py, database files, cogs/*.py, utils/*.py) plus documentation
    - **Direct OpenAI Integration**: Cost-optimized direct API calls bypassing Replit Agent for reduced expenses
    - **Expert-Level Guidance**: Enhanced to match Replit Agent capabilities with comprehensive system prompt
    - **Context-Aware Responses**: AI sees entire project structure and can provide specific, actionable advice referencing actual code

### System Design Choices
- **Database**: SQLite for simple, reliable, file-based storage with no external dependencies.
- **Discord.py Framework**: Chosen for its robustness, extensive features, and active community.
- **AI Model**: GPT-4o for all AI features (automated analytics, weekly reports, and development assistant), selected for its balance of cost-effectiveness, speed, and analytical capabilities.

## External Dependencies

### APIs and Services
- **Discord API**: Primary platform for bot interaction, provided via the `discord.py` library.
- **QPay Payment API**: Used for secure payment processing, invoice generation, and status verification.
- **OpenAI API**: Utilized for AI-powered business recommendations, analytics, and development assistance (GPT-4o model).
- **QuickChart.io API**: Generates visual charts for analytics dashboards.

### Python Libraries
- `discord.py`: Core library for Discord bot development.
- `sqlite3`: Built-in library for SQLite database interactions.
- `requests`: For making HTTP requests to external APIs (QPay, QuickChart.io).
- `openai` (v2.6.0): Official OpenAI client library for GPT-4o API access.
- `datetime`: For handling date and time operations, crucial for subscriptions and renewals.

### Infrastructure
- **SQLite Database**: Local file-based database stored as `database.db`.
- **Environment Variables**: For managing configuration, credentials, and settings.