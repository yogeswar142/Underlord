# cogs/upgrades.py
# /upgrade-item command — RNG item upgrades.
# *** CRITICAL: recalc_equipment_bonus if upgraded item is currently equipped ***

import random
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from pymongo import UpdateOne

import config
import db
import utils


class UpgradesCog(commands.Cog):
    """Item upgrade system with RNG tiers."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def upgrade_autocomplete(self, interaction: discord.Interaction, current: str):
        try:
            player = await db.get_player(str(interaction.user.id))
            if not player or not player.get("items"): return []
            
            database = db.get_db()
            items = await database.items.find({"_id": {"$in": player["items"]}}).to_list(None)
            
            choices = []
            for itm in items:
                upgrades = itm.get("upgrade_count", 0)
                name = f"[{upgrades}] {itm['name']} (+{itm['total_bonus']})"
                if current.lower() in name.lower() or current.lower() in itm["_id"]:
                    choices.append(app_commands.Choice(name=name[:100], value=itm["_id"][:8]))
                    if len(choices) >= 25: break
            return choices
        except Exception:
            return []

    @app_commands.command(
        name="upgrade-item", description="Upgrade an item with RNG outcomes"
    )
    @app_commands.describe(item_id="The item to upgrade")
    @app_commands.autocomplete(item_id=upgrade_autocomplete)
    async def upgrade_item(self, interaction: discord.Interaction, item_id: str):
        if not await utils.check_active(interaction):
            return
            
        try:
            player = await db.ensure_player(
                str(interaction.user.id), interaction.user.display_name
            )
            if player["faction"] is None:
                await self._no_faction(interaction)
                return

            # Find item — support short IDs
            all_items = await db.get_player_items(str(interaction.user.id))
            target_item = None
            for item in all_items:
                if item["_id"] == item_id or item["_id"].startswith(item_id):
                    target_item = item
                    break

            # Also check equipped items
            if not target_item:
                equipped_ids = [
                    iid for iid in player["inventory"].values() if iid
                ]
                equipped_items = await db.get_items_by_ids(equipped_ids)
                for iid, item in equipped_items.items():
                    if iid == item_id or iid.startswith(item_id):
                        target_item = item
                        break

            if not target_item:
                embed = discord.Embed(
                    title="❌  Item Not Found",
                    description=f"No item matching `{item_id}` in your inventory.",
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Check happiness
            if player["stats"]["happiness"] < config.UPGRADE_HAPPINESS_COST:
                embed = discord.Embed(
                    title="😔  Not Enough Happiness",
                    description=(
                        f"Need **{config.UPGRADE_HAPPINESS_COST}** happiness. "
                        f"You have **{player['stats']['happiness']}**.\n"
                        f"Equip Jewellery to boost happiness."
                    ),
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Calculate cost
            base_cost = config.UPGRADE_BASE_COST_BY_TIER[target_item["tier"]]
            factory_lvl = player["buildings"].get("factory", 0)
            if factory_lvl > 0:
                reduction = config.BUILDINGS["factory"]["upgrade_cost_reduction"][factory_lvl - 1]
                base_cost = int(base_cost * (1 - reduction))

            if player["cash_wallet"] < base_cost:
                embed = discord.Embed(
                    title="💸  Not Enough Cash",
                    description=(
                        f"Upgrade costs {utils.format_cash(base_cost)}. "
                        f"You have {utils.format_cash(player['cash_wallet'])}."
                    ),
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Deduct costs
            player["stats"]["happiness"] -= config.UPGRADE_HAPPINESS_COST
            player["cash_wallet"] -= base_cost

            # Roll upgrade outcome
            vip = utils.is_vip(player)
            table_key = "vip" if vip else "free"
            outcomes = config.UPGRADE_OUTCOMES[table_key]

            roll = random.random()
            cumulative = 0
            outcome_name = "normal"
            outcome = outcomes["normal"]
            for name, data in outcomes.items():
                cumulative += data["chance"]
                if roll <= cumulative:
                    outcome_name = name
                    outcome = data
                    break

            # Apply upgrade
            old_bonus = target_item["total_bonus"]
            old_tier = target_item["tier"]

            bonus_gain = int(target_item["base_stat"] * outcome["multiplier"])
            target_item["total_bonus"] += bonus_gain
            target_item["upgrade_count"] += 1

            # Tier up
            tier_up = False
            if outcome.get("tier_up"):
                new_tier = utils.next_tier(target_item["tier"])
                if new_tier:
                    target_item["tier"] = new_tier
                    target_item["base_stat"] = config.TIER_BONUS[new_tier]
                    tier_up = True

            await db.save_item(target_item)

            # *** CRITICAL: Recalc equipment_bonus if this item is equipped ***
            is_equipped = target_item["_id"] in player["inventory"].values()
            if is_equipped:
                equipped_ids = [
                    iid for iid in player["inventory"].values() if iid
                ]
                items_dict = await db.get_items_by_ids(equipped_ids)
                utils.recalc_equipment_bonus(player, items_dict)

            await db.save_player(player)

            # Build response
            outcome_colors = {
                "normal": config.COLOR_INFO,
                "rare": config.COLOR_SUCCESS,
                "very_rare": config.COLOR_VIP,
                "legendary": 0xFFD700,  # gold
            }
            outcome_labels = {
                "normal": "⬜ Normal",
                "rare": "🟦 Rare",
                "very_rare": "🟪 Very Rare",
                "legendary": "🟨 LEGENDARY",
            }

            embed = discord.Embed(
                title=f"🔧  Upgrade: {outcome_labels.get(outcome_name, outcome_name)}!",
                color=outcome_colors.get(outcome_name, config.COLOR_INFO),
            )
            embed.add_field(
                name=target_item["name"],
                value=(
                    f"Bonus: {old_bonus} → **{target_item['total_bonus']}** (+{bonus_gain})\n"
                    f"Tier: {old_tier.replace('_', ' ').title()}"
                    + (f" → **{target_item['tier'].replace('_', ' ').title()}** 🎉" if tier_up else "")
                    + f"\nUpgrades: {target_item['upgrade_count']}"
                ),
                inline=False,
            )
            embed.add_field(
                name="Cost",
                value=(
                    f"💵 {utils.format_cash(base_cost)}\n"
                    f"😊 -{config.UPGRADE_HAPPINESS_COST} happiness"
                ),
                inline=True,
            )
            if is_equipped:
                eb = player["equipment_bonus"]
                bonus_text = " | ".join(
                    f"{k.title()}: +{v}" for k, v in eb.items() if v > 0
                )
                embed.add_field(
                    name="📊 Updated Eq. Bonus", value=bonus_text or "None", inline=True
                )

            await interaction.response.send_message(embed=embed)

            # Async slot rank update (non-blocking)
            asyncio.create_task(
                self._update_slot_rank(target_item["_id"], target_item["slot"])
            )

        except Exception as e:
            import traceback; traceback.print_exc()
            await self._error(interaction)

    async def _update_slot_rank(self, item_id: str, slot: str):
        """
        Rank all items of the same slot by total_bonus descending.
        Runs asynchronously — does not block the user response.
        """
        try:
            database = db.get_db()
            items = await database.items.find(
                {"slot": slot}
            ).sort("total_bonus", -1).to_list(None)

            ops = []
            for rank, item in enumerate(items, start=1):
                ops.append(
                    UpdateOne(
                        {"_id": item["_id"]},
                        {"$set": {"slot_rank": rank}},
                    )
                )
            if ops:
                await database.items.bulk_write(ops)
        except Exception:
            import traceback; traceback.print_exc()

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
    await bot.add_cog(UpgradesCog(bot))
