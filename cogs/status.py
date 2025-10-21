
import os
import discord
from discord import app_commands
from discord.ext import commands
from database import (has_active_subscription, total_guild_revenue, count_active_members, 
                     available_to_collect, get_plans_breakdown, create_payout_record, mark_payout_done, get_payout, get_subscription)

# Get owner Discord ID from environment variable
OWNER_DISCORD_ID = int(os.getenv("OWNER_DISCORD_ID", "0"))

class CollectButton(discord.ui.Button):
    def __init__(self, net_mnt: int):
        super().__init__(label=f"📤 Collect {net_mnt:,}₮", style=discord.ButtonStyle.success)
        self.net_mnt = net_mnt

    async def callback(self, interaction: discord.Interaction):
        if self.net_mnt <= 0:
            await interaction.response.send_message("❌ No money available to collect.", ephemeral=True)
            return
        
        # Check minimum collection amount
        MIN_COLLECT = 100000
        if self.net_mnt < MIN_COLLECT:
            await interaction.response.send_message(
                f"⚠️ **Minimum collection amount is {MIN_COLLECT:,}₮**\n\n"
                f"Your current balance: **{self.net_mnt:,}₮**\n"
                f"You need **{MIN_COLLECT - self.net_mnt:,}₮** more to collect.\n\n"
                f"💡 Keep earning! You can collect once you reach {MIN_COLLECT:,}₮ or above.",
                ephemeral=True
            )
            return
        
        # Show modal for bank details
        await interaction.response.send_modal(CollectModal(self.net_mnt))


class CollectModal(discord.ui.Modal, title="Bank Account for Payout"):
    account_number = discord.ui.TextInput(label="Bank Account / IBAN", required=True, max_length=50)
    account_name = discord.ui.TextInput(label="Account Holder Name", required=True, max_length=100)
    note = discord.ui.TextInput(label="Bank Name or Note (optional)", required=False, max_length=200)

    def __init__(self, net_mnt: int):
        super().__init__()
        self.net_mnt = net_mnt

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ This must be used in a server.", ephemeral=True)
            return
            
        guild = interaction.guild
        admin = interaction.user

        # Calculate actual amounts from fresh data
        # Net is what's available to collect NOW (after previous payouts)
        net = available_to_collect(str(guild.id))
        
        # Back-calculate gross from net (net = gross - 3% fees)
        # If net is 97% of gross, then gross = net / 0.97
        gross = int(net / 0.97)
        
        # Calculate fees: QPay 1% + Service 2% = 3% total
        qpay_fee = int(gross * 0.01)
        service_fee = int(gross * 0.02)
        fee = qpay_fee + service_fee

        # Get actual values from TextInput fields
        account_num = self.account_number.value
        account_holder = self.account_name.value
        note_text = self.note.value or ""

        # Save payout in DB
        payout_id = create_payout_record(
            str(guild.id),
            gross_mnt=gross,
            fee_mnt=fee,
            net_mnt=net,
            account_number=account_num,
            account_name=account_holder,
            note=note_text
        )

        # Get plans breakdown for the report
        plans = get_plans_breakdown(str(guild.id))
        plans_text = "\n".join([f"- {name}: {members} members = {revenue:,}₮" for name, members, revenue in plans])

        # ✅ Send owner (you) a private notification
        try:
            owner = interaction.client.get_user(OWNER_DISCORD_ID)
            if owner:
                embed = discord.Embed(
                    title="💵 New Payout Request",
                    description=(
                        f"**Guild:** {guild.name} ({guild.id})\n"
                        f"**Admin:** {admin.mention} ({admin.id})\n\n"
                        f"**Gross Revenue:** {gross:,}₮\n"
                        f"**Fee (3%):** {fee:,}₮\n"
                        f"**Net Payout:** {net:,}₮\n\n"
                        f"🏦 **Bank Account:** {account_num}\n"
                        f"👤 **Holder:** {account_holder}\n"
                        f"📝 **Note:** {note_text or 'None'}\n\n"
                        f"📦 **Plans Breakdown:**\n{plans_text}"
                    ),
                    color=0xf1c40f
                )
                view = discord.ui.View(timeout=None)
                if payout_id:
                    view.add_item(DoneButton(payout_id))
                await owner.send(embed=embed, view=view)
        except Exception as e:
            print(f"Failed to notify owner: {e}")

        await interaction.response.send_message(
            f"✅ Payout request submitted. You will receive **{net:,}₮** soon.",
            ephemeral=True
        )


class DoneButton(discord.ui.Button):
    def __init__(self, payout_id: int):
        super().__init__(label="✅ Mark as Done", style=discord.ButtonStyle.primary)
        self.payout_id = payout_id

    async def callback(self, interaction: discord.Interaction):
        # Get payout details
        payout = get_payout(self.payout_id)
        if not payout:
            await interaction.response.send_message("❌ Payout not found.", ephemeral=True)
            return
        
        # Mark as done in database
        mark_payout_done(self.payout_id)
        
        # Get guild and admin information
        guild = interaction.client.get_guild(int(payout['guild_id']))
        if not guild:
            await interaction.response.send_message("✅ Marked as paid. (Guild not found for notifications)", ephemeral=True)
            return
        
        # Format date/time
        from datetime import datetime
        created_time = datetime.fromisoformat(payout['created_at']).strftime("%Y-%m-%d %H:%M:%S UTC")
        completed_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Find admin - check guild members for who has administrator permission
        admin = None
        
        # === 1. Send DM to Admin (Confirmation) ===
        try:
            for member in guild.members:
                if member.guild_permissions.administrator:
                    admin = member
                    break
            
            if admin:
                admin_embed = discord.Embed(
                    title="✅ Payout Completed!",
                    description=f"Your collection request has been approved and money has been sent!",
                    color=0x2ecc71,
                    timestamp=discord.utils.utcnow()
                )
                
                admin_embed.add_field(
                    name="💰 Amount Collected",
                    value=f"**{payout['net_mnt']:,}₮**",
                    inline=True
                )
                
                admin_embed.add_field(
                    name="🏦 Bank Account",
                    value=f"{payout['account_number']}\n{payout['account_name']}",
                    inline=True
                )
                
                admin_embed.add_field(
                    name="📅 Requested On",
                    value=created_time,
                    inline=True
                )
                
                admin_embed.add_field(
                    name="✅ Completed On",
                    value=completed_time,
                    inline=True
                )
                
                admin_embed.add_field(
                    name="📊 Revenue Breakdown",
                    value=f"Gross Revenue: {payout['gross_mnt']:,}₮\n"
                          f"Service Fee (3%): -{payout['fee_mnt']:,}₮\n"
                          f"**Net Received: {payout['net_mnt']:,}₮**",
                    inline=False
                )
                
                if payout['note']:
                    admin_embed.add_field(
                        name="📝 Note",
                        value=payout['note'],
                        inline=False
                    )
                
                admin_embed.set_footer(text=f"Server: {guild.name} | Payout ID: {payout['id']}")
                
                await admin.send(embed=admin_embed)
        except Exception as e:
            print(f"Failed to send admin confirmation DM: {e}")
        
        # === 2. Send DM to Owner (Checkpoint Record) ===
        try:
            owner = interaction.client.get_user(OWNER_DISCORD_ID)
            if owner:
                checkpoint_embed = discord.Embed(
                    title="📋 Payout Checkpoint - Transaction Complete",
                    description=f"**Permanent record of completed payout**\n"
                                f"Use this to verify your bank balance and bot analytics.",
                    color=0x3498db,
                    timestamp=discord.utils.utcnow()
                )
                
                checkpoint_embed.add_field(
                    name="🏢 Server",
                    value=f"**{guild.name}**\n`{guild.id}`",
                    inline=True
                )
                
                checkpoint_embed.add_field(
                    name="👤 Admin",
                    value=f"{admin.mention if admin else 'Unknown'}\n`{admin.id if admin else 'N/A'}`",
                    inline=True
                )
                
                checkpoint_embed.add_field(
                    name="💸 Amount Sent",
                    value=f"**{payout['net_mnt']:,}₮**",
                    inline=True
                )
                
                checkpoint_embed.add_field(
                    name="🏦 Bank Details",
                    value=f"**Account:** {payout['account_number']}\n"
                          f"**Holder:** {payout['account_name']}\n"
                          f"**Note:** {payout['note'] or 'None'}",
                    inline=False
                )
                
                checkpoint_embed.add_field(
                    name="📊 Transaction Details",
                    value=f"**Gross Revenue:** {payout['gross_mnt']:,}₮\n"
                          f"**Fee Deducted (3%):** {payout['fee_mnt']:,}₮\n"
                          f"**Net Paid Out:** {payout['net_mnt']:,}₮",
                    inline=False
                )
                
                checkpoint_embed.add_field(
                    name="📅 Timeline",
                    value=f"**Requested:** {created_time}\n"
                          f"**Completed:** {completed_time}",
                    inline=False
                )
                
                checkpoint_embed.set_footer(
                    text=f"🔐 Checkpoint ID: {payout['id']} | Keep this message for records and proof"
                )
                
                await owner.send(embed=checkpoint_embed)
        except Exception as e:
            print(f"Failed to send owner checkpoint DM: {e}")
        
        # Respond to interaction
        await interaction.response.send_message(
            f"✅ **Payout marked as completed!**\n\n"
            f"✉️ Confirmation sent to admin\n"
            f"📋 Checkpoint record saved to your DMs",
            ephemeral=True
        )


class StatusCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="status", description="Show detailed financial dashboard")
    @app_commands.checks.has_permissions(administrator=True)
    async def status_cmd(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ This must be used in a server.", ephemeral=True)
            return
            
        # ✅ Check if server has active subscription
        if not has_active_subscription(str(interaction.guild.id)):
            await interaction.response.send_message(
                "❌ Your bot subscription has expired or not paid. Run `/setup` to renew.",
                ephemeral=True
            )
            return
            
        gid = str(interaction.guild.id)
        
        # Get financial data
        total_revenue = total_guild_revenue(gid)
        available = available_to_collect(gid)
        active_members = count_active_members(gid)
        plans = get_plans_breakdown(gid)
        
        # Get subscription info for expiry date
        subscription = get_subscription(gid)

        # Build embed
        embed = discord.Embed(title="📊 Server Finance Dashboard", color=0x2ecc71)
        
        embed.add_field(
            name="💰 Total Revenue (All Time)",
            value=f"**{total_revenue:,}₮**\n> Available to collect: **{available:,}₮**",
            inline=False
        )
        
        embed.add_field(
            name="👥 Active Members (All Plans)",
            value=f"**{active_members} Active Members**",
            inline=True
        )

        # Plans breakdown
        if plans:
            plans_text = "\n".join([f"**{name}:** {members} members = {revenue:,}₮" for name, members, revenue in plans])
            embed.add_field(
                name="📦 Plans Breakdown",
                value=plans_text,
                inline=False
            )

        # Calculate correct "Available to Collect" breakdown
        # available is the net amount (after fee and previous payouts)
        # Back-calculate gross: if net = gross * 0.97, then gross = net / 0.97
        if available > 0:
            gross_available = int(available / 0.97)
            fee_on_available = gross_available - available
        else:
            gross_available = 0
            fee_on_available = 0
        
        MIN_COLLECT = 100000
        
        collect_status = ""
        if available < MIN_COLLECT:
            collect_status = f"\n⚠️ _Minimum {MIN_COLLECT:,}₮ required to collect_"
        else:
            collect_status = "\n✅ _Ready to collect!_"
        
        embed.add_field(
            name="💵 Available to Collect",
            value=f"Gross: {gross_available:,}₮\nFee (3%): -{fee_on_available:,}₮\n**Net: {available:,}₮**{collect_status}",
            inline=False
        )
        
        # Add bot subscription expiry info
        if subscription:
            plan_name, amount_mnt, expires_at, status = subscription
            from datetime import datetime
            try:
                expiry_date = datetime.fromisoformat(expires_at)
                days_left = (expiry_date - datetime.utcnow()).days
                
                if days_left < 0:
                    sub_status = "🔴 **Expired!**"
                elif days_left <= 3:
                    sub_status = f"🟡 **{days_left} days left** (Renew soon!)"
                elif days_left <= 7:
                    sub_status = f"🟡 **{days_left} days left**"
                else:
                    sub_status = f"🟢 **{days_left} days left**"
                
                embed.add_field(
                    name="🤖 Bot Subscription",
                    value=f"**Plan:** {plan_name}\n**Expires:** {expires_at[:10]}\n{sub_status}",
                    inline=False
                )
            except:
                embed.add_field(
                    name="🤖 Bot Subscription",
                    value=f"**Plan:** {plan_name}\n**Expires:** {expires_at[:10]}",
                    inline=False
                )

        embed.set_footer(text="💡 3% service fee deducted | Minimum 100,000₮ to collect")

        # Add collect button if there's money to collect
        view = discord.ui.View(timeout=300)
        if available > 0:
            view.add_item(CollectButton(available))

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @status_cmd.error
    async def status_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You need Administrator permission to view financial dashboard and collect money.",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(StatusCog(bot))
