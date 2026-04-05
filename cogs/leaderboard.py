# cogs/leaderboard.py
# /leaderboard [category] — top 10 rankings.

import discord
from discord import app_commands
from discord.ext import commands

import config
import db
import utils


class LeaderboardCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="View top 10 rankings")
    @app_commands.describe(category="Leaderboard category")
    @app_commands.choices(category=[
        app_commands.Choice(name="💪 Strength", value="strength"),
        app_commands.Choice(name="⚡ Speed", value="speed"),
        app_commands.Choice(name="🛡️ Defense", value="defense"),
        app_commands.Choice(name="📊 Level", value="level"),
        app_commands.Choice(name="💵 Cash", value="cash"),
        app_commands.Choice(name="🏴 Gang Power", value="gang_power"),
        app_commands.Choice(name="⚔️ Gang Shift", value="gang_shift"),
    ])
    async def leaderboard(self, interaction: discord.Interaction, category: str):
        try:
            database = db.get_db()
            embed = discord.Embed(color=config.COLOR_INFO)
            lines = []

            if category in ("strength", "speed", "defense"):
                # Stat leaderboards use stats + equipment_bonus
                players = await database.players.find(
                    {"faction": {"$ne": None}},
                    {"_id": 1, "username": 1, "stats": 1, "equipment_bonus": 1, "level": 1}
                ).to_list(None)

                # Sort by total stat
                players.sort(
                    key=lambda p: p["stats"].get(category, 0) + p.get("equipment_bonus", {}).get(category, 0),
                    reverse=True,
                )

                emoji = {"strength": "💪", "speed": "⚡", "defense": "🛡️"}[category]
                embed.title = f"{emoji} Top 10 — {category.title()}"

                for i, p in enumerate(players[:10], 1):
                    total = p["stats"].get(category, 0) + p.get("equipment_bonus", {}).get(category, 0)
                    medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"**{i}.**"
                    lines.append(f"{medal} **{p['username']}** — {total} (Lv.{p['level']})")

            elif category == "level":
                players = await database.players.find(
                    {"faction": {"$ne": None}},
                    {"_id": 1, "username": 1, "level": 1, "xp": 1}
                ).sort("level", -1).limit(10).to_list(None)

                embed.title = "📊 Top 10 — Level"
                for i, p in enumerate(players, 1):
                    medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"**{i}.**"
                    lines.append(f"{medal} **{p['username']}** — Level {p['level']} ({p['xp']:,} XP)")

            elif category == "cash":
                players = await database.players.find(
                    {"faction": {"$ne": None}},
                    {"_id": 1, "username": 1, "cash_wallet": 1, "level": 1}
                ).sort("cash_wallet", -1).limit(10).to_list(None)

                embed.title = "💵 Top 10 — Cash (Wallet)"
                for i, p in enumerate(players, 1):
                    medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"**{i}.**"
                    lines.append(f"{medal} **{p['username']}** — {utils.format_cash(p['cash_wallet'])}")

            elif category == "gang_power":
                gangs = await database.gangs.find().to_list(None)
                gangs.sort(key=lambda g: g.get("level", 0) + g.get("shift_wins", 0), reverse=True)

                embed.title = "🏴 Top 10 — Gang Power"
                for i, g in enumerate(gangs[:10], 1):
                    power = g.get("level", 0) + g.get("shift_wins", 0)
                    medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"**{i}.**"
                    lines.append(f"{medal} **{g.get('tag', '')} {g['name']}** — Power: {power}")

            elif category == "gang_shift":
                gangs = await database.gangs.find(
                    {"shift_state": "active"}
                ).sort("current_shift_points", -1).limit(10).to_list(None)

                embed.title = "⚔️ Top 10 — Gang Shift (Live)"
                if not gangs:
                    lines.append("No active gangs in the current shift.")
                for i, g in enumerate(gangs, 1):
                    medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"**{i}.**"
                    lines.append(f"{medal} **{g.get('tag', '')} {g['name']}** — {g['current_shift_points']} pts")

            embed.description = "\n".join(lines) if lines else "No data yet."
            await interaction.response.send_message(embed=embed)

        except Exception:
            import traceback; traceback.print_exc()
            embed = discord.Embed(title="❌ Error", description="Something went wrong.", color=config.COLOR_ERROR)
            try: await interaction.response.send_message(embed=embed, ephemeral=True)
            except: await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardCog(bot))
