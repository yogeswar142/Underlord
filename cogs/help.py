# cogs/help.py
# /help command — Interactive guide with dropdown menus for command categories.

import discord
from discord import app_commands
from discord.ext import commands

import config

HELP_CATEGORIES = {
    "basics": {
        "label": "Basic & Profile",
        "emoji": "👤",
        "description": "Profile, stats, and daily commands.",
        "commands": [
            "`/profile` — View your stats, levels, and equipment.",
            "`/daily` — Claim your daily cash, XP, and streak rewards.",
            "`/gym` — Train permanent stats using stamina.",
            "`/leaderboard` — View top players in various categories."
        ]
    },
    "combat": {
        "label": "Combat & Crime",
        "emoji": "💀",
        "description": "Attack other players and commit crimes.",
        "commands": [
            "`/crime` — Select a crime to commit for cash/XP.",
            "`/attack` — Fight another player to steal cash and deal HP damage.",
            "`/rob` — Speed contest to steal small amounts of cash without damage."
        ]
    },
    "buildings": {
        "label": "Buildings & Economy",
        "emoji": "🏗️",
        "description": "Construct buildings and run your empire.",
        "commands": [
            "`/build` — Construct a new building for your empire.",
            "`/upgrade` — Improve an existing building's level.",
            "`/collect` — Harvest passive income from your businesses.",
            "`/farm start` & `/farm collect` — Grow and harvest crops.",
            "`/ship send` & `/ship collect` — Ship cargo overseas for profit."
        ]
    },
    "inventory": {
        "label": "Inventory & Gear",
        "emoji": "🎒",
        "description": "Manage your items and upgrades.",
        "commands": [
            "`/items` — View all your owned and equipped items.",
            "`/equip` & `/unequip` — Manage your active gear.",
            "`/upgrade-item` — Permanently boost an item's stats (RNG)."
        ]
    },
    "market": {
        "label": "Marketplace",
        "emoji": "🏬",
        "description": "Trade items and VIP days with other players.",
        "commands": [
            "`/market browse` — View active market listings.",
            "`/market buy` — Purchase an item or VIP days.",
            "`/market list-item` — Sell one of your items.",
            "`/market list-vip` — Sell your spare VIP days."
        ]
    },
    "gangs": {
        "label": "Gangs & Turf",
        "emoji": "🏴",
        "description": "Team up, pool resources, and fight for dominance.",
        "commands": [
            "`/gang create` & `/gang join` & `/gang leave` — Manage membership.",
            "`/gang info` & `/gang members` — View gang stats and rosters.",
            "`/gang bank deposit` & `/gang bank withdraw` — Manage gang funds."
        ]
    },
    "vip": {
        "label": "VIP Perks",
        "emoji": "👑",
        "description": "Manage your premium status.",
        "commands": [
            "`/vip status` — View your current VIP perks and remaining time.",
            "`/vip activate` — Consume VIP days from your inventory to extend time."
        ]
    }
}

class HelpSelect(discord.ui.Select):
    """Dropdown menu for selecting a help category."""
    
    def __init__(self):
        options = []
        for key, data in HELP_CATEGORIES.items():
            options.append(discord.SelectOption(
                label=data["label"],
                value=key,
                description=data["description"],
                emoji=data["emoji"]
            ))
        super().__init__(
            placeholder="Select a category to view commands...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        # We don't verify user_id here so that if the help message isn't ephemeral, others could use the dropdown.
        # However, we are making the help command output ephemeral anyway.
        category_key = self.values[0]
        data = HELP_CATEGORIES[category_key]
        
        embed = discord.Embed(
            title=f"{data['emoji']}  {data['label']}",
            description="\n\n".join(data["commands"]),
            color=config.COLOR_INFO
        )
        embed.set_footer(text="Select another category below to explore more commands.")
        
        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300) # 5 minutes timeout
        self.add_item(HelpSelect())

class HelpCog(commands.Cog):
    """The game's interactive help menu."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Remove default help command so it doesn't conflict
        self.bot.remove_command('help')

    @app_commands.command(name="help", description="View the guide and command list for Underworld Empire")
    async def help_cmd(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title="📜  Underworld Empire — Help Guide",
                description=(
                    "Welcome to the **Underworld**! \n"
                    "Build your empire, join a gang, commit crimes, and climb the leaderboards.\n\n"
                    "**How to play:**\n"
                    "Start by using `/profile` to choose your faction. Then, commit crimes with `/crime` and train your stats with `/gym`.\n\n"
                    "Please choose a category from the **dropdown menu below** to see available commands."
                ),
                color=config.COLOR_INFO
            )
            
            # Using the bot's avatar for aesthetic
            if self.bot.user.avatar:
                embed.set_thumbnail(url=self.bot.user.avatar.url)
            
            view = HelpView()
            
            # Sending as ephemeral to keep the chat clean
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            import traceback; traceback.print_exc()
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ Error", description="Could not load help menu.", color=config.COLOR_ERROR),
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
