# tick.py
# 60-second renewable stat refill tick — the heartbeat of the game.
# Runs as an APScheduler job started in main.py.

from datetime import datetime, timezone
from pymongo import UpdateOne
import config


async def refill_tick(db):
    """
    Runs every 60 seconds.
    Refills stamina, courage, hp for ALL players by their refill rate.
    Uses bulk_write for efficiency — one DB round-trip for all players.
    """
    now = datetime.now(timezone.utc)

    # Fetch only the fields we need
    players = await db.players.find(
        {},
        {
            "_id": 1,
            "vip_active_until": 1,
            "renewable": 1,
            "level": 1,
            "state": 1,
            "prison_until": 1,
        },
    ).to_list(None)

    if not players:
        return

    ops = []
    for p in players:
        is_vip = (
            p.get("vip_active_until") is not None
            and p["vip_active_until"] > now
        )
        rate = config.REFILL_VIP_PCT if is_vip else config.REFILL_FREE_PCT

        r = p["renewable"]
        lvl = p["level"]

        # Recalculate caps based on current level
        st_max = config.STAMINA_BASE + lvl * config.STAMINA_PER_LEVEL
        co_max = config.COURAGE_BASE + int(lvl * config.COURAGE_PER_LEVEL)
        hp_max = config.HP_BASE + lvl * config.HP_PER_LEVEL

        # Refill: add percentage of max, capped at max
        new_st = min(st_max, r["stamina"] + int(st_max * rate))
        new_co = min(co_max, r["courage"] + int(co_max * rate))
        new_hp = min(hp_max, r["hp"] + int(hp_max * rate))
        
        updates = {
            "renewable.stamina": new_st,
            "renewable.stamina_max": st_max,
            "renewable.courage": new_co,
            "renewable.courage_max": co_max,
            "renewable.hp": new_hp,
            "renewable.hp_max": hp_max,
        }
        
        # Check Hospital state
        state = p.get("state", "normal")
        if state == "hospital" and new_hp >= (hp_max * 0.5):
            updates["state"] = "normal"
            
        # Check Prison state
        if state == "prison":
            p_until = p.get("prison_until")
            if p_until:
                if p_until.tzinfo is None:
                    p_until = p_until.replace(tzinfo=timezone.utc)
                if now >= p_until:
                    updates["state"] = "normal"

        ops.append(
            UpdateOne(
                {"_id": p["_id"]},
                {"$set": updates},
            )
        )

    if ops:
        await db.players.bulk_write(ops)
