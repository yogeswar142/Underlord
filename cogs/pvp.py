# cogs/pvp.py
# /attack and /rob commands — PvP combat system.
# Reads equipment_bonus for combat stats.

import random
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta

import config
import db
import utils
from shift import handle_kill_points


class PvPCog(commands.Cog):
    """Player vs Player combat — Kill and Rob."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Shared validation ─────────────────────────────────────

    async def _validate_pvp(
        self,
        interaction: discord.Interaction,
        target_user: discord.User,
        cost_type: str,  # "courage" or "stamina"
        cost_amount: int,
    ) -> tuple[dict | None, dict | None]:
        """
        Validate PvP prerequisites. Returns (attacker, target) or (None, None) on failure.
        Sends error embed on failure.
        """
        if target_user.id == interaction.user.id:
            embed = discord.Embed(
                title="❌  Can't Target Yourself",
                description="You can't attack yourself.",
                color=config.COLOR_ERROR,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return None, None

        if target_user.bot:
            embed = discord.Embed(
                title="❌  Invalid Target",
                description="You can't attack bots.",
                color=config.COLOR_ERROR,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return None, None

        attacker = await db.ensure_player(
            str(interaction.user.id), interaction.user.display_name
        )
        target = await db.get_player(str(target_user.id))

        if not target:
            embed = discord.Embed(
                title="❌  Target Not Found",
                description=f"**{target_user.display_name}** hasn't started playing yet.",
                color=config.COLOR_ERROR,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return None, None

        if attacker["faction"] is None:
            embed = discord.Embed(
                title="⚔️  Choose a Faction First",
                description="Use `/profile` to select your faction.",
                color=config.COLOR_WARNING,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return None, None

        # Check attacker shield — if shielded, attacking drops it
        now = datetime.now(timezone.utc)
        if attacker.get("shield_until"):
            s = attacker["shield_until"]
            if s.tzinfo is None:
                s = s.replace(tzinfo=timezone.utc)
            if s > now:
                # Drop shield on attack initiation
                attacker["shield_until"] = None
                await db.save_player(attacker)

        # Check target shield
        if target.get("shield_until"):
            s = target["shield_until"]
            if s.tzinfo is None:
                s = s.replace(tzinfo=timezone.utc)
            if s > now:
                rem = (s - now).total_seconds()
                embed = discord.Embed(
                    title="🛡️  Target is Shielded",
                    description=f"**{target['username']}** has a shield for **{utils.format_cooldown(rem)}**.",
                    color=config.COLOR_WARNING,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return None, None

        # Check level gap
        atk_gang = None
        if attacker.get("gang_id"):
            atk_gang = await db.get_gang(attacker["gang_id"])
        in_shift = utils.in_active_gang_shift(atk_gang)

        if not utils.level_gap_ok(attacker["level"], target["level"], in_shift):
            gap = config.PVP_LEVEL_GAP_GANG_WAR if in_shift else config.PVP_LEVEL_GAP
            embed = discord.Embed(
                title="❌  Level Gap Too Large",
                description=f"Max level difference: **{gap}**. You: Lv.{attacker['level']}, Target: Lv.{target['level']}.",
                color=config.COLOR_ERROR,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return None, None

        # Check cost
        if cost_type == "courage":
            if attacker["renewable"]["courage"] < cost_amount:
                embed = discord.Embed(
                    title="🦁  Not Enough Courage",
                    description=f"Need **{cost_amount}** courage. You have **{attacker['renewable']['courage']}**.",
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return None, None
        elif cost_type == "stamina":
            if attacker["renewable"]["stamina"] < cost_amount:
                embed = discord.Embed(
                    title="⚡  Not Enough Stamina",
                    description=f"Need **{cost_amount}** stamina. You have **{attacker['renewable']['stamina']}**.",
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return None, None

        return attacker, target

    def _get_total_stat(self, player: dict, stat: str) -> int:
        """Get a player's total stat = base + equipment_bonus."""
        base = player["stats"].get(stat, 0)
        bonus = player.get("equipment_bonus", {}).get(stat, 0)
        return base + bonus

    # ── /attack ───────────────────────────────────────────────

    @app_commands.command(name="attack", description="Attack another player (Kill)")
    @app_commands.describe(user="The player to attack")
    async def attack(self, interaction: discord.Interaction, user: discord.User):
        if not await utils.check_active(interaction):
            return
            
        try:
            attacker, target = await self._validate_pvp(
                interaction, user, "courage", config.PVP_ATTACK_COURAGE_COST
            )
            if not attacker or not target:
                return

            # Deduct courage
            attacker["renewable"]["courage"] -= config.PVP_ATTACK_COURAGE_COST

            # Combat roll using equipment_bonus stats
            atk_str = self._get_total_stat(attacker, "strength")
            atk_def = self._get_total_stat(attacker, "defense")
            tgt_str = self._get_total_stat(target, "strength")
            tgt_def = self._get_total_stat(target, "defense")

            attacker_power = atk_str + int(atk_def * 0.3) + random.randint(-10, 10)
            target_power = tgt_str + int(tgt_def * 0.3) + random.randint(-10, 10)

            now = datetime.now(timezone.utc)

            if attacker_power >= target_power:
                # ── WIN ──────────────────────────────────────
                atk_speed = self._get_total_stat(attacker, "speed")
                tgt_speed = self._get_total_stat(target, "speed")

                steal_pct = config.KILL_BASE_STEAL_PCT + max(
                    0, (atk_speed - tgt_speed) * config.KILL_SPEED_STEAL_BONUS
                )
                stolen = min(
                    int(target["cash_wallet"] * steal_pct),
                    target["cash_wallet"],
                )

                attacker["cash_wallet"] += stolen
                target["cash_wallet"] -= stolen

                hp_damage = random.randint(20, 40)
                target["renewable"]["hp"] = max(
                    0, target["renewable"]["hp"] - hp_damage
                )
                
                killed = target["renewable"]["hp"] == 0
                hospital_msg = ""
                if killed:
                    target["state"] = "hospital"
                    hospital_msg = f"\n🏥 **{target['username']}** has been sent to the Hospital!"
                    
                    # Country Kill Logic
                    database = db.get_db()
                    atk_country = attacker.get("country")
                    tgt_country = target.get("country")
                    if atk_country and tgt_country and atk_country != tgt_country:
                        await database.countries.update_one(
                            {"_id": atk_country}, {"$inc": {"points": 1}}, upsert=True
                        )
                        # We don't want negative points generally, but design says -1
                        # Let's get tgt country points and max 0
                        tc = await database.countries.find_one({"_id": tgt_country})
                        if tc and tc.get("points", 0) > 0:
                            await database.countries.update_one(
                                {"_id": tgt_country}, {"$inc": {"points": -1}}
                            )

                attacker["xp"] += 100

                # Shield target
                target["shield_until"] = now + timedelta(
                    seconds=config.SHIELD_DURATION_SECONDS
                )

                # Gang shift points
                if not 'database' in locals(): database = db.get_db()
                await handle_kill_points(
                    database, attacker["_id"], target["_id"]
                )

                # Level up check
                attacker, leveled = utils.check_level_up(attacker)

                embed = discord.Embed(
                    title=f"⚔️  Victory! You defeated {target['username']}!",
                    description=(
                        f"💪 Power: **{attacker_power}** vs {target_power}\n\n"
                        f"💵 Stolen: {utils.format_cash(stolen)}\n"
                        f"❤️ Dealt {hp_damage} HP damage\n"
                        f"⭐ +100 XP\n"
                        f"🛡️ Target shielded for {config.SHIELD_DURATION_SECONDS // 60}min{hospital_msg}"
                    ),
                    color=config.COLOR_SUCCESS,
                )
                if leveled:
                    embed.add_field(
                        name="🎉 LEVEL UP!",
                        value=f"You are now **Level {attacker['level']}**!",
                        inline=False,
                    )
            else:
                # ── LOSS ─────────────────────────────────────
                hp_damage = random.randint(15, 30)
                attacker["renewable"]["hp"] = max(
                    0, attacker["renewable"]["hp"] - hp_damage
                )
                
                killed = attacker["renewable"]["hp"] == 0
                hospital_msg = ""
                if killed:
                    attacker["state"] = "hospital"
                    hospital_msg = f"\n🏥 **You** have been sent to the Hospital!"

                # Target gang gets defense points
                if not 'database' in locals(): database = db.get_db()
                if target.get("gang_id"):
                    tgt_gang = await db.get_gang(target["gang_id"])
                    if tgt_gang and tgt_gang.get("shift_state") == "active":
                        await database.gangs.update_one(
                            {"_id": target["gang_id"]},
                            {"$inc": {"current_shift_points": config.SHIFT_KILL_POINTS}},
                        )

                # Shield target anyway
                target["shield_until"] = now + timedelta(
                    seconds=config.SHIELD_DURATION_SECONDS
                )

                embed = discord.Embed(
                    title=f"💀  Defeat! {target['username']} fought you off!",
                    description=(
                        f"💪 Power: {attacker_power} vs **{target_power}**\n\n"
                        f"❤️ You took {hp_damage} HP damage\n"
                        f"🛡️ Target shielded for {config.SHIELD_DURATION_SECONDS // 60}min{hospital_msg}"
                    ),
                    color=config.COLOR_ERROR,
                )

            await db.save_player(attacker)
            await db.save_player(target)
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            import traceback; traceback.print_exc()
            await self._error(interaction)

    # ── /rob ──────────────────────────────────────────────────

    @app_commands.command(name="rob", description="Rob another player (Speed contest)")
    @app_commands.describe(user="The player to rob")
    async def rob(self, interaction: discord.Interaction, user: discord.User):
        if not await utils.check_active(interaction):
            return
            
        try:
            attacker, target = await self._validate_pvp(
                interaction, user, "stamina", config.PVP_ROB_STAMINA_COST
            )
            if not attacker or not target:
                return

            # Check rob cooldown
            remaining = utils.cooldown_remaining(
                attacker["cooldowns"].get("rob"), 60  # 60-second cooldown
            )
            if remaining > 0:
                embed = discord.Embed(
                    title="⏳  Rob Cooldown",
                    description=f"Wait **{utils.format_cooldown(remaining)}** before robbing again.",
                    color=config.COLOR_WARNING,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Deduct stamina
            attacker["renewable"]["stamina"] -= config.PVP_ROB_STAMINA_COST

            # Speed contest
            atk_speed = self._get_total_stat(attacker, "speed")
            tgt_speed = self._get_total_stat(target, "speed")

            attacker_roll = atk_speed + random.randint(-5, 5)
            target_roll = tgt_speed + random.randint(-5, 5)

            attacker["cooldowns"]["rob"] = datetime.now(timezone.utc)

            if attacker_roll > target_roll:
                # ── WIN ──────────────────────────────────────
                steal_pct = config.ROB_BASE_STEAL_PCT + max(
                    0, (atk_speed - tgt_speed) * config.ROB_SPEED_STEAL_BONUS
                )
                stolen = min(
                    int(target["cash_wallet"] * steal_pct),
                    target["cash_wallet"],
                )

                attacker["cash_wallet"] += stolen
                target["cash_wallet"] -= stolen

                embed = discord.Embed(
                    title=f"🏃  Robbery Successful!",
                    description=(
                        f"⚡ Speed: **{attacker_roll}** vs {target_roll}\n\n"
                        f"💵 Stolen: {utils.format_cash(stolen)} from **{target['username']}**\n"
                        f"No shield applied. No HP damage."
                    ),
                    color=config.COLOR_SUCCESS,
                )
            else:
                # ── LOSS ─────────────────────────────────────
                # Arrested
                prison_mins = min(5, max(1, attacker["level"] // 20))
                attacker["state"] = "prison"
                attacker["prison_until"] = datetime.now(timezone.utc) + timedelta(minutes=prison_mins)
                
                embed = discord.Embed(
                    title=f"🚔  Busted! Robbery Failed!",
                    description=(
                        f"⚡ Speed: {attacker_roll} vs **{target_roll}**\n\n"
                        f"**{target['username']}** was too fast. You got caught and were sent to **Prison** for {prison_mins} minute(s)!"
                    ),
                    color=config.COLOR_ERROR,
                )

            await db.save_player(attacker)
            await db.save_player(target)
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            import traceback; traceback.print_exc()
            await self._error(interaction)

    # ── Helpers ───────────────────────────────────────────────

    async def _error(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="❌  Error",
            description="Something went wrong. Please try again.",
            color=config.COLOR_ERROR,
        )
        try:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.errors.InteractionResponded:
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PvPCog(bot))
