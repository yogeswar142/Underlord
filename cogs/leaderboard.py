# cogs/leaderboard.py
import discord
from discord import app_commands
from discord.ext import commands

import config
import db
import utils

class LeaderboardSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Strength", value="strength", emoji="💪"),
            discord.SelectOption(label="Speed", value="speed", emoji="⚡"),
            discord.SelectOption(label="Defense", value="defense", emoji="🛡️"),
            discord.SelectOption(label="Level", value="level", emoji="📊"),
            discord.SelectOption(label="Cash", value="cash", emoji="💵"),
            discord.SelectOption(label="Gang Power", value="gang_power", emoji="🏴"),
            discord.SelectOption(label="Gang Shift (Live)", value="gang_shift", emoji="⚔️"),
            discord.SelectOption(label="Country Shift (Live)", value="country_shift", emoji="🌍"),
            discord.SelectOption(label="Best Weapons", value="weapons", emoji="🔫"),
            discord.SelectOption(label="Best Equipment", value="equipment", emoji="🧥"),
        ]
        super().__init__(placeholder="Select a leaderboard...", options=options)

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        try:
            database = db.get_db()
            embed = discord.Embed(color=config.COLOR_INFO)
            lines = []

            if category in ("strength", "speed", "defense"):
                players = await database.players.find(
                    {"faction": {"$ne": None}},
                    {"_id": 1, "username": 1, "stats": 1, "equipment_bonus": 1, "level": 1}
                ).to_list(None)

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
                    
            elif category == "country_shift":
                countries = await database.countries.find().sort("points", -1).limit(10).to_list(None)
                embed.title = "🌍 Top 10 — Country Shift (Live)"
                if not countries:
                    lines.append("No country deaths yet.")
                for i, c in enumerate(countries, 1):
                    pts = c.get('points', 0)
                    if pts > 0:
                        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"**{i}.**"
                        lines.append(f"{medal} **{c['_id']}** — {pts} pts")
                        
            elif category in ("weapons", "equipment"):
                slots = ["weapon1", "weapon2"] if category == "weapons" else ["hat", "jacket", "shoes", "car", "jewellery"]
                items = await database.items.find(
                    {"slot": {"$in": slots}}
                ).sort("total_bonus", -1).limit(10).to_list(None)

                title_str = "Weapons" if category == "weapons" else "Equipment"
                embed.title = f"🏆 Top 10 — {title_str}"
                
                if not items:
                    lines.append("No items exist yet.")
                else:
                    TIER_EMOJIS = {"common": "⬜", "uncommon": "🟩", "rare": "🟦", "very_rare": "🟪", "legendary": "🟡"}
                    for i, itm in enumerate(items, 1):
                        owner_name = "Unknown Player"
                        if itm.get("owner_id"):
                            player = await database.players.find_one({"_id": itm["owner_id"]})
                            if player:
                                owner_name = player.get("username", "Unknown")
                                
                        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"**{i}.**"
                        emoji = TIER_EMOJIS.get(itm.get("tier", "common"), "⬜")
                        upg_str = f" [+ {itm.get('upgrade_count', 0)}]" if itm.get('upgrade_count', 0) > 0 else ""
                        lines.append(f"{medal} {emoji} **{itm['name']}**{upg_str} (+{itm['total_bonus']} {itm['stat_type'].title()})\n   └ Owner: **{owner_name}**")

            if category in ("weapons", "equipment"):
                embed.description = "\n\n".join(lines) if lines else "No data yet."
            else:
                embed.description = "\n".join(lines) if lines else "No data yet."
                
            await interaction.response.edit_message(embed=embed, view=self.view)

        except Exception:
            import traceback; traceback.print_exc()
            embed = discord.Embed(title="❌ Error", description="Something went wrong.", color=config.COLOR_ERROR)
            try: await interaction.response.send_message(embed=embed, ephemeral=True)
            except: pass

class LeaderboardView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(LeaderboardSelect())

class LeaderboardCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="View live rankings using an interactive menu")
    async def leaderboard(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title="🏆 Underworld Leaderboards",
                description="Select a category from the dropdown menu to view the Top 10.",
                color=config.COLOR_INFO
            )
            view = LeaderboardView()
            await interaction.response.send_message(embed=embed, view=view)
        except Exception as e:
            import traceback; traceback.print_exc()
            await interaction.response.send_message("❌ Failed to load leaderboards.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardCog(bot))
