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

client_ai = OpenAI(api_key=OPENAI_KEY)

class DevChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def read_all_code_files(self):
        """Read all Python and configuration files from the project"""
        code_files = {}
        
        # Directories and files to read
        paths_to_scan = [".", "cogs", "utils"]
        important_files = ["replit.md", "requirements.txt", "SETUP_COMPLETE.md", "RAILWAY_DATABASE_INFO.md"]
        
        # Scan all Python files
        for directory in paths_to_scan:
            if not os.path.exists(directory):
                continue
            
            if directory == ".":
                # Read root level .py files only
                for filename in os.listdir(directory):
                    if filename.endswith(".py") and os.path.isfile(filename):
                        try:
                            with open(filename, "r", encoding="utf-8") as f:
                                code_files[filename] = f.read()
                        except Exception as e:
                            code_files[filename] = f"Error reading: {e}"
            else:
                # Read all .py files in subdirectories
                for filename in os.listdir(directory):
                    filepath = os.path.join(directory, filename)
                    if filename.endswith(".py") and os.path.isfile(filepath):
                        try:
                            with open(filepath, "r", encoding="utf-8") as f:
                                code_files[filepath] = f.read()
                        except Exception as e:
                            code_files[filepath] = f"Error reading: {e}"
        
        # Read important documentation files
        for filename in important_files:
            if os.path.exists(filename):
                try:
                    with open(filename, "r", encoding="utf-8") as f:
                        code_files[filename] = f.read()
                except Exception as e:
                    code_files[filename] = f"Error reading: {e}"
        
        return code_files

    @app_commands.command(name="devchat", description="Talk with Twin Sun AI Developer Assistant (Owner only)")
    async def devchat(self, interaction: discord.Interaction, message: str):
        """
        AI-powered development assistant with full codebase access.
        Uses GPT-4o to provide expert development advice.
        Only accessible by the bot owner.
        """
        # Restrict access to owner only
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("⛔ Only the bot owner can use this command.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True, ephemeral=True)

        # Read ALL code files from the project
        code_files = self.read_all_code_files()
        
        # Build comprehensive code context
        code_context = "=== COMPLETE CODEBASE ===\n\n"
        for filepath, content in sorted(code_files.items()):
            code_context += f"\n{'='*60}\n"
            code_context += f"FILE: {filepath}\n"
            code_context += f"{'='*60}\n"
            code_context += content
            code_context += f"\n{'='*60}\n\n"

        # Create comprehensive system prompt matching Replit Agent capabilities
        system_prompt = """You are an expert AI software development assistant with the following capabilities:

**Your Role:**
- You are helping develop and maintain Twin Sun Bot, a Discord bot for monetization and membership management
- You have access to the COMPLETE codebase and can see every file
- You provide expert advice on Python, Discord.py, PostgreSQL, QPay integration, and bot architecture
- You can suggest code improvements, debug issues, and provide ready-to-use solutions

**Your Capabilities:**
- Full understanding of Python, Discord.py, async programming, and database management
- Expert knowledge of REST APIs, payment processing, and Discord bot best practices
- Ability to read and understand complex codebases
- Can write production-ready code with proper error handling
- Understand software architecture, design patterns, and code optimization
- Can debug errors, suggest refactoring, and improve code quality

**Your Guidelines:**
- Provide clear, actionable advice with code examples
- Write complete, working code that can be copy-pasted directly
- Consider the existing code structure and maintain consistency
- Suggest best practices and security improvements
- Explain your reasoning when making recommendations
- Be thorough but concise in your responses
- Focus on practical, implementable solutions

**Bot Architecture Context:**
- Python Discord bot using discord.py with slash commands
- PostgreSQL (production) and SQLite (development) databases
- QPay payment integration for Mongolian currency
- Role-based membership system with subscriptions
- Admin commands, analytics, weekly reports, and commission tracking
- Modular cog-based architecture

Respond like a professional software engineer and provide expert guidance."""

        # Create user prompt with full context
        user_prompt = f"""{code_context}

=== DEVELOPER QUESTION ===
{message}

=== INSTRUCTIONS ===
Analyze the complete codebase above and provide expert development advice.
Include ready-to-paste Python code when needed.
Be specific and reference actual files/functions from the codebase.
"""

        try:
            # Send request to OpenAI GPT-4o
            response = client_ai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=4000,
                temperature=0.7
            )

            answer = response.choices[0].message.content or "No response from AI"
            
            # Discord has a 2000 character limit per message
            # Split into multiple messages if needed
            if len(answer) > 1900:
                chunks = [answer[i:i+1900] for i in range(0, len(answer), 1900)]
                await interaction.followup.send(f"🧠 **Twin Sun AI Developer Assistant (GPT-4o):**\n{chunks[0]}", ephemeral=True)
                for chunk in chunks[1:]:
                    await interaction.followup.send(chunk, ephemeral=True)
            else:
                await interaction.followup.send(f"🧠 **Twin Sun AI Developer Assistant (GPT-4o):**\n{answer}", ephemeral=True)

        except Exception as e:
            error_message = f"❌ Error communicating with AI: {str(e)}\n\n"
            error_message += "This could be due to:\n"
            error_message += "- Invalid OpenAI API key\n"
            error_message += "- API quota exceeded\n"
            error_message += "- Network connectivity issues\n"
            error_message += "- Token limit exceeded (codebase too large)"
            await interaction.followup.send(error_message, ephemeral=True)

async def setup(bot):
    await bot.add_cog(DevChatCog(bot))
