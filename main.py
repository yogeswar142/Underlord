# main.py
# Bot bootstrap — Motor DB init, APScheduler, auto cog loader, tree sync.

import asyncio
import logging
import os
import traceback
from pathlib import Path

import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

import db
from tick import refill_tick
from shift import end_shift

load_dotenv()

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
log = logging.getLogger("underworld")

# ── Bot setup ─────────────────────────────────────────────────
intents = discord.Intents.default()
# intents.members = True # Disabled to avoid privileged intent requirement

bot = commands.Bot(command_prefix="!", intents=intents)


# ── Auto Cog Loader ──────────────────────────────────────────
async def load_cogs(bot: commands.Bot):
    """
    Recursively scan the cogs/ directory (and all subdirectories)
    for .py files that contain an `async def setup` function.
    Automatically converts file paths to dotted module names and loads them.

    This means you can create new cog files in cogs/ or any subfolder
    and they'll be loaded on next bot restart — zero manual registration.
    """
    cogs_dir = Path(__file__).parent / "cogs"

    if not cogs_dir.exists():
        cogs_dir.mkdir(parents=True, exist_ok=True)
        log.warning("Created empty cogs/ directory.")
        return

    loaded = 0
    failed = 0

    for py_file in sorted(cogs_dir.rglob("*.py")):
        # Skip __init__.py and any files starting with _
        if py_file.name.startswith("_"):
            continue

        # Read the file and check for the setup function
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception as e:
            log.warning(f"Could not read {py_file}: {e}")
            continue

        if "async def setup" not in content:
            log.debug(f"Skipping {py_file.name} — no setup() function found.")
            continue

        # Convert path to dotted module name: cogs/sub/module.py → cogs.sub.module
        relative = py_file.relative_to(Path(__file__).parent)
        module = ".".join(relative.with_suffix("").parts)

        try:
            await bot.load_extension(module)
            log.info(f"✅  Loaded cog: {module}")
            loaded += 1
        except Exception as e:
            log.error(f"❌  Failed to load cog {module}: {e}")
            failed += 1

    log.info(f"Cog loader finished: {loaded} loaded, {failed} failed.")


# ── Bot events ────────────────────────────────────────────────

@bot.event
async def on_ready():
    # ── Database ──────────────────────────────────────────────
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        log.critical("MONGO_URI not set in .env — cannot start.")
        await bot.close()
        return

    database = db.init_db(mongo_uri)
    bot.db = database
    log.info("Connected to MongoDB.")

    # ── Scheduler ─────────────────────────────────────────────
    scheduler = AsyncIOScheduler()

    # 60-second stat refill tick
    scheduler.add_job(
        refill_tick,
        "interval",
        seconds=60,
        args=[database],
        id="refill_tick",
        replace_existing=True,
    )

    # Gang shift ends at 08:00 and 20:00 UTC
    scheduler.add_job(
        end_shift,
        CronTrigger(hour="8,20", minute=0, timezone="UTC"),
        args=[bot, database],
        id="end_shift",
        replace_existing=True,
    )

    scheduler.start()
    bot.scheduler = scheduler
    log.info("APScheduler started (tick + shift jobs).")

    # ── Load cogs ─────────────────────────────────────────────
    await load_cogs(bot)

    # ── Sync slash commands ───────────────────────────────────
    try:
        synced = await bot.tree.sync()
        log.info(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        log.error(f"Failed to sync commands: {e}")

    log.info(f"🏴 Underworld Empire online as {bot.user} (ID: {bot.user.id})")


@bot.event
async def on_command_error(ctx, error):
    """Global error handler for prefix commands (fallback)."""
    log.error(f"Command error: {error}", exc_info=error)


# ── Slash Error Handler ───────────────────────────────────────
LOG_CHANNEL_ID = 1490407083164831796

async def on_tree_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Global error handler for all slash commands."""
    # Get the full traceback
    tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    
    # Metadata
    user = interaction.user
    guild = interaction.guild.name if interaction.guild else "Direct Messages"
    channel = interaction.channel.name if interaction.guild else "DM"
    command_name = interaction.command.name if interaction.command else "Unknown Command"
    
    # 1. Inform the user
    error_msg = "❌  **Something went wrong!** An internal error occurred while processing your request. The developers have been notified."
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(error_msg, ephemeral=True)
        else:
            await interaction.followup.send(error_msg, ephemeral=True)
    except:
        pass

    # 2. Log to the developer channel
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if not log_channel:
        # Fallback if channel not found/cached
        try:
            log_channel = await bot.fetch_channel(LOG_CHANNEL_ID)
        except:
            log.error(f"Could not find log channel {LOG_CHANNEL_ID}")
            return

    if log_channel:
        embed = discord.Embed(
            title="🧨  System Crash Hooked",
            color=0xFF0000,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="👤 User", value=f"{user.mention} (`{user.id}`)", inline=True)
        embed.add_field(name="⚙️ Command", value=f"`/{command_name}`", inline=True)
        embed.add_field(name="📍 Location", value=f"🏰 **{guild}**\n📺 **#{channel}**", inline=False)
        
        # Traceback handle (Discord limit 4096 per embed description)
        raw_trace = tb
        if len(raw_trace) < 3900:
            embed.description = f"```py\n{raw_trace}\n```"
            await log_channel.send(embed=embed)
        else:
            # Chunking logic for massive tracebacks
            chunks = [raw_trace[i:i+3800] for i in range(0, len(raw_trace), 3800)]
            embed.description = f"```py\n{chunks[0]}\n```"
            embed.set_footer(text=f"Part 1 of {len(chunks)}")
            last_msg = await log_channel.send(embed=embed)
            
            for i, chunk in enumerate(chunks[1:], 2):
                next_embed = discord.Embed(
                    description=f"```py\n{chunk}\n```",
                    color=0xFF0000
                )
                next_embed.set_footer(text=f"Part {i} of {len(chunks)}")
                last_msg = await log_channel.send(embed=next_embed, reference=last_msg)

    # 3. Log to console
    log.error(f"Slash Error in /{command_name}: {error}", exc_info=error)

bot.tree.on_error = on_tree_error


# ── Run ───────────────────────────────────────────────────────

def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        log.critical("DISCORD_TOKEN not set in .env — cannot start.")
        return
    bot.run(token)


if __name__ == "__main__":
    main()
