import discord
from discord import app_commands
from discord.ext import commands
import os
from database import _conn

class OwnerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="analytics", description="[OWNER ONLY] View comprehensive bot analytics")
    async def analytics_cmd(self, interaction: discord.Interaction):
        owner_id = int(os.getenv("OWNER_DISCORD_ID", "0"))
        
        # Check if user is owner
        if owner_id == 0 or interaction.user.id != owner_id:
            # Check if in DM or guild
            is_dm = interaction.guild is None
            await interaction.response.send_message("❌ This command is owner-only.", ephemeral=not is_dm)
            return
        
        # In DMs, don't use ephemeral
        is_dm = interaction.guild is None
        await interaction.response.defer(ephemeral=not is_dm)
        
        # Get all analytics data
        conn = _conn()
        c = conn.cursor()
        
        # === SERVERS & SUBSCRIPTIONS ===
        c.execute("SELECT COUNT(DISTINCT guild_id) FROM subscriptions")
        total_servers = c.fetchone()[0] or 0
        
        c.execute("SELECT COUNT(*) FROM subscriptions WHERE status='active'")
        active_subs = c.fetchone()[0] or 0
        
        c.execute("SELECT COUNT(*) FROM subscriptions WHERE status='expired'")
        expired_subs = c.fetchone()[0] or 0
        
        c.execute("SELECT COUNT(*) FROM subscriptions WHERE status='pending'")
        pending_subs = c.fetchone()[0] or 0
        
        # Subscription revenue
        c.execute("SELECT COALESCE(SUM(amount_mnt), 0) FROM subscriptions WHERE status='active'")
        subscription_revenue = c.fetchone()[0] or 0
        
        # === ROLE PLANS ===
        c.execute("SELECT COUNT(*) FROM role_plans")
        total_plans = c.fetchone()[0] or 0
        
        c.execute("SELECT COUNT(*) FROM role_plans WHERE active=1")
        active_plans = c.fetchone()[0] or 0
        
        # === MEMBERSHIPS ===
        c.execute("SELECT COUNT(*) FROM memberships WHERE active=1")
        active_memberships = c.fetchone()[0] or 0
        
        c.execute("SELECT COUNT(DISTINCT user_id) FROM memberships WHERE active=1")
        unique_members = c.fetchone()[0] or 0
        
        # === PAYMENTS & REVENUE ===
        c.execute("SELECT COUNT(*) FROM payments WHERE status='paid'")
        total_payments = c.fetchone()[0] or 0
        
        c.execute("SELECT COALESCE(SUM(amount_mnt), 0) FROM payments WHERE status='paid'")
        total_role_revenue = c.fetchone()[0] or 0
        
        # === MONEY FLOW ===
        # Total revenue from role sales
        gross_revenue = int(total_role_revenue)
        
        # QPay takes 1% from every transaction
        qpay_fee = int(gross_revenue * 0.01)
        
        # You take 2% from every transaction
        service_fee = int(gross_revenue * 0.02)
        
        # Net revenue for admins (gross - 1% QPay - 2% service fee = 97%)
        net_revenue = gross_revenue - qpay_fee - service_fee
        
        # Calculate total collected from completed payouts
        c.execute("SELECT COALESCE(SUM(net_mnt), 0) FROM payouts WHERE status='done'")
        total_collected = c.fetchone()[0] or 0
        
        # Pending = net revenue - collected
        total_pending = net_revenue - total_collected
        
        # Count number of actual completed payouts for bank transfer fee calculation
        # Each payout request (each /collect command) costs 200₮ in bank transfer fees
        c.execute("SELECT COUNT(*) FROM payouts WHERE status='done'")
        completed_payouts = c.fetchone()[0] or 0
        
        # Bank transfer fees (200₮ per payout transaction)
        bank_transfer_fees = completed_payouts * 200
        
        # === TOP PERFORMING SERVERS ===
        c.execute("""SELECT s.guild_id, s.plan_name, 
                            COALESCE(SUM(p.amount_mnt), 0) as revenue
                     FROM subscriptions s
                     LEFT JOIN payments p ON s.guild_id = p.guild_id AND p.status='paid'
                     WHERE s.status='active'
                     GROUP BY s.guild_id
                     ORDER BY revenue DESC
                     LIMIT 5""")
        top_servers = c.fetchall()
        
        conn.close()
        
        # === CREATE EMBEDS ===
        embeds = []
        
        # Embed 1: Overview
        embed1 = discord.Embed(
            title="📊 Bot Analytics Dashboard",
            description="Complete business overview and metrics",
            color=0x2ecc71,
            timestamp=discord.utils.utcnow()
        )
        
        embed1.add_field(
            name="🏢 Servers",
            value=f"**Total:** {total_servers}\n"
                  f"**Active Subs:** {active_subs} 🟢\n"
                  f"**Expired:** {expired_subs} 🔴\n"
                  f"**Pending:** {pending_subs} 🟡",
            inline=True
        )
        
        embed1.add_field(
            name="📦 Role Plans",
            value=f"**Total Plans:** {total_plans}\n"
                  f"**Active:** {active_plans}\n"
                  f"**Inactive:** {total_plans - active_plans}",
            inline=True
        )
        
        embed1.add_field(
            name="👥 Memberships",
            value=f"**Active:** {active_memberships}\n"
                  f"**Unique Users:** {unique_members}\n"
                  f"**Avg/User:** {round(active_memberships/unique_members, 1) if unique_members > 0 else 0}",
            inline=True
        )
        
        embeds.append(embed1)
        
        # Embed 2: Money Flow
        embed2 = discord.Embed(
            title="💰 Complete Money Flow",
            description="Detailed revenue breakdown with all fees",
            color=0x3498db
        )
        
        embed2.add_field(
            name="📥 Revenue Sources",
            value=f"**Bot Subscriptions:** {subscription_revenue:,}₮\n"
                  f"**Role Sales (Gross):** {gross_revenue:,}₮\n"
                  f"**Total Gross:** {subscription_revenue + gross_revenue:,}₮",
            inline=False
        )
        
        embed2.add_field(
            name="💵 Role Sales Breakdown",
            value=f"**Gross Revenue:** {gross_revenue:,}₮\n"
                  f"**QPay Fee (1%):** -{qpay_fee:,}₮\n"
                  f"**Your Service Fee (2%):** -{service_fee:,}₮\n"
                  f"**Total Fees (3%):** -{qpay_fee + service_fee:,}₮\n"
                  f"**Net (Admins Get 97%):** {net_revenue:,}₮",
            inline=False
        )
        
        embed2.add_field(
            name="📤 Payout Status",
            value=f"**Collected (Paid Out):** {total_collected:,}₮\n"
                  f"**Pending Requests:** {total_pending:,}₮\n"
                  f"**Total Payments:** {total_payments}\n"
                  f"**Completed Payouts:** {completed_payouts}",
            inline=False
        )
        
        embed2.add_field(
            name="🏦 Your Costs & Earnings",
            value=f"**Income:**\n"
                  f"  • Subscriptions: {subscription_revenue:,}₮\n"
                  f"  • Service Fees (2%): {service_fee:,}₮\n"
                  f"**Costs:**\n"
                  f"  • Bank Transfers (200₮×{completed_payouts}): -{bank_transfer_fees:,}₮\n"
                  f"**Net Profit:** {subscription_revenue + service_fee - bank_transfer_fees:,}₮",
            inline=False
        )
        
        embeds.append(embed2)
        
        # Embed 3: Top Servers
        embed3 = discord.Embed(
            title="🏆 Top Performing Servers",
            description="Servers generating the most revenue",
            color=0xf39c12
        )
        
        if top_servers:
            for i, (guild_id, plan_name, revenue) in enumerate(top_servers[:5], 1):
                try:
                    guild = self.bot.get_guild(int(guild_id))
                    guild_name = guild.name if guild else f"Server {guild_id[:8]}..."
                except:
                    guild_name = f"Server {guild_id[:8]}..."
                
                embed3.add_field(
                    name=f"#{i} {guild_name}",
                    value=f"Plan: {plan_name}\nRevenue: {int(revenue):,}₮",
                    inline=False
                )
        else:
            embed3.description = "No revenue data yet"
        
        embeds.append(embed3)
        
        # Embed 4: Summary
        embed4 = discord.Embed(
            title="📈 Summary & Key Metrics",
            color=0x9b59b6
        )
        
        embed4.add_field(
            name="💎 Business Health",
            value=f"**Active Servers:** {active_subs}/{total_servers}\n"
                  f"**Conversion Rate:** {round(active_subs/total_servers*100, 1) if total_servers > 0 else 0}%\n"
                  f"**Avg Revenue/Server:** {round((subscription_revenue + gross_revenue)/total_servers) if total_servers > 0 else 0:,}₮",
            inline=True
        )
        
        embed4.add_field(
            name="💰 Financial Overview",
            value=f"**Total In:** {subscription_revenue + gross_revenue:,}₮\n"
                  f"**Paid Out:** {total_collected:,}₮\n"
                  f"**Your Net Profit:** {subscription_revenue + service_fee - bank_transfer_fees:,}₮",
            inline=True
        )
        
        embed4.set_footer(text="🔒 Owner-Only Data • Confidential")
        
        embeds.append(embed4)
        
        # Send all embeds (ephemeral only in guilds, not DMs)
        await interaction.followup.send(embeds=embeds, ephemeral=not is_dm)

    @app_commands.command(name="testrenewal", description="[OWNER ONLY] Test renewal DM flow with a specific plan")
    async def test_renewal_cmd(self, interaction: discord.Interaction, guild_id: str, plan_id: int):
        owner_id = int(os.getenv("OWNER_DISCORD_ID", "0"))
        
        # Check if user is owner
        if owner_id == 0 or interaction.user.id != owner_id:
            await interaction.response.send_message("❌ This command is owner-only.", ephemeral=True)
            return
        
        from database import get_plan
        from cogs.membership import RenewalChoiceView
        
        # Get the plan details
        plan = get_plan(plan_id)
        if not plan:
            await interaction.response.send_message(f"❌ Plan ID {plan_id} not found.", ephemeral=True)
            return
        
        # Get guild name
        guild = self.bot.get_guild(int(guild_id))
        guild_name = guild.name if guild else f"Server {guild_id}"
        
        # Send renewal DM to the owner
        try:
            embed = discord.Embed(
                title="⏰ Your Membership Has Expired! (TEST)",
                description=f"**[TEST MODE]** Testing renewal flow for **{plan['role_name']}** in **{guild_name}**.",
                color=0xe74c3c
            )
            
            # Add plan description if available
            if plan.get('description'):
                embed.add_field(
                    name="✨ What This Role Includes:",
                    value=plan['description'],
                    inline=False
                )
            
            embed.add_field(
                name="💡 Want to Renew?",
                value="Choose an option below to continue:",
                inline=False
            )
            
            # Create renewal choice view with the plan details
            view = RenewalChoiceView(guild_id, guild_name, plan_id, plan['role_name'])
            
            await interaction.user.send(embed=embed, view=view)
            await interaction.response.send_message(
                f"✅ Test renewal DM sent for **{plan['role_name']}** in **{guild_name}**!\nCheck your DMs to test the payment flow.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message("❌ Couldn't send you a DM. Check your privacy settings.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(OwnerCog(bot))
