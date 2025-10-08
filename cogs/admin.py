from datetime import datetime, timedelta
import discord
from discord import app_commands
from discord.ext import commands
from database import (list_role_plans, add_role_plan, has_active_subscription, update_plan_description, 
                     get_plan, set_manager_role, get_manager_role, remove_manager_role)

# ---------------- CUSTOM PERMISSION CHECK ----------------
def is_admin_or_manager(interaction: discord.Interaction) -> bool:
    """Check if user has admin permission OR manager role"""
    if not interaction.guild or not interaction.user:
        return False
    
    # Check if user has administrator permission
    if interaction.user.guild_permissions.administrator:
        return True
    
    # Check if user has the manager role
    manager = get_manager_role(str(interaction.guild.id))
    if manager:
        manager_role = interaction.guild.get_role(int(manager['role_id']))
        if manager_role and manager_role in interaction.user.roles:
            return True
    
    return False

def admin_or_manager_check():
    """Decorator to check for admin OR manager role"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not is_admin_or_manager(interaction):
            raise app_commands.MissingPermissions(['administrator_or_manager'])
        return True
    return app_commands.check(predicate)

# ---------------- MODALS ----------------
class PlanDescriptionModal(discord.ui.Modal, title="Plan Description"):
    description = discord.ui.TextInput(
        label="What does this role include?",
        style=discord.TextStyle.paragraph,
        placeholder="🎯 Access to premium channels\n💬 Private voice rooms\n🎁 Exclusive perks\n✨ Priority support",
        required=False,
        max_length=1000
    )
    
    def __init__(self, guild_id: str, role_id: str, role_name: str, price: int, duration: int):
        super().__init__()
        self.guild_id = guild_id
        self.role_id = role_id
        self.role_name = role_name
        self.price = price
        self.duration = duration
    
    async def on_submit(self, interaction: discord.Interaction):
        desc = self.description.value or ""
        plan_id = add_role_plan(self.guild_id, self.role_id, self.role_name, self.price, self.duration, desc)
        await interaction.response.send_message(
            f"✅ Plan added: **{self.role_name}** — {self.price:,}₮/{self.duration}d\n"
            f"📝 Description: {desc[:100]}..." if desc else "✅ Plan added: **{self.role_name}** — {self.price:,}₮/{self.duration}d",
            ephemeral=True
        )

class EditDescriptionModal(discord.ui.Modal, title="Edit Plan Description"):
    description = discord.ui.TextInput(
        label="What does this role include?",
        style=discord.TextStyle.paragraph,
        placeholder="🎯 Access to premium channels\n💬 Private voice rooms\n🎁 Exclusive perks\n✨ Priority support",
        required=False,
        max_length=1000
    )
    
    def __init__(self, plan_id: int, plan_name: str, current_description: str = ""):
        super().__init__()
        self.plan_id = plan_id
        self.plan_name = plan_name
        self.description.default = current_description
    
    async def on_submit(self, interaction: discord.Interaction):
        desc = self.description.value or ""
        update_plan_description(self.plan_id, desc)
        await interaction.response.send_message(
            f"✅ Description updated for **{self.plan_name}**\n"
            f"📝 {desc[:200]}..." if len(desc) > 200 else f"✅ Description updated for **{self.plan_name}**\n📝 {desc}",
            ephemeral=True
        )

# ---------------- BUTTONS ----------------
class DetailedGuideButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="📖 Detailed Guide", style=discord.ButtonStyle.primary, custom_id="detailed_guide")
    
    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 Complete Bot Guide - Every Detail",
            description="Everything you need to know about using this bot successfully",
            color=0x9b59b6
        )
        
        # Critical Requirements
        embed.add_field(
            name="⚠️ CRITICAL REQUIREMENTS (Must Do First!)",
            value=(
                "❗ **Bot role MUST be positioned ABOVE all paid roles**\n"
                "   → Server Settings → Roles → Drag bot role to top\n"
                "   → If bot is below paid roles, it CANNOT assign them!\n\n"
                "❗ **Bot needs 'Manage Roles' permission**\n"
                "   → Check in Server Settings → Roles → Bot Role\n\n"
                "❗ **Run `/checksetup` after subscribing**\n"
                "   → Verifies bot can assign roles properly\n"
                "   → Shows role position and permission issues"
            ),
            inline=False
        )
        
        # Subscription Plans
        embed.add_field(
            name="💳 Subscription Plans (Required to Use Bot)",
            value=(
                "**Basic** - 100₮/month (30 days)\n"
                "**Pro** - 200₮/6 months (180 days)\n"
                "**Premium** - 300₮/year (365 days)\n\n"
                "• Pay via QPay Mongolia\n"
                "• Get DM reminder 3 days before expiry\n"
                "• Can renew with QPay or collected balance\n"
                "• Bot stops working if subscription expires"
            ),
            inline=False
        )
        
        # Complete Setup Workflow
        embed.add_field(
            name="🔄 Complete Setup Workflow (Step by Step)",
            value=(
                "**Step 1:** Run `/setup` → Choose plan → Pay via QPay\n"
                "**Step 2:** Run `/checksetup` → Verify everything works\n"
                "**Step 3:** Run `/plan_add` → Create paid role plan:\n"
                "   • Select a Discord role\n"
                "   • Set price in ₮ (Mongolian Tugrik)\n"
                "   • Set duration in days\n"
                "   • Add description (what members get)\n"
                "**Step 4:** Run `/paywall` to post payment buttons\n"
                "   • Or tell users to use `/buy` command directly\n"
                "**Step 5:** Monitor with `/status` and `/growth`"
            ),
            inline=False
        )
        
        # Payment Flow Explained
        embed.add_field(
            name="💰 How Payments Work (For You and Members)",
            value=(
                "**Member's Experience:**\n"
                "1. Click plan button or use `/buy`\n"
                "2. Get QPay payment link\n"
                "3. Pay using any bank in Mongolia\n"
                "4. Click 'Check Payment' button\n"
                "5. Bot auto-assigns role instantly!\n\n"
                "**Your Revenue:**\n"
                "• All payments tracked in database\n"
                "• 3% service fee auto-deducted (QPay 1% + owner 2%)\n"
                "• Check `/status` to see available balance\n"
                "• Click 'Collect' button to request payout\n"
                "• Owner gets DM with your bank details"
            ),
            inline=False
        )
        
        # All Commands Explained
        embed.add_field(
            name="🎮 All Admin Commands Explained",
            value=(
                "**`/setup`** - Subscribe to bot (required first step)\n"
                "**`/checksetup`** - Verify bot permissions and role position\n"
                "**`/plan_add`** - Create new paid role plan\n"
                "**`/plan_list`** - See all your plans with status\n"
                "**`/plan_toggle`** - Enable/disable plan temporarily\n"
                "**`/plan_delete`** - Permanently delete a plan\n"
                "**`/edit_plan_description`** - Update marketing text\n"
                "**`/paywall`** - Post payment buttons in channel\n"
                "**`/status`** - Revenue dashboard + collect money\n"
                "**`/growth`** - Visual charts and analytics\n"
                "**`/topmembers`** - See who spends the most\n"
                "**`/review`** - Send feedback to developer"
            ),
            inline=False
        )
        
        # Analytics Explained
        embed.add_field(
            name="📊 Analytics & Tracking Features",
            value=(
                "**`/status` Dashboard:**\n"
                "• Total revenue earned (all time)\n"
                "• Available balance (after 3% fee)\n"
                "• Active members count\n"
                "• Revenue breakdown by each plan\n"
                "• 'Collect' button to request payout\n\n"
                "**`/growth` Visual Charts:**\n"
                "• Line chart showing daily revenue (30 days)\n"
                "• Pie chart showing revenue by role\n"
                "• Growth percentage vs previous month\n"
                "• Top 5 most profitable plans\n\n"
                "**`/topmembers` Statistics:**\n"
                "• Top 10 overall spenders\n"
                "• Top 3 spenders per each role plan"
            ),
            inline=False
        )
        
        # Auto Features
        embed.add_field(
            name="⚡ Automatic Features (No Work Needed)",
            value=(
                "✅ **Role Assignment** - Instant after payment\n"
                "✅ **Expiry Reminders** - Members get DM before expiry\n"
                "✅ **Role Removal** - Auto-removed when expired\n"
                "✅ **Subscription Warnings** - You get DM 3 days before\n"
                "✅ **Payment Tracking** - All transactions logged\n"
                "✅ **Fee Calculation** - 3% auto-deducted from revenue"
            ),
            inline=False
        )
        
        # Plan Descriptions
        embed.add_field(
            name="📝 Plan Descriptions (Marketing Your Roles)",
            value=(
                "Add custom text to explain what each role includes:\n"
                "• Shows in `/buy` and `/paywall` buttons\n"
                "• Appears in payment confirmation messages\n"
                "• Included in renewal reminder DMs\n"
                "• Up to 1000 characters\n\n"
                "**Example Description:**\n"
                "🎯 Access to premium channels\n"
                "💬 Private voice rooms\n"
                "🎁 Weekly exclusive content\n"
                "✨ Priority support from staff"
            ),
            inline=False
        )
        
        # Money Flow
        embed.add_field(
            name="💸 Money Flow & Fees Explained",
            value=(
                "**Example: Member pays 1,000₮**\n"
                "1️⃣ Total payment: 1,000₮\n"
                "2️⃣ QPay fee (1%): -10₮\n"
                "3️⃣ Bot owner fee (2%): -20₮\n"
                "4️⃣ Your revenue: 970₮ (97%)\n\n"
                "**Payout Process:**\n"
                "• Click 'Collect' in `/status`\n"
                "• Enter your bank details\n"
                "• Owner gets DM notification\n"
                "• Owner sends money to your account\n"
                "• 200₮ bank transfer fee applies per payout"
            ),
            inline=False
        )
        
        # Troubleshooting
        embed.add_field(
            name="🔧 Common Issues & Solutions",
            value=(
                "**Problem:** Bot can't assign roles\n"
                "→ Solution: Move bot role ABOVE paid roles\n\n"
                "**Problem:** `/checksetup` shows errors\n"
                "→ Solution: Follow the error messages exactly\n\n"
                "**Problem:** Payment confirmed but no role\n"
                "→ Solution: Check bot permissions with `/checksetup`\n\n"
                "**Problem:** Subscription expired\n"
                "→ Solution: Run `/setup` again to renew\n\n"
                "**Problem:** Members don't see `/buy`\n"
                "→ Solution: Tell them to type it manually"
            ),
            inline=False
        )
        
        embed.set_footer(text="💡 Still have questions? Use /review to contact the developer!")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class DetailedGuideView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DetailedGuideButton())

class SubscribeButton(discord.ui.Button):
    def __init__(self, plan_name: str, base_amount: int):
        super().__init__(label=f"{plan_name} — {base_amount}₮", style=discord.ButtonStyle.success)
        self.plan_name = plan_name
        self.base_amount = base_amount

    async def callback(self, interaction: discord.Interaction):
        from utils.qpay import create_qpay_invoice
        from database import create_subscription

        if not interaction.guild:
            await interaction.response.send_message("❌ This must be used in a server.", ephemeral=True)
            return

        # Defer immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)

        # Invoice amount (no +3% for bot rental itself)
        amount = int(self.base_amount)

        # Create QPay invoice
        invoice_id, qr_text, payment_url = create_qpay_invoice(amount, f"{self.plan_name} Plan")
        if not invoice_id:
            await interaction.followup.send("❌ Failed to create QPay invoice.", ephemeral=True)
            return

        # Expiry depends on plan
        if self.plan_name == "Basic":
            expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
        elif self.plan_name == "Pro":
            expires_at = (datetime.utcnow() + timedelta(days=90)).isoformat()
        elif self.plan_name == "Premium":
            expires_at = (datetime.utcnow() + timedelta(days=180)).isoformat()
        else:
            expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()

        # Save subscription in DB (status = pending)
        create_subscription(str(interaction.guild.id), self.plan_name, amount, invoice_id, expires_at)

        # QPay link with buttons like user payment flow
        url = payment_url or f"https://s.qpay.mn/payment/{invoice_id}"
        embed = discord.Embed(
            title="💳 QPay Subscription Payment",
            description=f"**Plan:** {self.plan_name}\n**Amount:** {amount}₮\n\n"
                        f"🔥 **STEP 1:** Click **Pay with QPay** button below ⬇️\n"
                        f"🏦 **STEP 2:** Choose your bank and pay\n"
                        f"✅ **STEP 3:** Come back and click **Check Payment**\n\n"
                        f"⚠️ Don't click 'Check Payment' until you complete the payment!",
            color=0xff9900
        )

        view = discord.ui.View(timeout=None)
        # Add QPay link button (like user payments)
        view.add_item(discord.ui.Button(
            label="💳 Pay with QPay", 
            style=discord.ButtonStyle.link, 
            url=url
        ))
        # Add Check Payment button (grey like user payments)
        view.add_item(CheckPaymentButton(invoice_id, self.plan_name, expires_at))

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class CheckPaymentButton(discord.ui.Button):
    def __init__(self, invoice_id: str, plan_name: str, expires_at: str):
        super().__init__(label="🔍 Check Payment", style=discord.ButtonStyle.secondary)
        self.invoice_id = invoice_id
        self.plan_name = plan_name
        self.expires_at = expires_at

    async def callback(self, interaction: discord.Interaction):
        from utils.qpay import check_qpay_payment_status
        from database import mark_subscription_paid

        await interaction.response.defer(ephemeral=True)
        
        print(f"🔍 Admin checking subscription payment for invoice: {self.invoice_id}")
        status = check_qpay_payment_status(self.invoice_id)
        print(f"📊 Subscription payment status: {status}")
        
        if status == "PAID":
            # Mark subscription as active
            mark_subscription_paid(self.invoice_id)
            print(f"✅ Subscription {self.invoice_id} marked as paid")

            embed = discord.Embed(
                title="✅ Subscription Activated!",
                description=f"Bot rental activated for **{self.plan_name} Plan**.\n"
                            f"⏰ Expires at: **{self.expires_at[:10]}**\n\n"
                            f"You can now use `/plan_add` and other admin features.",
                color=0x2ecc71
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        elif status == "PENDING":
            await interaction.followup.send("⏳ Payment still pending. Try again in 1–2 minutes.", ephemeral=True)
        elif status == "CANCELLED":
            await interaction.followup.send("❌ Payment was cancelled. Please create a new subscription.", ephemeral=True)
        else:
            await interaction.followup.send(f"❓ Payment status: {status}", ephemeral=True)


# ---------------- ADMIN SETUP ----------------
class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Get subscription prices from environment (test vs production)
        import os
        self.basic_price = int(os.getenv("SUB_BASIC_PRICE", "100"))  # Default: test price
        self.pro_price = int(os.getenv("SUB_PRO_PRICE", "200"))      # Default: test price
        self.premium_price = int(os.getenv("SUB_PREMIUM_PRICE", "300"))  # Default: test price

    @app_commands.command(name="checksetup", description="Check if bot has correct permissions and role position")
    @app_commands.checks.has_permissions(administrator=True)
    async def checksetup_cmd(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ This must be used in a server.", ephemeral=True)
            return
        
        bot_member = interaction.guild.me
        issues = []
        
        # Check "Manage Roles" permission
        if not bot_member.guild_permissions.manage_roles:
            issues.append("❌ Bot is missing **Manage Roles** permission")
        
        # Check role position vs paid roles
        plans = list_role_plans(str(interaction.guild.id), only_active=False)
        bot_role_position = bot_member.top_role.position
        
        for plan in plans:
            role_id = plan[1]
            role = interaction.guild.get_role(int(role_id))
            if role and role.position >= bot_role_position:
                issues.append(f"❌ Bot role is below **{role.name}** (paid role must be below bot)")
        
        if issues:
            embed = discord.Embed(
                title="⚠️ Setup Issues Found",
                description="\n".join(issues) + "\n\n**How to fix:**\n"
                            "1. Go to **Server Settings** → **Roles**\n"
                            "2. Give bot's role **Manage Roles** permission\n"
                            "3. **Drag bot's role ABOVE all paid roles**\n\n"
                            "The bot must be above paid roles to assign them!",
                color=0xe74c3c
            )
        else:
            embed = discord.Embed(
                title="✅ Bot Setup is Perfect!",
                description="The bot has all required permissions and is positioned correctly.",
                color=0x2ecc71
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setup", description="Setup bot subscription (admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚙️ Bot Subscription",
            description=(
                "**Choose a plan to rent the bot.**\n\n"
                f"📦 **Basic** — 1 month (30 days) — {self.basic_price:,}₮\n"
                f"📦 **Pro** — 3 months (90 days) — {self.pro_price:,}₮\n"
                f"📦 **Premium** — 6 months (180 days) — {self.premium_price:,}₮\n\n"
                "💡 Note: When your members purchase paid roles, "
                "the system will automatically deduct a **3% service fee** from each transaction.\n\n"
                "⚙️ After subscribing, run `/checksetup` to verify bot permissions!"
            ),
            color=0x3498db
        )
        view = discord.ui.View(timeout=None)
        view.add_item(SubscribeButton("Basic", self.basic_price))
        view.add_item(SubscribeButton("Pro", self.pro_price))
        view.add_item(SubscribeButton("Premium", self.premium_price))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="plan_add", description="Add a paid role plan (requires active subscription)")
    @admin_or_manager_check()
    async def plan_add(self, interaction: discord.Interaction, 
                       role: discord.Role, 
                       display_name: str, 
                       price_mnt: int, 
                       duration_days: int):
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

        # Open modal to add description
        modal = PlanDescriptionModal(str(interaction.guild.id), str(role.id), display_name, price_mnt, duration_days)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="plan_list", description="List role plans")
    async def plan_list(self, interaction: discord.Interaction):
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

        plans = list_role_plans(str(interaction.guild.id), only_active=False)
        if not plans:
            await interaction.response.send_message("No plans yet.", ephemeral=True)
            return
        msg = "\n".join([f"**#{i+1}** {'🟢' if p[5]==1 else '🔴'} {p[2]} — {p[3]}₮ / {p[4]}d (ID: {p[0]})" for i, p in enumerate(plans)])
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="plan_toggle", description="Enable/disable a role plan")
    @admin_or_manager_check()
    async def plan_toggle(self, interaction: discord.Interaction, plan_id: int):
        from database import toggle_role_plan, get_plan

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

        plan = get_plan(plan_id)
        if not plan or plan['guild_id'] != str(interaction.guild.id):
            await interaction.response.send_message("❌ Plan not found in this server.", ephemeral=True)
            return

        # Toggle: if active (1) → disable (0), if disabled (0) → enable (1)
        new_status = 0 if plan['active'] == 1 else 1
        toggle_role_plan(plan_id, new_status)

        status_text = "enabled" if new_status == 1 else "disabled"
        await interaction.response.send_message(
            f"✅ Plan **{plan['role_name']}** has been {status_text}.",
            ephemeral=True
        )

    @plan_toggle.autocomplete('plan_id')
    async def plan_toggle_autocomplete(self, interaction: discord.Interaction, current: str):
        if not interaction.guild:
            return []
        
        plans = list_role_plans(str(interaction.guild.id), only_active=False)
        choices = []
        
        for i, plan in enumerate(plans[:25]):  # Discord limit: 25 choices
            plan_id = plan[0]
            display_name = plan[2]
            price = plan[3]
            duration = plan[4]
            is_active = plan[5]
            status = '🟢' if is_active == 1 else '🔴'
            
            choice_name = f"#{i+1} {status} {display_name} — {price}₮/{duration}d"
            choices.append(app_commands.Choice(name=choice_name, value=plan_id))
        
        return choices

    @app_commands.command(name="plan_delete", description="Permanently delete a role plan")
    @admin_or_manager_check()
    async def plan_delete(self, interaction: discord.Interaction, plan_id: int):
        from database import delete_role_plan, get_plan

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

        plan = get_plan(plan_id)
        if not plan or plan['guild_id'] != str(interaction.guild.id):
            await interaction.response.send_message("❌ Plan not found in this server.", ephemeral=True)
            return

        # Delete the plan
        success = delete_role_plan(plan_id)
        if success:
            await interaction.response.send_message(
                f"🗑️ Plan **{plan['role_name']}** has been permanently deleted.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Failed to delete plan.", ephemeral=True)

    @plan_delete.autocomplete('plan_id')
    async def plan_delete_autocomplete(self, interaction: discord.Interaction, current: str):
        if not interaction.guild:
            return []
        
        plans = list_role_plans(str(interaction.guild.id), only_active=False)
        choices = []
        
        for i, plan in enumerate(plans[:25]):  # Discord limit: 25 choices
            plan_id = plan[0]
            display_name = plan[2]
            price = plan[3]
            duration = plan[4]
            is_active = plan[5]
            status = '🟢' if is_active == 1 else '🔴'
            
            choice_name = f"#{i+1} {status} {display_name} — {price}₮/{duration}d"
            choices.append(app_commands.Choice(name=choice_name, value=plan_id))
        
        return choices

    @app_commands.command(name="edit_plan_description", description="Edit the description of a role plan")
    @admin_or_manager_check()
    async def edit_plan_description(self, interaction: discord.Interaction, plan_id: int):
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

        plan = get_plan(plan_id)
        if not plan or plan['guild_id'] != str(interaction.guild.id):
            await interaction.response.send_message("❌ Plan not found in this server.", ephemeral=True)
            return

        # Open modal to edit description
        modal = EditDescriptionModal(plan_id, plan['role_name'], plan.get('description', ''))
        await interaction.response.send_modal(modal)

    @edit_plan_description.autocomplete('plan_id')
    async def edit_description_autocomplete(self, interaction: discord.Interaction, current: str):
        if not interaction.guild:
            return []
        
        plans = list_role_plans(str(interaction.guild.id), only_active=False)
        choices = []
        
        for i, plan in enumerate(plans[:25]):  # Discord limit: 25 choices
            plan_id = plan[0]
            display_name = plan[2]
            price = plan[3]
            duration = plan[4]
            is_active = plan[5]
            status = '🟢' if is_active == 1 else '🔴'
            
            choice_name = f"#{i+1} {status} {display_name} — {price}₮/{duration}d"
            choices.append(app_commands.Choice(name=choice_name, value=plan_id))
        
        return choices

    @app_commands.command(name="bot_info", description="Show bot commands and features guide")
    @app_commands.checks.has_permissions(administrator=True)
    async def info_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🤖 Bot Commands Guide",
            description="Quick reference for all bot features",
            color=0x3498db
        )
        
        # CRITICAL WARNINGS FIRST
        embed.add_field(
            name="🚨 CRITICAL WARNINGS - READ FIRST!",
            value=(
                "❗ **Bot role MUST be ABOVE all paid roles**\n"
                "   → Server Settings → Roles → Drag bot to top\n"
                "   → Bot CANNOT assign roles below its position!\n\n"
                "❗ **Always run `/checksetup` after subscribing**\n"
                "   → Verifies permissions and role positioning\n"
                "   → Shows exactly what's wrong if errors occur\n\n"
                "❗ **Bot stops working when subscription expires**\n"
                "   → Get DM warning 3 days before expiry\n"
                "   → Renew immediately to keep features active"
            ),
            inline=False
        )
        
        # Admin Commands
        embed.add_field(
            name="👑 Admin Commands",
            value=(
                "**`/setup`** - Subscribe to bot (Basic/Pro/Premium)\n"
                "**`/plan_add`** - Create paid role with custom description\n"
                "**`/plan_list`** - View all your role plans\n"
                "**`/plan_toggle`** - Enable/disable a plan\n"
                "**`/plan_delete`** - Delete a plan\n"
                "**`/edit_plan_description`** - Update plan marketing text\n"
                "**`/paywall`** - Post payment buttons in channel"
            ),
            inline=False
        )
        
        # Manager/Moderator Commands
        embed.add_field(
            name="🛡️ Manager Role Commands (Delegate Plan Management)",
            value=(
                "**`/set_manager_role`** - Give a role permission to manage plans\n"
                "**`/view_manager_role`** - Check which role can manage plans\n"
                "**`/remove_manager_role`** - Remove manager permissions\n"
                "• Managers can add/edit/delete plans, but NOT handle money\n"
                "• Only admins can use /status, /growth, /setup"
            ),
            inline=False
        )
        
        # Analytics & Money
        embed.add_field(
            name="📊 Analytics & Revenue (Admin Only)",
            value=(
                "**`/status`** - Revenue dashboard + 'Collect' button\n"
                "**`/growth`** - Visual charts + AI business advice (GPT-4o) 🤖\n"
                "**`/topmembers`** - See top spenders and statistics\n"
                "• 🆕 AI analyzes your data and gives growth tips (2-3 points)\n"
                "• Growth shows 30-day trends and role breakdowns\n"
                "• Weekly AI reports sent every Monday to all admins\n"
                "• 3% fee auto-deducted from all revenue"
            ),
            inline=False
        )
        
        # User Commands
        embed.add_field(
            name="👥 User Commands",
            value=(
                "**`/buy`** - Purchase any role (works anywhere!)\n"
                "**`/myplan`** - Check ALL active memberships with timers 🟢🟡🔴\n"
                "**`/verifypayment`** - Backup: Verify payment if buttons fail\n"
                "• 🆕 Multi-role support: Buy and hold multiple roles at once!\n"
                "• Each role has independent expiry date and timer\n"
                "• Renewal DMs work in DMs with full QPay payment flow"
            ),
            inline=False
        )
        
        # Quick Setup
        embed.add_field(
            name="🚀 Quick Setup (5 Steps)",
            value=(
                "**1.** `/setup` → Subscribe and pay\n"
                "**2.** `/checksetup` → Verify bot permissions ⚠️\n"
                "**3.** `/plan_add` → Create role plans\n"
                "**4.** `/paywall` or share `/buy` with members\n"
                "**5.** `/growth` → Track your revenue!"
            ),
            inline=False
        )
        
        embed.set_footer(text="💡 Click 'Detailed Guide' button below for complete information!")
        
        view = DetailedGuideView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="review", description="Send bug report or feature suggestion to bot developer")
    @app_commands.checks.has_permissions(administrator=True)
    async def review_cmd(self, interaction: discord.Interaction):
        modal = ReviewModal()
        await interaction.response.send_modal(modal)

    @app_commands.command(name="topmembers", description="View top paying members and statistics (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def topmembers_cmd(self, interaction: discord.Interaction):
        from database import get_top_members, get_top_members_by_plan, list_role_plans, total_guild_revenue
        
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
        
        await interaction.response.defer(ephemeral=True)
        
        guild_id = str(interaction.guild.id)
        
        # Get overall top members
        top_overall = get_top_members(guild_id, limit=10)
        
        # Create main embed
        embed = discord.Embed(
            title="📊 Top Members Dashboard",
            description=f"💰 **Total Revenue:** {total_guild_revenue(guild_id):,}₮",
            color=0xf39c12
        )
        
        # Add overall top spenders
        if top_overall:
            top_text = ""
            for i, (user_id, username, payments, total_spent) in enumerate(top_overall, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**#{i}**"
                display_name = username or f"User {user_id}"
                top_text += f"{medal} **{display_name}** — {total_spent:,}₮ ({payments} payments)\n"
            
            embed.add_field(
                name="🏆 Top 10 Spenders (All Plans)",
                value=top_text,
                inline=False
            )
        else:
            embed.add_field(
                name="🏆 Top Spenders",
                value="_No payments yet_",
                inline=False
            )
        
        # Get all plans with revenue
        plans = list_role_plans(guild_id, only_active=False)
        
        # Add top members per plan
        for plan in plans[:5]:  # Show top 5 plans to avoid hitting embed limit
            plan_id = plan[0]
            role_name = plan[2]
            
            top_plan = get_top_members_by_plan(guild_id, plan_id, limit=3)
            
            if top_plan:
                plan_text = ""
                for i, (user_id, username, purchases, total_spent) in enumerate(top_plan, 1):
                    display_name = username or f"User {user_id}"
                    plan_text += f"{i}. **{display_name}** — {total_spent:,}₮ ({purchases}x)\n"
                
                embed.add_field(
                    name=f"💎 {role_name} - Top 3",
                    value=plan_text,
                    inline=True
                )
        
        embed.set_footer(text=f"Server: {interaction.guild.name}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)


# ---------- MODAL ----------
class ReviewModal(discord.ui.Modal, title="📝 Feedback & Bug Report"):
    feedback = discord.ui.TextInput(
        label="Bug Report or Feature Suggestion",
        style=discord.TextStyle.paragraph,
        placeholder="Describe the bug or your idea here...\nBe as detailed as possible!",
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        import os
        
        if not interaction.guild:
            await interaction.response.send_message("❌ This must be used in a server.", ephemeral=True)
            return
        
        guild = interaction.guild
        admin = interaction.user
        feedback_text = self.feedback.value
        
        # Get bot owner ID from environment f
        owner_id = os.getenv("OWNER_DISCORD_ID")
        if not owner_id:
            await interaction.response.send_message(
                "❌ Bot owner ID not configured. Contact developer.",
                ephemeral=True
            )
            return
        
        try:
            owner = await interaction.client.fetch_user(int(owner_id))
            
            # Create embed for owner (server info only)
            embed = discord.Embed(
                title="📨 New Feedback from Admin",
                color=0x3498db,
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(name="🏢 Server", value=f"{guild.name}\nID: {guild.id}", inline=True)
            embed.add_field(name="👤 Admin", value=f"{admin.mention} ({admin.name})\nID: {admin.id}", inline=True)
            
            embed.set_footer(text=f"From {guild.name}")
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            
            # Send embed + feedback as separate message (no character limit)
            await owner.send(embed=embed)
            await owner.send(f"**💬 Feedback Message:**\n{feedback_text}")
            
            # Confirm to admin
            await interaction.response.send_message(
                "✅ **Thank you!** Your feedback has been sent to the developer.\n"
                "They will review it and work on improvements!",
                ephemeral=True
            )
        except discord.NotFound:
            await interaction.response.send_message(
                "❌ Bot owner not found. Contact developer.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Cannot send DM to bot owner (DMs closed).",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to send feedback: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="set_manager_role", description="Set a role that can manage plans (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_manager_role_cmd(self, interaction: discord.Interaction, role: discord.Role):
        if not interaction.guild:
            await interaction.response.send_message("❌ This must be used in a server.", ephemeral=True)
            return
        
        # Prevent setting @everyone or bot roles
        if role.is_default() or role.managed:
            await interaction.response.send_message(
                "❌ Cannot set @everyone or managed bot roles as manager role.",
                ephemeral=True
            )
            return
        
        # Save manager role
        set_manager_role(str(interaction.guild.id), str(role.id), role.name)
        
        await interaction.response.send_message(
            f"✅ **Manager role set successfully!**\n\n"
            f"🔧 **Role:** {role.mention}\n\n"
            f"**Members with this role can now:**\n"
            f"• Add/edit/delete role plans\n"
            f"• Toggle plans on/off\n"
            f"• Post paywall messages\n"
            f"• Edit plan descriptions\n\n"
            f"**They CANNOT:**\n"
            f"• View financial dashboard\n"
            f"• Collect money\n"
            f"• View analytics\n"
            f"• Change bot subscription",
            ephemeral=True
        )

    @app_commands.command(name="view_manager_role", description="View the current manager role for plan management")
    async def view_manager_role_cmd(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ This must be used in a server.", ephemeral=True)
            return
        
        manager = get_manager_role(str(interaction.guild.id))
        
        if not manager:
            await interaction.response.send_message(
                "❌ No manager role set.\n\n"
                f"Admins can set one with `/set_manager_role`",
                ephemeral=True
            )
            return
        
        role = interaction.guild.get_role(int(manager['role_id']))
        if role:
            await interaction.response.send_message(
                f"🔧 **Current Manager Role:** {role.mention}\n\n"
                f"Members with this role can manage plans but cannot access money/analytics.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚠️ Manager role was set but no longer exists: **{manager['role_name']}**\n"
                f"Please set a new one with `/set_manager_role`",
                ephemeral=True
            )

    @app_commands.command(name="remove_manager_role", description="Remove the manager role (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_manager_role_cmd(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ This must be used in a server.", ephemeral=True)
            return
        
        manager = get_manager_role(str(interaction.guild.id))
        if not manager:
            await interaction.response.send_message(
                "❌ No manager role is currently set.",
                ephemeral=True
            )
            return
        
        remove_manager_role(str(interaction.guild.id))
        await interaction.response.send_message(
            f"✅ Manager role removed successfully!\n\n"
            f"Only administrators can now manage plans.",
            ephemeral=True
        )


# ---------- SETUP ----------
async def setup(bot):
    await bot.add_cog(AdminCog(bot))