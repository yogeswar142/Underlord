# cogs/shop.py
import discord
from discord import app_commands
from discord.ext import commands

import config
import db
import utils
from items_catalog import get_shop_items, ITEMS_CATALOG

TIER_EMOJIS = {
    "common": "⬜",
    "uncommon": "🟩",
    "rare": "🟦",
    "very_rare": "🟪",
    "legendary": "🟡",
}

class BuyButton(discord.ui.Button):
    def __init__(self, item_key: str, index: int, price: int):
        super().__init__(style=discord.ButtonStyle.success, label=f"Buy #{index}", custom_id=f"buy_{item_key}")
        self.item_key = item_key
        self.price = price

    async def callback(self, interaction: discord.Interaction):
        await handle_buy(interaction, self.item_key)

class NavButton(discord.ui.Button):
    def __init__(self, view_obj, direction: int, label: str):
        super().__init__(style=discord.ButtonStyle.secondary, label=label)
        self.view_obj = view_obj
        self.direction = direction

    async def callback(self, interaction: discord.Interaction):
        self.view_obj.page += self.direction
        await self.view_obj.update_page(interaction)

class ShopSelect(discord.ui.Select):
    def __init__(self, view_obj):
        self.view_obj = view_obj
        options = [
            discord.SelectOption(label="Hat", value="hat", emoji="🎩"),
            discord.SelectOption(label="Jacket", value="jacket", emoji="🧥"),
            discord.SelectOption(label="Shoes", value="shoes", emoji="👟"),
            discord.SelectOption(label="Car", value="car", emoji="🚗"),
            discord.SelectOption(label="Weapon", value="weapon", emoji="🔫"),
            discord.SelectOption(label="Jewellery", value="jewellery", emoji="💍"),
        ]
        super().__init__(placeholder="Select a category...", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view_obj.category = self.values[0]
        self.view_obj.page = 0
        await self.view_obj.update_page(interaction)

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.category = None
        self.page = 0
        self.items = []
        
        self.select = ShopSelect(self)
        self.add_item(self.select)
        
    async def update_page(self, interaction: discord.Interaction):
        self.clear_items()
        self.add_item(self.select) # ActionRow 1
        
        if not self.category:
            await interaction.response.edit_message(content="Please select a category.", embed=None, view=self)
            return

        # Fetch items
        if self.category == "weapon":
            w1 = get_shop_items("weapon1")
            w2 = get_shop_items("weapon2")
            all_dict = {**w1, **w2}
        else:
            all_dict = get_shop_items(self.category)
            
        self.items = sorted(list(all_dict.items()), key=lambda x: (x[1]["tier"] == "uncommon", x[1]["shop_price"]))
        
        total_pages = max(1, (len(self.items) + 4) // 5)
        self.page = max(0, min(self.page, total_pages - 1))
        
        start_idx = self.page * 5
        page_items = self.items[start_idx:start_idx+5]
        
        embed = discord.Embed(
            title=f"🏪  Black Market Shop — {self.category.title()}",
            description="Purchase equipment directly from the underworld suppliers.",
            color=config.COLOR_INFO
        )
        embed.set_footer(text=f"Page {self.page + 1} of {total_pages}")
        
        lines = []
        # ActionRow 2 for Buy Buttons
        for idx, (id_key, data) in enumerate(page_items, start=1):
            tier_emoji = TIER_EMOJIS.get(data["tier"], "⬜")
            tier_name = data["tier"].replace("_", " ").title()
            stat_name = data["stat_type"].title()
            price_str = utils.format_cash(data["shop_price"])
            
            lines.append(
                f"**#{idx}** {tier_emoji} **{data['name']}** ({tier_name})\n"
                f"Boost: **+{data['base_stat']} {stat_name}** | Price: **{price_str}**\n"
                f"*{data['lore']}*\n"
            )
            
            # Action Row 2 has Buy Buttons
            self.add_item(BuyButton(id_key, idx, data["shop_price"]))
            
        embed.description += "\n\n" + "\n".join(lines)
        
        # ActionRow 3 for Pagination
        if total_pages > 1:
            nav_row = []
            if self.page > 0:
                self.add_item(NavButton(self, -1, "⬅️ Previous"))
            if self.page < total_pages - 1:
                self.add_item(NavButton(self, 1, "Next ➡️"))
                
        await interaction.response.edit_message(embed=embed, view=self)

async def handle_buy(interaction: discord.Interaction, id_key: str):
    if not await utils.check_active(interaction):
        return
        
    try:
        player = await db.ensure_player(str(interaction.user.id), interaction.user.display_name)
        
        if id_key not in ITEMS_CATALOG or ITEMS_CATALOG[id_key]["shop_price"] is None:
            embed = discord.Embed(title="❌ Unavailable", description="This item is not for sale.", color=config.COLOR_ERROR)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        price = ITEMS_CATALOG[id_key]["shop_price"]
        if player["cash_wallet"] < price:
            embed = discord.Embed(
                title="💸 Insufficient Funds", 
                description=f"Need {utils.format_cash(price)}. You have {utils.format_cash(player['cash_wallet'])}.", 
                color=config.COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Deduct cash
        player["cash_wallet"] -= price
        
        # Output Item
        new_item = utils.generate_item_from_catalog(id_key)
        
        database = db.get_db()
        await database.items.insert_one(new_item)
        
        # Assige owner to DB directly on insert, then update owner_id
        await database.items.update_one({"_id": new_item["_id"]}, {"$set": {"owner_id": str(interaction.user.id)}})
        new_item["owner_id"] = str(interaction.user.id)
        
        player["items"].append(new_item["_id"])
        await db.save_player(player)
        
        from cogs.upgrades import update_slot_rank
        # Fire and forget the async rank update update
        import asyncio
        asyncio.create_task(update_slot_rank(new_item["slot"]))
        
        tier_emoji = TIER_EMOJIS.get(new_item["tier"], "⬜")
        embed = discord.Embed(
            title="🛒 Purchase Successful!",
            description=(
                f"You bought {tier_emoji} **{new_item['name']}**.\n\n"
                f"**Boost**: +{new_item['total_bonus']} {new_item['stat_type'].title()}\n"
                f"*{new_item['lore']}*\n\n"
                f"Use `/equip {new_item['_id'][:8]}` to wear it."
            ),
            color=config.COLOR_SUCCESS
        )
        embed.set_footer(text=f"Remaining Cash: {utils.format_cash(player['cash_wallet'])}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        import traceback; traceback.print_exc()
        try:
            await interaction.response.send_message("❌ Something went wrong.", ephemeral=True)
        except:
            pass

class ShopCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="shop", description="Browse and buy gear from the black market")
    async def shop(self, interaction: discord.Interaction):
        if not await utils.check_active(interaction):
            return
            
        try:
            embed = discord.Embed(
                title="🏪  Welcome to the Black Market",
                description="Select a category from the dropdown to start browsing gear.",
                color=config.COLOR_INFO
            )
            view = ShopView()
            await interaction.response.send_message(embed=embed, view=view)
        except Exception:
            import traceback; traceback.print_exc()

    shop_group = app_commands.Group(name="shop_cmd", description="Shop group if needed") # Keep /shop buy as a sub command
    # Actually wait, the spec said `/shop buy [id_key]`. If we have a single root command `/shop`
    # You can't mix root commands with subcommands of the same name cleanly in Discord.
    # The UI buttons handle buying directly. We'll add `/shop_buy` or rely solely on buttons.
    # Wait, the spec specifies "/shop buy [id_key]".
    
    # We can't have both `/shop` (slash command) and `/shop buy` 
    # unless /shop is a group. But we can't invoke a group!
    # I'll just rely on the interactive buttons which is perfectly standard and superior UX!
    # However I'll still provide a text based equivalent if really desired:
    @app_commands.command(name="buy_item", description="Directly purchase a shop item by ID Key (e.g. hat_c_001)")
    @app_commands.describe(id_key="Catalog ID key of the item")
    async def buy_item(self, interaction: discord.Interaction, id_key: str):
        await handle_buy(interaction, id_key)

async def setup(bot: commands.Bot):
    await bot.add_cog(ShopCog(bot))
