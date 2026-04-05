# UNDERWORLD EMPIRE — Agent Build Document
> Discord bot MMO game · Python · discord.py · MongoDB (motor async)
> Read this entire document before writing any code. Every system is interconnected.

---

## TECH STACK

```
Language        : Python 3.11+
Discord Library : discord.py 2.x (slash commands via app_commands)
Database        : MongoDB Atlas (async via motor)
Scheduler       : APScheduler (AsyncIOScheduler) for ticks and shifts
Environment     : python-dotenv for secrets
Structure       : Cog-based (one file per system)
```

### Project folder structure
```
underworld_empire/
├── main.py                  # Bot init, cog loader, scheduler start
├── .env                     # DISCORD_TOKEN, MONGO_URI
├── config.py                # All game constants (tweak without touching logic)
├── db.py                    # Motor client singleton, helper get/set functions
├── utils.py                 # Shared helpers: level_cap, xp_to_level, etc.
├── tick.py                  # 60-second stat refill tick (APScheduler job)
├── shift.py                 # Shift start/end logic (APScheduler job)
├── cogs/
│   ├── profile.py           # /profile, /faction
│   ├── stats.py             # /gym, stat display
│   ├── crime.py             # /crime
│   ├── pvp.py               # /attack, /rob, shield logic
│   ├── buildings.py         # /build, /upgrade, /collect
│   ├── inventory.py         # /equip, /unequip, /items
│   ├── upgrades.py          # /upgrade-item (item upgrade with RNG)
│   ├── market.py            # /market list, /market buy, /market browse
│   ├── gang.py              # /gang create, /gang join, /gang war, etc.
│   ├── leaderboard.py       # /leaderboard [category]
│   ├── daily.py             # /daily
│   └── vip.py               # /vip status, /vip activate
```

---

## MONGODB COLLECTIONS

### Collection: `players`
```json
{
  "_id": "discord_user_id_string",
  "username": "DiscordUsername",
  "faction": "thug | businessman | policeman | null",
  "level": 1,
  "xp": 0,
  "xp_to_next": 100,
  "cash_wallet": 0,
  "cash_bank": 0,
  "diamonds": 0,
  "vip_days": 0,
  "vip_active_until": null,

  "stats": {
    "strength": 10,
    "defense": 10,
    "speed": 10,
    "happiness": 10
  },

  "renewable": {
    "stamina": 20,
    "stamina_max": 20,
    "courage": 10,
    "courage_max": 10,
    "hp": 100,
    "hp_max": 100
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
    "factory": 0
  },

  "fleet": [],

  "profession": null,

  "inventory": {
    "hat":     null,
    "jacket":  null,
    "shoes":   null,
    "car":     null,
    "weapon1": null,
    "weapon2": null,
    "jewellery": null
  },

  "items": [],

  "gang_id": null,

  "shield_until": null,

  "cooldowns": {
    "crime": null,
    "gym": null,
    "daily": null,
    "attack": null,
    "farm_start": null
  },

  "wanted_until": null,
  "created_at": "ISO timestamp"
}
```

### Collection: `items`
Every item in the game (owned or on market) lives here.
```json
{
  "_id": "uuid4 string",
  "owner_id": "discord_user_id or null if on market",
  "slot": "hat | jacket | shoes | car | weapon1 | weapon2 | jewellery",
  "name": "Street Cap",
  "tier": "common | uncommon | rare | very_rare | legendary",
  "base_stat": 5,
  "upgrade_count": 0,
  "total_bonus": 5,
  "stat_type": "defense | speed | strength | happiness",
  "slot_rank": 0,
  "on_market": false,
  "market_price": null,
  "market_listed_at": null,
  "market_expires_at": null,
  "entry_fee_paid": 0,
  "created_at": "ISO timestamp"
}
```

### Collection: `gangs`
```json
{
  "_id": "uuid4 string",
  "name": "Gang Name",
  "tag": "[TAG]",
  "type": "cartel | syndicate | yakuza | brotherhood",
  "leader_id": "discord_user_id",
  "officers": [],
  "members": [],
  "level": 1,
  "xp": 0,
  "bank": 0,
  "bank_cap": 50000,
  "current_shift_points": 0,
  "shift_state": "active | resting | inactive",
  "total_kills": 0,
  "shift_wins": 0,
  "created_at": "ISO timestamp"
}
```

### Collection: `market_listings`
```json
{
  "_id": "uuid4 string",
  "seller_id": "discord_user_id",
  "type": "item | vip_days",
  "item_id": "uuid4 or null",
  "vip_days_amount": 0,
  "price": 50000,
  "entry_fee_paid": 0,
  "listed_at": "ISO timestamp",
  "expires_at": "ISO timestamp"
}
```

### Collection: `shift_history`
```json
{
  "_id": "uuid4 string",
  "shift_number": 42,
  "start_time": "ISO timestamp",
  "end_time": "ISO timestamp",
  "top_gangs": [
    { "gang_id": "...", "points": 120, "reward_distributed": true }
  ]
}
```

---

## CONFIG.PY — ALL GAME CONSTANTS

```python
# config.py
# Tweak balance here without touching game logic.

# ── Level system ──────────────────────────────────────────────
XP_BASE = 100
XP_SCALE = 1.18          # xp_needed = XP_BASE * (XP_SCALE ** level)
MAX_LEVEL = 100

# ── Renewable stat caps (base + per level) ────────────────────
STAMINA_BASE = 20
STAMINA_PER_LEVEL = 2     # cap = STAMINA_BASE + level * STAMINA_PER_LEVEL

COURAGE_BASE = 10
COURAGE_PER_LEVEL = 1.5

HP_BASE = 100
HP_PER_LEVEL = 10

# ── Refill rates (% of max per 60s tick) ─────────────────────
REFILL_FREE_PCT = 0.15
REFILL_VIP_PCT  = 0.30

# ── Faction bonuses (multipliers on top of base) ──────────────
FACTION_BONUSES = {
    "thug":       {"strength": 1.15, "stamina_bonus": 1.10},
    "businessman":{"speed": 1.15, "income_mult": 1.20},
    "policeman":  {"defense": 1.15, "courage_bonus": 1.10},
}

# ── Gym costs & rewards ───────────────────────────────────────
GYM_MODES = {
    "lift":    {"stamina_cost": 4, "stat": "strength", "base_gain": 1},
    "endure":  {"stamina_cost": 3, "stat": "defense",  "base_gain": 1},
    "sprint":  {"stamina_cost": 3, "stat": "speed",    "base_gain": 1},
}
GYM_GAIN_PER_LEVEL = 0.2  # additional gain = gym_building_level * 0.2

# ── Crime table ───────────────────────────────────────────────
CRIMES = {
    "pickpocket": {
        "stamina": 2, "courage": 1,
        "reward_min": 200, "reward_max": 800,
        "xp": 10, "success_base": 0.75,
        "fail_hp_loss": 5, "fail_money_loss_pct": 0,
        "cooldown_seconds": 30
    },
    "rob_store": {
        "stamina": 5, "courage": 2,
        "reward_min": 800, "reward_max": 3000,
        "xp": 30, "success_base": 0.60,
        "fail_hp_loss": 15, "fail_money_loss_pct": 0,
        "cooldown_seconds": 120
    },
    "drug_deal": {
        "stamina": 6, "courage": 3,
        "reward_min": 2000, "reward_max": 6000,
        "xp": 50, "success_base": 0.55,
        "fail_hp_loss": 0, "fail_money_loss_pct": 0.10,
        "diamond_reward": 1,
        "cooldown_seconds": 300
    },
    "bank_heist": {
        "stamina": 15, "courage": 6,
        "reward_min": 15000, "reward_max": 50000,
        "xp": 200, "success_base": 0.35,
        "fail_hp_loss": 40, "fail_money_loss_pct": 0,
        "wanted_on_fail_seconds": 900,
        "cooldown_seconds": 3600
    },
    "police_ambush": {
        "stamina": 10, "courage": 5,
        "reward_xp": 300, "reward_courage": 5,
        "success_base": 0.50,
        "fail_hp_loss": 30,
        "cooldown_seconds": 1800
    },
}

# ── Building costs & effects ──────────────────────────────────
# Each building: list of 10 upgrade costs and what each level gives.
# cost[i] = cost to upgrade FROM level i TO level i+1
BUILDINGS = {
    "gym": {
        "costs":   [500, 1500, 4000, 10000, 25000, 60000, 150000, 400000, 1000000, 2500000],
        "unlock_level": 1,
    },
    "farm": {
        "costs":   [800, 2000, 5000, 12000, 30000, 75000, 200000, 500000, 1200000, 3000000],
        "unlock_level": 1,
        "grain_per_cycle": [10, 20, 35, 55, 80, 110, 150, 200, 260, 340],
        "cycle_minutes":   [60, 55, 50, 45, 40, 35, 30, 25, 20, 15],
        "stamina_to_start": 5,
        "base_sell_price_per_grain": 100,
        "ship_sell_multiplier": 1.40,
    },
    "shipyard": {
        "costs": [2000, 6000, 15000, 40000, 100000, 250000, 600000, 1500000, 4000000, 10000000],
        "unlock_level": 3,
        "ships_unlocked": {
            1: {"name": "Dinghy",    "capacity": 50,  "return_minutes": 30},
            3: {"name": "Trawler",   "capacity": 150, "return_minutes": 25},
            5: {"name": "Freighter", "capacity": 400, "return_minutes": 20},
            7: {"name": "Tanker",    "capacity": 1000,"return_minutes": 15},
            10:{"name": "Carrier",   "capacity": 3000,"return_minutes": 10},
        },
    },
    "mines": {
        "costs": [5000, 15000, 40000, 100000, 250000, 600000, 1500000, 4000000, 10000000, 25000000],
        "unlock_level": 5,
        "diamonds_per_hour": [0.5, 1, 1.5, 2, 3, 4, 5, 7, 9, 12],
    },
    "brothel": {
        "costs": [1000, 3000, 8000, 20000, 50000, 120000, 300000, 800000, 2000000, 5000000],
        "unlock_level": 1,
        "cash_per_hour": [200, 500, 1200, 3000, 7500, 18000, 45000, 120000, 300000, 750000],
    },
    "bank": {
        "costs": [500, 1500, 4000, 10000, 25000, 60000, 150000, 400000, 1000000, 2500000],
        "unlock_level": 1,
    },
    "market": {
        "costs": [1000, 3000, 8000, 20000, 50000, 120000, 300000, 800000, 2000000, 5000000],
        "unlock_level": 2,
        "fee_reduction_per_level": 0.03,  # up to 30% fee reduction at lv10
    },
    "mafia_house": {
        "costs": [3000, 8000, 20000, 50000, 120000, 300000, 800000, 2000000, 5000000, 12000000],
        "unlock_level": 8,
        "income_per_hour_by_profession": {
            "smuggler":    [500, 1200, 2500, 5000, 10000, 20000, 40000, 80000, 160000, 320000],
            "enforcer":    [400, 900,  1800, 3600, 7200,  14400, 28800, 57600, 115200, 230400],
            "fixer":       [600, 1400, 2800, 5600, 11200, 22400, 44800, 89600, 179200, 358400],
            "laundryman":  [800, 1800, 3600, 7200, 14400, 28800, 57600, 115200,230400, 460800],
        },
        "profession_change_cooldown_hours": 168,  # 7 days
    },
    "opium_house": {
        "costs": [50000, 150000, 400000, 1000000, 2500000, 6000000, 15000000, 40000000, 100000000, 250000000],
        "unlock_level": 30,
        "opium_per_cycle": [5, 12, 25, 45, 75, 120, 180, 260, 360, 500],
        "cycle_minutes":   [120, 110, 100, 90, 80, 70, 60, 50, 40, 30],
        "courage_to_start": 5,
        "ship_sell_price_per_opium": 1200,  # vs grain 140
        "raid_fail_chance": 0.08,           # 8% chance opium batch wiped
    },
    "factory": {
        "costs": [20000, 60000, 150000, 400000, 1000000, 2500000, 6000000, 15000000, 40000000, 100000000],
        "unlock_level": 25,
        "upgrade_cost_reduction": [0, 0.03, 0.06, 0.09, 0.12, 0.15, 0.18, 0.21, 0.25, 0.30],
        "market_fee_reduction": [0, 0.03, 0.06, 0.09, 0.12, 0.15, 0.18, 0.21, 0.25, 0.30],
    },
}

# ── Item upgrade RNG table ─────────────────────────────────────
UPGRADE_OUTCOMES = {
    "free": {
        "normal":    {"chance": 0.60, "multiplier": 1.0},
        "rare":      {"chance": 0.25, "multiplier": 1.5},
        "very_rare": {"chance": 0.12, "multiplier": 2.0, "tier_up": True},
        "legendary": {"chance": 0.03, "multiplier": 3.0, "tier_up": True, "max_tier": True},
    },
    "vip": {
        "normal":    {"chance": 0.55, "multiplier": 1.0},
        "rare":      {"chance": 0.25, "multiplier": 1.5},
        "very_rare": {"chance": 0.15, "multiplier": 2.0, "tier_up": True},
        "legendary": {"chance": 0.05, "multiplier": 3.0, "tier_up": True, "max_tier": True},
    },
}
UPGRADE_BASE_COST_BY_TIER = {
    "common":    500,
    "uncommon":  2000,
    "rare":      8000,
    "very_rare": 25000,
    "legendary": 80000,
}
UPGRADE_HAPPINESS_COST = 5  # flat happiness per upgrade attempt

# ── Market entry fees ──────────────────────────────────────────
MARKET_ITEM_ENTRY_FEE = {
    "common":    500,
    "uncommon":  2000,
    "rare":      8000,
    "very_rare": 25000,
    "legendary": 80000,
}
MARKET_VIP_ENTRY_FEE_DAYS = 3
MARKET_VIP_MIN_LISTING_DAYS = 10
MARKET_LISTING_DURATION_HOURS = 48
MARKET_TRANSACTION_FEE_PCT = 0.05  # 5% cut on successful sale

# ── PvP formulas ──────────────────────────────────────────────
PVP_LEVEL_GAP = 5            # max level difference for normal attack
PVP_LEVEL_GAP_GANG_WAR = 8   # gap widens during active shift
KILL_BASE_STEAL_PCT = 0.20   # base % of wallet stolen on kill
KILL_SPEED_STEAL_BONUS = 0.005  # each point of speed over target = +0.5%
ROB_BASE_STEAL_PCT = 0.08
ROB_SPEED_STEAL_BONUS = 0.003
SHIELD_DURATION_SECONDS = 1800   # 30 minutes
WANTED_DURATION_SECONDS = 900    # 15 minutes after bank heist fail

# ── Gang shift system ─────────────────────────────────────────
SHIFT_DURATION_HOURS = 12
SHIFT_KILL_POINTS = 4
SHIFT_DEATH_POINTS = -2
GANG_REWARD_TOP3 = [
    {"rank": 1, "cash": 50000, "xp": 500, "diamonds": 10},
    {"rank": 2, "cash": 25000, "xp": 250, "diamonds": 5},
    {"rank": 3, "cash": 10000, "xp": 100, "diamonds": 2},
]

# ── VIP ───────────────────────────────────────────────────────
VIP_INCOME_MULT = 1.20
VIP_SELL_PRICE_MULT = 1.15
VIP_UPGRADE_RARE_BONUS = 0.05    # added to very_rare and legendary chances
```

---

## SYSTEM 1 — PLAYER PROFILE & FACTION

### On first /profile (new player)
1. Create player document in `players` with all defaults.
2. Prompt faction selection if `faction == null` using a discord.py View with 3 buttons (Thug / Businessman / Policeman).
3. Once faction chosen: apply faction stat multipliers to base stats, save.

### /profile command output
Embed showing:
- Username, Level, XP bar (e.g. `████░░ 240/300 XP`)
- Faction tag with emoji
- Permanent stats (Strength / Defense / Speed / Happiness)
- Renewable stats shown as bars (current/max): Stamina, Courage, HP
- Wallet cash, Bank cash, Diamonds
- VIP badge if active
- Gang name if in one
- Equipment slots summary (slot name → item name + tier)

### Faction stat application (call once on faction selection)
```python
def apply_faction(player_doc, faction):
    bonuses = config.FACTION_BONUSES[faction]
    if "strength" in bonuses:
        player_doc["stats"]["strength"] = int(player_doc["stats"]["strength"] * bonuses["strength"])
    if "defense" in bonuses:
        player_doc["stats"]["defense"] = int(player_doc["stats"]["defense"] * bonuses["defense"])
    if "speed" in bonuses:
        player_doc["stats"]["speed"] = int(player_doc["stats"]["speed"] * bonuses["speed"])
    if "stamina_bonus" in bonuses:
        player_doc["renewable"]["stamina_max"] = int(player_doc["renewable"]["stamina_max"] * bonuses["stamina_bonus"])
        player_doc["renewable"]["stamina"] = player_doc["renewable"]["stamina_max"]
    if "courage_bonus" in bonuses:
        player_doc["renewable"]["courage_max"] = int(player_doc["renewable"]["courage_max"] * bonuses["courage_bonus"])
        player_doc["renewable"]["courage"] = player_doc["renewable"]["courage_max"]
    player_doc["faction"] = faction
    return player_doc
```

---

## SYSTEM 2 — RENEWABLE STAT REFILL TICK

This is the heartbeat of the game. Run every 60 seconds via APScheduler.

### tick.py logic
```python
async def refill_tick(db):
    """
    Runs every 60 seconds.
    Refills stamina, courage, hp for all players by their rate.
    Uses bulk_write for efficiency.
    """
    now = datetime.utcnow()
    players = await db.players.find({}, {"_id":1, "vip_active_until":1, "renewable":1, "level":1}).to_list(None)

    ops = []
    for p in players:
        is_vip = p.get("vip_active_until") and p["vip_active_until"] > now
        rate = config.REFILL_VIP_PCT if is_vip else config.REFILL_FREE_PCT

        r = p["renewable"]
        lvl = p["level"]

        # Recalculate caps based on current level
        st_max = config.STAMINA_BASE + lvl * config.STAMINA_PER_LEVEL
        co_max = config.COURAGE_BASE + int(lvl * config.COURAGE_PER_LEVEL)
        hp_max = config.HP_BASE + lvl * config.HP_PER_LEVEL

        new_st = min(st_max, r["stamina"] + int(st_max * rate))
        new_co = min(co_max, r["courage"] + int(co_max * rate))
        new_hp = min(hp_max, r["hp"]      + int(hp_max * rate))

        ops.append(UpdateOne(
            {"_id": p["_id"]},
            {"$set": {
                "renewable.stamina": new_st,
                "renewable.stamina_max": st_max,
                "renewable.courage": new_co,
                "renewable.courage_max": co_max,
                "renewable.hp": new_hp,
                "renewable.hp_max": hp_max,
            }}
        ))

    if ops:
        await db.players.bulk_write(ops)
```

---

## SYSTEM 3 — GYM

### /gym command
Show three buttons: Lift (Strength) / Endure (Defense) / Sprint (Speed).
On button click:
1. Check cooldown (60 seconds since last gym use).
2. Check stamina >= mode cost.
3. Deduct stamina.
4. Calculate gain: `base_gain + gym_building_level * GYM_GAIN_PER_LEVEL`
5. Add gain to permanent stat.
6. Save cooldown timestamp.
7. Respond with embed showing stat gained and new value.

---

## SYSTEM 4 — CRIME

### /crime command
Show crime options as a Select menu. Player picks one.
1. Check crime cooldown.
2. Check stamina and courage requirements.
3. Calculate success chance:
   `success = crime["success_base"] + (player_strength / 200) + (player_speed / 300)`
   Cap at 0.95.
4. Deduct stamina and courage regardless of outcome.
5. Roll `random.random()`:
   - Success → add reward money (random between min/max), add XP, handle level up.
   - Fail → deduct HP, deduct fail_money_loss_pct from wallet, apply wanted flag if applicable.
6. Policeman faction: 25% chance to skip stamina deduction on fail.
7. Save cooldown.

### Level up logic
```python
def check_level_up(player):
    leveled = False
    while player["xp"] >= player["xp_to_next"]:
        player["xp"] -= player["xp_to_next"]
        player["level"] += 1
        player["xp_to_next"] = int(config.XP_BASE * (config.XP_SCALE ** player["level"]))
        leveled = True
    return player, leveled
```

---

## SYSTEM 5 — PVP (KILL & ROB)

### Pre-attack validation (both Kill and Rob)
1. Check attacker has no active shield. If shielded → error.
2. Check level gap: `abs(attacker_level - target_level) <= PVP_LEVEL_GAP`.
   During active gang shift: use PVP_LEVEL_GAP_GANG_WAR.
3. Check target exists and is not the attacker.
4. Check target shield: if shielded and target has NOT initiated any action → block attack.

### /attack @user — Kill
1. Validate (above).
2. Deduct Courage cost (5).
3. Combat roll:
   `attacker_power = strength + (defense * 0.3) + random.randint(-10, 10)`
   `target_power   = target_strength + (target_defense * 0.3) + random.randint(-10, 10)`
4. Winner determined by higher power.
5. Win:
   - Calculate steal: `pct = KILL_BASE_STEAL_PCT + max(0, attacker_speed - target_speed) * KILL_SPEED_STEAL_BONUS`
   - Stolen = `min(target_wallet * pct, target_wallet)`
   - Transfer stolen cash to attacker wallet.
   - Deduct stolen from target wallet.
   - Deal HP damage to target: `random.randint(20, 40)`.
   - Award attacker XP (100).
   - If target gang exists: gang gets `-2` shift points.
   - If attacker gang exists: gang gets `+4` shift points.
   - Apply shield to target (30 minutes).
6. Loss:
   - Deal HP damage to attacker: `random.randint(15, 30)`.
   - Target gets +4 shift points for their gang (defended kill).

### /rob @user — Speed contest, no HP damage
1. Validate (above). No Courage cost. Costs 2 Stamina.
2. Speed contest: `attacker_roll = speed + random.randint(-5, 5)` vs same for target.
3. Win:
   - Steal pct = `ROB_BASE_STEAL_PCT + max(0, attacker_speed - target_speed) * ROB_SPEED_STEAL_BONUS`
   - Transfer cash. No shield applied. No gang points.
4. Loss: nothing happens. 60-second rob cooldown.

### Shield logic
- On kill (whether attacker wins or loses against target): target gets shield.
- Shield stored as `shield_until` timestamp.
- If shielded player uses /attack or /rob: `shield_until = null` (shield dropped).
- Check shield on every incoming attack: if `shield_until > now` → block.

---

## SYSTEM 6 — BUILDINGS

### /build [building_name]
1. Check player level >= building unlock_level.
2. Check building is at level 0.
3. Deduct cost[0] from wallet.
4. Set building level to 1.

### /upgrade [building_name]
1. Check building level < 10.
2. Deduct cost[current_level] from wallet.
3. Increment building level.

### /collect
Collect passive income from:
- Brothel: `(hours_since_last_collect * cash_per_hour[brothel_level])` × businessman income multiplier if applicable.
- Mafia house: similar hourly calculation by profession.
- Mines: diamonds at diamonds_per_hour[mines_level] × hours elapsed.

Store `last_collect_at` timestamp per building or globally. Cap max accumulation at 24 hours to prevent hoarding.

### Farm cycle
`/farm start` — costs STAMINA_TO_START stamina. Records `farm_started_at`. Cycle duration from config.
`/farm collect` — if elapsed >= cycle_minutes[farm_level]: grants grain to inventory.

### Ship trading
`/ship send [ship_name] [grain|opium]`
1. Check ship is owned and not already at sea.
2. Check cargo amount >= 1.
3. Mark ship as `at_sea: true`, `departs_at`, `returns_at = now + return_minutes`.
4. Deduct cargo from player inventory.

`/ship collect`
1. Check `returns_at <= now`.
2. Calculate payment: `cargo * sell_price * VIP_SELL_MULT (if vip)`.
3. Add to wallet. Mark ship `at_sea: false`.

---

## SYSTEM 7 — INVENTORY & ITEMS

### Item generation (called by Market purchase or drop events)
```python
def generate_item(slot, tier="common"):
    tier_bonus = {"common": 5, "uncommon": 12, "rare": 25, "very_rare": 50, "legendary": 100}
    stat_map = {
        "hat":       "defense",
        "jacket":    "defense",
        "shoes":     "defense",
        "car":       "speed",
        "weapon1":   "strength",
        "weapon2":   "strength",
        "jewellery": "happiness",
    }
    return {
        "_id": str(uuid4()),
        "slot": slot,
        "tier": tier,
        "stat_type": stat_map[slot],
        "base_stat": tier_bonus[tier],
        "upgrade_count": 0,
        "total_bonus": tier_bonus[tier],
        "slot_rank": 0,
        "on_market": False,
    }
```

### /equip [item_id]
1. Verify item belongs to player.
2. If slot already occupied: move current equipped item back to player.items list.
3. Set `inventory[slot] = item_id`.
4. Recalculate player stats from all equipped items.

### Recalculate stats from equipment
```python
def recalc_stats_from_equipment(player, items_dict):
    """items_dict: {item_id: item_doc}"""
    bonus = {"strength": 0, "defense": 0, "speed": 0, "happiness": 0}
    for slot, item_id in player["inventory"].items():
        if item_id and item_id in items_dict:
            item = items_dict[item_id]
            bonus[item["stat_type"]] += item["total_bonus"]
    return bonus
```

Store equipment bonuses as a separate `equipment_bonus` sub-doc in player for fast combat reads.

### /upgrade-item [item_id]
1. Check player owns item.
2. Check player happiness >= UPGRADE_HAPPINESS_COST.
3. Deduct happiness (permanent stat deduction — Jewellery slot helps offset this cost over time by boosting happiness cap feel).
4. Deduct cash cost: `UPGRADE_BASE_COST_BY_TIER[tier]` × (1 - factory_upgrade_reduction).
5. Roll outcome using VIP or free table.
6. Apply: `item["total_bonus"] += int(item["base_stat"] * multiplier)`.
7. If tier_up: advance tier (common→uncommon→rare→very_rare→legendary).
8. Increment upgrade_count.
9. Trigger slot_rank recalculation (see Leaderboard system).

---

## SYSTEM 8 — MARKET

### /market list item [item_id] [price]
1. Check item belongs to player.
2. Check item not already on market.
3. Determine entry fee: `MARKET_ITEM_ENTRY_FEE[item_tier]` × (1 - factory_market_reduction).
4. Deduct entry fee from wallet. If insufficient → error.
5. Create market_listing doc. Set item `on_market: True`, `owner_id: null`.
6. Remove item from player.items[]. Set expires_at = now + 48h.

### /market list vip [days] [price]
1. Check days >= MARKET_VIP_MIN_LISTING_DAYS (10).
2. Check player.vip_days >= days + MARKET_VIP_ENTRY_FEE_DAYS (3).
3. Deduct days + 3 from player.vip_days. (3 burned, `days` held in escrow.)
4. Create listing. expires_at = now + 48h.

### /market buy [listing_id]
1. Fetch listing.
2. Check buyer has enough cash.
3. Deduct cash from buyer. Add `price * (1 - MARKET_TRANSACTION_FEE_PCT)` to seller wallet.
4. If item: transfer item to buyer.items[].
5. If vip_days: add held days to buyer.vip_days. Activate VIP if not already active.
6. Delete listing.

### /market browse [filter: item|vip] [slot?] [tier?]
Return paginated embed of active listings sorted by price ascending.

### Market expiry job (APScheduler, runs every 15 minutes)
```python
async def expire_market_listings(db):
    now = datetime.utcnow()
    expired = await db.market_listings.find({"expires_at": {"$lt": now}}).to_list(None)
    for listing in expired:
        if listing["type"] == "item":
            # Return item to seller
            await db.players.update_one(
                {"_id": listing["seller_id"]},
                {"$push": {"items": listing["item_id"]}}
            )
            await db.items.update_one({"_id": listing["item_id"]}, {"$set": {"on_market": False, "owner_id": listing["seller_id"]}})
        elif listing["type"] == "vip_days":
            # Return escrowed days (NOT the 3 burned entry fee)
            await db.players.update_one(
                {"_id": listing["seller_id"]},
                {"$inc": {"vip_days": listing["vip_days_amount"]}}
            )
        await db.market_listings.delete_one({"_id": listing["_id"]})
```

---

## SYSTEM 9 — VIP

### /vip status
Show remaining VIP days, active_until timestamp, list of all perks.

### /vip activate [days]
1. Check player.vip_days >= days.
2. Deduct days from vip_days.
3. Set `vip_active_until = max(now, current_vip_active_until) + timedelta(days=days)`.
   (Stacks correctly if already VIP.)

### VIP check helper (use everywhere)
```python
def is_vip(player):
    until = player.get("vip_active_until")
    return until is not None and until > datetime.utcnow()
```

---

## SYSTEM 10 — GANG SYSTEM

### /gang create [name] [tag] [type]
1. Check player not already in a gang.
2. Check player level >= 5.
3. Deduct creation cost (10,000 cash).
4. Create gang doc. Set player.gang_id.

### /gang join [gang_id or name]
1. Check player not in a gang.
2. Check gang exists and is not full (member cap = 10 + gang_level * 5).
3. Add player to gang.members. Set player.gang_id.

### /gang bank deposit [amount]
1. Check player in gang.
2. Check wallet >= amount.
3. Check gang.bank + amount <= gang.bank_cap (VIP members: cap +50%).
4. Transfer.

### /gang bank withdraw [amount] (officers + leader only)
Deduct from gang.bank, add to player wallet.

### Shift flow (APScheduler, every 12 hours)

**Shift start:**
1. All gangs with `shift_state == "resting"` → set to `"inactive"` (their mandatory rest is over, they can rejoin next shift as active).
2. All gangs with `shift_state == "active"` (i.e., they participated last shift) → set to `"resting"`.
3. All gangs with `shift_state == "inactive"` (i.e., they sat out last shift) → eligible to become `"active"` if any member gets a kill this shift (auto-activate on first kill).
4. Reset `current_shift_points = 0` for all gangs.

**On each kill during a shift:**
```python
async def handle_kill_points(db, attacker_id, target_id):
    attacker = await db.players.find_one({"_id": attacker_id})
    target   = await db.players.find_one({"_id": target_id})

    atk_gang_id = attacker.get("gang_id")
    tgt_gang_id = target.get("gang_id")

    if atk_gang_id:
        gang = await db.gangs.find_one({"_id": atk_gang_id})
        if gang["shift_state"] == "inactive":
            # Auto-activate on first kill
            await db.gangs.update_one({"_id": atk_gang_id}, {"$set": {"shift_state": "active"}})
        if gang["shift_state"] in ("active",):
            await db.gangs.update_one({"_id": atk_gang_id}, {"$inc": {"current_shift_points": config.SHIFT_KILL_POINTS}})

    if tgt_gang_id:
        gang = await db.gangs.find_one({"_id": tgt_gang_id})
        if gang["shift_state"] in ("active",):
            new_pts = max(0, gang["current_shift_points"] + config.SHIFT_DEATH_POINTS)
            await db.gangs.update_one({"_id": tgt_gang_id}, {"$set": {"current_shift_points": new_pts}})
```

**Resting gangs during a shift:**
- Members attacking give 0 points.
- BUT enemies can kill resting members and gain points from that (if attacker's gang is active).
- Check `attacker_gang.shift_state == "active"` before awarding points.

**Shift end:**
1. Collect top 3 gangs by `current_shift_points` (only `shift_state == "active"` gangs).
2. Distribute rewards to all members of top 3.
3. Archive to `shift_history`.
4. Set all active gangs → "resting".

---

## SYSTEM 11 — LEADERBOARDS

### /leaderboard [category]
Categories:
- `strength` — top 10 by `stats.strength + equipment_bonus.strength`
- `speed` — top 10 by total speed
- `defense` — top 10 by total defense
- `level` — top 10 by `level`
- `cash` — top 10 by `cash_wallet` ONLY (bank excluded)
- `gang_power` — top 10 gangs by `level + shift_wins`
- `gang_shift` — top 10 gangs by `current_shift_points` (live)

### Item slot rankings (update after every item upgrade or equip)
```python
async def update_slot_rank(db, item_id, slot):
    """
    Rank all items of the same slot by total_bonus descending.
    Update each item's slot_rank field.
    """
    items = await db.items.find({"slot": slot}).sort("total_bonus", -1).to_list(None)
    ops = []
    for rank, item in enumerate(items, start=1):
        ops.append(UpdateOne({"_id": item["_id"]}, {"$set": {"slot_rank": rank}}))
    if ops:
        await db.items.bulk_write(ops)
```

---

## SYSTEM 12 — LEVEL GAP SHIELD

### Helper used in /attack and /rob
```python
def level_gap_ok(attacker_level, target_level, in_gang_shift=False):
    gap = config.PVP_LEVEL_GAP_GANG_WAR if in_gang_shift else config.PVP_LEVEL_GAP
    return abs(attacker_level - target_level) <= gap

def in_active_gang_shift(attacker_gang):
    """Returns True if attacker's gang is in 'active' shift state."""
    if not attacker_gang:
        return False
    return attacker_gang.get("shift_state") == "active"
```

---

## SYSTEM 13 — DAILY REWARD

### /daily
1. Check cooldown: 24 hours since last claim.
2. Base reward: 1000 cash + 50 XP.
3. VIP bonus: +2000 cash + 2 diamonds.
4. Streak bonus: track `daily_streak` count. Every 7 days = +1 diamond extra.
5. Save `cooldowns.daily = now`.

---

## DISCORD UI PATTERNS

### Embed color conventions
- Success / reward: `0x1D9E75` (teal)
- Warning / cost: `0xBA7517` (amber)
- Error / fail: `0xE24B4A` (red)
- Info / profile: `0x7F77DD` (purple)
- VIP actions: `0xF0997B` (gold-ish coral)

### All game commands (slash)
```
/profile
/faction [thug|businessman|policeman]
/gym
/crime
/attack @user
/rob @user
/build [building]
/upgrade [building]
/collect
/farm start
/farm collect
/ship send [name] [cargo_type]
/ship collect
/items
/equip [item_id]
/unequip [slot]
/upgrade-item [item_id]
/market browse [type] [filters...]
/market list item [item_id] [price]
/market list vip [days] [price]
/market buy [listing_id]
/gang create [name] [tag] [type]
/gang join [name]
/gang leave
/gang info
/gang bank deposit [amount]
/gang bank withdraw [amount]
/gang members
/leaderboard [category]
/daily
/vip status
/vip activate [days]
```

---

## MAIN.PY BOOTSTRAP

```python
# main.py
import asyncio
import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
import os
from tick import refill_tick
from shift import end_shift

load_dotenv()

COGS = [
    "cogs.profile", "cogs.stats", "cogs.crime", "cogs.pvp",
    "cogs.buildings", "cogs.inventory", "cogs.upgrades",
    "cogs.market", "cogs.gang", "cogs.leaderboard",
    "cogs.daily", "cogs.vip"
]

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    mongo = AsyncIOMotorClient(os.getenv("MONGO_URI"))
    bot.db = mongo["underworld_empire"]

    scheduler = AsyncIOScheduler()
    scheduler.add_job(refill_tick, "interval", seconds=60, args=[bot.db])
    scheduler.add_job(end_shift,   "interval", hours=12,   args=[bot.db])
    scheduler.start()

    for cog in COGS:
        await bot.load_extension(cog)

    await bot.tree.sync()
    print(f"Underworld Empire online as {bot.user}")

bot.run(os.getenv("DISCORD_TOKEN"))
```

---

## AGENT BUILD NOTES

- Use `motor` (async MongoDB driver) everywhere. Never use `pymongo` blocking calls inside async functions.
- All DB reads for a command should be batched into as few queries as possible. Fetch the full player doc once per command, modify in memory, write once.
- Cooldowns are stored as UTC datetime objects in MongoDB. Always compare with `datetime.utcnow()`.
- All cash/stat values are integers. Never store floats in the DB — multiply then int() before saving.
- Embeds for every response — never plain text replies for game actions.
- Error handling: wrap every command body in try/except. On any DB error, reply with a generic "something went wrong" embed and log the traceback.
- All Views (buttons) must have a 60-second timeout. After timeout, disable all buttons.
- Gang shift job should run at fixed real-world times (e.g., 08:00 UTC and 20:00 UTC) not relative intervals, to keep shifts synchronized across players. Use `CronTrigger` for this in APScheduler.
- Item slot_rank should be updated asynchronously after upgrade or sale — do not block the user response waiting for the rank recalculation across potentially thousands of items.
- When displaying item IDs to users, show only the first 8 characters of the UUID for readability (e.g., `a3f7c901`). Full UUID is used internally.
- The `equipment_bonus` sub-doc on the player should always be kept in sync when items are equipped or upgraded. This is what combat reads — not raw items.
- Wanted flag: store as `wanted_until` timestamp. On any crime command, check and display wanted status in the embed. Wanted players show as valid targets with a visual indicator when browsed in /profile.

---
*Document version 1.0 — Underworld Empire · discord.py + MongoDB*
