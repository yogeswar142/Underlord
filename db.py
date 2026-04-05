# db.py
# Motor async MongoDB singleton + helper functions.
# All DB access goes through this module.

from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import config

_client = None
_db = None


def init_db(mongo_uri: str, db_name: str = "underworld_empire"):
    """Initialise the Motor client. Call once in main.py on_ready."""
    global _client, _db
    _client = AsyncIOMotorClient(mongo_uri)
    _db = _client[db_name]
    return _db


def get_db():
    """Return the database instance. Raises if init_db was not called."""
    if _db is None:
        raise RuntimeError("Database not initialised — call init_db() first.")
    return _db


# ── Default document factories ────────────────────────────────

def default_player(user_id: str, username: str) -> dict:
    """Create a fresh player document with all default values."""
    return {
        "_id": str(user_id),
        "username": username,
        "faction": None,
        "level": 1,
        "xp": 0,
        "xp_to_next": config.XP_BASE,
        "cash_wallet": 0,
        "cash_bank": 0,
        "diamonds": 0,
        "vip_days": 0,
        "vip_active_until": None,

        "stats": {
            "strength": 10,
            "defense": 10,
            "speed": 10,
            "happiness": 10,
        },

        "renewable": {
            "stamina": config.STAMINA_BASE + 1 * config.STAMINA_PER_LEVEL,
            "stamina_max": config.STAMINA_BASE + 1 * config.STAMINA_PER_LEVEL,
            "courage": config.COURAGE_BASE + int(1 * config.COURAGE_PER_LEVEL),
            "courage_max": config.COURAGE_BASE + int(1 * config.COURAGE_PER_LEVEL),
            "hp": config.HP_BASE + 1 * config.HP_PER_LEVEL,
            "hp_max": config.HP_BASE + 1 * config.HP_PER_LEVEL,
        },

        "buildings": {
            "gym": 0,
            "farm": 0,
            "shipyard": 0,
            "mines": 0,
            "brothel": 0,
            "bank": 0,
            "market": 0,
            "mafia_house": 0,
            "opium_house": 0,
            "factory": 0,
        },

        "fleet": [],

        "profession": None,

        "inventory": {
            "hat":      None,
            "jacket":   None,
            "shoes":    None,
            "car":      None,
            "weapon1":  None,
            "weapon2":  None,
            "jewellery": None,
        },

        "items": [],   # list of item _id strings owned but not equipped

        "equipment_bonus": {
            "strength": 0,
            "defense": 0,
            "speed": 0,
            "happiness": 0,
        },

        "gang_id": None,

        "shield_until": None,

        "cooldowns": {
            "crime": None,
            "gym": None,
            "daily": None,
            "attack": None,
            "rob": None,
            "farm_start": None,
        },

        "wanted_until": None,

        "grain": 0,
        "opium": 0,

        "last_collect_at": None,

        "daily_streak": 0,

        "created_at": datetime.now(timezone.utc),
        
        "country": None,
        "state": "normal",  # can be "normal", "hospital", "prison"
        "prison_until": None,
        
        "referred_by": None,
        "referral_claimed_by_inviter": False,
    }


# ── Player helpers ────────────────────────────────────────────

async def get_player(user_id) -> dict | None:
    """Fetch a full player document by Discord user ID."""
    return await get_db().players.find_one({"_id": str(user_id)})


async def save_player(player: dict):
    """Replace-save a full player document."""
    await get_db().players.replace_one(
        {"_id": player["_id"]},
        player,
        upsert=True,
    )


async def ensure_player(user_id, username: str) -> dict:
    """Get existing player or create a new one with defaults."""
    player = await get_player(user_id)
    if player is None:
        player = default_player(str(user_id), username)
        await get_db().players.insert_one(player)
    return player


# ── Item helpers ──────────────────────────────────────────────

async def get_item(item_id: str) -> dict | None:
    """Fetch an item document by its UUID."""
    return await get_db().items.find_one({"_id": item_id})


async def save_item(item: dict):
    """Replace-save an item document."""
    await get_db().items.replace_one(
        {"_id": item["_id"]},
        item,
        upsert=True,
    )


async def get_player_items(user_id) -> list[dict]:
    """Fetch all items owned by a player (not on market)."""
    return await get_db().items.find(
        {"owner_id": str(user_id), "on_market": False}
    ).to_list(None)


async def get_items_by_ids(item_ids: list[str]) -> dict:
    """Fetch multiple items by ID, return as {item_id: item_doc}."""
    if not item_ids:
        return {}
    items = await get_db().items.find(
        {"_id": {"$in": item_ids}}
    ).to_list(None)
    return {i["_id"]: i for i in items}


# ── Gang helpers ──────────────────────────────────────────────

async def get_gang(gang_id: str) -> dict | None:
    """Fetch a gang document."""
    return await get_db().gangs.find_one({"_id": gang_id})


async def save_gang(gang: dict):
    """Replace-save a gang document."""
    await get_db().gangs.replace_one(
        {"_id": gang["_id"]},
        gang,
        upsert=True,
    )
