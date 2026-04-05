# cogs/vip.py
# /vip status, /vip activate commands.

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta

import config
import db
import utils


class VIPCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    vip_group = app_commands.Group(name="vip", description="VIP management")

    @vip_group.command(name="status", description="View your VIP status and perks")
    async def status(self, interaction: discord.Interaction):
        try:
            player = await db.ensure_player(str(interaction.user.id), interaction.user.display_name)
            vip = utils.is_vip(player)

            embed = discord.Embed(
                title="👑  VIP Status",
                color=config.COLOR_VIP if vip else config.COLOR_INFO,
            )

            if vip:
                until = player["vip_active_until"]
                if until.tzinfo is None:
                    until = until.replace(tzinfo=timezone.utc)
                remaining = (until - datetime.now(timezone.utc)).total_seconds()
                days_left = remaining / 86400

                embed.add_field(
                    name="Status",
                    value=f"✅ **Active** — {days_left:.1f} days remaining",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="Status",
                    value="❌ **Inactive**",
                    inline=False,
                )

            embed.add_field(
                name="📦 VIP Days Available",
                value=f"**{player.get('vip_days', 0)}** days",
                inline=True,
            )

            perks = (
                f"♻️ **{int(config.REFILL_VIP_PCT * 100)}%** stat refill (vs {int(config.REFILL_FREE_PCT * 100)}%)\n"
                f"💵 **{int((config.VIP_INCOME_MULT - 1) * 100)}%** income boost\n"
                f"⛵ **{int((config.VIP_SELL_PRICE_MULT - 1) * 100)}%** ship sell bonus\n"
                f"🔧 **+{int(config.VIP_UPGRADE_RARE_BONUS * 100)}%** rare upgrade chance\n"
                f"🏦 **{int((config.VIP_GANG_BANK_CAP_MULT - 1) * 100)}%** gang bank cap\n"
                f"📅 +{config.DAILY_VIP_DIAMONDS}💎 daily bonus"
            )
            embed.add_field(name="🎁 VIP Perks", value=perks, inline=False)

            await interaction.response.send_message(embed=embed)

        except Exception:
            import traceback; traceback.print_exc()
            embed = discord.Embed(title="❌ Error", color=config.COLOR_ERROR)
            try: await interaction.response.send_message(embed=embed, ephemeral=True)
            except: pass

    @vip_group.command(name="activate", description="Activate VIP with your stored days")
    @app_commands.describe(days="Number of VIP days to activate")
    async def activate(self, interaction: discord.Interaction, days: int):
        try:
            player = await db.ensure_player(str(interaction.user.id), interaction.user.display_name)

            if days <= 0:
                await interaction.response.send_message(
                    embed=discord.Embed(title="❌ Invalid", description="Must be at least 1 day.", color=config.COLOR_ERROR),
                    ephemeral=True,
                )
                return

            if player.get("vip_days", 0) < days:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="❌ Not Enough Days",
                        description=f"You have **{player.get('vip_days', 0)}** days, need **{days}**.",
                        color=config.COLOR_ERROR,
                    ),
                    ephemeral=True,
                )
                return

            player["vip_days"] -= days
            now = datetime.now(timezone.utc)

            # Stack if already VIP
            current_until = player.get("vip_active_until")
            if current_until:
                if current_until.tzinfo is None:
                    current_until = current_until.replace(tzinfo=timezone.utc)
                base = max(now, current_until)
            else:
                base = now

            player["vip_active_until"] = base + timedelta(days=days)
            await db.save_player(player)

            until = player["vip_active_until"]
            embed = discord.Embed(
                title="👑  VIP Activated!",
                description=(
                    f"Added **{days}** days of VIP.\n"
                    f"Active until: **{until.strftime('%b %d, %Y %H:%M')} UTC**\n"
                    f"📦 Remaining days: **{player['vip_days']}**"
                ),
                color=config.COLOR_VIP,
            )
            await interaction.response.send_message(embed=embed)

        except Exception:
            import traceback; traceback.print_exc()
            embed = discord.Embed(title="❌ Error", color=config.COLOR_ERROR)
            try: await interaction.response.send_message(embed=embed, ephemeral=True)
            except: pass


async def setup(bot: commands.Bot):
    await bot.add_cog(VIPCog(bot))
