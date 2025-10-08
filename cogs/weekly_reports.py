import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import os
from openai import OpenAI

class WeeklyReportsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.openai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.weekly_report.start()
    
    async def cog_unload(self):
        self.weekly_report.cancel()
    
    @tasks.loop(hours=24)
    async def weekly_report(self):
        """Send weekly reports every Monday at 21:00"""
        now = datetime.utcnow()
        
        # Check if it's Monday (weekday 0) and around 21:00
        if now.weekday() != 0:  # Not Monday
            return
        
        # Check if it's between 21:00 and 21:59
        if now.hour != 21:
            return
        
        print(f"📊 Running weekly reports for {len(self.bot.guilds)} servers...")
        
        for guild in self.bot.guilds:
            try:
                await self.send_weekly_report(guild)
            except Exception as e:
                print(f"❌ Failed to send weekly report for {guild.name}: {e}")
    
    async def send_weekly_report(self, guild: discord.Guild):
        """Generate and send weekly report for a specific server"""
        from database import (
            total_guild_revenue, 
            available_to_collect, 
            get_subscription,
            list_role_plans
        )
        
        guild_id = str(guild.id)
        
        # Get server stats
        total_revenue = total_guild_revenue(guild_id)
        available_balance = available_to_collect(guild_id)
        subscription = get_subscription(guild_id)
        plans = list_role_plans(guild_id, only_active=True)
        
        # Calculate weekly revenue (last 7 days)
        weekly_revenue = self.get_weekly_revenue(guild_id)
        
        # Get AI-powered advice
        advice = await self.get_ai_advice(
            guild_name=guild.name,
            total_revenue=total_revenue,
            weekly_revenue=weekly_revenue,
            available_balance=available_balance,
            subscription=subscription,
            plan_count=len(plans) if plans else 0
        )
        
        # Create beautiful report embed
        embed = discord.Embed(
            title="📊 Weekly Performance Report",
            description=f"**Server:** {guild.name}\n"
                       f"**Date:** {datetime.utcnow().strftime('%B %d, %Y')}\n\n"
                       f"Here's your automated weekly summary with AI-powered recommendations!",
            color=0x3498db
        )
        
        # Stats section
        embed.add_field(
            name="💰 Revenue Summary",
            value=f"**All-Time Total:** {total_revenue:,}₮\n"
                  f"**This Week:** {weekly_revenue:,}₮\n"
                  f"**Available to Collect:** {available_balance:,}₮",
            inline=False
        )
        
        # Subscription status
        if subscription:
            plan_name, amount, expires_at, status = subscription
            embed.add_field(
                name="🤖 Bot Subscription",
                value=f"**Plan:** {plan_name}\n"
                      f"**Status:** {'✅ Active' if status == 'active' else '❌ Inactive'}\n"
                      f"**Expires:** {expires_at[:10] if expires_at else 'N/A'}",
                inline=False
            )
        else:
            embed.add_field(
                name="⚠️ Bot Subscription",
                value="No active subscription. Use `/setup` to activate!",
                inline=False
            )
        
        # AI advice section
        embed.add_field(
            name="🤖 AI-Powered Recommendations",
            value=advice,
            inline=False
        )
        
        embed.set_footer(text="📅 Reports sent every Monday at 21:00 UTC • Powered by ChatGPT")
        
        # Send to all admins
        admin_count = 0
        for member in guild.members:
            if member.guild_permissions.administrator and not member.bot:
                try:
                    await member.send(embed=embed)
                    admin_count += 1
                except:
                    pass  # Can't DM this admin
        
        print(f"✅ Sent weekly report to {admin_count} admins in {guild.name}")
    
    def get_weekly_revenue(self, guild_id: str) -> int:
        """Calculate revenue from last 7 days"""
        from database import _conn
        from datetime import datetime, timedelta
        
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        
        conn = _conn()
        c = conn.cursor()
        c.execute("""
            SELECT COALESCE(SUM(amount_mnt), 0) 
            FROM payments 
            WHERE guild_id=? AND status='paid' AND paid_at >= ?
        """, (guild_id, seven_days_ago))
        
        revenue = c.fetchone()[0] or 0
        conn.close()
        return int(revenue)
    
    async def get_ai_advice(self, guild_name: str, total_revenue: int, weekly_revenue: int, 
                           available_balance: int, subscription: tuple, plan_count: int) -> str:
        """Use ChatGPT to generate personalized advice"""
        
        # Prepare context for AI
        subscription_status = "Active" if subscription and subscription[3] == 'active' else "Inactive or Expired"
        
        prompt = f"""You are a business advisor for Discord server monetization. Analyze this server's performance and give 3 concise, actionable recommendations in 150 words or less.

Server: {guild_name}
All-Time Revenue: {total_revenue:,}₮
Last 7 Days Revenue: {weekly_revenue:,}₮
Available Balance: {available_balance:,}₮
Bot Subscription: {subscription_status}
Active Role Plans: {plan_count}

Focus on:
1. Revenue trends (growth/decline)
2. Bot subscription status
3. Actionable improvements

Use emojis and be encouraging. Keep it brief and practical."""

        try:
            # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
            # do not change this unless explicitly requested by the user
            response = self.openai.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": "You are a helpful business advisor specializing in Discord server monetization. Be concise, encouraging, and actionable."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=300
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            print(f"❌ OpenAI API error: {e}")
            # Fallback advice if AI fails
            if weekly_revenue == 0:
                return "💡 No revenue this week. Try promoting your roles more actively and consider adding new perks to attract members!"
            elif weekly_revenue > total_revenue * 0.5:
                return "🔥 Amazing week! Your revenue is growing fast. Keep up the great work and consider expanding your offerings!"
            else:
                return "📈 Steady progress! Focus on member retention and consider surveying your community to understand what they value most."
    
    @weekly_report.before_loop
    async def before_report(self):
        await self.bot.wait_until_ready()
    
    @discord.app_commands.command(name="testreport", description="[OWNER] Test weekly report immediately")
    async def test_report_cmd(self, interaction: discord.Interaction):
        """Test the weekly report feature immediately (owner only)"""
        owner_id = os.environ.get("OWNER_DISCORD_ID")
        if str(interaction.user.id) != owner_id:
            await interaction.response.send_message("❌ This command is owner-only.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        if not interaction.guild:
            await interaction.followup.send("❌ Use this in a server to test the report.", ephemeral=True)
            return
        
        try:
            await self.send_weekly_report(interaction.guild)
            await interaction.followup.send(
                f"✅ Test report sent to all admins in **{interaction.guild.name}**!\n\n"
                f"Check your DMs to see the weekly report with AI-powered advice.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Error sending report: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(WeeklyReportsCog(bot))
