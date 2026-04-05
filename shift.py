# shift.py
# Gang shift lifecycle — runs every 12 hours via APScheduler CronTrigger.
# Shift times: 08:00 UTC and 20:00 UTC.

from datetime import datetime, timezone
from uuid import uuid4
from pymongo import UpdateOne
import config


async def end_shift(db):
    """
    End the current shift:
    1. Rank active gangs by current_shift_points.
    2. Distribute top-3 rewards to all members of winning gangs.
    3. Archive the shift to shift_history.
    4. Rotate gang states: active → resting.
    5. Gangs that were resting → inactive (ready for next shift).
    6. Reset all shift points.
    """
    now = datetime.now(timezone.utc)

    # ── 1. Rank active gangs ──────────────────────────────────
    active_gangs = await db.gangs.find(
        {"shift_state": "active"}
    ).sort("current_shift_points", -1).to_list(None)

    top3 = active_gangs[:3]

    # ── 2. Distribute rewards to top 3 ───────────────────────
    shift_top = []
    for i, gang in enumerate(top3):
        if i >= len(config.GANG_REWARD_TOP3):
            break
        reward = config.GANG_REWARD_TOP3[i]

        # Gather all member IDs (leader + officers + members)
        all_members = (
            [gang["leader_id"]]
            + gang.get("officers", [])
            + gang.get("members", [])
        )
        # Deduplicate
        all_members = list(set(all_members))

        # Award each member
        if all_members:
            await db.players.update_many(
                {"_id": {"$in": all_members}},
                {
                    "$inc": {
                        "cash_wallet": reward["cash"],
                        "xp": reward["xp"],
                        "diamonds": reward["diamonds"],
                    }
                },
            )

        # Increment gang shift_wins
        await db.gangs.update_one(
            {"_id": gang["_id"]},
            {"$inc": {"shift_wins": 1}},
        )

        shift_top.append({
            "gang_id": gang["_id"],
            "gang_name": gang["name"],
            "points": gang["current_shift_points"],
            "reward_distributed": True,
        })

    # ── 3. Archive shift ─────────────────────────────────────
    # Get the last shift number
    last_shift = await db.shift_history.find_one(
        sort=[("shift_number", -1)]
    )
    shift_number = (last_shift["shift_number"] + 1) if last_shift else 1

    await db.shift_history.insert_one({
        "_id": str(uuid4()),
        "shift_number": shift_number,
        "start_time": None,  # We don't track exact start in this model
        "end_time": now,
        "top_gangs": shift_top,
    })

    # ── 4. Rotate states ─────────────────────────────────────
    # Active → Resting
    await db.gangs.update_many(
        {"shift_state": "active"},
        {"$set": {"shift_state": "resting"}},
    )

    # Resting (from previous shift) → Inactive (eligible for next)
    # Note: we already set active→resting above, so the "resting" ones
    # here are from the PREVIOUS shift rotation. We handle this by
    # running the resting→inactive BEFORE active→resting.
    # However since we already updated active→resting, we need a
    # different approach. Let's use a two-phase update with a temp state.

    # Actually, the correct approach:
    # Before updating active→resting, mark the currently resting as inactive.
    # But we already did active→resting. So let's fix: the gangs that were
    # resting at the START of this function should go to inactive.
    # Since we already moved active→resting, we can't distinguish.
    # Solution: query by _id for the gangs that were active (we have their IDs).

    active_gang_ids = [g["_id"] for g in active_gangs]

    # Set gangs that are now "resting" BUT were not in active_gangs → inactive
    # (these were already resting from previous shift)
    await db.gangs.update_many(
        {
            "shift_state": "resting",
            "_id": {"$nin": active_gang_ids},
        },
        {"$set": {"shift_state": "inactive"}},
    )

    # ── 5. Reset shift points for all gangs ──────────────────
    await db.gangs.update_many(
        {},
        {"$set": {"current_shift_points": 0}},
    )


async def handle_kill_points(db, attacker_id: str, target_id: str):
    """
    Award/deduct gang shift points when a kill happens.
    Called from the PvP cog after a successful kill.
    """
    attacker = await db.players.find_one({"_id": attacker_id})
    target = await db.players.find_one({"_id": target_id})

    if not attacker or not target:
        return

    atk_gang_id = attacker.get("gang_id")
    tgt_gang_id = target.get("gang_id")

    # Attacker's gang gains points
    if atk_gang_id:
        gang = await db.gangs.find_one({"_id": atk_gang_id})
        if gang:
            if gang["shift_state"] == "inactive":
                # Auto-activate on first kill
                await db.gangs.update_one(
                    {"_id": atk_gang_id},
                    {"$set": {"shift_state": "active"}},
                )
            if gang["shift_state"] in ("active", "inactive"):
                # inactive just got set to active above
                await db.gangs.update_one(
                    {"_id": atk_gang_id},
                    {"$inc": {"current_shift_points": config.SHIFT_KILL_POINTS}},
                )

    # Target's gang loses points
    if tgt_gang_id:
        gang = await db.gangs.find_one({"_id": tgt_gang_id})
        if gang and gang["shift_state"] == "active":
            new_pts = max(
                0, gang["current_shift_points"] + config.SHIFT_DEATH_POINTS
            )
            await db.gangs.update_one(
                {"_id": tgt_gang_id},
                {"$set": {"current_shift_points": new_pts}},
            )
