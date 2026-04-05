# main.py
# Bot bootstrap — Motor DB init, APScheduler, auto cog loader, tree sync.

import asyncio
import logging
import os
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
intents.members = True

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
        args=[database],
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


# ── Run ───────────────────────────────────────────────────────

def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        log.critical("DISCORD_TOKEN not set in .env — cannot start.")
        return
    bot.run(token)


if __name__ == "__main__":
    main()
