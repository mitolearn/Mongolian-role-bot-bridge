# Replit.md

## Overview

This Discord bot facilitates community management, integrating payment processing and leader commission tracking. It handles user registration, payment confirmations via QPay, and manages leader balances with a commission-based reward system. The bot is developed in Python using `discord.py` and supports both PostgreSQL and SQLite for data persistence, adapting to the deployment environment. Its purpose is to streamline community operations, automate payment handling, and provide valuable insights through AI-powered analytics. The project aims to enable efficient monetization and growth for Discord communities, allowing seamless sharing of data between the bot and a prospective website.

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
- **Modular Python**: Codebase structured with separate modules for database operations (`database_postgres.py`, `database_loader.py`), bot commands, and payment handling.
- **Database Abstraction**: A `database_loader.py` module intelligently switches between PostgreSQL and SQLite based on the `DATABASE_URL` environment variable, ensuring seamless deployment across environments.
- **Asynchronous Operations**: Leverages `asyncio` with `discord.py` for non-blocking I/O and efficient handling of concurrent requests.
- **Robust Error Handling**: Includes comprehensive null checks and error handling for Discord API interactions, database operations, and external API calls.
- **Environment Variable Configuration**: Uses environment variables for sensitive credentials (Discord token, QPay keys) and environment-specific settings (e.g., subscription prices for test vs. production).

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

### System Design Choices
- **Database**: PostgreSQL for production (Railway) for scalability and concurrent access, SQLite for development/testing (Replit) for ease of setup.
- **Discord.py Framework**: Chosen for its robustness, extensive features, and active community.
- **AI Model**: GPT-4o for AI analysis, selected for its balance of cost-effectiveness, speed, and analytical capabilities.

## External Dependencies

### APIs and Services
- **Discord API**: Primary platform for bot interaction, provided via the `discord.py` library.
- **QPay Payment API**: Used for secure payment processing, invoice generation, and status verification.
- **OpenAI API**: Utilized for AI-powered business recommendations and analysis (GPT-4o model).
- **QuickChart.io API**: Generates visual charts for analytics dashboards.

### Python Libraries
- `discord.py`: Core library for Discord bot development.
- `psycopg2` (implied by PostgreSQL usage): PostgreSQL adapter for Python.
- `sqlite3`: Built-in library for SQLite database interactions.
- `requests`: For making HTTP requests to external APIs (QPay, QuickChart.io, OpenAI).
- `datetime`: For handling date and time operations, crucial for subscriptions and renewals.

### Infrastructure
- **PostgreSQL Database**: Production database hosted on Railway.
- **SQLite Database**: Local file-based database for testing and backward compatibility.
- **Environment Variables**: For managing configuration, credentials, and environment-specific settings.