# cogs/status.py
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta

import config
import db
import utils

class StatusCog(commands.Cog):
    """View active timers and refill statuses."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="status", description="View all your running timers, refilling stats, and statuses")
    async def status(self, interaction: discord.Interaction):
        try:
            player = await db.ensure_player(str(interaction.user.id), interaction.user.display_name)
            
            embed = discord.Embed(
                title=f"⏱️  {player['username']}'s Status & Timers",
                color=config.COLOR_INFO
            )
            
            now = datetime.now(timezone.utc)
            
            # --- 1. Refill Stats ---
            r = player["renewable"]
            is_vip = (player.get("vip_active_until") is not None and player["vip_active_until"] > now)
            rate = config.REFILL_VIP_PCT if is_vip else config.REFILL_FREE_PCT
            
            stats_text = (
                f"⚡ **Stamina**: {r['stamina']}/{r['stamina_max']} (+{int(r['stamina_max'] * rate)}/min)\n"
                f"🦁 **Courage**: {r['courage']}/{r['courage_max']} (+{int(r['courage_max'] * rate)}/min)\n"
                f"❤️ **HP**: {r['hp']}/{r['hp_max']} (+{int(r['hp_max'] * rate)}/min)\n"
            )
            embed.add_field(name="Biological Refills", value=stats_text, inline=False)
            
            # --- 2. Cooldowns / Time-based activities (Farm, Crimes, etc) ---
            activities = []
            
            # Farm
            fs = player["cooldowns"].get("farm_start")
            farm_lvl = player["buildings"].get("farm", 0)
            if fs and farm_lvl > 0:
                if fs.tzinfo is None:
                    fs = fs.replace(tzinfo=timezone.utc)
                cycle_min = config.BUILDINGS["farm"]["cycle_minutes"][farm_lvl - 1]
                ready_at = fs + timedelta(minutes=cycle_min)
                
                if now < ready_at:
                    activities.append(f"🌾 **Farm ready in:** <t:{int(ready_at.timestamp())}:R>")
                else:
                    activities.append("🌾 **Farm ready!** (Use `/farm collect`)")
            
            # Wanted
            wanted_until = player.get("wanted_until")
            if wanted_until:
                if wanted_until.tzinfo is None:
                    wanted_until = wanted_until.replace(tzinfo=timezone.utc)
                if now < wanted_until:
                    activities.append(f"🚨 **Wanted status clears in:** <t:{int(wanted_until.timestamp())}:R>")

            # Cooldowns (Crime, Rob, Attack)
            for cd_key, name in [("crime", "Crime"), ("attack", "Attack"), ("rob", "Rob")]:
                cd_time = player["cooldowns"].get(cd_key)
                if cd_time:
                    if cd_time.tzinfo is None:
                        cd_time = cd_time.replace(tzinfo=timezone.utc)
                    
                    if cd_key == "crime":
                        wait_sec = 60 # crime has varied cooldowns, just rough estimate or we can just say 'Ready'
                        # Actually we can't easily fetch exact crime cooldown here because crime is chosen.
                        pass
                    elif cd_key == "attack":
                        due = cd_time + timedelta(seconds=config.PVP_COOLDOWN_SECONDS)
                        if now < due:
                            activities.append(f"⚔️ **Attack cooldown:** <t:{int(due.timestamp())}:R>")
                    elif cd_key == "rob":
                        due = cd_time + timedelta(seconds=config.PVP_COOLDOWN_SECONDS)
                        if now < due:
                            activities.append(f"🏃 **Rob cooldown:** <t:{int(due.timestamp())}:R>")

            if activities:
                embed.add_field(name="Activities & Timers", value="\n".join(activities), inline=False)
            
            # --- 3. Ships at Sea ---
            fleet = player.get("fleet", [])
            ships_at_sea = []
            for s in fleet:
                if s.get("at_sea"):
                    ret = s.get("returns_at")
                    if ret:
                        if ret.tzinfo is None:
                            ret = ret.replace(tzinfo=timezone.utc)
                        if now < ret:
                            ships_at_sea.append(f"⛵ **{s['name']}** returns in <t:{int(ret.timestamp())}:R>")
                        else:
                            ships_at_sea.append(f"⛵ **{s['name']}** returned! (Use `/ship collect`)")
            if ships_at_sea:
                embed.add_field(name="Fleet Status", value="\n".join(ships_at_sea), inline=False)
                
            # --- 4. Special States (Hospital/Prison) ---
            state = player.get("state", "normal")
            if state == "prison":
                p_until = player.get("prison_until")
                if p_until:
                    if p_until.tzinfo is None:
                        p_until = p_until.replace(tzinfo=timezone.utc)
                    if now < p_until:
                        embed.add_field(name="🚔 Behind Bars", value=f"Your sentence ends in <t:{int(p_until.timestamp())}:R>", inline=False)
                    else:
                         embed.add_field(name="🚔 Behind Bars", value="Your sentence just ended. Wait a moment for release.", inline=False)
            elif state == "hospital":
                # Hospital is HP based, calculate rough ticks needed
                hp_target = int(player["renewable"]["hp_max"] * 0.5)
                missing_hp = hp_target - player["renewable"]["hp"]
                if missing_hp > 0:
                    hp_per_min = int(player["renewable"]["hp_max"] * rate)
                    mins_left = (missing_hp // hp_per_min) + 1 if hp_per_min > 0 else 999
                    est_time = now + timedelta(minutes=mins_left)
                    embed.add_field(name="🏥 Incapacitated", value=f"You will recover to 50% HP roughly <t:{int(est_time.timestamp())}:R>.", inline=False)
                
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            import traceback; traceback.print_exc()
            await interaction.response.send_message("❌ Status error", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(StatusCog(bot))
