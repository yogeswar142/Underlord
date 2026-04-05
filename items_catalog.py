# items_catalog.py
# All base item definitions. Used by shop, drops, and item generation.
# Each entry: { id_key, name, lore, slot, tier, stat_type, base_stat, shop_price (None if not sold in shop) }

ITEMS_CATALOG = {

    # ── HAT ──────────────────────────────────────────────────────
    "hat_c_001": {"name": "Street Beanie",       "lore": "Pulled off a clothesline, still warm",              "slot": "hat", "tier": "common",    "stat_type": "defense", "base_stat": 5,   "shop_price": 800},
    "hat_c_002": {"name": "Snapback Cap",         "lore": "Worn backwards for max intimidation",               "slot": "hat", "tier": "common",    "stat_type": "defense", "base_stat": 5,   "shop_price": 800},
    "hat_c_003": {"name": "Bucket Hat",           "lore": "Low brim, nobody sees your eyes",                   "slot": "hat", "tier": "common",    "stat_type": "defense", "base_stat": 5,   "shop_price": 800},
    "hat_c_004": {"name": "Bandana Wrap",         "lore": "Old cotton, tied tight",                            "slot": "hat", "tier": "common",    "stat_type": "defense", "base_stat": 5,   "shop_price": 600},
    "hat_c_005": {"name": "Flat Cap",             "lore": "Old neighbourhood staple",                          "slot": "hat", "tier": "common",    "stat_type": "defense", "base_stat": 5,   "shop_price": 700},
    "hat_u_001": {"name": "Reinforced Bandana",   "lore": "Padded liner, blocks more than wind",               "slot": "hat", "tier": "uncommon",  "stat_type": "defense", "base_stat": 12,  "shop_price": 5000},
    "hat_u_002": {"name": "Tactical Cap",         "lore": "Military surplus, fitted right",                    "slot": "hat", "tier": "uncommon",  "stat_type": "defense", "base_stat": 12,  "shop_price": 5500},
    "hat_u_003": {"name": "Gang Rag",             "lore": "Faction-dyed, marks territory",                     "slot": "hat", "tier": "uncommon",  "stat_type": "defense", "base_stat": 12,  "shop_price": 4800},
    "hat_u_004": {"name": "Kevlar Liner Cap",     "lore": "Looks normal, hides armour",                        "slot": "hat", "tier": "uncommon",  "stat_type": "defense", "base_stat": 12,  "shop_price": 6000},
    "hat_u_005": {"name": "Riot Wrap",            "lore": "Borrowed from a supply truck",                      "slot": "hat", "tier": "uncommon",  "stat_type": "defense", "base_stat": 12,  "shop_price": 5200},
    "hat_r_001": {"name": "Bulletproof Beret",    "lore": "Composite fibre, parade-tested",                    "slot": "hat", "tier": "rare",      "stat_type": "defense", "base_stat": 25,  "shop_price": None},
    "hat_r_002": {"name": "Enforcer's Helmet",    "lore": "Riot surplus, full cranial cover",                  "slot": "hat", "tier": "rare",      "stat_type": "defense", "base_stat": 25,  "shop_price": None},
    "hat_r_003": {"name": "Shadow Hood",          "lore": "Stealth composite, heat-diffusing",                 "slot": "hat", "tier": "rare",      "stat_type": "defense", "base_stat": 25,  "shop_price": None},
    "hat_r_004": {"name": "Armoured Skully",      "lore": "Steel-weave knit, uncomfortable but safe",          "slot": "hat", "tier": "rare",      "stat_type": "defense", "base_stat": 25,  "shop_price": None},
    "hat_vr_001":{"name": "Warlord's Crown",      "lore": "Ornate armoured headgear, feared on sight",         "slot": "hat", "tier": "very_rare", "stat_type": "defense", "base_stat": 50,  "shop_price": None},
    "hat_vr_002":{"name": "Cartel Captain's Hat", "lore": "Gold-trimmed, custom-fitted tactical",              "slot": "hat", "tier": "very_rare", "stat_type": "defense", "base_stat": 50,  "shop_price": None},
    "hat_vr_003":{"name": "Phantom Balaclava",    "lore": "Full-face composite, zero reflection",              "slot": "hat", "tier": "very_rare", "stat_type": "defense", "base_stat": 50,  "shop_price": None},
    "hat_l_001": {"name": "The Don's Fedora",     "lore": "Worn through three wars, never once grazed",        "slot": "hat", "tier": "legendary", "stat_type": "defense", "base_stat": 100, "shop_price": None},
    "hat_l_002": {"name": "Iron Veil",            "lore": "A myth. They say it stopped an assassin's bullet in 1987", "slot": "hat", "tier": "legendary", "stat_type": "defense", "base_stat": 100, "shop_price": None},

    # ── JACKET ───────────────────────────────────────────────────
    "jkt_c_001": {"name": "Leather Jacket",          "lore": "Cracked at the elbows, toughened over time",         "slot": "jacket", "tier": "common",    "stat_type": "defense", "base_stat": 5,   "shop_price": 900},
    "jkt_c_002": {"name": "Denim Vest",              "lore": "Patches mean history",                               "slot": "jacket", "tier": "common",    "stat_type": "defense", "base_stat": 5,   "shop_price": 850},
    "jkt_c_003": {"name": "Hoodie",                  "lore": "Deep pockets, deeper intentions",                    "slot": "jacket", "tier": "common",    "stat_type": "defense", "base_stat": 5,   "shop_price": 750},
    "jkt_c_004": {"name": "Tracksuit Top",           "lore": "Fast to move in, easy to strip",                     "slot": "jacket", "tier": "common",    "stat_type": "defense", "base_stat": 5,   "shop_price": 700},
    "jkt_c_005": {"name": "Canvas Work Jacket",      "lore": "Built for labour, adapted for war",                  "slot": "jacket", "tier": "common",    "stat_type": "defense", "base_stat": 5,   "shop_price": 800},
    "jkt_u_001": {"name": "Gang Colors",             "lore": "Reinforced club jacket, means something",            "slot": "jacket", "tier": "uncommon",  "stat_type": "defense", "base_stat": 12,  "shop_price": 5500},
    "jkt_u_002": {"name": "Kevlar Shirt",            "lore": "Sits under anything, stops most things",             "slot": "jacket", "tier": "uncommon",  "stat_type": "defense", "base_stat": 12,  "shop_price": 7000},
    "jkt_u_003": {"name": "Bomber Jacket",           "lore": "Heavy duty shell, military surplus",                 "slot": "jacket", "tier": "uncommon",  "stat_type": "defense", "base_stat": 12,  "shop_price": 6000},
    "jkt_u_004": {"name": "Tactical Vest",           "lore": "Molle straps, lightweight plates",                   "slot": "jacket", "tier": "uncommon",  "stat_type": "defense", "base_stat": 12,  "shop_price": 7500},
    "jkt_u_005": {"name": "Syndicate Windbreaker",   "lore": "Water-resistant, gang-issued",                       "slot": "jacket", "tier": "uncommon",  "stat_type": "defense", "base_stat": 12,  "shop_price": 5800},
    "jkt_r_001": {"name": "Ballistic Vest",          "lore": "Military grade, two plate slots",                    "slot": "jacket", "tier": "rare",      "stat_type": "defense", "base_stat": 25,  "shop_price": None},
    "jkt_r_002": {"name": "Syndicate Coat",          "lore": "Officer-issue, earned not bought",                   "slot": "jacket", "tier": "rare",      "stat_type": "defense", "base_stat": 25,  "shop_price": None},
    "jkt_r_003": {"name": "Enforcer's Jacket",       "lore": "Riot composite, covers shoulders to waist",          "slot": "jacket", "tier": "rare",      "stat_type": "defense", "base_stat": 25,  "shop_price": None},
    "jkt_r_004": {"name": "Armoured Longcoat",       "lore": "Hidden steel weave, looks civilian",                 "slot": "jacket", "tier": "rare",      "stat_type": "defense", "base_stat": 25,  "shop_price": None},
    "jkt_vr_001":{"name": "Shadow Trench",           "lore": "Elite operative coat, stops rifle rounds",           "slot": "jacket", "tier": "very_rare", "stat_type": "defense", "base_stat": 50,  "shop_price": None},
    "jkt_vr_002":{"name": "Cartel Lieutenant Vest",  "lore": "Gold-plate inserts, custom fitted",                  "slot": "jacket", "tier": "very_rare", "stat_type": "defense", "base_stat": 50,  "shop_price": None},
    "jkt_vr_003":{"name": "Black Site Jacket",       "lore": "Classified material, no label, no origin",           "slot": "jacket", "tier": "very_rare", "stat_type": "defense", "base_stat": 50,  "shop_price": None},
    "jkt_l_001": {"name": "The Untouchable Coat",    "lore": "No bullet has ever passed through it. Nobody argues.", "slot": "jacket", "tier": "legendary", "stat_type": "defense", "base_stat": 100, "shop_price": None},
    "jkt_l_002": {"name": "Kingpin's Suit Jacket",   "lore": "Silk exterior, ceramic interior. Power is presentation.", "slot": "jacket", "tier": "legendary", "stat_type": "defense", "base_stat": 100, "shop_price": None},

    # ── SHOES ────────────────────────────────────────────────────
    "sho_c_001": {"name": "Street Kicks",        "lore": "Worn soles, still running",                          "slot": "shoes", "tier": "common",    "stat_type": "defense", "base_stat": 5,   "shop_price": 700},
    "sho_c_002": {"name": "Work Boots",          "lore": "Steel cap, cracked leather",                         "slot": "shoes", "tier": "common",    "stat_type": "defense", "base_stat": 5,   "shop_price": 750},
    "sho_c_003": {"name": "Running Shoes",       "lore": "Lifted from a sports store",                         "slot": "shoes", "tier": "common",    "stat_type": "defense", "base_stat": 5,   "shop_price": 650},
    "sho_c_004": {"name": "Slip-ons",            "lore": "Quick to put on, quick to run",                      "slot": "shoes", "tier": "common",    "stat_type": "defense", "base_stat": 5,   "shop_price": 500},
    "sho_c_005": {"name": "Army Surplus Boots",  "lore": "Worn by someone else first",                         "slot": "shoes", "tier": "common",    "stat_type": "defense", "base_stat": 5,   "shop_price": 800},
    "sho_u_001": {"name": "Steel Toe Boots",     "lore": "Reinforced cap, doubles as a weapon",                "slot": "shoes", "tier": "uncommon",  "stat_type": "defense", "base_stat": 12,  "shop_price": 4500},
    "sho_u_002": {"name": "Tactical Sneakers",   "lore": "Grip sole, ankle support, quiet",                    "slot": "shoes", "tier": "uncommon",  "stat_type": "defense", "base_stat": 12,  "shop_price": 5000},
    "sho_u_003": {"name": "Gang Stompers",       "lore": "Plated toe, leaves a mark",                          "slot": "shoes", "tier": "uncommon",  "stat_type": "defense", "base_stat": 12,  "shop_price": 4800},
    "sho_u_004": {"name": "Composite Boots",     "lore": "Lightweight armour layered into sole",               "slot": "shoes", "tier": "uncommon",  "stat_type": "defense", "base_stat": 12,  "shop_price": 5500},
    "sho_u_005": {"name": "Riot Boots",          "lore": "Full ankle guard, crowd-tested",                     "slot": "shoes", "tier": "uncommon",  "stat_type": "defense", "base_stat": 12,  "shop_price": 5200},
    "sho_r_001": {"name": "Armoured Boots",      "lore": "Full lower leg protection, military issue",          "slot": "shoes", "tier": "rare",      "stat_type": "defense", "base_stat": 25,  "shop_price": None},
    "sho_r_002": {"name": "Shadow Steps",        "lore": "Noise-dampening sole, near-silent movement",         "slot": "shoes", "tier": "rare",      "stat_type": "defense", "base_stat": 25,  "shop_price": None},
    "sho_r_003": {"name": "Enforcer's Cleats",   "lore": "Anti-slip armoured sole, grip on any surface",       "slot": "shoes", "tier": "rare",      "stat_type": "defense", "base_stat": 25,  "shop_price": None},
    "sho_r_004": {"name": "Syndicate Stompers",  "lore": "Officer-issue, reinforced heel and toe",             "slot": "shoes", "tier": "rare",      "stat_type": "defense", "base_stat": 25,  "shop_price": None},
    "sho_vr_001":{"name": "Phantom Treads",      "lore": "Cutting-edge composite, absorbs impact entirely",    "slot": "shoes", "tier": "very_rare", "stat_type": "defense", "base_stat": 50,  "shop_price": None},
    "sho_vr_002":{"name": "Warlord's Boots",     "lore": "Full shin armour, intimidates before you speak",     "slot": "shoes", "tier": "very_rare", "stat_type": "defense", "base_stat": 50,  "shop_price": None},
    "sho_vr_003":{"name": "Black Ops Footwear",  "lore": "No markings, no noise, no trace",                   "slot": "shoes", "tier": "very_rare", "stat_type": "defense", "base_stat": 50,  "shop_price": None},
    "sho_l_001": {"name": "Iron Ghost Boots",    "lore": "Legend says the wearer leaves no footprints and absorbs all blows", "slot": "shoes", "tier": "legendary", "stat_type": "defense", "base_stat": 100, "shop_price": None},
    "sho_l_002": {"name": "The Last Step",       "lore": "Worn by the man who walked out of a building that shouldn't have had survivors", "slot": "shoes", "tier": "legendary", "stat_type": "defense", "base_stat": 100, "shop_price": None},

    # ── CAR ──────────────────────────────────────────────────────
    "car_c_001": {"name": "Stolen Civic",         "lore": "Beat up but somehow still fast",                    "slot": "car", "tier": "common",    "stat_type": "speed", "base_stat": 5,   "shop_price": 2000},
    "car_c_002": {"name": "Rusted Pickup",         "lore": "Reliable if nothing else",                          "slot": "car", "tier": "common",    "stat_type": "speed", "base_stat": 5,   "shop_price": 1800},
    "car_c_003": {"name": "Old Taxi",              "lore": "Blends in, nobody questions it",                    "slot": "car", "tier": "common",    "stat_type": "speed", "base_stat": 5,   "shop_price": 2200},
    "car_c_004": {"name": "Spray-Painted Hatch",   "lore": "New plates every week",                             "slot": "car", "tier": "common",    "stat_type": "speed", "base_stat": 5,   "shop_price": 1900},
    "car_c_005": {"name": "Beat Sedan",            "lore": "Three dents, one working window",                   "slot": "car", "tier": "common",    "stat_type": "speed", "base_stat": 5,   "shop_price": 1600},
    "car_u_001": {"name": "Tuned Street Racer",    "lore": "Modified hatchback, beats everything at a light",   "slot": "car", "tier": "uncommon",  "stat_type": "speed", "base_stat": 12,  "shop_price": 15000},
    "car_u_002": {"name": "Gang Van",              "lore": "Tinted windows, reinforced doors",                  "slot": "car", "tier": "uncommon",  "stat_type": "speed", "base_stat": 12,  "shop_price": 14000},
    "car_u_003": {"name": "Impound Muscle",        "lore": "Seized and repainted, runs like it's trying to escape", "slot": "car", "tier": "uncommon","stat_type": "speed", "base_stat": 12,  "shop_price": 16000},
    "car_u_004": {"name": "Lowrider",              "lore": "Hydraulics and pride",                              "slot": "car", "tier": "uncommon",  "stat_type": "speed", "base_stat": 12,  "shop_price": 13500},
    "car_u_005": {"name": "Midnight Runner",       "lore": "Matte black, no chrome, no attention",              "slot": "car", "tier": "uncommon",  "stat_type": "speed", "base_stat": 12,  "shop_price": 15500},
    "car_r_001": {"name": "Stolen Sports Coupe",   "lore": "High performance, stolen from someone who deserved it", "slot": "car", "tier": "rare",   "stat_type": "speed", "base_stat": 25,  "shop_price": None},
    "car_r_002": {"name": "Syndicate Sedan",       "lore": "Armoured panels, fast enough to not need them",     "slot": "car", "tier": "rare",      "stat_type": "speed", "base_stat": 25,  "shop_price": None},
    "car_r_003": {"name": "Getaway Charger",       "lore": "Built for one thing and it does it perfectly",      "slot": "car", "tier": "rare",      "stat_type": "speed", "base_stat": 25,  "shop_price": None},
    "car_r_004": {"name": "Rigged Import",         "lore": "Tuned to the edge of mechanical reason",            "slot": "car", "tier": "rare",      "stat_type": "speed", "base_stat": 25,  "shop_price": None},
    "car_vr_001":{"name": "Cartel SUV",            "lore": "Bulletproofed, turbocharged, never pulled over",    "slot": "car", "tier": "very_rare", "stat_type": "speed", "base_stat": 50,  "shop_price": None},
    "car_vr_002":{"name": "Shadow Runner",         "lore": "Matte black, no plates, radar-invisible",           "slot": "car", "tier": "very_rare", "stat_type": "speed", "base_stat": 50,  "shop_price": None},
    "car_vr_003":{"name": "Phantom Six",           "lore": "Six cylinders of complete silence",                 "slot": "car", "tier": "very_rare", "stat_type": "speed", "base_stat": 50,  "shop_price": None},
    "car_l_001": {"name": "The Ghost Rider",       "lore": "No one has ever seen it stopped. Only heard it leaving.", "slot": "car", "tier": "legendary", "stat_type": "speed", "base_stat": 100, "shop_price": None},
    "car_l_002": {"name": "Omertà Wheels",         "lore": "The car that drove the Don to every meeting he walked out of", "slot": "car", "tier": "legendary", "stat_type": "speed", "base_stat": 100, "shop_price": None},

    # ── WEAPON 1 (primary) ───────────────────────────────────────
    "wp1_c_001": {"name": "Street Knife",          "lore": "Simple blade, does the job",                        "slot": "weapon1", "tier": "common",    "stat_type": "strength", "base_stat": 5,   "shop_price": 1000},
    "wp1_c_002": {"name": "Baseball Bat",          "lore": "Classic. No questions asked.",                       "slot": "weapon1", "tier": "common",    "stat_type": "strength", "base_stat": 5,   "shop_price": 900},
    "wp1_c_003": {"name": "Brass Knuckles",        "lore": "Close range persuasion",                             "slot": "weapon1", "tier": "common",    "stat_type": "strength", "base_stat": 5,   "shop_price": 850},
    "wp1_c_004": {"name": "Iron Pipe",             "lore": "Found, not bought",                                  "slot": "weapon1", "tier": "common",    "stat_type": "strength", "base_stat": 5,   "shop_price": 600},
    "wp1_c_005": {"name": "Wooden Baton",          "lore": "Old school discipline",                              "slot": "weapon1", "tier": "common",    "stat_type": "strength", "base_stat": 5,   "shop_price": 700},
    "wp1_u_001": {"name": "Machete",               "lore": "Gang-issued, kept very sharp",                       "slot": "weapon1", "tier": "uncommon",  "stat_type": "strength", "base_stat": 12,  "shop_price": 8000},
    "wp1_u_002": {"name": "Crowbar",               "lore": "Repurposed but never questioned",                    "slot": "weapon1", "tier": "uncommon",  "stat_type": "strength", "base_stat": 12,  "shop_price": 7000},
    "wp1_u_003": {"name": "Sawn-off Shotgun",      "lore": "Short range, maximum statement",                     "slot": "weapon1", "tier": "uncommon",  "stat_type": "strength", "base_stat": 12,  "shop_price": 12000},
    "wp1_u_004": {"name": "Reinforced Bat",        "lore": "Steel core wrapped in leather",                      "slot": "weapon1", "tier": "uncommon",  "stat_type": "strength", "base_stat": 12,  "shop_price": 8500},
    "wp1_u_005": {"name": "Combat Hatchet",        "lore": "Military surplus, edge holds well",                  "slot": "weapon1", "tier": "uncommon",  "stat_type": "strength", "base_stat": 12,  "shop_price": 9000},
    "wp1_r_001": {"name": "9mm Pistol",            "lore": "Reliable, accurate, respected",                      "slot": "weapon1", "tier": "rare",      "stat_type": "strength", "base_stat": 25,  "shop_price": None},
    "wp1_r_002": {"name": "Combat Knife",          "lore": "Military grade blade, weighted perfectly",           "slot": "weapon1", "tier": "rare",      "stat_type": "strength", "base_stat": 25,  "shop_price": None},
    "wp1_r_003": {"name": "Enforcer's Baton",      "lore": "Reinforced steel, extendable",                       "slot": "weapon1", "tier": "rare",      "stat_type": "strength", "base_stat": 25,  "shop_price": None},
    "wp1_r_004": {"name": "Pump Shotgun",          "lore": "Full barrel, full damage",                           "slot": "weapon1", "tier": "rare",      "stat_type": "strength", "base_stat": 25,  "shop_price": None},
    "wp1_vr_001":{"name": "Desert Eagle",          "lore": "Iconic. Heavy. Ends arguments.",                     "slot": "weapon1", "tier": "very_rare", "stat_type": "strength", "base_stat": 50,  "shop_price": None},
    "wp1_vr_002":{"name": "Syndicate SMG",         "lore": "Automatic, compact, cartel-marked",                  "slot": "weapon1", "tier": "very_rare", "stat_type": "strength", "base_stat": 50,  "shop_price": None},
    "wp1_vr_003":{"name": "Enforcer's Rifle",      "lore": "Long barrel, longer reach",                          "slot": "weapon1", "tier": "very_rare", "stat_type": "strength", "base_stat": 50,  "shop_price": None},
    "wp1_l_001": {"name": "The Godfather's Revolver","lore": "Engraved ivory grip. Used to end three empires.", "slot": "weapon1", "tier": "legendary", "stat_type": "strength", "base_stat": 100, "shop_price": None},
    "wp1_l_002": {"name": "Black Sermon",          "lore": "Custom automatic. Has no serial number. Never did.", "slot": "weapon1", "tier": "legendary", "stat_type": "strength", "base_stat": 100, "shop_price": None},

    # ── WEAPON 2 (secondary) ─────────────────────────────────────
    "wp2_c_001": {"name": "Pocket Knife",          "lore": "Concealable, last resort",                           "slot": "weapon2", "tier": "common",    "stat_type": "strength", "base_stat": 5,   "shop_price": 700},
    "wp2_c_002": {"name": "Broken Bottle",         "lore": "Improvised but effective",                           "slot": "weapon2", "tier": "common",    "stat_type": "strength", "base_stat": 5,   "shop_price": 300},
    "wp2_c_003": {"name": "Sling",                 "lore": "Range, no noise",                                    "slot": "weapon2", "tier": "common",    "stat_type": "strength", "base_stat": 5,   "shop_price": 500},
    "wp2_c_004": {"name": "Rusty Shiv",            "lore": "Crudely sharpened, worryingly effective",            "slot": "weapon2", "tier": "common",    "stat_type": "strength", "base_stat": 5,   "shop_price": 400},
    "wp2_c_005": {"name": "Chain Length",          "lore": "Pulled from a fence",                                "slot": "weapon2", "tier": "common",    "stat_type": "strength", "base_stat": 5,   "shop_price": 450},
    "wp2_u_001": {"name": "Taser",                 "lore": "Incapacitating, quiet, efficient",                   "slot": "weapon2", "tier": "uncommon",  "stat_type": "strength", "base_stat": 12,  "shop_price": 6000},
    "wp2_u_002": {"name": "Throwing Knives",       "lore": "Set of 5, well-balanced",                            "slot": "weapon2", "tier": "uncommon",  "stat_type": "strength", "base_stat": 12,  "shop_price": 7000},
    "wp2_u_003": {"name": "Nunchaku",              "lore": "Requires skill, rewards it too",                     "slot": "weapon2", "tier": "uncommon",  "stat_type": "strength", "base_stat": 12,  "shop_price": 6500},
    "wp2_u_004": {"name": "Tactical Baton",        "lore": "Collapsible, concealed",                             "slot": "weapon2", "tier": "uncommon",  "stat_type": "strength", "base_stat": 12,  "shop_price": 6800},
    "wp2_u_005": {"name": "Stiletto",              "lore": "Thin blade, deep reach",                             "slot": "weapon2", "tier": "uncommon",  "stat_type": "strength", "base_stat": 12,  "shop_price": 7200},
    "wp2_r_001": {"name": "Silenced Pistol",       "lore": "For quiet work on quiet nights",                     "slot": "weapon2", "tier": "rare",      "stat_type": "strength", "base_stat": 25,  "shop_price": None},
    "wp2_r_002": {"name": "Shiv Collection",       "lore": "Prison-crafted, each one different",                 "slot": "weapon2", "tier": "rare",      "stat_type": "strength", "base_stat": 25,  "shop_price": None},
    "wp2_r_003": {"name": "Molotov Set",           "lore": "Three bottles, one match, one exit",                 "slot": "weapon2", "tier": "rare",      "stat_type": "strength", "base_stat": 25,  "shop_price": None},
    "wp2_r_004": {"name": "Syndicate Dagger",      "lore": "Officer sidearm, balanced for throwing",             "slot": "weapon2", "tier": "rare",      "stat_type": "strength", "base_stat": 25,  "shop_price": None},
    "wp2_vr_001":{"name": "Twin Daggers",          "lore": "Matched pair, perfectly weighted, gifts from a dead man", "slot": "weapon2", "tier": "very_rare", "stat_type": "strength", "base_stat": 50,  "shop_price": None},
    "wp2_vr_002":{"name": "Cartel Switchblade",    "lore": "Gold handle, razor edge, given to the trusted",      "slot": "weapon2", "tier": "very_rare", "stat_type": "strength", "base_stat": 50,  "shop_price": None},
    "wp2_vr_003":{"name": "Phantom Pistol",        "lore": "Matte finish, suppressed, untraceable",              "slot": "weapon2", "tier": "very_rare", "stat_type": "strength", "base_stat": 50,  "shop_price": None},
    "wp2_l_001": {"name": "The Reaper's Sickle",   "lore": "A curved blade said to have ended 40 men across two continents", "slot": "weapon2", "tier": "legendary", "stat_type": "strength", "base_stat": 100, "shop_price": None},
    "wp2_l_002": {"name": "Last Rites",            "lore": "A custom silenced revolver. Nobody hears it. Nobody reports it.", "slot": "weapon2", "tier": "legendary", "stat_type": "strength", "base_stat": 100, "shop_price": None},

    # ── JEWELLERY ────────────────────────────────────────────────
    "jwl_c_001": {"name": "Silver Chain",           "lore": "Thin, real-ish",                                     "slot": "jewellery", "tier": "common",    "stat_type": "happiness", "base_stat": 5,   "shop_price": 1200},
    "jwl_c_002": {"name": "Cheap Watch",            "lore": "Tells time and nothing else",                         "slot": "jewellery", "tier": "common",    "stat_type": "happiness", "base_stat": 5,   "shop_price": 1000},
    "jwl_c_003": {"name": "Plastic Ring",           "lore": "Street market, not worth stealing",                   "slot": "jewellery", "tier": "common",    "stat_type": "happiness", "base_stat": 5,   "shop_price": 400},
    "jwl_c_004": {"name": "Copper Bracelet",        "lore": "Dented but worn with pride",                          "slot": "jewellery", "tier": "common",    "stat_type": "happiness", "base_stat": 5,   "shop_price": 600},
    "jwl_c_005": {"name": "Glass Stud Earrings",    "lore": "You'd have to look close to know",                    "slot": "jewellery", "tier": "common",    "stat_type": "happiness", "base_stat": 5,   "shop_price": 500},
    "jwl_u_001": {"name": "Gold Chain",             "lore": "Heavy, real gold plating, noticed",                   "slot": "jewellery", "tier": "uncommon",  "stat_type": "happiness", "base_stat": 12,  "shop_price": 10000},
    "jwl_u_002": {"name": "Diamond Stud Earrings",  "lore": "Small but real, authenticated",                       "slot": "jewellery", "tier": "uncommon",  "stat_type": "happiness", "base_stat": 12,  "shop_price": 12000},
    "jwl_u_003": {"name": "Signet Ring",            "lore": "Faction-marked, says who you are",                    "slot": "jewellery", "tier": "uncommon",  "stat_type": "happiness", "base_stat": 12,  "shop_price": 9500},
    "jwl_u_004": {"name": "Gold Bracelet",          "lore": "Thick links, street credibility",                     "slot": "jewellery", "tier": "uncommon",  "stat_type": "happiness", "base_stat": 12,  "shop_price": 11000},
    "jwl_u_005": {"name": "Silver Pendant",         "lore": "Engraved, personal, intimidating",                    "slot": "jewellery", "tier": "uncommon",  "stat_type": "happiness", "base_stat": 12,  "shop_price": 9000},
    "jwl_r_001": {"name": "Cuban Link Chain",       "lore": "Thick heavy gold, floor-length if you want it",       "slot": "jewellery", "tier": "rare",      "stat_type": "happiness", "base_stat": 25,  "shop_price": None},
    "jwl_r_002": {"name": "Near-Perfect Rolex",     "lore": "The only person who knows it's fake is the seller",   "slot": "jewellery", "tier": "rare",      "stat_type": "happiness", "base_stat": 25,  "shop_price": None},
    "jwl_r_003": {"name": "Emerald Ring",           "lore": "Natural stone, cut by hand, stolen from the right person", "slot": "jewellery", "tier": "rare", "stat_type": "happiness", "base_stat": 25,  "shop_price": None},
    "jwl_r_004": {"name": "Platinum Pendant",       "lore": "No name on it. Everyone knows whose it was.",          "slot": "jewellery", "tier": "rare",      "stat_type": "happiness", "base_stat": 25,  "shop_price": None},
    "jwl_vr_001":{"name": "Diamond Tennis Chain",   "lore": "Full setting, each stone verified",                    "slot": "jewellery", "tier": "very_rare", "stat_type": "happiness", "base_stat": 50,  "shop_price": None},
    "jwl_vr_002":{"name": "Platinum Bracelet",      "lore": "Cartel-gifted, given once, never returned",            "slot": "jewellery", "tier": "very_rare", "stat_type": "happiness", "base_stat": 50,  "shop_price": None},
    "jwl_vr_003":{"name": "The Consigliere's Ring", "lore": "Worn by advisors, respected by generals",              "slot": "jewellery", "tier": "very_rare", "stat_type": "happiness", "base_stat": 50,  "shop_price": None},
    "jwl_l_001": {"name": "The Don's Watch",        "lore": "One of a kind. Has passed through four empires. Still ticking.", "slot": "jewellery", "tier": "legendary", "stat_type": "happiness", "base_stat": 100, "shop_price": None},
    "jwl_l_002": {"name": "Omertà Chain",           "lore": "Solid gold. Given only to those who have proven silence.", "slot": "jewellery", "tier": "legendary", "stat_type": "happiness", "base_stat": 100, "shop_price": None},
}

# ── Derived lookup tables ─────────────────────────────────────

def get_shop_items(slot=None):
    """Returns all items with a shop_price (Common + Uncommon)."""
    return {
        k: v for k, v in ITEMS_CATALOG.items()
        if v["shop_price"] is not None
        and (slot is None or v["slot"] == slot)
    }

def get_drop_pool(slot, tier):
    """Returns list of id_keys eligible to drop for a given slot + tier."""
    return [
        k for k, v in ITEMS_CATALOG.items()
        if v["slot"] == slot and v["tier"] == tier
    ]

def get_all_slots():
    return ["hat", "jacket", "shoes", "car", "weapon1", "weapon2", "jewellery"]

def get_random_drop_slot():
    import random
    return random.choice(get_all_slots())
