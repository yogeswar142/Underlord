# cogs/news.py
import discord
from discord import app_commands
from discord.ext import commands
import config
import db
import utils

class NewsSelect(discord.ui.Select):
    def __init__(self, news_entries):
        options = []
        for idx, news in enumerate(news_entries[:25], 1):
            label = f"Event #{idx}"
            text_preview = news["text"][:90] + ("..." if len(news["text"]) > 90 else "")
            options.append(discord.SelectOption(label=label, description=text_preview, value=str(idx), emoji="📰"))
            
        if not options:
            options.append(discord.SelectOption(label="No New News", value="none", emoji="📰"))
            
        super().__init__(placeholder="View exactly what happened in these events...", options=options, custom_id="news_select")
        self.news_entries = news_entries

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("No recent events.", ephemeral=True)
            return

        idx = int(self.values[0]) - 1
        news = self.news_entries[idx]
        
        embed = discord.Embed(
            title="📰 Underworld Newspaper",
            description=news["text"],
            color=config.COLOR_INFO,
            timestamp=news["timestamp"]
        )
        embed.set_footer(text="Broadcasted")
        
        await interaction.response.edit_message(embed=embed, view=self.view)


class NewsView(discord.ui.View):
    def __init__(self, news_entries):
        super().__init__(timeout=120)
        self.add_item(NewsSelect(news_entries))


class NewsCog(commands.Cog):
    """The latest live news from the Underworld."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="news", description="Read the latest 10 major events from the server")
    async def news(self, interaction: discord.Interaction):
        try:
            database = db.get_db()
            news_cursor = database.news.find().sort("timestamp", -1).limit(10)
            news_entries = await news_cursor.to_list(None)
            
            if not news_entries:
                embed = discord.Embed(title="📰  Underworld Times", description="Nothing interesting has happened lately.", color=config.COLOR_INFO)
                await interaction.response.send_message(embed=embed)
                return

            embed = discord.Embed(
                title="📰  Underworld Times — Latest Headlines",
                color=config.COLOR_INFO
            )
            
            lines = []
            for idx, entry in enumerate(news_entries, 1):
                raw_time = entry["timestamp"]
                ts = int(raw_time.timestamp())
                lines.append(f"**{idx}.** <t:{ts}:R> — {entry['text']}")
                
            embed.description = "\n\n".join(lines)
            embed.set_footer(text="Select an entry from the dropdown menu to focus on it.")
            
            view = NewsView(news_entries)
            await interaction.response.send_message(embed=embed, view=view)

        except Exception as e:
            import traceback; traceback.print_exc()
            await interaction.response.send_message("❌ Failed to fetch news.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(NewsCog(bot))
