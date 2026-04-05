# cogs/daily.py
# /daily command — daily reward with streak system.

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone

import config
import db
import utils


class DailyCog(commands.Cog):
    """Daily reward system."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="daily", description="Claim your daily reward")
    async def daily(self, interaction: discord.Interaction):
        if not await utils.check_active(interaction):
            return
            
        try:
            player = await db.ensure_player(
                str(interaction.user.id), interaction.user.display_name
            )

            if player["faction"] is None:
                embed = discord.Embed(
                    title="⚔️  Choose a Faction First",
                    description="Use `/profile` to select your faction.",
                    color=config.COLOR_WARNING,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Check 24h cooldown
            remaining = utils.cooldown_remaining(
                player["cooldowns"].get("daily"), 86400  # 24 hours
            )
            if remaining > 0:
                embed = discord.Embed(
                    title="⏳  Already Claimed",
                    description=(
                        f"Come back in **{utils.format_cooldown(remaining)}**.\n"
                        f"🔥 Current streak: **{player.get('daily_streak', 0)}** days"
                    ),
                    color=config.COLOR_WARNING,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Calculate rewards
            vip = utils.is_vip(player)
            rewards = []

            # Base cash
            cash = config.DAILY_BASE_CASH
            rewards.append(f"💵 +{utils.format_cash(cash)}")

            # Base XP
            xp = config.DAILY_BASE_XP
            rewards.append(f"⭐ +{xp} XP")

            # VIP bonus
            if vip:
                cash += config.DAILY_VIP_CASH
                rewards.append(f"👑 VIP bonus: +{utils.format_cash(config.DAILY_VIP_CASH)}")
                player["diamonds"] += config.DAILY_VIP_DIAMONDS
                rewards.append(f"👑 VIP bonus: +{config.DAILY_VIP_DIAMONDS} 💎")

            # Streak
            streak = player.get("daily_streak", 0) + 1
            player["daily_streak"] = streak
            rewards.append(f"🔥 Streak: **{streak}** days")

            # Streak diamond bonus
            if streak % config.DAILY_STREAK_DIAMOND_INTERVAL == 0:
                bonus_diamonds = 1
                player["diamonds"] += bonus_diamonds
                rewards.append(f"🎉 Streak milestone! +{bonus_diamonds} 💎")

            # Apply rewards
            player["cash_wallet"] += cash
            player["xp"] += xp
            player["cooldowns"]["daily"] = datetime.now(timezone.utc)

            # Check level up
            player, leveled = utils.check_level_up(player)
            if leveled:
                rewards.append(f"🎉 **LEVEL UP!** You are now Level {player['level']}!")

            embed = discord.Embed(
                title="📅  Daily Reward Claimed!",
                description="\n".join(rewards),
                color=config.COLOR_VIP if vip else config.COLOR_SUCCESS,
            )

            # Check for Item Drops based on streak
            drop = None
            if streak % 30 == 0:
                drop = utils.roll_item_drop("daily_30", is_vip=vip)
            elif streak % 7 == 0:
                drop = utils.roll_item_drop("daily_7", is_vip=vip)
                
            if drop:
                import asyncio
                asyncio.create_task(self.process_daily_drop(str(interaction.user.id), drop))
                
                TIER_EMOJIS = {"common": "⬜", "uncommon": "🟩", "rare": "🟦", "very_rare": "🟪", "legendary": "🟡"}
                emoji = TIER_EMOJIS.get(drop["tier"], "⬜")
                tier_name = drop["tier"].replace("_", " ").title()
                
                embed.add_field(
                    name="🎁  Loyalty Drop!",
                    value=(
                        f"{emoji} **{drop['name']}** ({tier_name})\n"
                        f"**Bonus:** +{drop['total_bonus']} {drop['stat_type'].title()}\n"
                        f"*{drop['lore']}*"
                    ),
                    inline=False
                )

            await db.save_player(player)
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            import traceback
            traceback.print_exc()
            embed = discord.Embed(
                title="❌  Error",
                description="Something went wrong. Please try again.",
                color=config.COLOR_ERROR,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def process_daily_drop(self, player_id: str, item: dict):
        """Async task to save the daily drop."""
        try:
            item["owner_id"] = player_id
            database = db.get_db()
            await database.items.insert_one(item)
            await database.players.update_one(
                {"_id": player_id},
                {"$push": {"items": item["_id"]}}
            )
            from cogs.upgrades import update_slot_rank
            await update_slot_rank(item["slot"])
        except Exception as e:
            import logging
            logging.error(f"Failed to process daily drop: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(DailyCog(bot))
