# cogs/referral.py
# /referral command — Referral system with add, show, and claim subcommands.

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta

import config
import db
import utils

class ReferralCog(commands.Cog):
    """Underworld Referral System — Invite friends and earn rewards."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    referral_group = app_commands.Group(name="referral", description="Manage your referrals")

    # ── /referral add ──────────────────────────────────────────
    @referral_group.command(name="add", description="Add the user who referred you (within 3 days of joining)")
    @app_commands.describe(user="The player who invited you to the Underworld")
    async def referral_add(self, interaction: discord.Interaction, user: discord.User):
        try:
            player = await db.get_player(str(interaction.user.id))
            if not player:
                return await interaction.response.send_message("❌ You must register first with `/register`.", ephemeral=True)

            if player.get("referred_by"):
                return await interaction.response.send_message("❌ You have already added a referral.", ephemeral=True)

            # Check 3-day window
            created_at = player.get("created_at")
            if created_at:
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                
                if datetime.now(timezone.utc) > created_at + timedelta(days=3):
                    return await interaction.response.send_message("❌ Your 3-day referral period has expired.", ephemeral=True)

            if user.id == interaction.user.id:
                return await interaction.response.send_message("❌ You cannot refer yourself.", ephemeral=True)

            if user.bot:
                return await interaction.response.send_message("❌ Bots cannot refer players.", ephemeral=True)

            # Check if referral user exists
            ref_player = await db.get_player(str(user.id))
            if not ref_player:
                return await interaction.response.send_message(f"❌ **Mentioned User is not valid.** {user.display_name} has not registered yet.", ephemeral=True)

            # Save the referral
            player["referred_by"] = str(user.id)
            await db.save_player(player)

            embed = discord.Embed(
                title="🤝 Referral Added!",
                description=f"You've successfully added **{user.display_name}** as your referral.\n\nOnce you reach **Level 35**, they will be able to claim a reward!",
                color=config.COLOR_SUCCESS
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            import traceback; traceback.print_exc()
            await interaction.response.send_message("❌ An error occurred.", ephemeral=True)

    # ── /referral show ─────────────────────────────────────────
    @referral_group.command(name="show", description="Show users you have referred and their status")
    async def referral_show(self, interaction: discord.Interaction):
        try:
            database = db.get_db()
            # Find all players who set their 'referred_by' to THIS user
            cursor = database.players.find({"referred_by": str(interaction.user.id)})
            referred_players = await cursor.to_list(None)

            if not referred_players:
                return await interaction.response.send_message("You haven't referred any players yet.", ephemeral=True)

            lines = []
            for p in referred_players:
                status = "✅ Claimed" if p.get("referral_claimed_by_inviter") else "⏳ Unclaimed"
                lvl_needed = " (Lv. 35+)" if p["level"] < 35 and not p.get("referral_claimed_by_inviter") else ""
                lines.append(f"• **{p['username']}** | Level {p['level']}{lvl_needed} | {status}")

            embed = discord.Embed(
                title="🤝 Your Referrals",
                description="\n".join(lines),
                color=config.COLOR_INFO
            )
            embed.set_footer(text="Referred players must reach Level 35 for you to claim 100k coins.")
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            import traceback; traceback.print_exc()
            await interaction.response.send_message("❌ An error occurred.", ephemeral=True)

    # ── /referral claim ────────────────────────────────────────
    @referral_group.command(name="claim", description="Claim rewards for referred players who reached Level 35")
    async def referral_claim(self, interaction: discord.Interaction):
        try:
            database = db.get_db()
            # Find players referred by THIS user, who are level 35+, and rewards not yet claimed
            query = {
                "referred_by": str(interaction.user.id),
                "level": {"$gte": 35},
                "referral_claimed_by_inviter": {"$ne": True}
            }
            claimable_players = await database.players.find(query).to_list(None)

            if not claimable_players:
                return await interaction.response.send_message("❌ No claimable referral rewards found. Referred players must reach **Level 35**.", ephemeral=True)

            reward_per_player = 100000
            total_reward = len(claimable_players) * reward_per_player

            # Update inviter's wallet
            inviter = await db.get_player(str(interaction.user.id))
            inviter["cash_wallet"] += total_reward
            await db.save_player(inviter)

            # Mark referred players as claimed
            for p in claimable_players:
                await database.players.update_one(
                    {"_id": p["_id"]},
                    {"$set": {"referral_claimed_by_inviter": True}}
                )

            embed = discord.Embed(
                title="💰 Referral Rewards Claimed!",
                description=f"Successfully claimed rewards for **{len(claimable_players)}** referred player(s)!\n\n💵 **Total Received:** {utils.format_cash(total_reward)}",
                color=config.COLOR_SUCCESS
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            import traceback; traceback.print_exc()
            await interaction.response.send_message("❌ An error occurred.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ReferralCog(bot))
