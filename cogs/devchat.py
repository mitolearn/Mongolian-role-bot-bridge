import os
import discord
from discord import app_commands
from discord.ext import commands
from openai import OpenAI

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_KEY:
    raise RuntimeError("OPENAI_API_KEY not set in Replit Secrets.")

OWNER_ID_STR = os.getenv("OWNER_ID")
if not OWNER_ID_STR:
    raise RuntimeError("OWNER_ID not set in Replit Secrets.")
OWNER_ID = int(OWNER_ID_STR)

# the newest OpenAI model is "gpt-5" which was released August 7, 2025.
# do not change this unless explicitly requested by the user
client_ai = OpenAI(api_key=OPENAI_KEY)

class DevChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="devchat", description="Talk with Twin Sun AI Developer Assistant (Owner only)")
    async def devchat(self, interaction: discord.Interaction, message: str):
        """
        AI-powered development assistant that can see your bot's code
        and provide direct advice for improving Twin Sun Bot.
        Only accessible by the bot owner to reduce costs.
        """
        # Restrict access to owner only
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("⛔ Only the bot owner can use this command.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True, ephemeral=True)

        # Gather code context from main files
        code_summary = ""
        files_to_read = ["main.py", "database.py", "database_postgres.py", "utils/qpay.py"]
        
        for filepath in files_to_read:
            try:
                with open(filepath, "r") as f:
                    content = f.read()[:3000]  # Read partial code to stay within token limits
                    code_summary += f"\n\n--- {filepath} ---\n{content}"
            except Exception as e:
                code_summary += f"\n\n--- {filepath} ---\n(Could not read: {e})"

        # Get list of available cogs
        try:
            cogs_list = ", ".join([f.replace(".py", "") for f in os.listdir("cogs") if f.endswith(".py")])
            code_summary += f"\n\n--- Available Cogs ---\n{cogs_list}"
        except:
            pass

        # Create comprehensive prompt with context
        prompt = f"""
You are the Twin Sun Development Assistant - an expert AI advisor for a QPay-based Discord bot.

**Bot Overview:**
Twin Sun Bot is a monetization and membership management system for Mongolian Discord communities. It handles:
- QPay payment integration for role subscriptions
- Automated role assignment based on payments
- Membership tracking and renewal
- Admin dashboard and analytics
- Weekly reports and status monitoring

**Current Code Context:**
{code_summary}

**Developer's Question:**
{message}

**Instructions:**
- Provide clear, actionable advice
- Include ready-to-paste Python code when appropriate
- Consider the existing code structure and patterns
- Suggest improvements that align with the bot's architecture
- Be concise but thorough
- Focus on practical solutions

Respond as a professional development advisor.
"""

        try:
            # Send request to OpenAI GPT-5
            response = client_ai.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": "You are an expert Python developer and Discord bot architect. You provide clear, actionable advice with code examples."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000
            )

            answer = response.choices[0].message.content or "No response from AI"
            
            # Discord has a 2000 character limit per message
            if len(answer) > 1900:
                # Split into multiple messages
                chunks = [answer[i:i+1900] for i in range(0, len(answer), 1900)]
                await interaction.followup.send(f"🧠 **Twin Sun AI Developer Assistant:**\n{chunks[0]}", ephemeral=True)
                for chunk in chunks[1:]:
                    await interaction.followup.send(chunk, ephemeral=True)
            else:
                await interaction.followup.send(f"🧠 **Twin Sun AI Developer Assistant:**\n{answer}", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Error communicating with AI: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(DevChatCog(bot))
