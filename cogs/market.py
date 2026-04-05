# cogs/market.py
# /market browse, /market list, /market buy commands.
# Also schedules market expiry cleanup job.

import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import config
import db
import utils


class MarketCog(commands.Cog):
    """Player-to-player marketplace for items and VIP days."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.expire_listings.start()

    def cog_unload(self):
        self.expire_listings.cancel()

    # ── Expiry task (every 15 minutes) ────────────────────────

    @tasks.loop(minutes=15)
    async def expire_listings(self):
        """Remove expired listings and return items/days to sellers."""
        try:
            database = db.get_db()
            now = datetime.now(timezone.utc)
            expired = await database.market_listings.find(
                {"expires_at": {"$lt": now}}
            ).to_list(None)

            for listing in expired:
                if listing["type"] == "item":
                    # Return item to seller
                    await database.players.update_one(
                        {"_id": listing["seller_id"]},
                        {"$push": {"items": listing["item_id"]}},
                    )
                    await database.items.update_one(
                        {"_id": listing["item_id"]},
                        {"$set": {"on_market": False, "owner_id": listing["seller_id"]}},
                    )
                elif listing["type"] == "vip_days":
                    # Return escrowed days (NOT the 3 burned entry fee)
                    await database.players.update_one(
                        {"_id": listing["seller_id"]},
                        {"$inc": {"vip_days": listing["vip_days_amount"]}},
                    )
                await database.market_listings.delete_one({"_id": listing["_id"]})
        except Exception:
            import traceback; traceback.print_exc()

    @expire_listings.before_loop
    async def before_expire(self):
        await self.bot.wait_until_ready()

    # ── /market group ─────────────────────────────────────────

    market_group = app_commands.Group(name="market", description="Player marketplace")

    # ── /market browse ────────────────────────────────────────

    @market_group.command(name="browse", description="Browse market listings")
    @app_commands.describe(
        listing_type="Filter by type",
        slot="Filter by item slot (optional)",
        tier="Filter by item tier (optional)",
    )
    @app_commands.choices(
        listing_type=[
            app_commands.Choice(name="🎒 Items", value="item"),
            app_commands.Choice(name="👑 VIP Days", value="vip_days"),
        ],
        slot=[
            app_commands.Choice(name=f"{e} {s.title()}", value=s)
            for s, e in {
                "hat": "🎩", "jacket": "🧥", "shoes": "👟",
                "car": "🚗", "weapon1": "🔫", "weapon2": "🗡️",
                "jewellery": "💍",
            }.items()
        ],
        tier=[
            app_commands.Choice(name=t.replace("_", " ").title(), value=t)
            for t in config.TIER_ORDER
        ],
    )
    async def browse(
        self,
        interaction: discord.Interaction,
        listing_type: str = "item",
        slot: str | None = None,
        tier: str | None = None,
    ):
        try:
            database = db.get_db()
            now = datetime.now(timezone.utc)

            query = {"type": listing_type, "expires_at": {"$gt": now}}
            listings = await database.market_listings.find(query).sort(
                "price", 1
            ).to_list(50)

            if not listings:
                embed = discord.Embed(
                    title="🏬  Market — No Listings",
                    description=f"No active {listing_type.replace('_', ' ')} listings found.",
                    color=config.COLOR_INFO,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            embed = discord.Embed(
                title=f"🏬  Market — {listing_type.replace('_', ' ').title()} Listings",
                color=config.COLOR_INFO,
            )

            lines = []
            for listing in listings:
                lid = utils.short_id(listing["_id"])
                price = utils.format_cash(listing["price"])

                if listing["type"] == "item" and listing.get("item_id"):
                    item = await db.get_item(listing["item_id"])
                    if item:
                        # Apply slot/tier filters
                        if slot and item["slot"] != slot:
                            continue
                        if tier and item["tier"] != tier:
                            continue
                        tier_name = item["tier"].replace("_", " ").title()
                        lines.append(
                            f"`{lid}` **{item['name']}** ({tier_name}) "
                            f"+{item['total_bonus']} {item['stat_type']} — {price}"
                        )
                elif listing["type"] == "vip_days":
                    days = listing.get("vip_days_amount", 0)
                    lines.append(f"`{lid}` 👑 **{days} VIP Days** — {price}")

            if not lines:
                embed.description = "No listings match your filters."
            else:
                # Paginate (show max 10 per page)
                embed.description = "\n".join(lines[:10])
                if len(lines) > 10:
                    embed.set_footer(
                        text=f"Showing 10 of {len(lines)} listings"
                    )

            embed.add_field(
                name="💡 How to Buy",
                value="Use `/market buy <listing_id>` with the ID shown above.",
                inline=False,
            )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            import traceback; traceback.print_exc()
            await self._error(interaction)

    # ── /market list item ─────────────────────────────────────

    @market_group.command(name="list-item", description="List an item on the market")
    @app_commands.describe(
        item_id="Item ID to list (8-char short ID)",
        price="Asking price in cash",
    )
    async def list_item(
        self, interaction: discord.Interaction, item_id: str, price: int
    ):
        try:
            player = await db.ensure_player(
                str(interaction.user.id), interaction.user.display_name
            )

            if price <= 0:
                embed = discord.Embed(
                    title="❌  Invalid Price",
                    description="Price must be greater than 0.",
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Find item
            all_items = await db.get_player_items(str(interaction.user.id))
            target_item = None
            for item in all_items:
                if item["_id"] == item_id or item["_id"].startswith(item_id):
                    target_item = item
                    break

            if not target_item:
                embed = discord.Embed(
                    title="❌  Item Not Found",
                    description=(
                        f"No item matching `{item_id}` in your backpack.\n"
                        "You must unequip an item before listing it."
                    ),
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if target_item.get("on_market"):
                embed = discord.Embed(
                    title="❌  Already Listed",
                    description="This item is already on the market.",
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Calculate entry fee
            entry_fee = config.MARKET_ITEM_ENTRY_FEE[target_item["tier"]]
            factory_lvl = player["buildings"].get("factory", 0)
            if factory_lvl > 0:
                reduction = config.BUILDINGS["factory"]["market_fee_reduction"][factory_lvl - 1]
                entry_fee = int(entry_fee * (1 - reduction))
            market_lvl = player["buildings"].get("market", 0)
            if market_lvl > 0:
                reduction = config.BUILDINGS["market"]["fee_reduction_per_level"] * market_lvl
                entry_fee = int(entry_fee * (1 - reduction))

            if player["cash_wallet"] < entry_fee:
                embed = discord.Embed(
                    title="💸  Not Enough Cash",
                    description=(
                        f"Entry fee: {utils.format_cash(entry_fee)}. "
                        f"You have {utils.format_cash(player['cash_wallet'])}."
                    ),
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Deduct fee
            player["cash_wallet"] -= entry_fee

            # Remove item from player's items list
            if target_item["_id"] in player["items"]:
                player["items"].remove(target_item["_id"])

            now = datetime.now(timezone.utc)
            expires = now + timedelta(hours=config.MARKET_LISTING_DURATION_HOURS)

            # Create listing
            listing = {
                "_id": str(uuid4()),
                "seller_id": str(interaction.user.id),
                "type": "item",
                "item_id": target_item["_id"],
                "vip_days_amount": 0,
                "price": price,
                "entry_fee_paid": entry_fee,
                "listed_at": now,
                "expires_at": expires,
            }
            database = db.get_db()
            await database.market_listings.insert_one(listing)

            # Mark item as on market
            target_item["on_market"] = True
            target_item["owner_id"] = None
            target_item["market_price"] = price
            target_item["market_listed_at"] = now
            target_item["market_expires_at"] = expires
            await db.save_item(target_item)

            await db.save_player(player)

            embed = discord.Embed(
                title="🏬  Item Listed!",
                description=(
                    f"**{target_item['name']}** ({target_item['tier'].replace('_', ' ').title()})\n"
                    f"💵 Price: {utils.format_cash(price)}\n"
                    f"📋 Fee paid: {utils.format_cash(entry_fee)}\n"
                    f"⏱️ Expires in {config.MARKET_LISTING_DURATION_HOURS}h\n"
                    f"📝 Listing ID: `{utils.short_id(listing['_id'])}`"
                ),
                color=config.COLOR_SUCCESS,
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            import traceback; traceback.print_exc()
            await self._error(interaction)

    # ── /market list vip ──────────────────────────────────────

    @market_group.command(name="list-vip", description="List VIP days on the market")
    @app_commands.describe(days="Number of VIP days to list (min 10)", price="Asking price in cash")
    async def list_vip(
        self, interaction: discord.Interaction, days: int, price: int
    ):
        try:
            player = await db.ensure_player(
                str(interaction.user.id), interaction.user.display_name
            )

            if days < config.MARKET_VIP_MIN_LISTING_DAYS:
                embed = discord.Embed(
                    title="❌  Minimum Days",
                    description=f"Must list at least **{config.MARKET_VIP_MIN_LISTING_DAYS}** VIP days.",
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            total_needed = days + config.MARKET_VIP_ENTRY_FEE_DAYS
            if player.get("vip_days", 0) < total_needed:
                embed = discord.Embed(
                    title="❌  Not Enough VIP Days",
                    description=(
                        f"Need **{total_needed}** days ({days} to list + "
                        f"{config.MARKET_VIP_ENTRY_FEE_DAYS} entry fee). "
                        f"You have **{player.get('vip_days', 0)}**."
                    ),
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Deduct days
            player["vip_days"] -= total_needed

            now = datetime.now(timezone.utc)
            expires = now + timedelta(hours=config.MARKET_LISTING_DURATION_HOURS)

            listing = {
                "_id": str(uuid4()),
                "seller_id": str(interaction.user.id),
                "type": "vip_days",
                "item_id": None,
                "vip_days_amount": days,
                "price": price,
                "entry_fee_paid": config.MARKET_VIP_ENTRY_FEE_DAYS,
                "listed_at": now,
                "expires_at": expires,
            }
            database = db.get_db()
            await database.market_listings.insert_one(listing)
            await db.save_player(player)

            embed = discord.Embed(
                title="🏬  VIP Days Listed!",
                description=(
                    f"👑 **{days} VIP Days** listed for {utils.format_cash(price)}\n"
                    f"📋 Entry fee: {config.MARKET_VIP_ENTRY_FEE_DAYS} days burned\n"
                    f"⏱️ Expires in {config.MARKET_LISTING_DURATION_HOURS}h\n"
                    f"📝 Listing ID: `{utils.short_id(listing['_id'])}`"
                ),
                color=config.COLOR_SUCCESS,
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            import traceback; traceback.print_exc()
            await self._error(interaction)

    # ── /market buy ───────────────────────────────────────────

    @market_group.command(name="buy", description="Buy a market listing")
    @app_commands.describe(listing_id="The listing ID (8-char short ID)")
    async def buy(self, interaction: discord.Interaction, listing_id: str):
        try:
            player = await db.ensure_player(
                str(interaction.user.id), interaction.user.display_name
            )

            database = db.get_db()

            # Find listing — support short IDs
            listings = await database.market_listings.find().to_list(None)
            listing = None
            for l in listings:
                if l["_id"] == listing_id or l["_id"].startswith(listing_id):
                    listing = l
                    break

            if not listing:
                embed = discord.Embed(
                    title="❌  Listing Not Found",
                    description=f"No listing matching `{listing_id}`.",
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Can't buy your own listing
            if listing["seller_id"] == str(interaction.user.id):
                embed = discord.Embed(
                    title="❌  Can't Buy Own Listing",
                    description="You can't buy your own listing.",
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            price = listing["price"]
            if player["cash_wallet"] < price:
                embed = discord.Embed(
                    title="💸  Not Enough Cash",
                    description=f"This costs {utils.format_cash(price)}. You have {utils.format_cash(player['cash_wallet'])}.",
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Process purchase
            player["cash_wallet"] -= price

            # Seller gets price minus transaction fee
            seller_payout = int(price * (1 - config.MARKET_TRANSACTION_FEE_PCT))
            await database.players.update_one(
                {"_id": listing["seller_id"]},
                {"$inc": {"cash_wallet": seller_payout}},
            )

            result_desc = ""

            if listing["type"] == "item":
                # Transfer item to buyer
                item_id = listing["item_id"]
                player["items"].append(item_id)
                await database.items.update_one(
                    {"_id": item_id},
                    {"$set": {
                        "on_market": False,
                        "owner_id": str(interaction.user.id),
                        "market_price": None,
                        "market_listed_at": None,
                        "market_expires_at": None,
                    }},
                )
                item = await db.get_item(item_id)
                item_name = item["name"] if item else "Unknown"
                result_desc = f"🎒 **{item_name}** added to your inventory."

            elif listing["type"] == "vip_days":
                days = listing["vip_days_amount"]
                player["vip_days"] = player.get("vip_days", 0) + days
                result_desc = f"👑 **{days} VIP days** added to your account."

            # Delete listing
            await database.market_listings.delete_one({"_id": listing["_id"]})
            await db.save_player(player)

            embed = discord.Embed(
                title="🛒  Purchase Complete!",
                description=(
                    f"{result_desc}\n"
                    f"💵 Paid: {utils.format_cash(price)}\n"
                    f"💰 Remaining: {utils.format_cash(player['cash_wallet'])}"
                ),
                color=config.COLOR_SUCCESS,
            )
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
    await bot.add_cog(MarketCog(bot))
