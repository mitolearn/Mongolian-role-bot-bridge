import discord
from discord import app_commands
from discord.ext import commands, tasks
from database import list_expired, get_plan, deactivate_membership, get_user_active_membership, create_payment, list_role_plans
from datetime import datetime, timedelta
from utils.qpay import create_qpay_invoice

class RenewalChoiceView(discord.ui.View):
    """View with two buttons: Renew Same Plan or See Other Plans"""
    def __init__(self, guild_id: str, guild_name: str, plan_id: int, plan_name: str):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.guild_name = guild_name
        self.plan_id = plan_id
        self.plan_name = plan_name
    
    @discord.ui.button(label="🔄 Renew Same Plan", style=discord.ButtonStyle.success)
    async def renew_same_plan(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Renew the same plan - triggers payment flow"""
        from cogs.payment import PayPlanButton
        
        # Trigger the same flow as clicking a plan in paywall
        plan_button = PayPlanButton(self.plan_id, f"{self.plan_name}")
        await plan_button.callback(interaction)
    
    @discord.ui.button(label="🛍️ See Other Plans", style=discord.ButtonStyle.primary)
    async def see_other_plans(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show all available plans in DM (like paywall but in DM)"""
        await interaction.response.defer(ephemeral=True)
        
        # Get all active plans
        plans = list_role_plans(self.guild_id, only_active=True)
        if not plans:
            await interaction.followup.send("❌ No plans available right now.", ephemeral=True)
            return
        
        # Create paywall-style embed
        embed = discord.Embed(
            title=f"🔑 Available Plans in {self.guild_name}",
            description="Choose any plan below to unlock exclusive perks!",
            color=0x2ecc71
        )
        
        # Add plan details
        for pid, role_id, role_name, price, days, active, description in plans:
            desc_text = description if description else "_No description added yet_"
            embed.add_field(
                name=f"💎 {role_name} — {price:,}₮/{days} days",
                value=desc_text,
                inline=False
            )
        
        # Create view with plan buttons
        from cogs.payment import PayPlanButton
        view = discord.ui.View(timeout=None)
        for pid, role_id, role_name, price, days, active, description in plans:
            view.add_item(PayPlanButton(pid, f"{role_name} — {price}₮/{days}d"))
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

class MembershipCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.expire_watcher.start()

    async def cog_unload(self):
        self.expire_watcher.cancel()

    @tasks.loop(minutes=30)
    async def expire_watcher(self):
        for guild in self.bot.guilds:
            expired = list_expired(str(guild.id))
            for user_id, plan_id in expired:
                member = guild.get_member(int(user_id))
                plan = get_plan(int(plan_id))
                deactivate_membership(str(guild.id), user_id)
                if member and plan:
                    role = guild.get_role(int(plan["role_id"]))
                    if role:
                        await member.remove_roles(role, reason="Membership expired")
                    
                    # Send DM based on plan availability
                    try:
                        # Check if plan is still active
                        if plan.get("active") == 1:
                            # Plan is still active - offer renewal with choice buttons
                            embed = discord.Embed(
                                title="⏰ Your Membership Has Expired!",
                                description=f"Your **{plan['role_name']}** membership in **{guild.name}** has ended.",
                                color=0xe74c3c
                            )
                            
                            embed.add_field(
                                name="📦 Expired Plan",
                                value=f"**{plan['role_name']}**",
                                inline=True
                            )
                            
                            embed.add_field(
                                name="💰 Renewal Price",
                                value=f"**{plan['price_mnt']:,}₮**",
                                inline=True
                            )
                            
                            embed.add_field(
                                name="⏱️ Duration",
                                value=f"**{plan['duration_days']} days**",
                                inline=True
                            )
                            
                            # Add description if available
                            desc = plan.get('description', '')
                            if desc:
                                embed.add_field(
                                    name="✨ What You'll Get",
                                    value=desc,
                                    inline=False
                                )
                            
                            embed.add_field(
                                name="🔄 Choose Your Next Step",
                                value="**🔄 Renew Same Plan** - Quick renewal of your previous plan\n"
                                      "**🛍️ See Other Plans** - Browse all available plans\n\n"
                                      "Click a button below to continue!",
                                inline=False
                            )
                            
                            embed.set_footer(text=f"Server: {guild.name}")
                            
                            # Create renewal choice view with two buttons
                            view = RenewalChoiceView(
                                str(guild.id), 
                                guild.name, 
                                plan_id, 
                                plan["role_name"]
                            )
                            
                            await member.send(embed=embed, view=view)
                        else:
                            # Plan is deleted or deactivated - notify user
                            embed = discord.Embed(
                                title="⏰ Your Membership Has Expired!",
                                description=f"Your **{plan['role_name']}** membership in **{guild.name}** has ended.",
                                color=0x95a5a6
                            )
                            
                            embed.add_field(
                                name="📦 Expired Plan",
                                value=f"**{plan['role_name']}**",
                                inline=False
                            )
                            
                            embed.add_field(
                                name="⚠️ Plan No Longer Available",
                                value=(
                                    "This plan has been removed or deactivated by the server admin.\n\n"
                                    f"Use `/buy` in **{guild.name}** to see other available plans!"
                                ),
                                inline=False
                            )
                            
                            embed.set_footer(text=f"Server: {guild.name}")
                            
                            await member.send(embed=embed)
                    except Exception as e:
                        print(f"Failed to send renewal DM: {e}")

    @expire_watcher.before_loop
    async def before_watcher(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="verifypayment", description="Verify your QPay payment and get your role")
    async def verify_payment_cmd(self, interaction: discord.Interaction):
        """Allow users to manually verify their payment if buttons fail"""
        from database import get_payment_by_user, mark_payment_paid, grant_membership, get_plan
        from utils.qpay import check_qpay_payment_status
        
        if not interaction.guild:
            await interaction.response.send_message("❌ This must be used in a server.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Get user's most recent pending payment
        payment = get_payment_by_user(str(interaction.guild.id), str(interaction.user.id))
        
        if not payment:
            await interaction.followup.send(
                "❌ No recent payment found.\n\nUse `/buy` to purchase a role!",
                ephemeral=True
            )
            return
        
        invoice_id, guild_id, user_id, plan_id, amount, status, payment_url = payment
        
        # Check QPay status
        qpay_status = check_qpay_payment_status(invoice_id)
        
        if qpay_status == "PAID":
            # Get plan details
            plan = get_plan(int(plan_id))
            if not plan:
                await interaction.followup.send("❌ Plan not found.", ephemeral=True)
                return
            
            # Already marked paid?
            if status == "paid":
                await interaction.followup.send(
                    f"✅ Payment already confirmed!\n\nYou already have the **{plan['role_name']}** role.",
                    ephemeral=True
                )
                return
            
            # First time confirmation - grant membership
            mark_payment_paid(invoice_id)
            ends_at = grant_membership(guild_id, user_id, plan_id, plan["duration_days"], invoice_id)
            
            # Add role
            member = interaction.guild.get_member(int(user_id))
            role = interaction.guild.get_role(int(plan["role_id"]))
            
            if member and role:
                await member.add_roles(role, reason="QPay payment verified via command")
            
            # Success message
            desc_text = ""
            desc = plan.get('description', '')
            if desc:
                desc_text = f"\n\n**✨ What You Get:**\n{desc}"
            
            embed = discord.Embed(
                title="✅ Payment Verified!",
                description=f"🎉 **Success!**\n\n"
                            f"**Role:** {plan['role_name']}\n"
                            f"**Expires:** {ends_at[:10]}{desc_text}\n\n"
                            f"Enjoy your benefits! 🚀",
                color=0x00ff88
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        elif qpay_status == "PENDING":
            await interaction.followup.send(
                f"⏳ Payment still pending.\n\n"
                f"**Amount:** {amount:,}₮\n"
                f"Complete your payment and try again!",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"❌ Payment not confirmed.\n\n"
                f"**Status:** {qpay_status}\n"
                f"Please complete your payment first.",
                ephemeral=True
            )

    @app_commands.command(name="myplan", description="Check your active membership and expiry date")
    async def myplan_cmd(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ This must be used in a server.", ephemeral=True)
            return

        # Get user's active membership
        membership = get_user_active_membership(str(interaction.guild.id), str(interaction.user.id))
        
        if not membership:
            await interaction.response.send_message(
                "❌ You don't have an active membership.\n\nUse `/buy` to purchase a role!",
                ephemeral=True
            )
            return

        plan_id, access_ends_at = membership
        
        # Get plan details
        plan = get_plan(int(plan_id))
        if not plan:
            await interaction.response.send_message("❌ Plan not found.", ephemeral=True)
            return

        # Calculate remaining days
        try:
            expiry_date = datetime.fromisoformat(access_ends_at)
            days_left = (expiry_date - datetime.utcnow()).days
            
            if days_left < 0:
                days_left = 0
        except:
            days_left = 0

        # Create embed with membership info
        embed = discord.Embed(
            title="🎫 Your Membership",
            description=f"Here's your current subscription details:",
            color=0x2ecc71 if days_left > 7 else 0xe74c3c
        )
        
        embed.add_field(
            name="📦 Plan",
            value=f"**{plan['role_name']}**",
            inline=True
        )
        
        embed.add_field(
            name="⏰ Expires On",
            value=f"{access_ends_at[:10]}",
            inline=True
        )
        
        embed.add_field(
            name="⏳ Days Remaining",
            value=f"**{days_left}** days",
            inline=True
        )
        
        if days_left <= 7 and days_left > 0:
            embed.set_footer(text="⚠️ Your membership is expiring soon! Renew with /buy")
        elif days_left == 0:
            embed.set_footer(text="⚠️ Your membership has expired or expires today!")
        else:
            embed.set_footer(text="✨ Enjoy your benefits!")

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(MembershipCog(bot))