# cogs/crime.py
# /crime command — commit crimes for cash, XP, and diamonds.

import random
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta

import config
import db
import utils


class CrimeSelect(discord.ui.Select):
    """Drop-down menu of available crimes."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        options = []
        for key, crime in config.CRIMES.items():
            label = key.replace("_", " ").title()
            desc = crime.get("description", "")
            emoji = crime.get("emoji", "💀")
            options.append(
                discord.SelectOption(
                    label=label, value=key, description=desc, emoji=emoji
                )
            )
        super().__init__(
            placeholder="Choose a crime...", options=options, min_values=1, max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "This isn't your crime menu.", ephemeral=True
            )
            return
            
        if not await utils.check_active(interaction):
            return

        crime_key = self.values[0]
        crime = config.CRIMES[crime_key]
        crime_name = crime_key.replace("_", " ").title()

        try:
            player = await db.get_player(self.user_id)
            if not player:
                await interaction.response.send_message(
                    "Player not found.", ephemeral=True
                )
                return

            # Check cooldown
            remaining = utils.cooldown_remaining(
                player["cooldowns"].get("crime"), crime["cooldown_seconds"]
            )
            if remaining > 0:
                embed = discord.Embed(
                    title="⏳  Crime Cooldown",
                    description=f"You can commit another crime in **{utils.format_cooldown(remaining)}**.",
                    color=config.COLOR_WARNING,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Check stamina
            stamina_needed = crime.get("stamina", 0)
            if player["renewable"]["stamina"] < stamina_needed:
                embed = discord.Embed(
                    title="⚡  Not Enough Stamina",
                    description=f"Need **{stamina_needed}** stamina, you have **{player['renewable']['stamina']}**.",
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Check courage
            courage_needed = crime.get("courage", 0)
            if player["renewable"]["courage"] < courage_needed:
                embed = discord.Embed(
                    title="🦁  Not Enough Courage",
                    description=f"Need **{courage_needed}** courage, you have **{player['renewable']['courage']}**.",
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Deduct stamina and courage regardless
            player["renewable"]["stamina"] -= stamina_needed
            player["renewable"]["courage"] -= courage_needed

            # Calculate success chance
            success_chance = crime["success_base"]
            success_chance += player["stats"]["strength"] / 200
            success_chance += player["stats"]["speed"] / 300
            success_chance = min(0.95, success_chance)

            roll = random.random()
            success = roll <= success_chance

            if success:
                embed = await self._handle_success(player, crime, crime_name, interaction)
            else:
                embed = await self._handle_failure(
                    player, crime, crime_name, interaction
                )

            # Save cooldown
            player["cooldowns"]["crime"] = datetime.now(timezone.utc)

            # Check level up
            player, leveled = utils.check_level_up(player)
            if leveled:
                embed.add_field(
                    name="🎉  LEVEL UP!",
                    value=f"You are now **Level {player['level']}**!",
                    inline=False,
                )

            await db.save_player(player)

            # Disable the select after use
            self.disabled = True
            self.view.stop()

            await interaction.response.edit_message(embed=embed, view=self.view)

        except Exception as e:
            import traceback
            traceback.print_exc()
            embed = discord.Embed(
                title="❌  Error",
                description="Something went wrong. Please try again.",
                color=config.COLOR_ERROR,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _handle_success(
        self, player: dict, crime: dict, crime_name: str, interaction: discord.Interaction
    ) -> discord.Embed:
        """Handle successful crime."""
        results = []

        # Cash reward
        if "reward_min" in crime and "reward_max" in crime:
            cash = random.randint(crime["reward_min"], crime["reward_max"])
            player["cash_wallet"] += cash
            results.append(f"💵 +{utils.format_cash(cash)}")

        # XP reward
        xp = crime.get("xp", 0) or crime.get("reward_xp", 0)
        if xp > 0:
            player["xp"] += xp
            results.append(f"⭐ +{xp} XP")

        # Diamond reward
        diamonds = crime.get("diamond_reward", 0)
        if diamonds > 0:
            player["diamonds"] += diamonds
            results.append(f"💎 +{diamonds} diamond(s)")

        # Courage reward (police_ambush)
        courage_reward = crime.get("reward_courage", 0)
        if courage_reward > 0:
            player["renewable"]["courage"] = min(
                player["renewable"]["courage_max"],
                player["renewable"]["courage"] + courage_reward,
            )
            results.append(f"🦁 +{courage_reward} Courage")

        embed = discord.Embed(
            title=f"✅  {crime_name} — Success!",
            description="\n".join(results),
            color=config.COLOR_SUCCESS,
        )
        embed.add_field(
            name="Stamina",
            value=f"{player['renewable']['stamina']}/{player['renewable']['stamina_max']}",
            inline=True,
        )
        
        # Roll Item Drop
        drop = utils.roll_item_drop("crime", is_vip=utils.is_vip(player))
        if drop:
            # Process DB asynchronously so it doesn't block the UI
            import asyncio
            asyncio.create_task(self.process_crime_drop(interaction, player["_id"], drop))
            
            TIER_EMOJIS = {"common": "⬜", "uncommon": "🟩", "rare": "🟦", "very_rare": "🟪", "legendary": "🟡"}
            emoji = TIER_EMOJIS.get(drop["tier"], "⬜")
            tier_name = drop["tier"].replace("_", " ").title()
            
            # Append Drop Section
            embed.add_field(
                name="🎁  Loot Drop!",
                value=(
                    f"{emoji} **{drop['name']}** ({tier_name})\n"
                    f"**Bonus:** +{drop['total_bonus']} {drop['stat_type'].title()}\n"
                    f"*{drop['lore']}*"
                ),
                inline=False
            )
            
        return embed

    async def process_crime_drop(self, interaction: discord.Interaction, player_id: str, item: dict):
        """Async task to save the drop so it doesn't block."""
        try:
            item["owner_id"] = player_id
            database = db.get_db()
            await database.items.insert_one(item)
            await database.players.update_one(
                {"_id": player_id},
                {"$push": {"items": item["_id"]}}
            )
            from cogs.upgrades import update_slot_rank
            await update_slot_rank(item["slot"])
            
            p = await database.players.find_one({"_id": player_id})
            if p and item.get("tier") in ("rare", "very_rare", "legendary"):
                tier_name = item["tier"].replace("_", " ").title()
                await utils.add_news(f"**{p['username']}** found a **{tier_name}** {item['name']}!")
        except Exception as e:
            import logging
            logging.error(f"Failed to process crime drop: {e}")


    async def _handle_failure(
        self,
        player: dict,
        crime: dict,
        crime_name: str,
        interaction: discord.Interaction,
    ) -> discord.Embed:
        """Handle failed crime."""
        results = []

        # HP loss
        hp_loss = crime.get("fail_hp_loss", 0)
        if hp_loss > 0:
            # Policeman faction: 25% chance to skip stamina deduction on fail
            # (design says stamina, but we already deducted it — skip HP loss instead)
            skip = (
                player.get("faction") == "policeman"
                and random.random() < 0.25
            )
            if skip:
                results.append("🛡️ Policeman instinct saved you from HP loss!")
            else:
                player["renewable"]["hp"] = max(
                    0, player["renewable"]["hp"] - hp_loss
                )
                results.append(f"❤️ -{hp_loss} HP")

        # Money loss
        money_loss_pct = crime.get("fail_money_loss_pct", 0)
        if money_loss_pct > 0:
            lost = int(player["cash_wallet"] * money_loss_pct)
            player["cash_wallet"] = max(0, player["cash_wallet"] - lost)
            results.append(f"💵 Lost {utils.format_cash(lost)}")

        # Wanted flag
        wanted_seconds = crime.get("wanted_on_fail_seconds", 0)
        if wanted_seconds > 0:
            player["wanted_until"] = datetime.now(timezone.utc) + timedelta(
                seconds=wanted_seconds
            )
            results.append(
                f"🚨 You are now **WANTED** for {utils.format_cooldown(wanted_seconds)}!"
            )

        if not results:
            results.append("You got away, but with nothing.")

        embed = discord.Embed(
            title=f"❌  {crime_name} — Failed!",
            description="\n".join(results),
            color=config.COLOR_ERROR,
        )
        embed.add_field(
            name="Stamina",
            value=f"{player['renewable']['stamina']}/{player['renewable']['stamina_max']}",
            inline=True,
        )
        embed.add_field(
            name="HP",
            value=f"{player['renewable']['hp']}/{player['renewable']['hp_max']}",
            inline=True,
        )
        return embed


class CrimeView(discord.ui.View):
    """View containing the crime select menu."""

    def __init__(self, user_id: str):
        super().__init__(timeout=60)
        self.add_item(CrimeSelect(user_id))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True


class CrimeCog(commands.Cog):
    """Crime system."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="crime", description="Commit a crime for cash, XP, and more")
    async def crime(self, interaction: discord.Interaction):
        if not await utils.check_active(interaction):
            return
            
        try:
            player = await db.ensure_player(
                str(interaction.user.id), interaction.user.display_name
            )

            if player["faction"] is None:
                embed = discord.Embed(
                    title="⚔️  Choose a Faction First",
                    description="Use `/profile` to select your faction.",
                    color=config.COLOR_WARNING,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Wanted status display
            wanted_text = ""
            if player.get("wanted_until"):
                w = player["wanted_until"]
                if w.tzinfo is None:
                    w = w.replace(tzinfo=timezone.utc)
                if w > datetime.now(timezone.utc):
                    rem = (w - datetime.now(timezone.utc)).total_seconds()
                    wanted_text = f"\n🚨 **WANTED** — {utils.format_cooldown(rem)} remaining\n"

            embed = discord.Embed(
                title="💀  Crime",
                description=(
                    f"🔋 Stamina: **{player['renewable']['stamina']}/{player['renewable']['stamina_max']}**\n"
                    f"🦁 Courage: **{player['renewable']['courage']}/{player['renewable']['courage_max']}**"
                    f"{wanted_text}\n\n"
                    "Select a crime from the menu below."
                ),
                color=config.COLOR_INFO,
            )
            view = CrimeView(str(interaction.user.id))
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


async def setup(bot: commands.Bot):
    await bot.add_cog(CrimeCog(bot))
