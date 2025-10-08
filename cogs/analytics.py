import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import os
from openai import OpenAI

class AnalyticsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.openai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    async def get_comprehensive_ai_advice(self, guild_name: str, analytics_data: dict) -> str:
        """Generate comprehensive AI advice using ALL server data"""
        
        # Build detailed prompt with all data
        prompt = f"""You are an expert business advisor for Discord server monetization. Analyze this comprehensive data and provide 3-4 specific, actionable recommendations.

SERVER: {guild_name}

📊 REVENUE METRICS:
- All-Time Total: {analytics_data['total_revenue']:,}₮
- Last 30 Days: {analytics_data['last_30_days']:,}₮
- Previous 30 Days: {analytics_data['prev_30_days']:,}₮
- Available Balance: {analytics_data['available_balance']:,}₮
- Growth: {analytics_data['growth_text']}

👥 MEMBERSHIP:
- Active Members: {analytics_data['active_members']}
- Active Plans: {analytics_data['plan_count']}

🎯 TOP PERFORMING PLANS:
{analytics_data['top_plans_text']}

🤖 BOT STATUS:
- Subscription: {analytics_data['subscription_status']}

Based on this data, provide:
1. Revenue trend analysis (what's working/not working)
2. Specific pricing/marketing recommendations
3. Member retention strategies
4. Growth opportunities

Be specific, actionable, and encouraging. Use emojis. Keep under 400 words."""

        try:
            print(f"🤖 Calling OpenAI API for {guild_name}...")
            # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
            # do not change this unless explicitly requested by the user
            response = self.openai.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": "You are an expert business advisor specializing in Discord server monetization and revenue optimization. Provide data-driven, actionable advice."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=500
            )
            
            # Debug the full response
            print(f"📋 Full OpenAI response: {response}")
            print(f"📋 Message object: {response.choices[0].message}")
            
            content = response.choices[0].message.content
            print(f"📋 Raw content: {repr(content)}")
            
            if content:
                advice = content.strip()
                print(f"✅ OpenAI returned {len(advice)} characters of advice")
                return advice
            else:
                print(f"⚠️ OpenAI returned empty/None content")
                return "AI response was empty. Please try again."
        
        except Exception as e:
            print(f"❌ OpenAI API error: {e}")
            import traceback
            traceback.print_exc()
            # Fallback advice
            if analytics_data['growth_percent'] and analytics_data['growth_percent'] > 20:
                return "🔥 **Strong Growth!** Your revenue is trending up significantly. Focus on:\n• Maintaining current marketing efforts\n• Adding premium tiers for top spenders\n• Engaging with new members to improve retention"
            elif analytics_data['growth_percent'] and analytics_data['growth_percent'] < -10:
                return "📉 **Revenue Declining.** Take action:\n• Survey members to understand why they're not renewing\n• Consider price adjustments or new perks\n• Promote your best-performing plan more actively"
            else:
                return "📊 **Steady Performance.** Recommendations:\n• Analyze your top-performing plan and create similar offers\n• Engage inactive members with special promotions\n• Track which perks members value most"

    @app_commands.command(name="growth", description="📈 View your server's revenue growth and analytics with AI advice")
    @app_commands.checks.has_permissions(administrator=True)
    async def growth_cmd(self, interaction: discord.Interaction):
        from database import (
            has_active_subscription, get_revenue_by_day, 
            get_role_revenue_breakdown, get_growth_stats,
            total_guild_revenue, available_to_collect, get_subscription, list_role_plans
        )
        from utils.charts import generate_revenue_growth_chart, generate_role_breakdown_chart
        
        if not interaction.guild:
            await interaction.response.send_message("❌ This must be used in a server.", ephemeral=True)
            return
        
        if not has_active_subscription(str(interaction.guild.id)):
            await interaction.response.send_message(
                "❌ Your bot subscription has expired. Run `/setup` to renew.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        guild_id = str(interaction.guild.id)
        
        growth_stats = get_growth_stats(guild_id)
        daily_revenue = get_revenue_by_day(guild_id, days=30)
        role_breakdown = get_role_revenue_breakdown(guild_id)
        
        total_revenue = total_guild_revenue(guild_id)
        available = available_to_collect(guild_id)
        subscription = get_subscription(guild_id)
        plans = list_role_plans(guild_id, only_active=True)
        
        embed = discord.Embed(
            title="📈 Growth Analytics Dashboard",
            description=f"Revenue insights for **{interaction.guild.name}**",
            color=0x2ecc71,
            timestamp=datetime.utcnow()
        )
        
        growth_percent = growth_stats['growth_percent']
        
        if growth_percent is None:
            growth_emoji = "🚀"
            growth_text = "**New Growth!**"
        elif growth_percent > 0:
            growth_emoji = "📈"
            growth_text = f"**+{growth_percent:.1f}%**"
        elif growth_percent < 0:
            growth_emoji = "📉"
            growth_text = f"**{growth_percent:.1f}%**"
        else:
            growth_emoji = "➖"
            growth_text = "**No Change**"
        
        embed.add_field(
            name="💰 Total Revenue",
            value=f"**{total_revenue:,}₮**\n_All-time earnings_",
            inline=True
        )
        
        embed.add_field(
            name="💵 Available to Collect",
            value=f"**{available:,}₮**\n_After 3% fee_",
            inline=True
        )
        
        embed.add_field(
            name="👥 Active Members",
            value=f"**{growth_stats['active_members']}**\n_Current subscribers_",
            inline=True
        )
        
        embed.add_field(
            name=f"{growth_emoji} 30-Day Growth",
            value=f"{growth_text}\n"
                  f"Last 30d: {growth_stats['last_30_days']:,}₮\n"
                  f"Previous 30d: {growth_stats['prev_30_days']:,}₮",
            inline=False
        )
        
        if role_breakdown:
            top_role = role_breakdown[0]
            role_revenue_text = "\n".join([
                f"**{i+1}.** {name} — {revenue:,}₮ ({count} payments)"
                for i, (name, revenue, count) in enumerate(role_breakdown[:5])
            ])
            
            embed.add_field(
                name="🎯 Top Role Plans",
                value=role_revenue_text or "_No data yet_",
                inline=False
            )
        
        # Prepare data for AI analysis
        top_plans_text = "\n".join([
            f"{i+1}. {name}: {revenue:,}₮ ({count} payments)"
            for i, (name, revenue, count) in enumerate(role_breakdown[:5])
        ]) if role_breakdown else "No data yet"
        
        analytics_data = {
            'total_revenue': total_revenue,
            'last_30_days': growth_stats['last_30_days'],
            'prev_30_days': growth_stats['prev_30_days'],
            'available_balance': available,
            'growth_percent': growth_percent,
            'growth_text': growth_text,
            'active_members': growth_stats['active_members'],
            'plan_count': len(plans) if plans else 0,
            'top_plans_text': top_plans_text,
            'subscription_status': 'Active' if subscription and subscription[3] == 'active' else 'Inactive or Expired'
        }
        
        # Get AI advice
        ai_advice = await self.get_comprehensive_ai_advice(interaction.guild.name, analytics_data)
        
        # Ensure advice exists and fits Discord's 1024 char limit for embed fields
        if not ai_advice or ai_advice.strip() == "":
            ai_advice = "📊 Enable AI recommendations by ensuring OpenAI API is configured properly."
        elif len(ai_advice) > 1024:
            ai_advice = ai_advice[:1020] + "..."
        
        # Add AI advice to embed
        embed.add_field(
            name="🤖 AI-Powered Growth Recommendations",
            value=ai_advice,
            inline=False
        )
        
        embed.set_footer(text=f"Data as of {datetime.utcnow().strftime('%B %d, %Y')} • Powered by ChatGPT")
        
        files = []
        
        if daily_revenue and len(daily_revenue) > 0:
            growth_chart_url = generate_revenue_growth_chart(daily_revenue)
            if growth_chart_url:
                embed.set_image(url=growth_chart_url)
        
        if role_breakdown and len(role_breakdown) > 1:
            pie_chart_url = generate_role_breakdown_chart(role_breakdown)
            if pie_chart_url:
                pie_embed = discord.Embed(
                    title="🎯 Revenue Distribution by Role",
                    color=0x3498db
                )
                pie_embed.set_image(url=pie_chart_url)
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                await interaction.followup.send(embed=pie_embed, ephemeral=True)
                return
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @growth_cmd.error
    async def growth_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You need Administrator permission to view analytics.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(AnalyticsCog(bot))
