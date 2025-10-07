import discord
from discord import app_commands
from discord.ext import commands
from database import get_plan, create_payment, get_payment, mark_payment_paid, grant_membership
from utils.qpay import create_qpay_invoice, check_qpay_payment_status
from cogs.admin import admin_or_manager_check


class PayPlanButton(discord.ui.Button):
    def __init__(self, plan_id: int, label: str):
        super().__init__(label=f"💳 {label}", style=discord.ButtonStyle.success)
        self.plan_id = plan_id

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ This must be used in a server.", ephemeral=True)
            return
            
        plan = get_plan(self.plan_id)
        if not plan or plan["active"] != 1:
            await interaction.response.send_message("❌ Plan not available.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Create invoice
        invoice_id, qr_text, payment_url = create_qpay_invoice(plan["price_mnt"], plan["role_name"])
        if not invoice_id:
            await interaction.followup.send("❌ Failed to create QPay invoice.", ephemeral=True)
            return

        # Save payment
        create_payment(invoice_id, str(interaction.guild.id), str(interaction.user.id),
                       self.plan_id, plan["price_mnt"], payment_url or f"qr:{qr_text}")

        # Build payment view
        view = discord.ui.View()
        view.add_item(PayNowButton(invoice_id, payment_url or ""))
        view.add_item(CheckPaymentButton(invoice_id))

        embed = discord.Embed(
            title="💳 Payment Ready!",
            description=f"**Plan:** {plan['role_name']}\n"
                        f"**Amount:** {plan['price_mnt']}₮\n\n"
                        "📱 **How to Pay:**\n"
                        "1. Click **Pay Now**\n"
                        "2. Choose your bank\n"
                        "3. Complete payment\n"
                        "4. Return & press **Check Payment**",
            color=0x00ff88
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class PayNowButton(discord.ui.Button):
    def __init__(self, invoice_id: str, payment_url: str):
        super().__init__(label="💰 Pay Now", style=discord.ButtonStyle.primary)
        self.invoice_id = invoice_id
        self.payment_url = payment_url

    async def callback(self, interaction: discord.Interaction):
        url = self.payment_url or f"https://s.qpay.mn/payment/{self.invoice_id}"
        embed = discord.Embed(
            title="💰 QPay Payment",
            description=f"[**Open Payment Page**]({url})\n\nChoose your bank & pay safely.",
            color=0x00ff88
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class CheckPaymentButton(discord.ui.Button):
    def __init__(self, invoice_id: str):
        super().__init__(label="🔍 Check Payment", style=discord.ButtonStyle.primary)
        self.invoice_id = invoice_id

    async def callback(self, interaction: discord.Interaction):
        from database import get_membership_by_invoice
        
        await interaction.response.defer(ephemeral=True)
        
        status = check_qpay_payment_status(self.invoice_id)

        if status == "PAID":
            row = get_payment(self.invoice_id)
            if not row:
                await interaction.followup.send("❌ Payment not found.", ephemeral=True)
                return

            # Get plan details
            plan = get_plan(int(row[3]))
            if not plan:
                await interaction.followup.send("❌ Plan not found.", ephemeral=True)
                return

            # Already marked paid?
            if row[5] == "paid":
                # Get membership to show end date
                membership = get_membership_by_invoice(self.invoice_id)
                if membership:
                    ends_at = membership[4]  # access_ends_at
                    
                    # Build description text
                    desc_text = ""
                    desc = plan.get('description', '')
                    if desc:
                        desc_text = f"\n\n**✨ What You Get:**\n{desc}"
                    
                    embed = discord.Embed(
                        title="✅ Payment Complete!",
                        description=f"🎉 **You already have this role!**\n\n"
                                    f"**Role:** {plan['role_name']}\n"
                                    f"**Expires:** {ends_at[:10]}{desc_text}\n\n"
                                    f"Good luck and enjoy your benefits! 🚀",
                        color=0x00ff88
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.followup.send("✅ Payment complete! Role already granted.", ephemeral=True)
                return

            # First time confirmation - grant membership
            mark_payment_paid(self.invoice_id)
            ends_at = grant_membership(row[1], row[2], row[3], plan["duration_days"], self.invoice_id)

            # Add role with null safety
            guild = interaction.client.get_guild(int(row[1]))
            if not guild:
                await interaction.followup.send("❌ Server not found.", ephemeral=True)
                return
                
            member = guild.get_member(int(row[2]))
            role = guild.get_role(int(plan["role_id"]))
            
            if member and role:
                await member.add_roles(role, reason="QPay payment confirmed")

            # Build confirmation embed with description
            desc_text = ""
            desc = plan.get('description', '')
            if desc:
                desc_text = f"\n\n**✨ What You Get:**\n{desc}"
            
            embed = discord.Embed(
                title="✅ Payment Complete!",
                description=f"🎉 **Congratulations!**\n\n"
                            f"**Role:** {plan['role_name']}\n"
                            f"**Expires:** {ends_at[:10]}{desc_text}\n\n"
                            f"Good luck and enjoy your benefits! 🚀",
                color=0x00ff88
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        elif status == "PENDING":
            await interaction.followup.send("⏳ Payment still pending.", ephemeral=True)
        elif status == "CANCELLED":
            await interaction.followup.send("❌ Payment was cancelled.", ephemeral=True)
        else:
            await interaction.followup.send(f"❓ Status: {status}", ephemeral=True)


class PaymentsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="paywall", description="Post paywall for users to purchase roles")
    @admin_or_manager_check()
    async def paywall_cmd(self, interaction: discord.Interaction):
        from database import list_role_plans, has_active_subscription
        
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
            
        plans = list_role_plans(str(interaction.guild.id), only_active=True)
        if not plans:
            await interaction.response.send_message("❌ No active plans.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🔑 Premium Access",
            description="Choose a plan below to unlock exclusive perks!",
            color=0x2ecc71
        )
        
        # Add plan details as fields
        for pid, role_id, role_name, price, days, active, description in plans:
            desc_text = description if description else "_No description added yet_"
            embed.add_field(
                name=f"💎 {role_name} — {price:,}₮/{days} days",
                value=desc_text,
                inline=False
            )
        
        view = discord.ui.View(timeout=None)
        for pid, role_id, role_name, price, days, active, description in plans:
            view.add_item(PayPlanButton(pid, f"{role_name} — {price}₮/{days}d"))

        await interaction.response.send_message("Paywall posted below 👇", ephemeral=True)
        
        if interaction.channel and hasattr(interaction.channel, 'send'):
            await interaction.channel.send(embed=embed, view=view)

    @app_commands.command(name="buy", description="Purchase a role directly - choose your plan!")
    async def buy_cmd(self, interaction: discord.Interaction):
        from database import list_role_plans, has_active_subscription
        
        if not interaction.guild:
            await interaction.response.send_message("❌ This must be used in a server.", ephemeral=True)
            return
        
        # ✅ Check if server has active subscription
        if not has_active_subscription(str(interaction.guild.id)):
            await interaction.response.send_message(
                "❌ This server's bot subscription has expired. Ask an admin to run `/setup` to renew.",
                ephemeral=True
            )
            return
            
        plans = list_role_plans(str(interaction.guild.id), only_active=True)
        if not plans:
            await interaction.response.send_message("❌ No plans available for purchase.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🔑 Premium Access",
            description="Choose a plan below to unlock exclusive perks!",
            color=0x2ecc71
        )
        
        # Add plan details as fields
        for pid, role_id, role_name, price, days, active, description in plans:
            desc_text = description if description else "_No description added yet_"
            embed.add_field(
                name=f"💎 {role_name} — {price:,}₮/{days} days",
                value=desc_text,
                inline=False
            )
        
        view = discord.ui.View(timeout=None)
        for pid, role_id, role_name, price, days, active, description in plans:
            view.add_item(PayPlanButton(pid, f"{role_name} — {price}₮/{days}d"))

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(PaymentsCog(bot))