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


# ── Item generation ───────────────────────────────────────────

def generate_item(
    slot: str,
    tier: str = "common",
    name: str = "Unknown Item",
    owner_id: str | None = None,
) -> dict:
    """Create a new item document."""
    return {
        "_id": str(uuid4()),
        "owner_id": owner_id,
        "slot": slot,
        "name": name,
        "tier": tier,
        "stat_type": config.SLOT_STAT_MAP[slot],
        "base_stat": config.TIER_BONUS[tier],
        "upgrade_count": 0,
        "total_bonus": config.TIER_BONUS[tier],
        "slot_rank": 0,
        "on_market": False,
        "market_price": None,
        "market_listed_at": None,
        "market_expires_at": None,
        "entry_fee_paid": 0,
        "created_at": datetime.now(timezone.utc),
    }


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
