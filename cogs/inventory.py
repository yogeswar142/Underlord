# cogs/inventory.py
# /items, /equip, /unequip commands.
# *** CRITICAL: recalc_equipment_bonus on EVERY equip/unequip ***

import discord
from discord import app_commands
from discord.ext import commands

import config
import db
import utils


class InventoryCog(commands.Cog):
    """Inventory management — equip, unequip, view items."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── /items ────────────────────────────────────────────────

    @app_commands.command(name="items", description="View your item inventory")
    async def items(self, interaction: discord.Interaction):
        try:
            player = await db.ensure_player(
                str(interaction.user.id), interaction.user.display_name
            )

            # Get all owned items
            all_items = await db.get_player_items(str(interaction.user.id))

            if not all_items and not any(player["inventory"].values()):
                embed = discord.Embed(
                    title="🎒  Empty Inventory",
                    description="You don't own any items yet.\nBuy some from `/market browse`!",
                    color=config.COLOR_INFO,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Equipped items
            equipped_ids = [
                iid for iid in player["inventory"].values() if iid
            ]
            equipped_dict = await db.get_items_by_ids(equipped_ids)

            slot_emojis = {
                "hat": "🎩", "jacket": "🧥", "shoes": "👟",
                "car": "🚗", "weapon1": "🔫", "weapon2": "🗡️",
                "jewellery": "💍",
            }

            embed = discord.Embed(
                title="🎒  Your Inventory",
                color=config.COLOR_INFO,
            )

            # Equipped section
            equip_lines = []
            for slot, item_id in player["inventory"].items():
                emoji = slot_emojis.get(slot, "•")
                if item_id and item_id in equipped_dict:
                    item = equipped_dict[item_id]
                    tier = item["tier"].replace("_", " ").title()
                    rank_str = f" | {slot.title()} Global Rank #{item['slot_rank']}" if item.get("slot_rank", 0) > 0 else ""
                    upg_str = f" [+ {item.get('upgrade_count', 0)}]" if item.get("upgrade_count", 0) > 0 else ""
                    equip_lines.append(
                        f"{emoji} **{slot.title()}**: **{item['name']}**{upg_str} ({tier})\n"
                        f"   └ ⚡ +{item['total_bonus']} {item['stat_type'].title()}{rank_str}\n"
                        f"   └ *{item.get('lore', '')}*"
                    )
                else:
                    equip_lines.append(f"{emoji} **{slot.title()}**: — empty")

            embed.add_field(
                name="⚔️ Equipped",
                value="\n".join(equip_lines),
                inline=False,
            )

            # Unequipped items
            unequipped = [i for i in all_items if i["_id"] not in equipped_ids]
            if unequipped:
                inv_lines = []
                for item in unequipped[:15]:  # Cap display at 15
                    tier = item["tier"].replace("_", " ").title()
                    emoji = slot_emojis.get(item["slot"], "•")
                    rank_str = f" | Rank #{item['slot_rank']}" if item.get("slot_rank", 0) > 0 else ""
                    upg_str = f" [+ {item.get('upgrade_count', 0)}]" if item.get("upgrade_count", 0) > 0 else ""
                    inv_lines.append(
                        f"{emoji} `{utils.short_id(item['_id'])}` "
                        f"**{item['name']}**{upg_str} ({tier}) — "
                        f"+{item['total_bonus']} {item['stat_type']}{rank_str}\n"
                        f"   └ *{item.get('lore', '')}*"
                    )
                if len(unequipped) > 15:
                    inv_lines.append(f"... and {len(unequipped) - 15} more")
                embed.add_field(
                    name=f"📦 Backpack ({len(unequipped)} items)",
                    value="\n".join(inv_lines),
                    inline=False,
                )

            # Equipment bonus totals
            eb = player.get("equipment_bonus", {})
            if any(v > 0 for v in eb.values()):
                bonus_text = " | ".join(
                    f"{k.title()}: +{v}" for k, v in eb.items() if v > 0
                )
                embed.set_footer(text=f"Equipment Bonuses: {bonus_text}")

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            import traceback; traceback.print_exc()
            await self._error(interaction)

    # ── /equip ────────────────────────────────────────────────

    async def equip_autocomplete(self, interaction: discord.Interaction, current: str):
        try:
            player = await db.get_player(str(interaction.user.id))
            if not player or not player.get("items"): return []
            
            database = db.get_db()
            items = await database.items.find({"_id": {"$in": player["items"]}}).to_list(None)
            
            choices = []
            for itm in items:
                # Don't show equipped items
                if itm["_id"] in player["inventory"].values(): continue
                name = f"{itm['name']} (+{itm['total_bonus']} {itm['stat_type']})"
                if current.lower() in name.lower() or current.lower() in itm["_id"]:
                    choices.append(app_commands.Choice(name=name[:100], value=itm["_id"][:8]))
                    if len(choices) >= 25: break
            return choices
        except Exception:
            return []

    @app_commands.command(name="equip", description="Equip an item from your inventory")
    @app_commands.describe(item_id="The item to equip")
    @app_commands.autocomplete(item_id=equip_autocomplete)
    async def equip(self, interaction: discord.Interaction, item_id: str):
        if not await utils.check_active(interaction):
            return
            
        try:
            player = await db.ensure_player(
                str(interaction.user.id), interaction.user.display_name
            )
            if player["faction"] is None:
                await self._no_faction(interaction)
                return

            # Find the item — support short IDs
            all_items = await db.get_player_items(str(interaction.user.id))
            target_item = None
            for item in all_items:
                if item["_id"] == item_id or item["_id"].startswith(item_id):
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

            slot = target_item["slot"]

            # If slot already occupied → move current item to backpack
            current_equipped_id = player["inventory"].get(slot)
            swap_msg = ""
            if current_equipped_id:
                # Add old item back to player's items list
                if current_equipped_id not in player["items"]:
                    player["items"].append(current_equipped_id)
                swap_msg = f"\n📤 Unequipped previous {slot} item."

            # Equip new item
            player["inventory"][slot] = target_item["_id"]
            # Remove from backpack list
            if target_item["_id"] in player["items"]:
                player["items"].remove(target_item["_id"])

            # *** CRITICAL: Recalculate equipment_bonus ***
            equipped_ids = [
                iid for iid in player["inventory"].values() if iid
            ]
            items_dict = await db.get_items_by_ids(equipped_ids)
            utils.recalc_equipment_bonus(player, items_dict)

            await db.save_player(player)

            tier = target_item["tier"].replace("_", " ").title()
            rank_str = f" | {slot.title()} Global Rank #{target_item.get('slot_rank')}" if target_item.get("slot_rank", 0) > 0 else ""
            upg_str = f" [+ {target_item.get('upgrade_count', 0)}]" if target_item.get('upgrade_count', 0) > 0 else ""
            
            embed = discord.Embed(
                title=f"⚔️  Equipped: {target_item['name']}",
                description=(
                    f"**{target_item['name']}**{upg_str} ({tier}) → **{slot.title()}**\n"
                    f"⚡ +{target_item['total_bonus']} {target_item['stat_type'].title()}{rank_str}\n"
                    f"*{target_item.get('lore', '')}*\n"
                    f"{swap_msg}"
                ),
                color=config.COLOR_SUCCESS,
            )

            # Show updated total bonus
            eb = player["equipment_bonus"]
            bonus_text = " | ".join(
                f"{k.title()}: +{v}" for k, v in eb.items() if v > 0
            )
            if bonus_text:
                embed.add_field(
                    name="📊 Equipment Bonuses",
                    value=bonus_text,
                    inline=False,
                )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            import traceback; traceback.print_exc()
            await self._error(interaction)

    # ── /unequip ──────────────────────────────────────────────

    @app_commands.command(name="unequip", description="Unequip an item from a slot")
    @app_commands.describe(slot="The equipment slot to unequip")
    @app_commands.choices(slot=[
        app_commands.Choice(name="🎩 Hat", value="hat"),
        app_commands.Choice(name="🧥 Jacket", value="jacket"),
        app_commands.Choice(name="👟 Shoes", value="shoes"),
        app_commands.Choice(name="🚗 Car", value="car"),
        app_commands.Choice(name="🔫 Weapon 1", value="weapon1"),
        app_commands.Choice(name="🗡️ Weapon 2", value="weapon2"),
        app_commands.Choice(name="💍 Jewellery", value="jewellery"),
    ])
    async def unequip(self, interaction: discord.Interaction, slot: str):
        if not await utils.check_active(interaction):
            return
            
        try:
            player = await db.ensure_player(
                str(interaction.user.id), interaction.user.display_name
            )

            item_id = player["inventory"].get(slot)
            if not item_id:
                embed = discord.Embed(
                    title="❌  Nothing Equipped",
                    description=f"No item in **{slot.title()}** slot.",
                    color=config.COLOR_WARNING,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Move to backpack
            if item_id not in player["items"]:
                player["items"].append(item_id)
            player["inventory"][slot] = None

            # *** CRITICAL: Recalculate equipment_bonus ***
            equipped_ids = [
                iid for iid in player["inventory"].values() if iid
            ]
            items_dict = await db.get_items_by_ids(equipped_ids)
            utils.recalc_equipment_bonus(player, items_dict)

            await db.save_player(player)

            item = await db.get_item(item_id)
            item_name = item["name"] if item else "Unknown"

            embed = discord.Embed(
                title=f"📤  Unequipped: {item_name}",
                description=f"Removed **{item_name}** from **{slot.title()}** slot.\nItem moved to your backpack.",
                color=config.COLOR_SUCCESS,
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
    await bot.add_cog(InventoryCog(bot))
