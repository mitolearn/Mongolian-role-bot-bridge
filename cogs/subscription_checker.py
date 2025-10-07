import discord
from discord.ext import tasks, commands
from datetime import datetime
from database import (get_all_subscriptions, deactivate_subscription, list_expired, 
                      deactivate_membership, get_plan, get_subscriptions_expiring_soon,
                      available_to_collect, renew_subscription_with_balance, mark_subscription_paid, create_subscription)
from datetime import timedelta

# Store warned guilds to avoid spamming
warned_guilds = set()

class RenewalOptionsView(discord.ui.View):
    def __init__(self, guild_id: str, guild_name: str):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.guild_name = guild_name

    @discord.ui.button(label="💳 Pay with QPay", style=discord.ButtonStyle.success)
    async def qpay_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Show 3 subscription packages
        embed = discord.Embed(
            title="💳 Renew with QPay",
            description="Choose a subscription package:",
            color=0x3498db
        )
        embed.add_field(name="📦 Basic", value="100₮ — 30 days", inline=False)
        embed.add_field(name="📦 Pro", value="200₮ — 180 days (6 months)", inline=False)
        embed.add_field(name="📦 Premium", value="300₮ — 365 days (1 year)", inline=False)
        
        view = SubscriptionPackageView(self.guild_id, self.guild_name)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="💰 Pay with Collected Money", style=discord.ButtonStyle.primary)
    async def balance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check available balance
        available = available_to_collect(self.guild_id)
        
        embed = discord.Embed(
            title="💰 Pay with Collected Money",
            description=f"**Available Balance:** {available:,}₮\n\nChoose a package to deduct from your balance:",
            color=0xf39c12
        )
        embed.add_field(name="📦 Basic", value="100₮ — 30 days", inline=False)
        embed.add_field(name="📦 Pro", value="200₮ — 180 days", inline=False)
        embed.add_field(name="📦 Premium", value="300₮ — 365 days", inline=False)
        
        if available < 100:
            embed.add_field(
                name="⚠️ Insufficient Balance",
                value=f"You need at least 100₮. Current balance: {available:,}₮\n\n"
                      f"Please use **Pay with QPay** instead.",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            view = BalancePaymentView(self.guild_id, self.guild_name, available)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class SubscriptionPackageView(discord.ui.View):
    def __init__(self, guild_id: str, guild_name: str):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.guild_name = guild_name

    async def create_qpay_renewal(self, interaction: discord.Interaction, plan_name: str, amount: int, days: int):
        from utils.qpay import create_qpay_invoice
        from database import get_subscription
        
        await interaction.response.defer(ephemeral=True)
        
        # Create QPay invoice
        invoice_id, qr_text, payment_url = create_qpay_invoice(amount, f"{plan_name} Subscription")
        if not invoice_id:
            await interaction.followup.send("❌ Failed to create QPay invoice.", ephemeral=True)
            return

        # Get existing subscription
        existing = get_subscription(self.guild_id)
        now = datetime.utcnow()
        
        if existing and existing[3] == 'active':
            # Active subscription exists - calculate expiry from existing end date
            existing_expiry = datetime.fromisoformat(existing[2])
            
            # If still valid, extend from expiry date
            if existing_expiry > now:
                expires_at = (existing_expiry + timedelta(days=days)).isoformat()
            else:
                # Expired - start from now
                expires_at = (now + timedelta(days=days)).isoformat()
        else:
            # No active subscription - start from now
            expires_at = (now + timedelta(days=days)).isoformat()
        
        # Save subscription
        create_subscription(self.guild_id, plan_name, amount, invoice_id, expires_at)
        
        # Send payment link
        url = payment_url or f"https://s.qpay.mn/payment/{invoice_id}"
        embed = discord.Embed(
            title="💳 Subscription Renewal Payment",
            description=f"**Plan:** {plan_name}\n**Amount:** {amount}₮\n**Duration:** {days} days\n\n"
                        f"🔗 [Pay with QPay here]({url})\n\n"
                        f"After paying, the system will automatically activate your subscription.",
            color=0x00ff88
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="Basic — 100₮", style=discord.ButtonStyle.success)
    async def basic_qpay(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_qpay_renewal(interaction, "Basic", 100, 30)

    @discord.ui.button(label="Pro — 200₮", style=discord.ButtonStyle.success)
    async def pro_qpay(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_qpay_renewal(interaction, "Pro", 200, 180)

    @discord.ui.button(label="Premium — 300₮", style=discord.ButtonStyle.success)
    async def premium_qpay(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_qpay_renewal(interaction, "Premium", 300, 365)

class BalancePaymentView(discord.ui.View):
    def __init__(self, guild_id: str, guild_name: str, available: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.guild_name = guild_name
        self.available = available

    async def pay_with_balance(self, interaction: discord.Interaction, plan_name: str, amount: int, days: int):
        await interaction.response.defer(ephemeral=True)
        
        success, new_expiry, message = renew_subscription_with_balance(
            self.guild_id, plan_name, days, amount
        )
        
        if success:
            embed = discord.Embed(
                title="✅ Subscription Renewed!",
                description=f"**Plan:** {plan_name}\n"
                            f"**Amount Deducted:** {amount:,}₮\n"
                            f"**New Expiry:** {new_expiry[:10]}\n\n"
                            f"Your bot is now active for {days} days!",
                color=0x2ecc71
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="❌ Payment Failed",
                description=message,
                color=0xe74c3c
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="Basic — 100₮", style=discord.ButtonStyle.primary)
    async def basic_balance(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.pay_with_balance(interaction, "Basic", 100, 30)

    @discord.ui.button(label="Pro — 200₮", style=discord.ButtonStyle.primary)
    async def pro_balance(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.pay_with_balance(interaction, "Pro", 200, 180)

    @discord.ui.button(label="Premium — 300₮", style=discord.ButtonStyle.primary)
    async def premium_balance(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.pay_with_balance(interaction, "Premium", 300, 365)

class SubscriptionChecker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_expiry.start()
        self.check_membership_expiry.start()
        self.warn_expiring_soon.start()

    async def cog_unload(self):
        self.check_expiry.cancel()
        self.check_membership_expiry.cancel()
        self.warn_expiring_soon.cancel()

    @tasks.loop(hours=12)  # check every 12 hours
    async def warn_expiring_soon(self):
        """Warn admins 3 days before subscription expires"""
        expiring = get_subscriptions_expiring_soon(days=3)
        
        for guild_id, plan_name, expires_at, amount in expiring:
            # Skip if already warned recently
            if guild_id in warned_guilds:
                continue
            
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue
            
            # Get all admins
            admins = [m for m in guild.members if m.guild_permissions.administrator and not m.bot]
            
            for admin in admins:
                try:
                    # Calculate days remaining
                    expires_dt = datetime.fromisoformat(expires_at)
                    days_left = (expires_dt - datetime.utcnow()).days
                    
                    available = available_to_collect(guild_id)
                    
                    embed = discord.Embed(
                        title="⚠️ Subscription Expiring Soon!",
                        description=f"Your bot subscription for **{guild.name}** expires in **{days_left} days**!\n\n"
                                    f"**Current Plan:** {plan_name}\n"
                                    f"**Expires:** {expires_at[:10]}\n"
                                    f"**Your Collected Balance:** {available:,}₮",
                        color=0xe74c3c
                    )
                    
                    embed.add_field(
                        name="💡 Renew Now",
                        value="Choose how you want to renew:\n\n"
                              "💳 **Pay with QPay** - Get a fresh payment link\n"
                              "💰 **Pay with Collected Money** - Use your earned balance",
                        inline=False
                    )
                    
                    view = RenewalOptionsView(guild_id, guild.name)
                    await admin.send(embed=embed, view=view)
                    print(f"📨 Sent renewal warning to {admin.name} for {guild.name}")
                except Exception as e:
                    print(f"❌ Failed to send renewal warning: {e}")
            
            # Mark as warned
            warned_guilds.add(guild_id)

    @tasks.loop(hours=1)  # check every 1 hour
    async def check_expiry(self):
        now = datetime.utcnow().isoformat()
        subs = get_all_subscriptions()

        for sub in subs:
            guild_id, expires_at = sub
            if expires_at < now:  # expired
                deactivate_subscription(guild_id)
                
                # Remove from warned set
                warned_guilds.discard(guild_id)

                guild = self.bot.get_guild(int(guild_id))
                if guild:
                    # Message all admins
                    admins = [m for m in guild.members if m.guild_permissions.administrator and not m.bot]
                    for admin in admins:
                        try:
                            embed = discord.Embed(
                                title="❌ Bot Subscription Expired",
                                description=f"Your bot subscription for **{guild.name}** has expired.\n\n"
                                            f"The bot will no longer work until you renew. Members will see an expiry message when trying to use commands.",
                                color=0xe74c3c
                            )
                            view = RenewalOptionsView(guild_id, guild.name)
                            await admin.send(embed=embed, view=view)
                        except:
                            pass

    @tasks.loop(hours=1)  # check every 1 hour
    async def check_membership_expiry(self):
        # Get all guilds the bot is in
        for guild in self.bot.guilds:
            expired = list_expired(str(guild.id))
            
            for user_id, plan_id in expired:
                # Get plan details
                plan = get_plan(plan_id)
                if not plan:
                    continue
                
                # Get member and role
                member = guild.get_member(int(user_id))
                role = guild.get_role(int(plan["role_id"]))
                
                # Remove role if member and role exist
                if member and role:
                    try:
                        await member.remove_roles(role, reason="Membership expired")
                        print(f"🔴 Removed role {role.name} from {member.name} in {guild.name} (expired)")
                    except Exception as e:
                        print(f"❌ Failed to remove role: {e}")
                    
                    # Send DM notification
                    try:
                        await member.send(
                            f"⏰ **Membership Expired**\n\n"
                            f"Your **{plan['role_name']}** membership in **{guild.name}** has expired.\n\n"
                            f"To continue enjoying the benefits, please purchase a new membership! 💫"
                        )
                        print(f"📨 Sent expiry DM to {member.name}")
                    except Exception as e:
                        print(f"❌ Could not DM {member.name}: {e}")
                
                # Deactivate membership in database
                deactivate_membership(str(guild.id), str(user_id))

    @warn_expiring_soon.before_loop
    async def before_warn_expiring(self):
        await self.bot.wait_until_ready()

    @check_expiry.before_loop
    async def before_check_expiry(self):
        await self.bot.wait_until_ready()

    @check_membership_expiry.before_loop
    async def before_check_membership_expiry(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(SubscriptionChecker(bot))