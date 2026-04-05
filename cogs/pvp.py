# cogs/pvp.py
# /attack and /rob commands — PvP combat system.
# Reads equipment_bonus for combat stats.

import random
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta

import config
import db
import utils
from shift import handle_kill_points

# ── Dramatic Flavor Text ─────────────────────────────────────────
ATTACK_VERBS = [
    "threw a devastating haymaker at",
    "lunged forward and slashed at",
    "pulled out a shiv and stabbed at",
    "smashed a bottle over the head of",
    "delivered a brutal uppercut to",
    "kicked the legs out from under",
    "blindsided with a steel pipe",
    "fired a warning shot that grazed",
    "sucker-punched",
    "headbutted",
    "hit with a flying knee strike at",
    "dropped a heavy combo on",
    "cracked knuckles and decked",
    "went full berserker mode on",
    "caught with a vicious right hook",
    "unleashed a flurry of punches on",
    "body-slammed",
    "swept the feet and stomped on",
    "landed a clean cross on",
    "charged in and tackled",
]

DODGE_TEXTS = [
    "barely dodged the attack!",
    "rolled sideways at the last second!",
    "blocked with their forearms!",
    "ducked just in time!",
    "parried the blow!",
    "took a glancing hit!",
    "staggered back but stayed standing!",
]

KILL_MESSAGES = [
    "💀 **{winner}** stood over **{loser}**'s unconscious body. The streets remember.",
    "💀 **{loser}** crumpled to the ground. **{winner}** spat and walked away.",
    "💀 **{winner}** delivered the final blow. **{loser}** won't be getting up anytime soon.",
    "💀 The fight is over. **{loser}** lies broken on the pavement. **{winner}** claims victory.",
    "💀 **{winner}** wiped the blood off their knuckles. **{loser}** was carried away on a stretcher.",
    "💀 Sirens wail in the distance. **{loser}** is down. **{winner}** vanishes into the shadows.",
    "💀 **{winner}** cracked their neck and looked down at **{loser}**. \"Stay down.\"",
    "💀 It's over. **{loser}** never saw **{winner}**'s last hit coming.",
]

MAX_ROUNDS = 10  # Cap the number of rounds


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

    @app_commands.command(name="attack", description="Attack another player (Turn-based combat)")
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

            # ── Gather Combat Stats ──────────────────────────
            atk_str = self._get_total_stat(attacker, "strength")
            atk_def = self._get_total_stat(attacker, "defense")
            atk_spd = self._get_total_stat(attacker, "speed")

            tgt_str = self._get_total_stat(target, "strength")
            tgt_def = self._get_total_stat(target, "defense")
            tgt_spd = self._get_total_stat(target, "speed")

            # HP pools for this fight
            atk_hp = attacker["renewable"]["hp"]
            tgt_hp = target["renewable"]["hp"]
            atk_hp_max = attacker["renewable"]["hp_max"]
            tgt_hp_max = target["renewable"]["hp_max"]

            atk_name = attacker["username"]
            tgt_name = target["username"]

            # ── Send initial embed ───────────────────────────
            embed = discord.Embed(
                title="⚔️  FIGHT!",
                description=(
                    f"**{atk_name}** challenges **{tgt_name}** to a street brawl!\n\n"
                    f"❤️ {atk_name}: {atk_hp}/{atk_hp_max} HP\n"
                    f"❤️ {tgt_name}: {tgt_hp}/{tgt_hp_max} HP\n\n"
                    f"*The fight begins...*"
                ),
                color=0x2b2d31,
            )
            await interaction.response.send_message(embed=embed)
            msg = await interaction.original_response()

            # ── Turn-based combat loop ──────────────────────
            combat_log = []
            round_num = 0
            winner = None
            loser = None

            while atk_hp > 0 and tgt_hp > 0 and round_num < MAX_ROUNDS:
                round_num += 1
                await asyncio.sleep(2.5)

                # ── Attacker's turn ──────────────────────────
                # Damage scales heavily with strength, reduced by target defense
                weapon_dmg = int(atk_str * 2.5)  # Scale strength making gear matter much more
                base_dmg = max(1, weapon_dmg + random.randint(-5, 10))
                reduction = max(0, int((tgt_def * 1.5) * 0.3) + random.randint(-2, 5))
                dmg = max(1, int(base_dmg - reduction))

                tgt_hp = max(0, tgt_hp - dmg)
                verb = random.choice(ATTACK_VERBS)
                combat_log.append(f"**{atk_name}** {verb} **{tgt_name}** for **{dmg}** damage!")

                if tgt_hp <= 0:
                    winner = attacker
                    loser = target
                    break

                # ── Target's turn ────────────────────────────
                weapon_dmg = int(tgt_str * 2.5)
                base_dmg = max(1, weapon_dmg + random.randint(-5, 10))
                reduction = max(0, int((atk_def * 1.5) * 0.3) + random.randint(-2, 5))
                dmg = max(1, int(base_dmg - reduction))

                atk_hp = max(0, atk_hp - dmg)
                verb = random.choice(ATTACK_VERBS)
                combat_log.append(f"**{tgt_name}** {verb} **{atk_name}** for **{dmg}** damage!")

                if atk_hp <= 0:
                    winner = target
                    loser = attacker
                    break

                # ── Update the live embed ────────────────────
                # Show only last 4 log lines to keep it clean
                recent_log = "\n".join(combat_log[-4:])

                progress_embed = discord.Embed(
                    title=f"⚔️  ROUND {round_num}",
                    description=(
                        f"❤️ {atk_name}: **{atk_hp}**/{atk_hp_max} HP\n"
                        f"❤️ {tgt_name}: **{tgt_hp}**/{tgt_hp_max} HP\n\n"
                        f"{recent_log}"
                    ),
                    color=0x2b2d31,
                )
                progress_embed.set_footer(text=f"Round {round_num}/{MAX_ROUNDS}")

                try:
                    await msg.edit(embed=progress_embed)
                except Exception:
                    pass

            # ── If max rounds hit with no kill ────────────────
            if winner is None:
                # Whoever has more HP left wins, loser is forced to 0 HP
                if atk_hp >= tgt_hp:
                    winner = attacker
                    loser = target
                    tgt_hp = 0
                else:
                    winner = target
                    loser = attacker
                    atk_hp = 0

            # Determine which is the attacker vs target for saving
            attacker_won = (winner["_id"] == attacker["_id"])

            # ── Final HP updates ─────────────────────────────
            attacker["renewable"]["hp"] = atk_hp
            target["renewable"]["hp"] = tgt_hp

            # ── Process kill (hp == 0) ───────────────────────
            killed = loser["renewable"]["hp"] == 0
            if killed:
                loser["state"] = "hospital"

            # ── Rewards ──────────────────────────────────────
            winner_spd = self._get_total_stat(winner, "speed")
            # Steal coins from loser's wallet based on winner's speed
            steal_pct = config.KILL_BASE_STEAL_PCT + max(0, winner_spd * config.KILL_SPEED_STEAL_BONUS)
            steal_pct = min(0.50, steal_pct)  # Max 50%

            stolen = min(int(loser["cash_wallet"] * steal_pct), loser["cash_wallet"])
            winner["cash_wallet"] += stolen
            loser["cash_wallet"] -= stolen

            xp_gain = 100 + (winner_spd // 5)
            winner["xp"] += xp_gain
            winner, leveled = utils.check_level_up(winner)

            # ── Shield the loser ─────────────────────────────
            now = datetime.now(timezone.utc)
            loser["shield_until"] = now + timedelta(seconds=config.SHIELD_DURATION_SECONDS)

            # ── Country points (only on actual kill) ─────────
            country_msg = ""
            if killed:
                database = db.get_db()
                w_country = winner.get("country")
                l_country = loser.get("country")
                if w_country and l_country and w_country != l_country:
                    await database.countries.update_one(
                        {"_id": w_country}, {"$inc": {"points": 1}}, upsert=True
                    )
                    tc = await database.countries.find_one({"_id": l_country})
                    if tc and tc.get("points", 0) > 0:
                        await database.countries.update_one(
                            {"_id": l_country}, {"$inc": {"points": -1}}
                        )
                    country_msg = f"\n🌍 +1 **{w_country}** | -1 **{l_country}**"

            # ── Gang shift points (ONLY if BOTH are in gangs) ──
            gang_msg = ""
            if killed:
                if not 'database' in dir(): database = db.get_db()
                w_gang_id = winner.get("gang_id")
                l_gang_id = loser.get("gang_id")
                if w_gang_id and l_gang_id:
                    w_gang = await db.get_gang(w_gang_id)
                    l_gang = await db.get_gang(l_gang_id)

                    if w_gang and w_gang.get("shift_state") == "active":
                        await database.gangs.update_one(
                            {"_id": w_gang_id},
                            {"$inc": {"current_shift_points": config.SHIFT_KILL_POINTS}},
                        )
                        gang_msg += f"\n🏴 +{config.SHIFT_KILL_POINTS} pts [{w_gang.get('tag', '')}]"

                    if l_gang and l_gang.get("shift_state") == "active":
                        new_pts = max(0, l_gang.get("current_shift_points", 0) - config.SHIFT_KILL_POINTS)
                        await database.gangs.update_one(
                            {"_id": l_gang_id},
                            {"$set": {"current_shift_points": new_pts}},
                        )
                        gang_msg += f" | -{config.SHIFT_KILL_POINTS} pts [{l_gang.get('tag', '')}]"

            # ── News broadcast ───────────────────────────────
            if killed:
                news_text = f"**{winner['username']}** hospitalised **{loser['username']}** in combat!"
                if gang_msg:
                    news_text += gang_msg
                if country_msg:
                    news_text += country_msg
                asyncio.create_task(utils.add_news(news_text))

            # ── Save both players ────────────────────────────
            await db.save_player(attacker)
            await db.save_player(target)

            # ── Build final dramatic embed ───────────────────
            await asyncio.sleep(2)

            kill_line = random.choice(KILL_MESSAGES).format(
                winner=winner["username"], loser=loser["username"]
            )

            hospital_line = ""
            if killed:
                hospital_line = f"\n\n🏥 **{loser['username']}** has been sent to the Hospital!"

            final_embed = discord.Embed(
                title="⚔️  THE FIGHT IS OVER",
                description=(
                    f"{kill_line}\n\n"
                    f"───────────────────\n"
                    f"❤️ {atk_name}: **{atk_hp}** HP\n"
                    f"❤️ {tgt_name}: **{tgt_hp}** HP\n"
                    f"───────────────────\n\n"
                    f"**Rewards for {winner['username']}:**\n"
                    f"💵 Looted: {utils.format_cash(stolen)}\n"
                    f"⭐ +{xp_gain} XP\n"
                    f"🛡️ {loser['username']} shielded for {config.SHIELD_DURATION_SECONDS // 60}min"
                    f"{hospital_line}{country_msg}{gang_msg}"
                ),
                color=config.COLOR_SUCCESS if attacker_won else config.COLOR_ERROR,
            )

            if leveled:
                final_embed.add_field(
                    name="🎉 LEVEL UP!",
                    value=f"**{winner['username']}** is now **Level {winner['level']}**!",
                    inline=False,
                )

            final_embed.set_footer(text=f"Fight lasted {round_num} round(s)")

            try:
                await msg.edit(embed=final_embed)
            except Exception:
                pass

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

                if stolen > 0:
                    asyncio.create_task(utils.add_news(f"**{attacker['username']}** successfully robbed **{target['username']}** for {utils.format_cash(stolen)}!"))

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

                asyncio.create_task(utils.add_news(f"**{attacker['username']}** was sent to Jail for a failed robbery attempt on **{target['username']}**!"))

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
