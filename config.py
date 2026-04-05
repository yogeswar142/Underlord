# config.py
# All game constants — tweak balance here without touching game logic.

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

# ── Countries ─────────────────────────────────────────────────
COUNTRIES = [
    "USA", "Russia", "Italy", "Japan", "Colombia", "Mexico", "China", "UK", 
    "Brazil", "India", "France", "Germany", "Canada", "Australia", "Spain", 
    "South Korea", "Turkey", "Argentina", "South Africa", "Nigeria", "Egypt", 
    "Saudi Arabia", "Indonesia", "Iran", "Pakistan", "Thailand", "Vietnam", 
    "Philippines", "Ukraine", "Poland", "Sweden", "Netherlands", "Belgium", 
    "Switzerland", "Austria", "Greece", "Portugal", "Ireland", "Norway", 
    "Denmark", "Finland", "New Zealand", "Singapore", "Malaysia", "UAE", 
    "Israel", "Chile", "Peru", "Morocco", "Kenya"
]

# ── Gym costs & rewards ───────────────────────────────────────
GYM_MODES = {
    "lift":    {"stamina_cost": 4, "stat": "strength", "base_gain": 1},
    "endure":  {"stamina_cost": 3, "stat": "defense",  "base_gain": 1},
    "sprint":  {"stamina_cost": 3, "stat": "speed",    "base_gain": 1},
}
GYM_GAIN_PER_LEVEL = 0.2  # additional gain = gym_building_level * 0.2
GYM_COOLDOWN_SECONDS = 60

# ── Crime table ───────────────────────────────────────────────
CRIMES = {
    "pickpocket": {
        "stamina": 2, "courage": 1,
        "reward_min": 200, "reward_max": 800,
        "xp": 10, "success_base": 0.75,
        "fail_hp_loss": 5, "fail_money_loss_pct": 0,
        "cooldown_seconds": 30,
        "emoji": "🤏",
        "description": "Quick fingers, small payout.",
    },
    "rob_store": {
        "stamina": 5, "courage": 2,
        "reward_min": 800, "reward_max": 3000,
        "xp": 30, "success_base": 0.60,
        "fail_hp_loss": 15, "fail_money_loss_pct": 0,
        "cooldown_seconds": 120,
        "emoji": "🏪",
        "description": "Hit a corner store. Medium risk.",
    },
    "drug_deal": {
        "stamina": 6, "courage": 3,
        "reward_min": 2000, "reward_max": 6000,
        "xp": 50, "success_base": 0.55,
        "fail_hp_loss": 0, "fail_money_loss_pct": 0.10,
        "diamond_reward": 1,
        "cooldown_seconds": 300,
        "emoji": "💊",
        "description": "Move product on the street. Possible diamond bonus.",
    },
    "bank_heist": {
        "stamina": 15, "courage": 6,
        "reward_min": 15000, "reward_max": 50000,
        "xp": 200, "success_base": 0.35,
        "fail_hp_loss": 40, "fail_money_loss_pct": 0,
        "wanted_on_fail_seconds": 900,
        "cooldown_seconds": 3600,
        "emoji": "🏦",
        "description": "The big score. High risk, high reward.",
    },
    "police_ambush": {
        "stamina": 10, "courage": 5,
        "reward_xp": 300, "reward_courage": 5,
        "success_base": 0.50,
        "fail_hp_loss": 30,
        "cooldown_seconds": 1800,
        "emoji": "🚔",
        "description": "Ambush a patrol car. XP and courage reward.",
    },
}

# ── Building costs & effects ──────────────────────────────────
# Each building: list of 10 upgrade costs and what each level gives.
# cost[i] = cost to upgrade FROM level i TO level i+1
BUILDINGS = {
    "gym": {
        "costs":   [500, 1500, 4000, 10000, 25000, 60000, 150000, 400000, 1000000, 2500000],
        "unlock_level": 1,
        "emoji": "🏋️",
        "description": "Boosts stat gains from training.",
    },
    "farm": {
        "costs":   [800, 2000, 5000, 12000, 30000, 75000, 200000, 500000, 1200000, 3000000],
        "unlock_level": 1,
        "grain_per_cycle": [10, 20, 35, 55, 80, 110, 150, 200, 260, 340],
        "cycle_minutes":   [60, 55, 50, 45, 40, 35, 30, 25, 20, 15],
        "stamina_to_start": 5,
        "base_sell_price_per_grain": 100,
        "ship_sell_multiplier": 1.40,
        "emoji": "🌾",
        "description": "Grow grain to sell or ship overseas.",
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
        "emoji": "⚓",
        "description": "Build ships to trade grain and opium overseas.",
    },
    "mines": {
        "costs": [5000, 15000, 40000, 100000, 250000, 600000, 1500000, 4000000, 10000000, 25000000],
        "unlock_level": 5,
        "diamonds_per_hour": [0.5, 1, 1.5, 2, 3, 4, 5, 7, 9, 12],
        "emoji": "⛏️",
        "description": "Passive diamond income.",
    },
    "brothel": {
        "costs": [1000, 3000, 8000, 20000, 50000, 120000, 300000, 800000, 2000000, 5000000],
        "unlock_level": 1,
        "cash_per_hour": [200, 500, 1200, 3000, 7500, 18000, 45000, 120000, 300000, 750000],
        "emoji": "🏩",
        "description": "Passive cash income.",
    },
    "bank": {
        "costs": [500, 1500, 4000, 10000, 25000, 60000, 150000, 400000, 1000000, 2500000],
        "unlock_level": 1,
        "emoji": "🏦",
        "description": "Increase bank storage capacity.",
    },
    "market": {
        "costs": [1000, 3000, 8000, 20000, 50000, 120000, 300000, 800000, 2000000, 5000000],
        "unlock_level": 2,
        "fee_reduction_per_level": 0.03,  # up to 30% fee reduction at lv10
        "emoji": "🏬",
        "description": "Reduces market listing fees.",
    },
    "mafia_house": {
        "costs": [3000, 8000, 20000, 50000, 120000, 300000, 800000, 2000000, 5000000, 12000000],
        "unlock_level": 8,
        "income_per_hour_by_profession": {
            "smuggler":    [500, 1200, 2500, 5000, 10000, 20000, 40000, 80000, 160000, 320000],
            "enforcer":    [400, 900,  1800, 3600, 7200,  14400, 28800, 57600, 115200, 230400],
            "fixer":       [600, 1400, 2800, 5600, 11200, 22400, 44800, 89600, 179200, 358400],
            "laundryman":  [800, 1800, 3600, 7200, 14400, 28800, 57600, 115200, 230400, 460800],
        },
        "profession_change_cooldown_hours": 168,  # 7 days
        "emoji": "🏚️",
        "description": "Profession-based income. Choose wisely.",
    },
    "opium_house": {
        "costs": [50000, 150000, 400000, 1000000, 2500000, 6000000, 15000000, 40000000, 100000000, 250000000],
        "unlock_level": 30,
        "opium_per_cycle": [5, 12, 25, 45, 75, 120, 180, 260, 360, 500],
        "cycle_minutes":   [120, 110, 100, 90, 80, 70, 60, 50, 40, 30],
        "courage_to_start": 5,
        "ship_sell_price_per_opium": 1200,  # vs grain 140
        "raid_fail_chance": 0.08,           # 8% chance opium batch wiped
        "emoji": "🌿",
        "description": "High-value contraband. Risk of raids.",
    },
    "factory": {
        "costs": [20000, 60000, 150000, 400000, 1000000, 2500000, 6000000, 15000000, 40000000, 100000000],
        "unlock_level": 25,
        "upgrade_cost_reduction": [0, 0.03, 0.06, 0.09, 0.12, 0.15, 0.18, 0.21, 0.25, 0.30],
        "market_fee_reduction": [0, 0.03, 0.06, 0.09, 0.12, 0.15, 0.18, 0.21, 0.25, 0.30],
        "emoji": "🏭",
        "description": "Reduces upgrade and market costs.",
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

# ── Tier order (for tier-up logic) ────────────────────────────
TIER_ORDER = ["common", "uncommon", "rare", "very_rare", "legendary"]
TIER_BONUS = {"common": 5, "uncommon": 12, "rare": 25, "very_rare": 50, "legendary": 100}

# ── Item slot → stat mapping ──────────────────────────────────
SLOT_STAT_MAP = {
    "hat":       "defense",
    "jacket":    "defense",
    "shoes":     "defense",
    "car":       "speed",
    "weapon1":   "strength",
    "weapon2":   "strength",
    "jewellery": "happiness",
}

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
PVP_ATTACK_COURAGE_COST = 5
PVP_ROB_STAMINA_COST = 2

# ── Gang shift system ─────────────────────────────────────────
SHIFT_DURATION_HOURS = 12
SHIFT_KILL_POINTS = 4
SHIFT_DEATH_POINTS = -2
GANG_CREATE_COST = 10000
GANG_CREATE_MIN_LEVEL = 5
GANG_BASE_MEMBER_CAP = 10
GANG_MEMBER_CAP_PER_LEVEL = 5
GANG_REWARD_TOP3 = [
    {"rank": 1, "cash": 50000, "xp": 500, "diamonds": 10},
    {"rank": 2, "cash": 25000, "xp": 250, "diamonds": 5},
    {"rank": 3, "cash": 10000, "xp": 100, "diamonds": 2},
]

# ── Daily reward ──────────────────────────────────────────────
DAILY_BASE_CASH = 1000
DAILY_BASE_XP = 50
DAILY_VIP_CASH = 2000
DAILY_VIP_DIAMONDS = 2
DAILY_STREAK_DIAMOND_INTERVAL = 7  # every 7 days = +1 diamond

# ── VIP ───────────────────────────────────────────────────────
VIP_INCOME_MULT = 1.20
VIP_SELL_PRICE_MULT = 1.15
VIP_UPGRADE_RARE_BONUS = 0.05    # added to very_rare and legendary chances
VIP_GANG_BANK_CAP_MULT = 1.50   # +50% gang bank cap for VIP members

# ── Embed colors ──────────────────────────────────────────────
COLOR_SUCCESS = 0x1D9E75   # teal
COLOR_WARNING = 0xBA7517   # amber
COLOR_ERROR   = 0xE24B4A   # red
COLOR_INFO    = 0x7F77DD   # purple
COLOR_VIP     = 0xF0997B   # gold-ish coral

# ── Faction emojis ────────────────────────────────────────────
FACTION_EMOJIS = {
    "thug":       "🔪",
    "businessman": "💼",
    "policeman":  "🛡️",
}

# ── Max building level ────────────────────────────────────────
MAX_BUILDING_LEVEL = 10
