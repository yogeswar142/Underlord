# cogs/register.py
# /register command — Full onboarding flow (faction, country, optional referral)
# All steps happen in one interactive session.

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta

import config
import db
import utils


# ── Step 1: Faction Selection ─────────────────────────────────────

class RegisterFactionSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Thug",
                value="thug",
                description="+15% Strength, +10% Stamina cap",
                emoji="🔪",
            ),
            discord.SelectOption(
                label="Businessman",
                value="businessman",
                description="+15% Speed, +20% income",
                emoji="💼",
            ),
            discord.SelectOption(
                label="Policeman",
                value="policeman",
                description="+15% Defense, +10% Courage cap",
                emoji="🛡️",
            ),
        ]
        super().__init__(placeholder="Choose your faction...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.view.user_id:
            return await interaction.response.send_message("This isn't your registration.", ephemeral=True)

        self.view.faction = self.values[0]

        # Disable faction select, move to Step 2: Country
        for child in self.view.children:
            child.disabled = True

        # Build the country selection embed
        embed = discord.Embed(
            title="🌍  Step 2 — Select Your Country",
            description=(
                "Swear allegiance to a nation.\n\n"
                "Foreign kills during gang shifts will earn your country points!\n"
                "Use the dropdown below or press **Next 25** to browse more."
            ),
            color=config.COLOR_INFO,
        )

        # Create new view for country
        country_view = RegisterCountryView(self.view.user_id, self.view.faction, self.view.username)
        await interaction.response.edit_message(embed=embed, view=country_view)


class RegisterFactionView(discord.ui.View):
    def __init__(self, user_id: str, username: str):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.username = username
        self.faction = None
        self.add_item(RegisterFactionSelect())


# ── Step 2: Country Selection ─────────────────────────────────────

class RegisterCountrySelect(discord.ui.Select):
    def __init__(self, page: int = 0):
        self.page = page
        start = page * 25
        options = []
        for country in config.COUNTRIES[start:start + 25]:
            options.append(discord.SelectOption(label=country, value=country, emoji="🌍"))
        super().__init__(placeholder=f"Select country (Page {page + 1})...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.view.user_id:
            return await interaction.response.send_message("This isn't your registration.", ephemeral=True)

        self.view.country = self.values[0]

        # Disable country select
        for child in self.view.children:
            child.disabled = True

        # Move to Step 3: Referral (optional)
        embed = discord.Embed(
            title="🤝  Step 3 — Referral (Optional)",
            description=(
                f"**Faction:** {config.FACTION_EMOJIS.get(self.view.faction, '❓')} {self.view.faction.title()}\n"
                f"**Country:** 🌍 {self.view.country}\n\n"
                "Were you invited by another player?\n"
                "Use the **button below** to mention who referred you — or **Skip** to finish.\n\n"
                "*You'll have 3 days to add a referral later using `/referral add`.*"
            ),
            color=config.COLOR_INFO,
        )

        referral_view = RegisterReferralView(
            self.view.user_id, self.view.username, self.view.faction, self.view.country
        )
        await interaction.response.edit_message(embed=embed, view=referral_view)


class RegisterCountryView(discord.ui.View):
    def __init__(self, user_id: str, faction: str, username: str):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.faction = faction
        self.username = username
        self.country = None
        self.page = 0
        self.select = RegisterCountrySelect(self.page)
        self.add_item(self.select)

    @discord.ui.button(label="Next 25 Countries ▶", style=discord.ButtonStyle.secondary, row=1)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            return

        self.page += 1
        if self.page * 25 >= len(config.COUNTRIES):
            self.page = 0

        self.remove_item(self.select)
        self.select = RegisterCountrySelect(self.page)
        self.children.insert(0, self.select)
        await interaction.response.edit_message(view=self)


# ── Step 3: Referral (Optional) ───────────────────────────────────

class ReferralModal(discord.ui.Modal, title="Enter Referral"):
    referral_input = discord.ui.TextInput(
        label="Who referred you? (Discord User ID or @mention)",
        placeholder="e.g. 123456789012345678",
        required=True,
        max_length=50,
    )

    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.referral_input.value.strip()
        # Extract ID from mention format <@123456> or raw number
        ref_id = raw.replace("<", "").replace(">", "").replace("@", "").replace("!", "").strip()

        if not ref_id.isdigit():
            await interaction.response.send_message("❌ Invalid user ID. Enter a numeric Discord ID.", ephemeral=True)
            return

        if ref_id == self.parent_view.user_id:
            await interaction.response.send_message("❌ You can't refer yourself!", ephemeral=True)
            return

        # Check if referred user exists
        ref_player = await db.get_player(ref_id)
        if not ref_player:
            await interaction.response.send_message(
                "❌ **Mentioned User is not valid.** They don't have an account yet.\n"
                "*You have 3 days to add a referral using `/referral add`.*",
                ephemeral=True,
            )
            return

        self.parent_view.referral_id = ref_id
        await self.parent_view.finalize_registration(interaction)


class RegisterReferralView(discord.ui.View):
    def __init__(self, user_id: str, username: str, faction: str, country: str):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.username = username
        self.faction = faction
        self.country = country
        self.referral_id = None

    @discord.ui.button(label="🤝 Add Referral", style=discord.ButtonStyle.primary)
    async def add_referral_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            return
        modal = ReferralModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Skip & Finish ✅", style=discord.ButtonStyle.success)
    async def skip_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            return
        await self.finalize_registration(interaction)

    async def finalize_registration(self, interaction: discord.Interaction):
        """Create the player document and finalize everything."""
        # Check if already registered
        existing = await db.get_player(self.user_id)
        if existing and existing.get("faction") and existing.get("country"):
            embed = discord.Embed(
                title="⚠️  Already Registered",
                description="You're already fully registered! Use `/profile` to view your stats.",
                color=config.COLOR_WARNING,
            )
            try:
                await interaction.response.edit_message(embed=embed, view=None)
            except discord.errors.InteractionResponded:
                await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Create or get the player
        player = existing or db.default_player(self.user_id, self.username)

        # Apply faction
        player = utils.apply_faction(player, self.faction)
        player["country"] = self.country

        # Apply referral
        if self.referral_id:
            player["referred_by"] = self.referral_id

        # Save
        if existing:
            await db.save_player(player)
        else:
            await db.get_db().players.insert_one(player)

        # Disable all buttons
        for child in self.children:
            child.disabled = True

        ref_text = ""
        if self.referral_id:
            ref_text = f"\n🤝 **Referred by:** <@{self.referral_id}>"

        embed = discord.Embed(
            title="🎉  Welcome to the Underworld!",
            description=(
                f"Registration complete! You're now a member of the criminal underground.\n\n"
                f"**Faction:** {config.FACTION_EMOJIS.get(self.faction, '❓')} {self.faction.title()}\n"
                f"**Country:** 🌍 {self.country}\n"
                f"{ref_text}\n\n"
                f"Use `/profile` to view your stats.\n"
                f"Use `/help` to see all available commands.\n\n"
                f"*The streets are watching. Make your mark.*"
            ),
            color=config.COLOR_SUCCESS,
        )

        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.errors.InteractionResponded:
            await interaction.followup.send(embed=embed)


# ── Register Cog ──────────────────────────────────────────────────

class RegisterCog(commands.Cog):
    """Player registration and onboarding."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="register", description="Create your Underworld character")
    async def register(self, interaction: discord.Interaction):
        try:
            player = await db.get_player(str(interaction.user.id))

            if player and player.get("faction") and player.get("country"):
                embed = discord.Embed(
                    title="⚠️  Already Registered",
                    description="You're already fully registered! Use `/profile` to view your stats.",
                    color=config.COLOR_WARNING,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # If partially registered (has player doc but missing faction/country), resume
            if player and not player.get("faction"):
                # Start from faction
                embed = discord.Embed(
                    title="⚔️  Step 1 — Choose Your Faction",
                    description=(
                        "This is a **permanent** choice that shapes your playstyle.\n\n"
                        "🔪 **Thug** — +15% Strength, +10% Stamina cap\n"
                        "💼 **Businessman** — +15% Speed, +20% income\n"
                        "🛡️ **Policeman** — +15% Defense, +10% Courage cap"
                    ),
                    color=config.COLOR_INFO,
                )
                view = RegisterFactionView(str(interaction.user.id), interaction.user.display_name)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                return

            if player and player.get("faction") and not player.get("country"):
                # Jump to country selection
                embed = discord.Embed(
                    title="🌍  Step 2 — Select Your Country",
                    description=(
                        "Swear allegiance to a nation.\n\n"
                        "Foreign kills during gang shifts will earn your country points!"
                    ),
                    color=config.COLOR_INFO,
                )
                view = RegisterCountryView(str(interaction.user.id), player["faction"], interaction.user.display_name)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                return

            # Fresh registration
            embed = discord.Embed(
                title="⚔️  Step 1 — Choose Your Faction",
                description=(
                    "Welcome to the **Underworld Empire**.\n\n"
                    "Before you enter the streets, choose your **faction**.\n"
                    "This is a **permanent** choice that shapes your playstyle.\n\n"
                    "🔪 **Thug** — +15% Strength, +10% Stamina cap\n"
                    "💼 **Businessman** — +15% Speed, +20% income\n"
                    "🛡️ **Policeman** — +15% Defense, +10% Courage cap"
                ),
                color=config.COLOR_INFO,
            )
            view = RegisterFactionView(str(interaction.user.id), interaction.user.display_name)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            import traceback; traceback.print_exc()
            embed = discord.Embed(
                title="❌  Error",
                description="Something went wrong during registration.",
                color=config.COLOR_ERROR,
            )
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except discord.errors.InteractionResponded:
                await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(RegisterCog(bot))
