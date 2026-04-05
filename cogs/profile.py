# cogs/profile.py
# /profile and /faction commands — the foundation cog.
# Every other system depends on a player document existing.

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone

import config
import db
import utils


class FactionSelectView(discord.ui.View):
    """Three-button view for one-time faction selection."""

    def __init__(self, user_id: str):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.chosen = False

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

    async def _pick_faction(
        self, interaction: discord.Interaction, faction: str
    ):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "This isn't your selection.", ephemeral=True
            )
            return

        if self.chosen:
            await interaction.response.send_message(
                "You already picked a faction.", ephemeral=True
            )
            return

        self.chosen = True

        # Fetch & update player
        player = await db.get_player(self.user_id)
        if not player:
            await interaction.response.send_message(
                "Player not found.", ephemeral=True
            )
            return

        player = utils.apply_faction(player, faction)
        await db.save_player(player)

        emoji = config.FACTION_EMOJIS[faction]
        embed = discord.Embed(
            title=f"{emoji}  Faction Chosen: {faction.title()}",
            description=(
                f"Your stats have been adjusted with **{faction.title()}** bonuses.\n\n"
                f"Now use `/profile` again to select your **Country**."
            ),
            color=config.COLOR_SUCCESS,
        )
        # Disable all buttons
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🔪 Thug", style=discord.ButtonStyle.danger)
    async def thug_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._pick_faction(interaction, "thug")

    @discord.ui.button(label="💼 Businessman", style=discord.ButtonStyle.primary)
    async def businessman_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._pick_faction(interaction, "businessman")

    @discord.ui.button(label="🛡️ Policeman", style=discord.ButtonStyle.success)
    async def policeman_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._pick_faction(interaction, "policeman")


class CountrySelect(discord.ui.Select):
    def __init__(self, user_id: str, page: int = 0):
        self.user_id = user_id
        options = []
        start = page * 25
        # Discord limits select menus to 25 items
        for country in config.COUNTRIES[start:start+25]:
            options.append(discord.SelectOption(label=country, value=country, emoji="🌍"))
            
        super().__init__(placeholder="Select your country...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This isn't your setup.", ephemeral=True)
            return

        choice = self.values[0]
        player = await db.get_player(self.user_id)
        if player:
            player["country"] = choice
            await db.save_player(player)

            embed = discord.Embed(
                title=f"🌍  Country Chosen: {choice}",
                description="Your nationality is sealed in blood. You are now fully registered in the Underworld.\n\nRun `/profile` to view your stats.",
                color=config.COLOR_SUCCESS
            )
            for child in self.view.children:
                child.disabled = True
            await interaction.response.edit_message(embed=embed, view=self.view)

class CountrySelectView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.page = 0
        self.select = CountrySelect(user_id, self.page)
        self.add_item(self.select)

    @discord.ui.button(label="Next 25 Countries", style=discord.ButtonStyle.secondary, row=1)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            return
            
        self.page += 1
        if self.page * 25 >= len(config.COUNTRIES):
            self.page = 0 # loop back
            
        self.remove_item(self.select)
        self.select = CountrySelect(self.user_id, self.page)
        # re-insert at the top
        self.children.insert(0, self.select)
        await interaction.response.edit_message(view=self)


class ProfilePaginationSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Overview", value="overview", description="Basic info, Faction, Rank", emoji="📋"),
            discord.SelectOption(label="Stats & Resources", value="stats", description="Permanent & renewable stats, Currency", emoji="📈"),
            discord.SelectOption(label="Equipment Setup", value="equipment", description="Equipped items & combat loadout", emoji="🎒"),
            discord.SelectOption(label="Properties & Assets", value="buildings", description="Owned buildings & real estate", emoji="🏗️"),
        ]
        super().__init__(placeholder="Select profile category...", options=options, custom_id="profile_select")

    async def callback(self, interaction: discord.Interaction):
        # We fetch fresh player data in case it updated
        database = db.get_db()
        player = await database.players.find_one({"_id": str(self.view.target.id)})
        
        if not player:
            return await interaction.response.send_message("Could not retrieve player.", ephemeral=True)
            
        embed = await self.view.cog.build_profile_embed(player, self.view.target, self.values[0])
        await interaction.response.edit_message(embed=embed, view=self.view)


class ProfileView(discord.ui.View):
    def __init__(self, cog, target: discord.User):
        super().__init__(timeout=120)
        self.cog = cog
        self.target = target
        self.add_item(ProfilePaginationSelect())


class ProfileCog(commands.Cog):
    """Player profile and faction selection."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="profile", description="View your (or another player's) profile")
    @app_commands.describe(user="The player to view (leave blank for yourself)")
    async def profile(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
    ):
        try:
            target = user or interaction.user
            player = await db.get_player(str(target.id))

            if not player:
                if target.id == interaction.user.id:
                    embed = discord.Embed(
                        title="❌  Not Registered",
                        description="You haven't joined the Underworld yet!\nUse `/register` to create your character.",
                        color=config.COLOR_ERROR,
                    )
                else:
                    embed = discord.Embed(
                        title="❌  Player Not Found",
                        description=f"**{target.display_name}** hasn't registered yet.",
                        color=config.COLOR_ERROR,
                    )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if player["faction"] is None or player.get("country") is None:
                embed = discord.Embed(
                    title="⚠️  Registration Incomplete",
                    description="Your setup isn't complete yet.\nUse `/register` to finish choosing your faction and country.",
                    color=config.COLOR_WARNING,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # ── Build profile embed ───────────────────────────
            embed = await self.build_profile_embed(player, target, "overview")
            view = ProfileView(self, target)
            await interaction.response.send_message(embed=embed, view=view)

        except Exception as e:
            import traceback
            traceback.print_exc()
            embed = discord.Embed(
                title="❌  Error",
                description="Something went wrong. Please try again.",
                color=config.COLOR_ERROR,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def build_profile_embed(self, player: dict, discord_user: discord.User, category: str = "overview") -> discord.Embed:
        """Build the paginated profile embed."""
        vip = utils.is_vip(player)
        vip_badge = " 👑 VIP" if vip else ""
        
        wanted = ""
        if player.get("wanted_until"):
            w_until = player["wanted_until"]
            if w_until.tzinfo is None:
                w_until = w_until.replace(tzinfo=timezone.utc)
            if w_until > datetime.now(timezone.utc):
                wanted = " 🚨 WANTED"
                
        state_badge = ""
        user_state = player.get("state", "normal")
        if user_state == "hospital":
            state_badge = " 🏥 INCAPACITATED"
        elif user_state == "prison":
            state_badge = " 🚔 IN PRISON"

        embed = discord.Embed(
            title=f"{discord_user.display_name}{vip_badge}{wanted}{state_badge}",
            color=config.COLOR_VIP if vip else config.COLOR_INFO,
        )

        if discord_user.avatar:
            embed.set_thumbnail(url=discord_user.avatar.url)

        embed.set_footer(text=f"ID: {player['_id']} • Player since {player['created_at'].strftime('%b %d, %Y')}")

        if category == "overview":
            faction = player.get("faction") or "None"
            faction_emoji = config.FACTION_EMOJIS.get(faction, "❓")
            faction_display = f"{faction_emoji} {faction.title()}" if faction != "None" else "❓ No Faction"
            
            country = player.get("country") or "Unknown"
            
            gang_name = "None"
            if player.get("gang_id"):
                gang = await db.get_gang(player["gang_id"])
                if gang:
                    gang_name = f"{gang.get('tag', '')} {gang['name']}"
                    
            xp_display = utils.xp_bar(player["xp"], player["xp_to_next"])
            
            embed.description = "### 📋 Overview"
            embed.add_field(name="Level & XP", value=f"**Level {player['level']}**\n{xp_display}", inline=False)
            embed.add_field(name="Identity", value=f"**Faction**: {faction_display}\n**Country**: 🌍 {country}", inline=True)
            embed.add_field(name="Gang", value=f"**{gang_name}**", inline=True)
            
        elif category == "stats":
            embed.description = "### 📈 Stats & Resources"
            
            s = player["stats"]
            eb = player.get("equipment_bonus", {"strength": 0, "defense": 0, "speed": 0, "happiness": 0})
            stats_text = (
                f"💪 Strength: **{s['strength']}** (+{eb['strength']})\n"
                f"🛡️ Defense: **{s['defense']}** (+{eb['defense']})\n"
                f"⚡ Speed: **{s['speed']}** (+{eb['speed']})\n"
                f"😊 Happiness: **{s['happiness']}** (+{eb['happiness']})"
            )
            embed.add_field(name="Permanent Stats", value=stats_text, inline=True)
            
            r = player["renewable"]
            renew_text = (
                f"🔋 Stamina:\n{utils.stat_bar(r['stamina'], r['stamina_max'], 8)}\n"
                f"🦁 Courage:\n{utils.stat_bar(r['courage'], r['courage_max'], 8)}\n"
                f"❤️ HP:\n{utils.stat_bar(r['hp'], r['hp_max'], 8)}"
            )
            embed.add_field(name="Renewable Reserves", value=renew_text, inline=True)
            
            wallet_text = (
                f"💵 Wallet: {utils.format_cash(player['cash_wallet'])}\n"
                f"🏦 Bank: {utils.format_cash(player['cash_bank'])}\n"
                f"💎 Diamonds: {player['diamonds']:,}"
            )
            embed.add_field(name="Finances", value=wallet_text, inline=False)
            
        elif category == "equipment":
            embed.description = "### 🎒 Equipment Setup"
            
            inv = player["inventory"]
            equipped_ids = [iid for iid in inv.values() if iid is not None]
            items_dict = await db.get_items_by_ids(equipped_ids)

            slot_emojis = {
                "hat": "🎩", "jacket": "🧥", "shoes": "👟",
                "car": "🚗", "weapon1": "🔫", "weapon2": "🗡️",
                "jewellery": "💍",
            }

            equip_lines = []
            for slot, item_id in inv.items():
                emoji = slot_emojis.get(slot, "•")
                if item_id and item_id in items_dict:
                    item = items_dict[item_id]
                    tier_tag = item["tier"].replace("_", " ").title()
                    equip_lines.append(f"{emoji} **{slot.title()}**: {item['name']} ({tier_tag})\n└ *Bonus: +{item['total_bonus']} {item['stat_type'].title()}*")
                else:
                    equip_lines.append(f"{emoji} **{slot.title()}**: —\n└ *(Empty)*")

            embed.add_field(name="Combat Loadout", value="\n\n".join(equip_lines[:4]), inline=True)
            embed.add_field(name="Accessories", value="\n\n".join(equip_lines[4:]), inline=True)
            
        elif category == "buildings":
            embed.description = "### 🏗️ Properties & Assets"
            
            bldgs = player.get("buildings", {})
            if not bldgs:
                embed.add_field(name="Real Estate", value="You don't own any properties yet.\nUse `/build` to get started.", inline=False)
            else:
                lines = []
                for k, v in bldgs.items():
                    emoji = config.BUILDINGS.get(k, {}).get("emoji", "🏗️")
                    name = k.replace("_", " ").title()
                    lines.append(f"{emoji} **{name}** — Level {v}")
                
                embed.add_field(name="Real Estate Portfolio", value="\n".join(lines), inline=False)
                
            fleet = player.get("fleet", [])
            if fleet:
                ships_text = []
                for s in fleet:
                    status = "At Sea" if s.get("at_sea") else "Docked"
                    ships_text.append(f"⛵ **{s['name']}** ({status})")
                embed.add_field(name="Naval Fleet", value="\n".join(ships_text), inline=False)

        return embed


async def setup(bot: commands.Bot):
    await bot.add_cog(ProfileCog(bot))
