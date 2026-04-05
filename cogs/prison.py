# cogs/prison.py
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
import config
import db
import utils

class PrisonCog(commands.Cog):
    """Prison system for viewing and breaking out jailed players."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="prison", description="View players in Prison and attempt to break them out")
    async def prison(self, interaction: discord.Interaction):
        try:
            player = await db.ensure_player(str(interaction.user.id), interaction.user.display_name)
            
            # Fetch players in prison (make sure they are actually still in by checking prison_until)
            database = db.get_db()
            now = datetime.now(timezone.utc)
            prison_inmatesRaw = await database.players.find({"state": "prison"}).to_list(None)
            
            prison_inmates = []
            for p in prison_inmatesRaw:
                p_until = p.get("prison_until")
                if p_until:
                    if p_until.tzinfo is None:
                        p_until = p_until.replace(tzinfo=timezone.utc)
                    if now < p_until:
                        prison_inmates.append(p)
                    else:
                        # They should be free, tick async will handle it soon
                        pass
                        
            if not prison_inmates:
                embed = discord.Embed(
                    title="🚔  The Prison is Empty",
                    description="No one is currently behind bars.",
                    color=config.COLOR_INFO
                )
                await interaction.response.send_message(embed=embed)
                return
                
            # Sort by: Same Gang first -> Same Country -> User Level (desc)
            def inmate_sort_key(p):
                score = 0
                if player.get("gang_id") and p.get("gang_id") == player.get("gang_id"):
                    score += 1000000
                if player.get("country") and p.get("country") == player.get("country"):
                    score += 100000
                score += p.get("level", 1)
                return score
                
            prison_inmates.sort(key=inmate_sort_key, reverse=True)
            
            embed = discord.Embed(
                title="🚔  Prison Cell Block",
                description="The following players are currently locked up. You can attempt to bust them out if you have the Stamina.",
                color=config.COLOR_INFO
            )
            
            lines = []
            for idx, p in enumerate(prison_inmates[:10], start=1):
                gang_tag = "🏳️"
                if player.get("gang_id") and p.get("gang_id") == player.get("gang_id"):
                    gang_tag = "🤝"
                    
                ctry = p.get("country") or "Unknown"
                country_tag = "🌍"
                if player.get("country") and ctry == player.get("country"):
                    country_tag = "📍"
                    
                p_until = p.get("prison_until")
                if p_until.tzinfo is None:
                    p_until = p_until.replace(tzinfo=timezone.utc)
                rem_seconds = max(0, (p_until - now).total_seconds())
                
                lines.append(
                    f"**#{idx}** {gang_tag} {country_tag} **{p['username']}** | Level: {p.get('level', 1)}\n"
                    f"└ *Country*: **{ctry}** | *Time Left*: {utils.format_cooldown(rem_seconds)}"
                )
                
            embed.description += "\n\n" + "\n".join(lines)
            
            embed.set_footer(text="Use /bust [user] to attempt a breakout.")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            import traceback; traceback.print_exc()
            await interaction.response.send_message("❌ Error loading prison.", ephemeral=True)


    @app_commands.command(name="bust", description="Attempt to bust a player out of prison (Depends on your Speed)")
    @app_commands.describe(user="The player to bust out")
    async def bust(self, interaction: discord.Interaction, user: discord.User):
        if not await utils.check_active(interaction):
            return
            
        try:
            player = await db.ensure_player(str(interaction.user.id), interaction.user.display_name)
            target = await db.get_player(str(user.id))
            
            if not target:
                await interaction.response.send_message("❌ Player not found.", ephemeral=True)
                return
                
            if target["state"] != "prison":
                await interaction.response.send_message("🚔 That player is not in prison.", ephemeral=True)
                return
                
            now = datetime.now(timezone.utc)
            p_until = target.get("prison_until")
            if p_until:
                if p_until.tzinfo is None:
                    p_until = p_until.replace(tzinfo=timezone.utc)
                if now >= p_until:
                    await interaction.response.send_message("🚔 That player's sentence is already over.", ephemeral=True)
                    return
                
            if interaction.user.id == user.id:
                await interaction.response.send_message("❌ You cannot bust yourself out while you're not in prison.", ephemeral=True)
                return
                
            # Costs
            stamina_cost = 15
            
            if player["renewable"]["stamina"] < stamina_cost:
                embed = discord.Embed(
                    title="⚡  Exhausted", 
                    description=f"You need **{stamina_cost} Stamina** to attempt a bust.", 
                    color=config.COLOR_ERROR
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
                
            player["renewable"]["stamina"] -= stamina_cost
            
            # Success chance scales heavily with speed
            player_speed = player["stats"].get("speed", 1)
            target_level = target.get("level", 1)
            
            # Base chance 30%. Add 1% for every 10 Speed.
            chance = 0.30 + (player_speed / 1000)
            chance = min(0.90, max(0.10, chance)) 
            
            import random
            success = random.random() < chance
            
            if success:
                target["state"] = "normal"
                target["prison_until"] = None
                await db.save_player(target)
                
                # Reward
                xp_gain = 75
                player["xp"] += xp_gain
                player,_ = utils.check_level_up(player)
                await db.save_player(player)
                
                embed = discord.Embed(
                    title="🚨  Bust Successful!",
                    description=f"You managed to evade the guards and free **{target['username']}**!",
                    color=config.COLOR_SUCCESS
                )
                embed.add_field(name="XP Gained", value=f"⭐ +{xp_gain} XP")
            else:
                await db.save_player(player)
                embed = discord.Embed(
                    title="📸  Bust Failed!",
                    description=f"You triggered the alarms and had to run away! **{target['username']}** is still in prison.",
                    color=config.COLOR_ERROR
                )
                
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            import traceback; traceback.print_exc()
            await interaction.response.send_message("❌ Error during jailbreak.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(PrisonCog(bot))
