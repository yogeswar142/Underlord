# cogs/hospital.py
import discord
from discord import app_commands
from discord.ext import commands
import random
import config
import db
import utils

class HospitalCog(commands.Cog):
    """Hospital system for viewing and reviving incapacitated players."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="hospital", description="View players in the Hospital and attempt to revive them")
    async def hospital(self, interaction: discord.Interaction):
        # We allow people in hospital to VIEW the hospital, just not to ACT.
        # But wait, the user said "just can use commands to see the leaderboards and news",
        # Actually in `utils.check_active()` we check for ALL commands that modify state.
        # The `/hospital` command allows viewing, and maybe a button to revive?
        # If we use a button to revive, the button click must run check_active().
        
        try:
            player = await db.ensure_player(str(interaction.user.id), interaction.user.display_name)
            
            # Fetch all players currently in hospital
            database = db.get_db()
            hospital_patients = await database.players.find({"state": "hospital"}).to_list(None)
            
            if not hospital_patients:
                embed = discord.Embed(
                    title="🏥  The Hospital is Empty",
                    description="No one is currently incapacitated.",
                    color=config.COLOR_INFO
                )
                await interaction.response.send_message(embed=embed)
                return
                
            # Sort by: Same Gang first -> Same Country -> User Level (desc)
            def patient_sort_key(p):
                score = 0
                if player.get("gang_id") and p.get("gang_id") == player.get("gang_id"):
                    score += 1000000
                if player.get("country") and p.get("country") == player.get("country"):
                    score += 100000
                score += p.get("level", 1)
                return score
                
            hospital_patients.sort(key=patient_sort_key, reverse=True)
            
            embed = discord.Embed(
                title="🏥  Hospital Wards",
                description="The following players are currently unconscious and recovering. You can try to revive them, but it costs Stamina and Courage.",
                color=config.COLOR_INFO
            )
            
            # We'll just show the top 10 for now
            lines = []
            for idx, p in enumerate(hospital_patients[:10], start=1):
                gang_tag = "🏳️"
                if player.get("gang_id") and p.get("gang_id") == player.get("gang_id"):
                    gang_tag = "🤝"
                    
                ctry = p.get("country") or "Unknown"
                country_tag = "🌍"
                if player.get("country") and ctry == player.get("country"):
                    country_tag = "📍"
                    
                hp_pct = int((p["renewable"]["hp"] / p["renewable"]["hp_max"]) * 100) if p["renewable"]["hp_max"] > 0 else 0
                
                lines.append(
                    f"**#{idx}** {gang_tag} {country_tag} **{p['username']}** | Level: {p.get('level', 1)}\n"
                    f"└ *Country*: **{ctry}** | *Recovery*: {hp_pct}% / 50%"
                )
                
            embed.description += "\n\n" + "\n".join(lines)
            
            # Subcommand hint
            embed.set_footer(text="Use /revive [user] to attempt a recovery.")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            import traceback; traceback.print_exc()
            await interaction.response.send_message("❌ Error loading hospital.", ephemeral=True)


    @app_commands.command(name="revive", description="Attempt to revive a player from the hospital")
    @app_commands.describe(user="The player to revive")
    async def revive(self, interaction: discord.Interaction, user: discord.User):
        if not await utils.check_active(interaction):
            return
            
        try:
            player = await db.ensure_player(str(interaction.user.id), interaction.user.display_name)
            target = await db.get_player(str(user.id))
            
            if not target:
                await interaction.response.send_message("❌ Player not found.", ephemeral=True)
                return
                
            if target["state"] != "hospital":
                await interaction.response.send_message("🏥 That player is not in the hospital.", ephemeral=True)
                return
                
            if interaction.user.id == user.id:
                await interaction.response.send_message("❌ You cannot revive yourself.", ephemeral=True)
                return
                
            # Costs
            stamina_cost = 10
            courage_cost = 5
            
            if player["renewable"]["stamina"] < stamina_cost or player["renewable"]["courage"] < courage_cost:
                embed = discord.Embed(
                    title="⚡  Exhausted", 
                    description=f"You need **{stamina_cost} Stamina** & **{courage_cost} Courage** to attempt a revive.", 
                    color=config.COLOR_ERROR
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
                
            player["renewable"]["stamina"] -= stamina_cost
            player["renewable"]["courage"] -= courage_cost
            
            # Luck-based success (50% base + small boost from level difference)
            lvl_diff = player["level"] - target.get("level", 1)
            chance = 0.50 + (lvl_diff * 0.01)
            chance = min(0.85, max(0.15, chance)) # Cap between 15% and 85%
            
            success = random.random() < chance
            
            if success:
                target["state"] = "normal"
                # Keep their HP as is, just remove the state lock (as requested)
                await db.save_player(target)
                
                # Reward the reviver slightly
                player["xp"] += 50
                await db.save_player(player)
                
                embed = discord.Embed(
                    title="💉  Revive Successful!",
                    description=f"You successfully treated **{target['username']}**! They are now free from the hospital.",
                    color=config.COLOR_SUCCESS
                )
                embed.add_field(name="XP Gained", value="⭐ +50 XP")
            else:
                await db.save_player(player) # Save deducted stats
                embed = discord.Embed(
                    title="🩸  Revive Failed!",
                    description=f"You tried your best, but **{target['username']}** is still in critical condition.",
                    color=config.COLOR_ERROR
                )
                
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            import traceback; traceback.print_exc()
            await interaction.response.send_message("❌ Error during revive.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(HospitalCog(bot))
