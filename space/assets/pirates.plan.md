---
name: Pirates
overview: Faction privateers built on the 1 move = 1 turn clock. A sensor game (signature, area pings, sun glare, patrol zones) leads into turn-based duels with instant range-based hits, where the shield is armour, weapon battery and loudest signal at once.
todos:
  - id: factions
    content: Give worlds to factions, everyone-against-the-Assembly stance, reputation that moves, hail and scan text
    status: completed
  - id: sensors
    content: Signature, contact levels, area ping with its spreading ring and bearing wedges, enemy pings you can dodge, sun glare, patrol zones
    status: completed
  - id: privateer-ai
    content: Privateers as clock actors (patrol, hunt, search, engage, retreat, wave friends by) with faction sprites
    status: completed
  - id: combat
    content: Light weapon, targeting, scan-to-reveal intents, shield as battery, range-based hits, wrecks and salvage
    status: completed
  - id: world-hooks
    content: Raid events and background patrols spawn privateers, bounties and news, distress beacons (mostly traps)
    status: pending
  - id: caravaneer-people
    content: A Caravaneer NPC set (jobs, sprites, portrait outfits, dialogue lines) so Etheora's surface matches its new faction
    status: pending
isProject: false
---

# Pirates: the privateers of Sol

## The hook

Your shield is your armour, your weapon's battery and your loudest signal at the same time, so every turn of a fight spends one pool three ways. Around that:

- **Pings work like sonar.** They find enemies but tell them where you are.
- **The sun is cover.** Its glare blinds sensors, and you pay for hiding there in hull.
- **Reputation decides who hunts you.**

Steps 1–4 are built. Numbers are the shipped values; all are constants and easy to tune. Distances are in metres: one pixel is one metre, and a tile is 24 m.

## Decided

- **Core:** tactical duels plus hunt and hide, with visual pings.
- **Who:** faction privateers. Worlds are given to factions, and everyone is against the Assembly.
- **Reputation:** rivals hunt you, and friends of a privateer's sponsor get waved by. A hauler with no standing anywhere is hunted.
- **Your ship:** a light weapon that draws on the shield as its battery.
- **Enemy intents:** shown only after you scan the ship.
- **Weapon fire:** instant hits whose chance and damage drop with range.
- **What gives you away:** pinging, moving, a raised shield, boosting, firing and a heavy hold.
- **Running dark:** holding still (waiting or pinging) with the shield down.
- **Where you can hide:** sun glare, running dark, and Assembly patrol zones.
- **Keys:** F fire, Tab next target, R scan, P area ping, S shield, Space wait.
- **How pirates show up:** news rumors then blips, background patrols, and distress-beacon lures (step 5).
- **How fights end:** pirates retreat when hurt, leave wrecks to salvage, and the Assembly pays bounties (bounties in step 5).
- **Etheora's people:** they become Caravaneers (step 6). Until then its surface stays Assembly.

**Not doing (for now):** pirates hailing or negotiating, nemesis captains, hiding behind planets, escalating heavier ships, chokepoint ambushes, cargo loss on defeat (the existing tow stays).

## 1. Factions (built)

Code: `world/factions.py`; territory in `star_systems/sol.json`.

| Faction | Holds | Hails as |
|---|---|---|
| Assembly | Governus Centralis, Terramonta, Nexum Astra | Assembly Traffic Control |
| Dominion | Ferrica | Dominion Port Authority |
| Cohort | Ageria, Arboresia | Cohort Commons Relay |
| Caravaneers | Cosmopolara, Etheora | Caravaneer Moot |

- **Everyone against the Assembly:** the Dominion, Cohort and Caravaneers license privateers against Assembly-friendly shipping. The Assembly is the law: it runs patrol zones and will pay bounties.
- **Waved by:** a privateer leaves you alone at +30 standing with its sponsor. It still pings you, and you get `PINGED BY COHORT - THEY KNOW YOU`.
- **Hunted harder:** each 5 points of Assembly standing adds a turn to how long a privateer searches for you. At +30 Assembly, outer factions' hails warn "You fly Assembly colours. Our privateers have noticed."
- **Standing** stays within -100..+100 (dialogue changes included) and moves by:

  | Event | Change |
  |---|---|
  | Trading at a faction's world | +1 per $1000 bought or sold, carried over, up to +40 from trade alone |
  | Destroying a privateer | sponsor -5, Assembly +3 |
  | Bounty paid (step 5) | Assembly up |
  | Rescuing a real distress beacon (step 5) | rescued hauler's faction up |

- **Hails and scans:** each faction answers in its own voice. Worlds without a landing map say "We've no berth for independents." Scans show the faction, your standing (`Friendly (+25)`), and "Licenses privateers against Assembly shipping" for the outer three.

## 2. Hunt and hide (built)

Code: `modes/star_system_mode/sensors.py` (logic), `sensor_fx.py` (drawing).

- **Signature:** the range at which others can sense a ship. It works the same both ways and is recalculated every turn. The HUD shows it as `SIGNAL [####------] 700 QUIET` (DARK at 300, LOUD at 1200 and up).

  | State | Signature |
  |---|---|
  | Holding still (waiting or pinging), shield down: running dark | 300 |
  | Moved this turn | 700 |
  | Raised shield | +500 |
  | Boosting | +500 |
  | Fired this turn | +900 |
  | Full hold (scaled by how full) | up to +400 |

- **Area ping:** P, or `ping` with no name in the ship computer. It costs 1 turn.
  - A cyan ring of glyph dots spreads from your ship (2500 m per second on screen), and ships in sight blink as it passes.
  - Hidden ships it finds get a bearing wedge (dotted edges, faint fill, narrower when closer) with a `?` and a rough range (to the nearest 100 m). Wedges fade over 4 turns. The ship computer lists each contact, for example `Contact E, about 1200 m`.
  - It finds a ship within its catch range (below), and every ship within 6000 m hears it and gets a fix on you.
  - `ping <planet>` works as before.
- **Enemy pings:** your sensors pick up the pulse as it leaves, so an amber wedge points back at the pinger at once. The wavefront then travels 1000 m per turn and catches or misses you when it arrives.
  - **Warning:** `INCOMING PING 4000 m NW, 3 TURNS - DODGE: HOLD STILL, SHIELD DOWN (SIGNAL UNDER 600)`. The advice is the least restrictive way of flying that dodges, accounting for cargo. Within 3000 m it says `TOO CLOSE TO DODGE`; in glare, `THE GLARE HIDES YOU`.
  - **Arrival:** `PINGED - DOMINION HAS YOUR POSITION` or `PING MISSED YOU`.
- **Catch range:** how close a ping must be to find a ship. 3000 m running dark, sliding to 6000 m at signal 1200 or louder.

  | You're doing | Signal | Caught within |
  |---|---|---|
  | Holding still, shield down | 300 | 3000 m |
  | Moving, shield down | 700 | about 4300 m |
  | Holding still, shield up | 800 | about 4700 m |
  | Moving with shield up, or louder | 1200+ | 6000 m |

- **Sun glare:** inside the sun's heat zone (within 60% of its radius) nobody can sense, ping, lock or scan, in either direction. The HUD shows `GLARE - SENSORS BLIND`.
- **Patrol zones:** within 2500 m of Assembly worlds and Nexum Astra. Privateers never enter them and break off when you're inside. The HUD shows `ASSEMBLY PATROL`. There are no patrol ships yet; it's just a zone.
- **HUNTED:** an amber HUD tag while any privateer is hunting, searching for or engaging you.

## Contacts

| Level | What you know | How it's shown |
|---|---|---|
| Blip | A bearing and rough range, from an area ping or an enemy ping | wedge, `?` and range |
| Contact | Its position: within its signature of you, outside glare | its sprite, or an edge arrow off screen |
| Scanned | Sponsor, class, hull, shield and its next intent | intent glyph above it and the target panel |

Test drones (`<o>`, from step 2) are sensor targets only: unarmed and not targetable.

## 3. Privateers (built)

Code: `modes/star_system_mode/privateers.py`, `vessels.py`; art from `tools/art/qud_glyph/generate_privateers.py` into `assets/img/ships/`.

| Class | Speed | Hull | Shield | Damage |
|---|---|---|---|---|
| Cutter | 150 | 40 | 30 | 0.8× |
| Raider | 100 | 70 | 50 | 1.0× |
| Gunship | 75 | 120 | 80 | 1.5× |

Each has a 400 fuel tank and boosts at double speed and double burn while over 100 fuel.

- **Patrol:** wander within 2000 m of home, pinging every 12 actions.
- **Hunt:** head for their last fix on you, boosting while more than 600 m away, pinging every 4 actions.
- **Search:** at the fix with no contact, wander within 6 tiles pinging. Give up after 12 turns plus 1 per 5 Assembly standing. If a ping places you somewhere new, hunt again.
- **Engage:** once they sense you, close to 8 tiles (192 m) and hold, with the shield up while they can fire and down to recharge when they can't.
- **Retreat:** below 40% hull, boost for home and stay there.
- **Never:** fly into glare or patrol zones, or hunt you inside a patrol zone or when you're friendly with their sponsor.
- **Look:** 48×48 glyph sprites in the barge's style, colored by faction (Dominion red `#b3424e`, Cohort green `#5bae70`, Caravaneer orange `#cc733f`), rotated to their heading, with the damage tint and shield shell your ship has.
- **Testing:** `DEBUG_PRIVATEERS` and `DEBUG_DRONES` in `main.py` spawn them near the start (default 0).

## 4. Fights (built)

Code: `modes/star_system_mode/combat.py`, `combat_fx.py`, `wrecks.py`.

- **Your actions:** move, boost and wait as before; fire 1 turn; scan 1 turn; area ping 1 turn; shield toggle free.
- **Weapon** (yours, and privateers' times their class damage):

  | Range | Distance | Hit chance | Damage |
  |---|---|---|---|
  | Close | up to 96 m (4 tiles) | 90% | 20 |
  | Effective | up to 192 m (8 tiles) | 65% | 14 |
  | Long | up to 288 m (12 tiles) | 35% | 8 |

  Hits go through the shield-then-hull system. Out of range, too little charge, or glare give a notice and cost no turn.
- **Shield as battery:** a shot costs 12 shield charge whether the shield is up or down, is loud, and stops the shield recharging that turn. Enemy hits on your raised shield drain your battery too. A privateer too low to fire drops its shield to recharge faster, which leaves its hull open.
- **Targeting:** Tab cycles armed ships in sight, nearest first. F and R use the target, or the nearest if there isn't one. A white bracket marks it.
- **Scanning:** R, 1 turn, up to 480 m (20 tiles), not in glare. Scanned status lasts until the privateer gives up the hunt.
- **Intents:** each action a privateer declares what it will do next. It only fires on an action it declared as firing, so a scanned privateer always warns you a turn ahead; stepping out of range or sight spoils the shot.

  | Glyph | Meaning |
  |---|---|
  | `(*) 65%` | firing next turn, with its hit chance |
  | `>>` | closing in |
  | `==` | holding range |
  | `<<` | retreating |
  | `?` | searching |
  | `((` | pinging next turn |
  | `..` | patrolling |

- **Target panel** (top right): scanned shows sponsor, class, hull, shield and intent; unscanned shows "UNKNOWN CONTACT". Both show exact range, your hit chance and damage, and the keys.
- **Shots:** a 140 ms chunky beam in the shooter's colour (yours cyan); a miss stops short in a spark. Notices: `HIT - 14 DAMAGE`, `MISS`, `HULL HIT - 9`.
- **Kills:** standing moves (sponsor -5, Assembly +3) and the kill is logged in `player.kill_log` for bounties.
- **Wrecks:** last 40 turns. Fly up, press E for the ship computer (wreck readout and its own debris art), and `salvage`: goods and credits by class (cutter 2–4 goods and $40–80, raider 3–6 and $80–150, gunship 5–10 and $150–300). Goods come from the sponsor's worlds' markets; while those have none (only Terramonta, Etheora and Nexum Astra have markets), from anything that sells in Sol. What doesn't fit the hold stays aboard.
- **Losing:** hull 0 means the tow.
- **Balance** (simulated duels, firing whenever charged and recharging with the shield down): cutters fall in 25–60 turns and barely hurt you; raiders retreat after about 80 turns, having cost you 30–55 hull; gunships tow you or grind on. Run from gunships.

## 5. World hooks (next)

- **Raids are real:** the existing `Pirate Raids Reported` economy event spawns a raid group, with one of the outer factions as sponsor, around that world for the event's duration.
  - The news story is the rumor; out there they show up as blips.
  - Wiping out the group ends the event early ("raids subside"), easing prices.
- **Background patrols:** a few privateers stay near their own faction's worlds. Spawn rate should rise with Assembly standing.
- **Bounties:** Assembly docking terminals pay out logged kills with a `bounty` command (raising Assembly standing), and the news reports them.
- **Distress beacons:** they always broadcast, so they show up as SOS blips.
  - About 70% are traps: privateers running dark nearby spring the ambush when you come within about 12 tiles.
  - The rest are genuine stranded haulers you can `refuel` for credits and standing with their faction.
  - Scanning from just outside the trap's trigger range (scans reach 20 tiles) tells you which kind it is.

## 6. Caravaneer people (later)

A planet's faction in space comes from `sol.json`, but the people on its surface come from its map file, and only the Assembly has an NPC set today. Etheora is the only reassigned world with a surface map, so this step makes its people Caravaneers. Cosmopolara will use the same set once it has a map. It only depends on step 1.

- **`entities/npcs/caravaneers_npc.py`:** job classes, name lists and hobbies. `npc_generator` already loads a faction's set by name.
- **Jobs (proposal, confirm when we get here):**

  | Caravaneer | Like the Assembly's |
  |---|---|
  | Caravan Master | Foreman |
  | Trader | |
  | Navigator | |
  | Rigger (mechanic) | |
  | Outrider (escort and security) | Security |

- **Sprites:** a 24×24 sprite per job in `assets/img/objects/`, recolored from the existing miner and foreman sprites in Caravaneer orange.
- **Portraits:** an outfit per job, drawn by `tools/gen_portrait_placeholders.py` and listed in the portrait manifest. The Caravaneer accent `#cc733f` is already there.
- **Dialogue:** goods and job lines per job in `dialogue/topics.py`, plus Etheora's tech-goods bias.
- **Etheora's map:** `guild` set to `caravaneers`, `npc_jobs` set to the new jobs, and the job posts moved to match.
- **Tests:** rolling a Caravaneer roster, building each job, portraits picking the right outfits, and landing on Etheora.

## Open questions

- **Assembly patrols:** stay a zone, or become visible patrol ships?
- **Market coverage:** Dominion and Cohort worlds have no markets, so their wrecks carry other goods and trading can't raise standing with them yet.
