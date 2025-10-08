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
            list_role_plans,
            get_growth_stats,
            get_role_revenue_breakdown,
            get_revenue_by_day
        )
        from utils.charts import generate_revenue_growth_chart, generate_role_breakdown_chart
        
        guild_id = str(guild.id)
        
        # Get comprehensive server stats (same as /growth command)
        total_revenue = total_guild_revenue(guild_id)
        available_balance = available_to_collect(guild_id)
        subscription = get_subscription(guild_id)
        plans = list_role_plans(guild_id, only_active=True)
        growth_stats = get_growth_stats(guild_id)
        role_breakdown = get_role_revenue_breakdown(guild_id)
        daily_revenue = get_revenue_by_day(guild_id, days=30)
        
        # Prepare growth text
        growth_percent = growth_stats['growth_percent']
        if growth_percent is None:
            growth_text = "New Growth!"
        elif growth_percent > 0:
            growth_text = f"+{growth_percent:.1f}%"
        elif growth_percent < 0:
            growth_text = f"{growth_percent:.1f}%"
        else:
            growth_text = "No Change"
        
        # Prepare top plans text for AI
        top_plans_text = "\n".join([
            f"{i+1}. {name}: {revenue:,}₮ ({count} payments)"
            for i, (name, revenue, count) in enumerate(role_breakdown[:5])
        ]) if role_breakdown else "No data yet"
        
        # Prepare analytics data for AI
        analytics_data = {
            'total_revenue': total_revenue,
            'last_30_days': growth_stats['last_30_days'],
            'prev_30_days': growth_stats['prev_30_days'],
            'available_balance': available_balance,
            'growth_percent': growth_percent,
            'growth_text': growth_text,
            'active_members': growth_stats['active_members'],
            'plan_count': len(plans) if plans else 0,
            'top_plans_text': top_plans_text,
            'subscription_status': 'Active' if subscription and subscription[3] == 'active' else 'Inactive or Expired'
        }
        
        # Get comprehensive AI advice using same function as /growth
        from cogs.analytics import AnalyticsCog
        analytics_cog = self.bot.get_cog('AnalyticsCog')
        if analytics_cog:
            advice = await analytics_cog.get_comprehensive_ai_advice(guild.name, analytics_data)
        else:
            advice = "Enable analytics for AI-powered recommendations!"
        
        # Create comprehensive report embed (same structure as /growth command)
        embed = discord.Embed(
            title="📊 Weekly Performance Report",
            description=f"**Server:** {guild.name}\n"
                       f"**Date:** {datetime.utcnow().strftime('%B %d, %Y')}\n\n"
                       f"Your automated weekly analytics with AI-powered growth strategy!",
            color=0x2ecc71,
            timestamp=datetime.utcnow()
        )
        
        # Growth emoji based on performance
        if growth_percent is None:
            growth_emoji = "🚀"
        elif growth_percent > 0:
            growth_emoji = "📈"
        elif growth_percent < 0:
            growth_emoji = "📉"
        else:
            growth_emoji = "➖"
        
        # Revenue metrics (same as /growth)
        embed.add_field(
            name="💰 Total Revenue",
            value=f"**{total_revenue:,}₮**\n_All-time earnings_",
            inline=True
        )
        
        embed.add_field(
            name="💵 Available to Collect",
            value=f"**{available_balance:,}₮**\n_After 3% fee_",
            inline=True
        )
        
        embed.add_field(
            name="👥 Active Members",
            value=f"**{growth_stats['active_members']}**\n_Current subscribers_",
            inline=True
        )
        
        embed.add_field(
            name=f"{growth_emoji} 30-Day Growth",
            value=f"**{growth_text}**\n"
                  f"Last 30d: {growth_stats['last_30_days']:,}₮\n"
                  f"Previous 30d: {growth_stats['prev_30_days']:,}₮",
            inline=False
        )
        
        # Top performing plans
        if role_breakdown:
            role_revenue_text = "\n".join([
                f"**{i+1}.** {name} — {revenue:,}₮ ({count} payments)"
                for i, (name, revenue, count) in enumerate(role_breakdown[:5])
            ])
            
            embed.add_field(
                name="🎯 Top Role Plans",
                value=role_revenue_text or "_No data yet_",
                inline=False
            )
        
        # Subscription status
        if subscription:
            plan_name, amount, expires_at, status = subscription
            embed.add_field(
                name="🤖 Bot Subscription",
                value=f"**Plan:** {plan_name} | **Status:** {'✅ Active' if status == 'active' else '❌ Inactive'}\n"
                      f"**Expires:** {expires_at[:10] if expires_at else 'N/A'}",
                inline=False
            )
        
        # AI-powered recommendations
        embed.add_field(
            name="🤖 AI-Powered Growth Recommendations",
            value=advice,
            inline=False
        )
        
        # Add revenue growth chart (same as /growth)
        if daily_revenue and len(daily_revenue) > 0:
            growth_chart_url = generate_revenue_growth_chart(daily_revenue)
            if growth_chart_url:
                embed.set_image(url=growth_chart_url)
        
        embed.set_footer(text="📅 Sent every Monday at 21:00 UTC • Powered by ChatGPT")
        
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
    
    @weekly_report.before_loop
    async def before_report(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(WeeklyReportsCog(bot))
