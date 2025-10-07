import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

class AnalyticsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="growth", description="📈 View your server's revenue growth and analytics")
    @app_commands.checks.has_permissions(administrator=True)
    async def growth_cmd(self, interaction: discord.Interaction):
        from database import (
            has_active_subscription, get_revenue_by_day, 
            get_role_revenue_breakdown, get_growth_stats,
            total_guild_revenue, available_to_collect
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
        
        embed.set_footer(text=f"Data as of {datetime.utcnow().strftime('%B %d, %Y')}")
        
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
