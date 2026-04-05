# cogs/gang.py
# /gang create, join, leave, info, members, bank deposit/withdraw

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from uuid import uuid4

import config
import db
import utils


class GangCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    gang_group = app_commands.Group(name="gang", description="Gang management")
    bank_group = app_commands.Group(name="bank", description="Gang bank", parent=gang_group)

    @gang_group.command(name="create", description="Create a new gang")
    @app_commands.describe(name="Gang name", tag="Short tag", gang_type="Type")
    @app_commands.choices(gang_type=[
        app_commands.Choice(name="Cartel", value="cartel"),
        app_commands.Choice(name="Syndicate", value="syndicate"),
        app_commands.Choice(name="Yakuza", value="yakuza"),
        app_commands.Choice(name="Brotherhood", value="brotherhood"),
    ])
    async def create(self, interaction: discord.Interaction, name: str, tag: str, gang_type: str):
        try:
            player = await db.ensure_player(str(interaction.user.id), interaction.user.display_name)
            if player.get("gang_id"):
                await interaction.response.send_message(embed=discord.Embed(title="❌ Already in a gang", color=config.COLOR_ERROR), ephemeral=True); return
            if player["level"] < config.GANG_CREATE_MIN_LEVEL:
                await interaction.response.send_message(embed=discord.Embed(title="🔒 Need Level 5", color=config.COLOR_ERROR), ephemeral=True); return
            if player["cash_wallet"] < config.GANG_CREATE_COST:
                await interaction.response.send_message(embed=discord.Embed(title="💸 Need $10,000", color=config.COLOR_ERROR), ephemeral=True); return
            database = db.get_db()
            if await database.gangs.find_one({"name": name}):
                await interaction.response.send_message(embed=discord.Embed(title="❌ Name taken", color=config.COLOR_ERROR), ephemeral=True); return
            player["cash_wallet"] -= config.GANG_CREATE_COST
            gang = {"_id": str(uuid4()), "name": name, "tag": f"[{tag.strip('[]')}]", "type": gang_type, "leader_id": str(interaction.user.id), "officers": [], "members": [], "level": 1, "xp": 0, "bank": 0, "bank_cap": 50000, "current_shift_points": 0, "shift_state": "inactive", "total_kills": 0, "shift_wins": 0, "created_at": datetime.now(timezone.utc)}
            await database.gangs.insert_one(gang)
            player["gang_id"] = gang["_id"]
            await db.save_player(player)
            await interaction.response.send_message(embed=discord.Embed(title=f"🏴 Created: {gang['tag']} {name}", description=f"Type: {gang_type.title()}\nLeader: **{interaction.user.display_name}**", color=config.COLOR_SUCCESS))
        except Exception: import traceback; traceback.print_exc(); await self._error(interaction)

    @gang_group.command(name="join", description="Join a gang")
    @app_commands.describe(name="Gang name")
    async def join(self, interaction: discord.Interaction, name: str):
        try:
            player = await db.ensure_player(str(interaction.user.id), interaction.user.display_name)
            if player.get("gang_id"):
                await interaction.response.send_message(embed=discord.Embed(title="❌ Already in a gang", color=config.COLOR_ERROR), ephemeral=True); return
            database = db.get_db()
            gang = await database.gangs.find_one({"name": name})
            if not gang:
                await interaction.response.send_message(embed=discord.Embed(title="❌ Gang not found", color=config.COLOR_ERROR), ephemeral=True); return
            total = 1 + len(gang.get("officers", [])) + len(gang.get("members", []))
            cap = config.GANG_BASE_MEMBER_CAP + gang["level"] * config.GANG_MEMBER_CAP_PER_LEVEL
            if total >= cap:
                await interaction.response.send_message(embed=discord.Embed(title="❌ Gang full", color=config.COLOR_ERROR), ephemeral=True); return
            await database.gangs.update_one({"_id": gang["_id"]}, {"$push": {"members": str(interaction.user.id)}})
            player["gang_id"] = gang["_id"]
            await db.save_player(player)
            await interaction.response.send_message(embed=discord.Embed(title=f"🏴 Joined {gang['tag']} {gang['name']}!", color=config.COLOR_SUCCESS))
        except Exception: import traceback; traceback.print_exc(); await self._error(interaction)

    @gang_group.command(name="leave", description="Leave your gang")
    async def leave(self, interaction: discord.Interaction):
        try:
            player = await db.ensure_player(str(interaction.user.id), interaction.user.display_name)
            if not player.get("gang_id"):
                await interaction.response.send_message(embed=discord.Embed(title="❌ Not in a gang", color=config.COLOR_ERROR), ephemeral=True); return
            gang = await db.get_gang(player["gang_id"])
            uid = str(interaction.user.id)
            if gang and gang["leader_id"] == uid:
                await interaction.response.send_message(embed=discord.Embed(title="❌ Leaders can't leave", color=config.COLOR_ERROR), ephemeral=True); return
            if gang:
                database = db.get_db()
                await database.gangs.update_one({"_id": gang["_id"]}, {"$pull": {"officers": uid, "members": uid}})
            player["gang_id"] = None
            await db.save_player(player)
            gname = f"{gang['tag']} {gang['name']}" if gang else "gang"
            await interaction.response.send_message(embed=discord.Embed(title=f"👋 Left {gname}", color=config.COLOR_WARNING))
        except Exception: import traceback; traceback.print_exc(); await self._error(interaction)

    @gang_group.command(name="info", description="View gang info")
    async def info(self, interaction: discord.Interaction):
        try:
            player = await db.ensure_player(str(interaction.user.id), interaction.user.display_name)
            if not player.get("gang_id"):
                await interaction.response.send_message(embed=discord.Embed(title="❌ Not in a gang", color=config.COLOR_ERROR), ephemeral=True); return
            gang = await db.get_gang(player["gang_id"])
            if not gang:
                await interaction.response.send_message(embed=discord.Embed(title="❌ Gang not found", color=config.COLOR_ERROR), ephemeral=True); return
            total = 1 + len(gang.get("officers", [])) + len(gang.get("members", []))
            cap = config.GANG_BASE_MEMBER_CAP + gang["level"] * config.GANG_MEMBER_CAP_PER_LEVEL
            shift_map = {"active": "🟢 Active", "resting": "🟡 Resting", "inactive": "⚪ Inactive"}
            embed = discord.Embed(title=f"🏴 {gang['tag']} {gang['name']}", color=config.COLOR_INFO)
            embed.add_field(name="Info", value=f"Type: {gang['type'].title()}\nLevel: **{gang['level']}**\nMembers: **{total}/{cap}**", inline=True)
            embed.add_field(name="Stats", value=f"🏦 Bank: {utils.format_cash(gang['bank'])}/{utils.format_cash(gang['bank_cap'])}\n⚔️ Kills: {gang['total_kills']}\n🏆 Wins: {gang['shift_wins']}", inline=True)
            embed.add_field(name="Shift", value=f"Status: {shift_map.get(gang['shift_state'], gang['shift_state'])}\nPoints: **{gang['current_shift_points']}**", inline=False)
            await interaction.response.send_message(embed=embed)
        except Exception: import traceback; traceback.print_exc(); await self._error(interaction)

    @gang_group.command(name="members", description="View members")
    async def members(self, interaction: discord.Interaction):
        try:
            player = await db.ensure_player(str(interaction.user.id), interaction.user.display_name)
            if not player.get("gang_id"):
                await interaction.response.send_message(embed=discord.Embed(title="❌ Not in a gang", color=config.COLOR_ERROR), ephemeral=True); return
            gang = await db.get_gang(player["gang_id"])
            if not gang: return
            lines = [f"👑 <@{gang['leader_id']}>"]
            for o in gang.get("officers", []): lines.append(f"⭐ <@{o}>")
            for m in gang.get("members", []): lines.append(f"• <@{m}>")
            embed = discord.Embed(title=f"🏴 {gang['tag']} {gang['name']} — Members", description="\n".join(lines), color=config.COLOR_INFO)
            await interaction.response.send_message(embed=embed)
        except Exception: import traceback; traceback.print_exc(); await self._error(interaction)

    @bank_group.command(name="deposit", description="Deposit into gang bank")
    @app_commands.describe(amount="Amount")
    async def deposit(self, interaction: discord.Interaction, amount: int):
        try:
            player = await db.ensure_player(str(interaction.user.id), interaction.user.display_name)
            if not player.get("gang_id"):
                await interaction.response.send_message(embed=discord.Embed(title="❌ Not in a gang", color=config.COLOR_ERROR), ephemeral=True); return
            if amount <= 0 or player["cash_wallet"] < amount:
                await interaction.response.send_message(embed=discord.Embed(title="💸 Invalid amount", color=config.COLOR_ERROR), ephemeral=True); return
            gang = await db.get_gang(player["gang_id"])
            if not gang: return
            bank_cap = int(gang["bank_cap"] * config.VIP_GANG_BANK_CAP_MULT) if utils.is_vip(player) else gang["bank_cap"]
            if gang["bank"] + amount > bank_cap:
                await interaction.response.send_message(embed=discord.Embed(title="🏦 Bank full", description=f"Space: {utils.format_cash(bank_cap - gang['bank'])}", color=config.COLOR_ERROR), ephemeral=True); return
            player["cash_wallet"] -= amount
            await db.get_db().gangs.update_one({"_id": gang["_id"]}, {"$inc": {"bank": amount}})
            await db.save_player(player)
            await interaction.response.send_message(embed=discord.Embed(title="🏦 Deposited!", description=f"{utils.format_cash(amount)} → gang bank", color=config.COLOR_SUCCESS))
        except Exception: import traceback; traceback.print_exc(); await self._error(interaction)

    @bank_group.command(name="withdraw", description="Withdraw from gang bank")
    @app_commands.describe(amount="Amount")
    async def withdraw(self, interaction: discord.Interaction, amount: int):
        try:
            player = await db.ensure_player(str(interaction.user.id), interaction.user.display_name)
            if not player.get("gang_id"):
                await interaction.response.send_message(embed=discord.Embed(title="❌ Not in a gang", color=config.COLOR_ERROR), ephemeral=True); return
            gang = await db.get_gang(player["gang_id"])
            if not gang: return
            uid = str(interaction.user.id)
            if uid != gang["leader_id"] and uid not in gang.get("officers", []):
                await interaction.response.send_message(embed=discord.Embed(title="❌ Officers/leader only", color=config.COLOR_ERROR), ephemeral=True); return
            if amount <= 0 or amount > gang["bank"]:
                await interaction.response.send_message(embed=discord.Embed(title="💸 Invalid amount", color=config.COLOR_ERROR), ephemeral=True); return
            player["cash_wallet"] += amount
            await db.get_db().gangs.update_one({"_id": gang["_id"]}, {"$inc": {"bank": -amount}})
            await db.save_player(player)
            await interaction.response.send_message(embed=discord.Embed(title="🏦 Withdrawn!", description=f"{utils.format_cash(amount)} → wallet", color=config.COLOR_SUCCESS))
        except Exception: import traceback; traceback.print_exc(); await self._error(interaction)

    async def _error(self, interaction):
        embed = discord.Embed(title="❌ Error", description="Something went wrong.", color=config.COLOR_ERROR)
        try: await interaction.response.send_message(embed=embed, ephemeral=True)
        except: await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GangCog(bot))
