# utils.py
# Shared gameplay helpers used across cogs.

from datetime import datetime, timezone
from uuid import uuid4
import config


# ── Level system ──────────────────────────────────────────────

def check_level_up(player: dict) -> tuple[dict, bool]:
    """
    Process XP overflow into level-ups.
    Returns (updated_player, did_level_up).
    """
    leveled = False
    while (
        player["xp"] >= player["xp_to_next"]
        and player["level"] < config.MAX_LEVEL
    ):
        player["xp"] -= player["xp_to_next"]
        player["level"] += 1
        player["xp_to_next"] = int(
            config.XP_BASE * (config.XP_SCALE ** player["level"])
        )
        leveled = True
    return player, leveled


# ── Faction application ──────────────────────────────────────

def apply_faction(player: dict, faction: str) -> dict:
    """Apply one-time faction stat bonuses. Called once on faction selection."""
    bonuses = config.FACTION_BONUSES[faction]
    if "strength" in bonuses:
        player["stats"]["strength"] = int(
            player["stats"]["strength"] * bonuses["strength"]
        )
    if "defense" in bonuses:
        player["stats"]["defense"] = int(
            player["stats"]["defense"] * bonuses["defense"]
        )
    if "speed" in bonuses:
        player["stats"]["speed"] = int(
            player["stats"]["speed"] * bonuses["speed"]
        )
    if "stamina_bonus" in bonuses:
        player["renewable"]["stamina_max"] = int(
            player["renewable"]["stamina_max"] * bonuses["stamina_bonus"]
        )
        player["renewable"]["stamina"] = player["renewable"]["stamina_max"]
    if "courage_bonus" in bonuses:
        player["renewable"]["courage_max"] = int(
            player["renewable"]["courage_max"] * bonuses["courage_bonus"]
        )
        player["renewable"]["courage"] = player["renewable"]["courage_max"]
    player["faction"] = faction
    return player


# ── VIP check ─────────────────────────────────────────────────

def is_vip(player: dict) -> bool:
    """Check if a player currently has active VIP status."""
    until = player.get("vip_active_until")
    return until is not None and until > datetime.now(timezone.utc)

# ── State check ───────────────────────────────────────────────

async def check_active(interaction) -> bool:
    """Returns True if player is normal. If hospital/prison, sends error and returns False."""
    import db
    import discord
    player = await db.get_player(str(interaction.user.id))
    if not player:
        return True
        
    state = player.get("state", "normal")
    if state == "hospital":
        embed = discord.Embed(
            title="🏥  Incapacitated",
            description="You are currently recovering in the Hospital! You cannot do this right now.",
            color=config.COLOR_ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False
    elif state == "prison":
        embed = discord.Embed(
            title="🚔  Behind Bars",
            description="You are currently locked up in Prison! You cannot do this right now.",
            color=config.COLOR_ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False
        
    return True


# ── Equipment bonus recalculation ─────────────────────────────

def recalc_equipment_bonus(player: dict, items_dict: dict) -> dict:
    """
    Compute the equipment_bonus sub-doc from all equipped items.
    items_dict: {item_id: item_doc}
    Returns the bonus dict AND updates player["equipment_bonus"] in place.
    
    *** CRITICAL: Call this on EVERY equip, unequip, and item upgrade. ***
    """
    bonus = {"strength": 0, "defense": 0, "speed": 0, "happiness": 0}
    for slot, item_id in player["inventory"].items():
        if item_id and item_id in items_dict:
            item = items_dict[item_id]
            bonus[item["stat_type"]] += item["total_bonus"]
    player["equipment_bonus"] = bonus
    return bonus


# ── Item generation & drops ──────────────────────────────────────

def generate_item_from_catalog(id_key: str) -> dict:
    """
    Creates a new item document in the items collection format
    from a catalog entry.
    """
    from items_catalog import ITEMS_CATALOG
    from uuid import uuid4
    from datetime import datetime, timezone

    template = ITEMS_CATALOG[id_key]
    return {
        "_id": str(uuid4()),
        "catalog_id": id_key,
        "owner_id": None,          # set after purchase/drop
        "slot": template["slot"],
        "name": template["name"],
        "lore": template["lore"],
        "tier": template["tier"],
        "stat_type": template["stat_type"],
        "base_stat": template["base_stat"],
        "upgrade_count": 0,
        "total_bonus": template["base_stat"],
        "slot_rank": 0,
        "on_market": False,
        "market_price": None,
        "market_listed_at": None,
        "market_expires_at": None,
        "entry_fee_paid": 0,
        "created_at": datetime.now(timezone.utc),
    }

def roll_item_drop(source: str, is_vip: bool = False) -> dict | None:
    """
    Roll for an item drop based on DROP RATE TABLE.
    source: "crime" | "bank_heist" | "daily_7" | "daily_30" | "shift_top1" | "shift_top2" | "shift_top3" | "mine"
    """
    import random
    from items_catalog import get_all_slots, get_drop_pool
    
    # [Common, Uncommon, Rare, Very Rare, Legendary]
    rates = {
        "crime": {"common": 0.30, "uncommon": 0.08, "rare": 0.02, "very_rare": 0.0, "legendary": 0.0},
        "bank_heist": {"common": 0.0, "uncommon": 0.20, "rare": 0.15, "very_rare": 0.05, "legendary": 0.0},
        "shift_top1": {"common": 0.0, "uncommon": 0.0, "rare": 0.0, "very_rare": 0.40, "legendary": 0.05},
        "shift_top2": {"common": 0.0, "uncommon": 0.0, "rare": 0.0, "very_rare": 0.20, "legendary": 0.02},
        "shift_top3": {"common": 0.0, "uncommon": 0.0, "rare": 0.30, "very_rare": 0.10, "legendary": 0.0},
        "daily_7": {"common": 0.0, "uncommon": 0.50, "rare": 0.30, "very_rare": 0.0, "legendary": 0.0},
        "daily_30": {"common": 0.0, "uncommon": 0.0, "rare": 0.50, "very_rare": 0.30, "legendary": 0.05},
        "mine": {"common": 0.0, "uncommon": 0.0, "rare": 0.20, "very_rare": 0.05, "legendary": 0.0}, # per 10 diamonds
    }
    
    if source not in rates:
        return None
        
    source_rates = rates[source]
    roll = random.random()
    
    # Process from rarest to most common to give them precedence
    tier_found = None
    if roll < source_rates["legendary"]:
        tier_found = "legendary"
    elif roll < source_rates["legendary"] + source_rates["very_rare"]:
        tier_found = "very_rare"
    elif roll < source_rates["legendary"] + source_rates["very_rare"] + source_rates["rare"]:
        tier_found = "rare"
    elif roll < source_rates["legendary"] + source_rates["very_rare"] + source_rates["rare"] + source_rates["uncommon"]:
        tier_found = "uncommon"
    elif roll < source_rates["legendary"] + source_rates["very_rare"] + source_rates["rare"] + source_rates["uncommon"] + source_rates["common"]:
        tier_found = "common"
        
    if not tier_found:
        return None
        
    slot = random.choice(get_all_slots())
    pool = get_drop_pool(slot, tier_found)
    
    if not pool:
        return None
        
    id_key = random.choice(pool)
    return generate_item_from_catalog(id_key)


# ── PvP helpers ───────────────────────────────────────────────

def level_gap_ok(
    attacker_level: int, target_level: int, in_gang_shift: bool = False
) -> bool:
    """Check if the level gap allows PvP between two players."""
    gap = (
        config.PVP_LEVEL_GAP_GANG_WAR if in_gang_shift
        else config.PVP_LEVEL_GAP
    )
    return abs(attacker_level - target_level) <= gap


def in_active_gang_shift(gang: dict | None) -> bool:
    """Check if a gang is currently in an active shift."""
    if not gang:
        return False
    return gang.get("shift_state") == "active"


# ── Display helpers ───────────────────────────────────────────

def xp_bar(xp: int, xp_to_next: int, length: int = 10) -> str:
    """Render an XP progress bar: ████░░░░░░ 240/300 XP"""
    if xp_to_next <= 0:
        ratio = 1.0
    else:
        ratio = min(xp / xp_to_next, 1.0)
    filled = int(ratio * length)
    empty = length - filled
    bar = "█" * filled + "░" * empty
    return f"{bar} {xp:,}/{xp_to_next:,} XP"


def stat_bar(current: int, maximum: int, length: int = 10) -> str:
    """Render a stat bar: ████████░░ 80/100"""
    if maximum <= 0:
        ratio = 1.0
    else:
        ratio = min(current / maximum, 1.0)
    filled = int(ratio * length)
    empty = length - filled
    bar = "█" * filled + "░" * empty
    return f"{bar} {current:,}/{maximum:,}"


def format_cooldown(seconds_remaining: float) -> str:
    """Format seconds into human-readable cooldown string."""
    if seconds_remaining <= 0:
        return "Ready!"
    seconds_remaining = int(seconds_remaining)
    hours = seconds_remaining // 3600
    minutes = (seconds_remaining % 3600) // 60
    secs = seconds_remaining % 60
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def short_id(uuid_str: str) -> str:
    """Return first 8 chars of a UUID for display."""
    return uuid_str[:8]


def format_cash(amount: int) -> str:
    """Format cash with dollar sign and commas."""
    return f"${amount:,}"


# ── Cooldown check ────────────────────────────────────────────

def cooldown_remaining(timestamp, cooldown_seconds: int) -> float:
    """
    Returns seconds remaining on a cooldown.
    Returns 0 if ready. timestamp can be None (= ready).
    """
    if timestamp is None:
        return 0
    now = datetime.now(timezone.utc)
    # Handle naive datetimes from DB
    if timestamp.tzinfo is None:
        from datetime import timezone as tz
        timestamp = timestamp.replace(tzinfo=tz.utc)
    elapsed = (now - timestamp).total_seconds()
    remaining = cooldown_seconds - elapsed
    return max(0, remaining)


# ── Tier helpers ──────────────────────────────────────────────

def next_tier(current_tier: str) -> str | None:
    """Return the next tier up, or None if already legendary."""
    idx = config.TIER_ORDER.index(current_tier)
    if idx >= len(config.TIER_ORDER) - 1:
        return None
    return config.TIER_ORDER[idx + 1]
