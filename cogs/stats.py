# cogs/stats.py
# /gym command — train permanent stats using stamina.

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone

import config
import db
import utils


class GymView(discord.ui.View):
    """Three-button view for gym training."""

    def __init__(self, user_id: str):
        super().__init__(timeout=60)
        self.user_id = user_id

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

    async def _train(
        self, interaction: discord.Interaction, mode: str
    ):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "This isn't your gym session.", ephemeral=True
            )
            return

        if not await utils.check_active(interaction):
            return

        try:
            player = await db.get_player(self.user_id)
            if not player:
                await interaction.response.send_message(
                    "Player not found.", ephemeral=True
                )
                return

            # Check faction
            if player["faction"] is None:
                await interaction.response.send_message(
                    "Choose a faction first with `/profile`.", ephemeral=True
                )
                return

            # Check cooldown
            remaining = utils.cooldown_remaining(
                player["cooldowns"].get("gym"), config.GYM_COOLDOWN_SECONDS
            )
            if remaining > 0:
                embed = discord.Embed(
                    title="⏳  Gym Cooldown",
                    description=f"You can train again in **{utils.format_cooldown(remaining)}**.",
                    color=config.COLOR_WARNING,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            gym_mode = config.GYM_MODES[mode]

            # Check stamina
            if player["renewable"]["stamina"] < gym_mode["stamina_cost"]:
                embed = discord.Embed(
                    title="⚡  Not Enough Stamina",
                    description=(
                        f"You need **{gym_mode['stamina_cost']}** stamina but have "
                        f"**{player['renewable']['stamina']}**."
                    ),
                    color=config.COLOR_ERROR,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Deduct stamina
            player["renewable"]["stamina"] -= gym_mode["stamina_cost"]

            # Calculate gain
            gym_level = player["buildings"].get("gym", 0)
            gain = int(gym_mode["base_gain"] + gym_level * config.GYM_GAIN_PER_LEVEL)
            gain = max(1, gain)  # always gain at least 1

            stat_name = gym_mode["stat"]
            old_val = player["stats"][stat_name]
            player["stats"][stat_name] += gain

            # Save cooldown
            player["cooldowns"]["gym"] = datetime.now(timezone.utc)

            await db.save_player(player)

            # Response
            stat_emoji = {"strength": "💪", "defense": "🛡️", "speed": "⚡"}
            embed = discord.Embed(
                title=f"🏋️  {mode.title()} Training Complete!",
                description=(
                    f"{stat_emoji.get(stat_name, '📈')} **{stat_name.title()}**: "
                    f"{old_val} → **{player['stats'][stat_name]}** (+{gain})\n\n"
                    f"🔋 Stamina: {player['renewable']['stamina']}/{player['renewable']['stamina_max']}"
                ),
                color=config.COLOR_SUCCESS,
            )
            if gym_level > 0:
                embed.set_footer(text=f"Gym Building Lv.{gym_level} bonus applied")

            # Disable buttons after use
            for child in self.children:
                child.disabled = True

            await interaction.response.edit_message(embed=embed, view=self)

        except Exception as e:
            import traceback
            traceback.print_exc()
            embed = discord.Embed(
                title="❌  Error",
                description="Something went wrong. Please try again.",
                color=config.COLOR_ERROR,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="💪 Lift (STR)", style=discord.ButtonStyle.danger)
    async def lift_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._train(interaction, "lift")

    @discord.ui.button(label="🛡️ Endure (DEF)", style=discord.ButtonStyle.primary)
    async def endure_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._train(interaction, "endure")

    @discord.ui.button(label="⚡ Sprint (SPD)", style=discord.ButtonStyle.success)
    async def sprint_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._train(interaction, "sprint")


class StatsCog(commands.Cog):
    """Gym training system."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="gym", description="Train your stats at the gym")
    async def gym(self, interaction: discord.Interaction):
        if not await utils.check_active(interaction):
            return
            
        try:
            player = await db.ensure_player(
                str(interaction.user.id), interaction.user.display_name
            )

            if player["faction"] is None:
                embed = discord.Embed(
                    title="⚔️  Choose a Faction First",
                    description="Use `/profile` to select your faction before training.",
                    color=config.COLOR_WARNING,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Check cooldown for display
            remaining = utils.cooldown_remaining(
                player["cooldowns"].get("gym"), config.GYM_COOLDOWN_SECONDS
            )

            gym_level = player["buildings"].get("gym", 0)
            bonus_text = f" (+{gym_level * config.GYM_GAIN_PER_LEVEL:.1f} bonus from Gym Lv.{gym_level})" if gym_level > 0 else ""

            description = (
                f"🔋 Stamina: **{player['renewable']['stamina']}/{player['renewable']['stamina_max']}**\n\n"
                f"Choose your training:\n"
                f"💪 **Lift** — Strength +1{bonus_text} (costs {config.GYM_MODES['lift']['stamina_cost']} stamina)\n"
                f"🛡️ **Endure** — Defense +1{bonus_text} (costs {config.GYM_MODES['endure']['stamina_cost']} stamina)\n"
                f"⚡ **Sprint** — Speed +1{bonus_text} (costs {config.GYM_MODES['sprint']['stamina_cost']} stamina)"
            )

            if remaining > 0:
                description += f"\n\n⏳ Cooldown: **{utils.format_cooldown(remaining)}**"

            embed = discord.Embed(
                title="🏋️  Gym",
                description=description,
                color=config.COLOR_INFO,
            )

            view = GymView(str(interaction.user.id))
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
    await bot.add_cog(StatsCog(bot))
