# cogs/buildings.py
# /build, /upgrade, /collect, /farm, /ship commands.

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta

import config
import db
import utils


class BuildingsCog(commands.Cog):
    """Building construction, upgrades, and passive income."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── /build ────────────────────────────────────────────────

    @app_commands.command(name="build", description="Construct a new building")
    @app_commands.describe(building="The building to construct")
    @app_commands.choices(building=[
        app_commands.Choice(name=f"{v.get('emoji', '🏗️')} {k.replace('_', ' ').title()}", value=k)
        for k, v in config.BUILDINGS.items()
    ])
    async def build(
        self, interaction: discord.Interaction, building: str
    ):
        if not await utils.check_active(interaction):
            return
            
        try:
            player = await db.ensure_player(
                str(interaction.user.id), interaction.user.display_name
            )
            if player["faction"] is None:
                await self._no_faction(interaction)
                return

            bldg = config.BUILDINGS.get(building)
            if not bldg:
                await interaction.response.send_message(
                    embed=discord.Embed(title="❌ Invalid building.", color=config.COLOR_ERROR),
                    ephemeral=True,
                )
                return

            # Check already built
            if player["buildings"].get(building, 0) > 0:
                embed = discord.Embed(
                    title="🏗️  Already Built",
                    description=f"Your **{building.replace('_', ' ').title()}** is already at level {player['buildings'][building]}. Use `/upgrade` to improve it.",
                    color=config.COLOR_WARNING,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Check unlock level
            if player["level"] < bldg["unlock_level"]:
                embed = discord.Embed(
                    title="🔒  Locked",
                    description=f"You need **Level {bldg['unlock_level']}** to build a {building.replace('_', ' ').title()}. You are Level {player['level']}.",
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Check cost
            cost = bldg["costs"][0]
            if player["cash_wallet"] < cost:
                embed = discord.Embed(
                    title="💸  Not Enough Cash",
                    description=f"Building costs {utils.format_cash(cost)}. You have {utils.format_cash(player['cash_wallet'])}.",
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Build it
            player["cash_wallet"] -= cost
            player["buildings"][building] = 1
            await db.save_player(player)

            emoji = bldg.get("emoji", "🏗️")
            embed = discord.Embed(
                title=f"{emoji}  {building.replace('_', ' ').title()} — Built!",
                description=(
                    f"Your {building.replace('_', ' ').title()} is now **Level 1**.\n"
                    f"💵 Cost: {utils.format_cash(cost)}\n"
                    f"💰 Remaining: {utils.format_cash(player['cash_wallet'])}"
                ),
                color=config.COLOR_SUCCESS,
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            import traceback; traceback.print_exc()
            await self._error(interaction)

    # ── /upgrade building ─────────────────────────────────────

    @app_commands.command(name="upgrade", description="Upgrade an existing building")
    @app_commands.describe(building="The building to upgrade")
    @app_commands.choices(building=[
        app_commands.Choice(name=f"{v.get('emoji', '🏗️')} {k.replace('_', ' ').title()}", value=k)
        for k, v in config.BUILDINGS.items()
    ])
    async def upgrade(
        self, interaction: discord.Interaction, building: str
    ):
        if not await utils.check_active(interaction):
            return
            
        try:
            player = await db.ensure_player(
                str(interaction.user.id), interaction.user.display_name
            )
            if player["faction"] is None:
                await self._no_faction(interaction)
                return

            bldg = config.BUILDINGS.get(building)
            if not bldg:
                await interaction.response.send_message(
                    embed=discord.Embed(title="❌ Invalid building.", color=config.COLOR_ERROR),
                    ephemeral=True,
                )
                return

            current_level = player["buildings"].get(building, 0)
            if current_level == 0:
                embed = discord.Embed(
                    title="🏗️  Not Built",
                    description=f"Use `/build {building.replace('_', ' ')}` first.",
                    color=config.COLOR_WARNING,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if current_level >= config.MAX_BUILDING_LEVEL:
                embed = discord.Embed(
                    title="🏗️  Max Level",
                    description=f"Your {building.replace('_', ' ').title()} is already at max level ({config.MAX_BUILDING_LEVEL}).",
                    color=config.COLOR_WARNING,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            cost = bldg["costs"][current_level]

            # Factory cost reduction for upgrades
            factory_level = player["buildings"].get("factory", 0)
            if factory_level > 0 and building != "factory":
                reduction = config.BUILDINGS["factory"]["upgrade_cost_reduction"][factory_level - 1]
                cost = int(cost * (1 - reduction))

            if player["cash_wallet"] < cost:
                embed = discord.Embed(
                    title="💸  Not Enough Cash",
                    description=f"Upgrade costs {utils.format_cash(cost)}. You have {utils.format_cash(player['cash_wallet'])}.",
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            player["cash_wallet"] -= cost
            player["buildings"][building] = current_level + 1
            await db.save_player(player)

            emoji = bldg.get("emoji", "🏗️")
            embed = discord.Embed(
                title=f"{emoji}  {building.replace('_', ' ').title()} — Upgraded!",
                description=(
                    f"Level {current_level} → **Level {current_level + 1}**\n"
                    f"💵 Cost: {utils.format_cash(cost)}\n"
                    f"💰 Remaining: {utils.format_cash(player['cash_wallet'])}"
                ),
                color=config.COLOR_SUCCESS,
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            import traceback; traceback.print_exc()
            await self._error(interaction)

    # ── /collect ──────────────────────────────────────────────

    @app_commands.command(name="collect", description="Collect passive income from buildings")
    async def collect(self, interaction: discord.Interaction):
        if not await utils.check_active(interaction):
            return
            
        try:
            player = await db.ensure_player(
                str(interaction.user.id), interaction.user.display_name
            )
            if player["faction"] is None:
                await self._no_faction(interaction)
                return

            now = datetime.now(timezone.utc)
            last = player.get("last_collect_at")
            if last is None:
                last = player["created_at"]
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)

            elapsed_hours = min(
                (now - last).total_seconds() / 3600, 24  # cap at 24h
            )

            if elapsed_hours < 0.01:
                embed = discord.Embed(
                    title="⏳  Nothing to Collect",
                    description="Come back later for passive income.",
                    color=config.COLOR_WARNING,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            vip = utils.is_vip(player)
            income_mult = config.VIP_INCOME_MULT if vip else 1.0
            # Businessman income multiplier
            if player.get("faction") == "businessman":
                income_mult *= config.FACTION_BONUSES["businessman"].get("income_mult", 1.0)

            results = []
            total_cash = 0
            total_diamonds = 0

            # Brothel
            brothel_lvl = player["buildings"].get("brothel", 0)
            if brothel_lvl > 0:
                cash = int(
                    config.BUILDINGS["brothel"]["cash_per_hour"][brothel_lvl - 1]
                    * elapsed_hours
                    * income_mult
                )
                total_cash += cash
                results.append(f"🏩 Brothel Lv.{brothel_lvl}: +{utils.format_cash(cash)}")

            # Mafia house
            mafia_lvl = player["buildings"].get("mafia_house", 0)
            if mafia_lvl > 0 and player.get("profession"):
                prof = player["profession"]
                income_table = config.BUILDINGS["mafia_house"]["income_per_hour_by_profession"]
                if prof in income_table:
                    cash = int(
                        income_table[prof][mafia_lvl - 1]
                        * elapsed_hours
                        * income_mult
                    )
                    total_cash += cash
                    results.append(
                        f"🏚️ Mafia House Lv.{mafia_lvl} ({prof.title()}): +{utils.format_cash(cash)}"
                    )

            # Mines
            mines_lvl = player["buildings"].get("mines", 0)
            if mines_lvl > 0:
                diamonds = int(
                    config.BUILDINGS["mines"]["diamonds_per_hour"][mines_lvl - 1]
                    * elapsed_hours
                )
                total_diamonds += diamonds
                if diamonds > 0:
                    results.append(f"⛏️ Mines Lv.{mines_lvl}: +{diamonds} 💎")

            if not results:
                embed = discord.Embed(
                    title="📦  Nothing to Collect",
                    description="Build income-producing buildings first (Brothel, Mafia House, Mines).",
                    color=config.COLOR_WARNING,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            player["cash_wallet"] += total_cash
            player["diamonds"] += total_diamonds
            player["last_collect_at"] = now
            await db.save_player(player)

            embed = discord.Embed(
                title="📥  Income Collected!",
                description="\n".join(results),
                color=config.COLOR_SUCCESS,
            )
            embed.add_field(
                name="Totals",
                value=(
                    f"💵 {utils.format_cash(total_cash)} cash\n"
                    f"💎 {total_diamonds} diamonds\n"
                    f"⏱️ {elapsed_hours:.1f}h accumulated"
                ),
                inline=False,
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            import traceback; traceback.print_exc()
            await self._error(interaction)

    # ── /farm ─────────────────────────────────────────────────

    farm_group = app_commands.Group(name="farm", description="Farm management")

    @farm_group.command(name="start", description="Start a farming cycle")
    async def farm_start(self, interaction: discord.Interaction):
        if not await utils.check_active(interaction):
            return
            
        try:
            player = await db.ensure_player(
                str(interaction.user.id), interaction.user.display_name
            )
            if player["faction"] is None:
                await self._no_faction(interaction)
                return

            farm_lvl = player["buildings"].get("farm", 0)
            if farm_lvl == 0:
                embed = discord.Embed(
                    title="🌾  No Farm",
                    description="Build a farm first with `/build farm`.",
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            stamina_cost = config.BUILDINGS["farm"]["stamina_to_start"]
            if player["renewable"]["stamina"] < stamina_cost:
                embed = discord.Embed(
                    title="⚡  Not Enough Stamina",
                    description=f"Need **{stamina_cost}** stamina to start farming.",
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Check if already farming
            if player["cooldowns"].get("farm_start"):
                fs = player["cooldowns"]["farm_start"]
                if fs.tzinfo is None:
                    fs = fs.replace(tzinfo=timezone.utc)
                cycle_min = config.BUILDINGS["farm"]["cycle_minutes"][farm_lvl - 1]
                ready_at = fs + timedelta(minutes=cycle_min)
                if datetime.now(timezone.utc) < ready_at:
                    remaining = (ready_at - datetime.now(timezone.utc)).total_seconds()
                    embed = discord.Embed(
                        title="🌾  Already Farming",
                        description=f"Your crops will be ready in **{utils.format_cooldown(remaining)}**.\nUse `/farm collect` when ready.",
                        color=config.COLOR_WARNING,
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                else:
                    embed = discord.Embed(
                        title="🌾  Crops Ready",
                        description="You have crops waiting to be harvested!\nUse `/farm collect` before starting a new cycle.",
                        color=config.COLOR_WARNING,
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

            player["renewable"]["stamina"] -= stamina_cost
            player["cooldowns"]["farm_start"] = datetime.now(timezone.utc)
            await db.save_player(player)

            cycle_min = config.BUILDINGS["farm"]["cycle_minutes"][farm_lvl - 1]
            grain = config.BUILDINGS["farm"]["grain_per_cycle"][farm_lvl - 1]

            embed = discord.Embed(
                title="🌾  Farming Started!",
                description=(
                    f"Your farm (Lv.{farm_lvl}) is growing crops.\n"
                    f"🕐 Ready in: **{cycle_min} minutes**\n"
                    f"🌾 Expected yield: **{grain}** grain\n\n"
                    f"Use `/farm collect` when ready."
                ),
                color=config.COLOR_SUCCESS,
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            import traceback; traceback.print_exc()
            await self._error(interaction)

    @farm_group.command(name="collect", description="Collect harvested grain")
    async def farm_collect(self, interaction: discord.Interaction):
        if not await utils.check_active(interaction):
            return
            
        try:
            player = await db.ensure_player(
                str(interaction.user.id), interaction.user.display_name
            )

            farm_lvl = player["buildings"].get("farm", 0)
            if farm_lvl == 0:
                embed = discord.Embed(
                    title="🌾  No Farm",
                    description="Build a farm first with `/build farm`.",
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            fs = player["cooldowns"].get("farm_start")
            if not fs:
                embed = discord.Embed(
                    title="🌾  No Active Crop",
                    description="Use `/farm start` to begin farming.",
                    color=config.COLOR_WARNING,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if fs.tzinfo is None:
                fs = fs.replace(tzinfo=timezone.utc)

            cycle_min = config.BUILDINGS["farm"]["cycle_minutes"][farm_lvl - 1]
            ready_at = fs + timedelta(minutes=cycle_min)

            if datetime.now(timezone.utc) < ready_at:
                remaining = (ready_at - datetime.now(timezone.utc)).total_seconds()
                embed = discord.Embed(
                    title="🌾  Not Ready Yet",
                    description=f"Your crops need **{utils.format_cooldown(remaining)}** more.",
                    color=config.COLOR_WARNING,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            grain = config.BUILDINGS["farm"]["grain_per_cycle"][farm_lvl - 1]
            player["grain"] = player.get("grain", 0) + grain
            player["cooldowns"]["farm_start"] = None
            await db.save_player(player)

            embed = discord.Embed(
                title="🌾  Harvest Complete!",
                description=(
                    f"You harvested **{grain}** grain.\n"
                    f"📦 Total grain in storage: **{player['grain']}**\n\n"
                    f"Sell locally or use `/ship send` for better prices."
                ),
                color=config.COLOR_SUCCESS,
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            import traceback; traceback.print_exc()
            await self._error(interaction)

    # ── /ship ─────────────────────────────────────────────────

    ship_group = app_commands.Group(name="ship", description="Ship trading")

    async def ship_autocomplete(self, interaction: discord.Interaction, current: str):
        try:
            player = await db.get_player(str(interaction.user.id))
            if not player or not player.get("fleet"): return []
            
            choices = []
            for s in player["fleet"]:
                if s.get("at_sea"): continue
                if current.lower() in s["name"].lower():
                    cap = config.SHIP_CAPACITY.get(s["type"], 100)
                    desc = f"{s['name']} ({s['type'].title()} — Cap: {cap})"
                    choices.append(app_commands.Choice(name=desc[:100], value=s["name"]))
                    if len(choices) >= 25: break
            return choices
        except Exception:
            return []

    @ship_group.command(name="send", description="Send a ship with cargo")
    @app_commands.describe(
        ship_name="Name of the ship to send",
        cargo_type="Type of cargo: grain or opium",
    )
    @app_commands.choices(cargo_type=[
        app_commands.Choice(name="🌾 Grain", value="grain"),
        app_commands.Choice(name="🌿 Opium", value="opium"),
    ])
    @app_commands.autocomplete(ship_name=ship_autocomplete)
    async def ship_send(
        self,
        interaction: discord.Interaction,
        ship_name: str,
        cargo_type: str,
    ):
        if not await utils.check_active(interaction):
            return
            
        try:
            player = await db.ensure_player(
                str(interaction.user.id), interaction.user.display_name
            )
            if player["faction"] is None:
                await self._no_faction(interaction)
                return

            shipyard_lvl = player["buildings"].get("shipyard", 0)
            if shipyard_lvl == 0:
                embed = discord.Embed(
                    title="⚓  No Shipyard",
                    description="Build a shipyard first with `/build shipyard`.",
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Find available ships
            ships_cfg = config.BUILDINGS["shipyard"]["ships_unlocked"]
            available_ships = {
                lvl: ship for lvl, ship in ships_cfg.items()
                if lvl <= shipyard_lvl
            }

            # Find the requested ship
            target_ship = None
            for lvl, ship in available_ships.items():
                if ship["name"].lower() == ship_name.lower():
                    target_ship = ship
                    break

            if not target_ship:
                names = ", ".join(s["name"] for s in available_ships.values())
                embed = discord.Embed(
                    title="⚓  Ship Not Found",
                    description=f"Available ships: {names}",
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Check ship not already at sea
            fleet = player.get("fleet", [])
            for f in fleet:
                if f["name"] == target_ship["name"] and f.get("at_sea"):
                    return_at = f.get("returns_at")
                    if return_at and return_at.tzinfo is None:
                        return_at = return_at.replace(tzinfo=timezone.utc)
                    if return_at:
                        if return_at > datetime.now(timezone.utc):
                            rem = (return_at - datetime.now(timezone.utc)).total_seconds()
                            embed = discord.Embed(
                                title="⚓  Ship at Sea",
                                description=f"**{target_ship['name']}** returns in **{utils.format_cooldown(rem)}**.",
                                color=config.COLOR_WARNING,
                            )
                            await interaction.response.send_message(embed=embed, ephemeral=True)
                            return
                        else:
                            embed = discord.Embed(
                                title="⚓  Ship Waiting",
                                description=f"**{target_ship['name']}** has returned and is waiting to unload!\nUse `/ship collect` first.",
                                color=config.COLOR_WARNING,
                            )
                            await interaction.response.send_message(embed=embed, ephemeral=True)
                            return

            # Check cargo
            cargo_amount = player.get(cargo_type, 0)
            load = min(cargo_amount, target_ship["capacity"])
            if load <= 0:
                embed = discord.Embed(
                    title=f"📦  No {cargo_type.title()}",
                    description=f"You have no {cargo_type} to ship.",
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Send ship
            player[cargo_type] -= load
            now = datetime.now(timezone.utc)
            ship_entry = {
                "name": target_ship["name"],
                "at_sea": True,
                "cargo_type": cargo_type,
                "cargo_amount": load,
                "departs_at": now,
                "returns_at": now + timedelta(minutes=target_ship["return_minutes"]),
            }

            # Update or add to fleet
            updated = False
            for i, f in enumerate(fleet):
                if f["name"] == target_ship["name"]:
                    fleet[i] = ship_entry
                    updated = True
                    break
            if not updated:
                fleet.append(ship_entry)

            player["fleet"] = fleet
            await db.save_player(player)

            embed = discord.Embed(
                title=f"⛵  {target_ship['name']} Departed!",
                description=(
                    f"Carrying **{load}** {cargo_type}\n"
                    f"🕐 Returns in: **{target_ship['return_minutes']} minutes**\n\n"
                    f"Use `/ship collect` when it returns."
                ),
                color=config.COLOR_SUCCESS,
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            import traceback; traceback.print_exc()
            await self._error(interaction)

    @ship_group.command(name="collect", description="Collect returning ships")
    async def ship_collect(self, interaction: discord.Interaction):
        if not await utils.check_active(interaction):
            return
            
        try:
            player = await db.ensure_player(
                str(interaction.user.id), interaction.user.display_name
            )

            fleet = player.get("fleet", [])
            if not fleet:
                embed = discord.Embed(
                    title="⚓  No Ships",
                    description="You haven't sent any ships yet.",
                    color=config.COLOR_WARNING,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            now = datetime.now(timezone.utc)
            vip = utils.is_vip(player)
            collected = []
            total_cash = 0

            for ship in fleet:
                if not ship.get("at_sea"):
                    continue
                ret = ship.get("returns_at")
                if ret and ret.tzinfo is None:
                    ret = ret.replace(tzinfo=timezone.utc)
                if ret and ret <= now:
                    cargo_type = ship["cargo_type"]
                    cargo_amount = ship["cargo_amount"]

                    if cargo_type == "grain":
                        price = config.BUILDINGS["farm"]["base_sell_price_per_grain"]
                        price = int(price * config.BUILDINGS["farm"]["ship_sell_multiplier"])
                    elif cargo_type == "opium":
                        price = config.BUILDINGS["opium_house"]["ship_sell_price_per_opium"]
                    else:
                        price = 100

                    payment = int(cargo_amount * price)
                    if vip:
                        payment = int(payment * config.VIP_SELL_PRICE_MULT)

                    total_cash += payment
                    ship["at_sea"] = False
                    collected.append(
                        f"⛵ **{ship['name']}**: {cargo_amount} {cargo_type} → {utils.format_cash(payment)}"
                    )

            if not collected:
                # Show status of ships at sea
                at_sea = [s for s in fleet if s.get("at_sea")]
                if at_sea:
                    lines = []
                    for s in at_sea:
                        ret = s.get("returns_at")
                        if ret and ret.tzinfo is None:
                            ret = ret.replace(tzinfo=timezone.utc)
                        rem = (ret - now).total_seconds() if ret else 0
                        lines.append(f"⛵ **{s['name']}**: {utils.format_cooldown(rem)}")
                    embed = discord.Embed(
                        title="⚓  Ships Still at Sea",
                        description="\n".join(lines),
                        color=config.COLOR_WARNING,
                    )
                else:
                    embed = discord.Embed(
                        title="⚓  No Ships to Collect",
                        description="Send a ship first with `/ship send`.",
                        color=config.COLOR_WARNING,
                    )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            player["cash_wallet"] += total_cash
            player["fleet"] = fleet
            await db.save_player(player)

            embed = discord.Embed(
                title="📥  Ships Collected!",
                description="\n".join(collected),
                color=config.COLOR_SUCCESS,
            )
            embed.add_field(
                name="Total", value=f"💵 {utils.format_cash(total_cash)}", inline=False
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            import traceback; traceback.print_exc()
            await self._error(interaction)

    # ── Helpers ───────────────────────────────────────────────

    async def _no_faction(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚔️  Choose a Faction First",
            description="Use `/profile` to select your faction.",
            color=config.COLOR_WARNING,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

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
    await bot.add_cog(BuildingsCog(bot))
