import os
import discord
from discord.ext import commands

# Auto-detect database type and import from loader
from database_loader import init_db

from utils.qpay import validate_qpay_credentials

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("Set DISCORD_TOKEN in Replit Secrets.")

# Validate QPay credentials
try:
    validate_qpay_credentials()
    print("✅ QPay credentials validated")
except RuntimeError as e:
    print(f"⚠️ Warning: {e}")
    print("⚠️ Payment features will not work until credentials are set")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Init DB
init_db()

# List of all cogs
initial_extensions = [
    "cogs.admin",
    "cogs.payment",
    "cogs.membership",
    "cogs.status",
    "cogs.subscription_checker",
    "cogs.owner",
    "cogs.analytics",
    "cogs.weekly_reports",
    "cogs.devchat"
]

async def load_cogs():
    for ext in initial_extensions:
        try:
            await bot.load_extension(ext)   # ✅ must use await
            print(f"✅ Loaded {ext}")
        except Exception as e:
            print(f"❌ Failed to load {ext}: {e}")

@bot.event
async def on_ready():
    await load_cogs()
    try:
        await bot.tree.sync()
    except Exception as e:
        print("Slash sync error:", e)
    print(f"✅ Logged in as {bot.user} | Slash commands synced.")

bot.run(TOKEN)