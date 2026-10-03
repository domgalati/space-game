---
name: Pirates
overview: Faction privateers built on the 1 move = 1 turn clock. A sensor game (signature, area pings, sun glare, patrol zones) leads into turn-based duels with instant range-based hits, where the shield is armour, weapon battery and loudest signal at once.
todos:
  - id: factions
    content: Give worlds to factions, everyone-against-the-Assembly stance, reputation that moves, hail and scan text
    status: completed
  - id: sensors
    content: Signature, contact levels, area ping with its spreading ring and bearing wedges, enemy pings, sun glare, patrol zones
    status: completed
  - id: privateer-ai
    content: Privateers as clock actors (patrol, hunt, engage, search, retreat, wave friends by) with faction sprites
    status: completed
  - id: combat
    content: Light weapon, targeting, scan-to-reveal intents, shield as battery, range-based hits, wrecks and salvage
    status: pending
  - id: world-hooks
    content: Raid events spawn privateers, bounties and news, distress beacons (mostly traps)
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

All numbers below are starting points to tune.

## Decided in the interview

- **Core:** tactical duels plus hunt and hide. Pings should be visual.
- **Who:** faction privateers. Worlds are given to factions, and everyone is against the Assembly.
- **Reputation:** rivals hunt you, and friends of a privateer's sponsor get waved by.
- **Your ship:** starts with a light weapon that draws on the shield as its battery.
- **Enemy intents:** shown only after you scan the ship.
- **Weapon fire:** instant hits whose chance and damage drop with range.
- **What gives you away:** pinging, a raised shield, boosting and a heavy hold.
- **Where you can hide:** sun glare, running dark, and Assembly patrol zones.
- **How pirates show up:** news rumors, then unknown blips; also distress-beacon lures, mostly traps with some real.
- **How fights end:** pirates retreat when hurt, leave wrecks to salvage, and the Assembly pays bounties.
- **Etheora's people:** they become Caravaneers (step 6). Until then its surface stays Assembly.

**Not doing (for now):** pirates hailing or negotiating, nemesis captains, hiding behind planets, escalating heavier ships, chokepoint ambushes, cargo loss on defeat (the existing tow stays).

## The world

**Territory** (planet faction fields in `sol.json`):

| Faction | Holds |
|---|---|
| Assembly | Governus Centralis, Terramonta, Nexum Astra |
| Dominion | Ferrica |
| Cohort | Ageria, Arboresia |
| Caravaneers | Cosmopolara, Etheora |

- **Everyone against the Assembly:** the Dominion, Cohort and Caravaneers license privateers against Assembly-friendly shipping. The Assembly is the law: it runs patrol zones and pays bounties.
- **Who hunts you:** a privateer waves you by if your standing with its sponsor is +30 or more; it may still ping you to check. Otherwise you're prey, and the higher your Assembly standing, the more often they spawn near you and the longer they chase.
- **Reputation that moves:**
  - a kill: standing down with the sponsor, up with the Assembly;
  - a bounty paid: up with the Assembly;
  - rescuing a real distress beacon: up with the rescued hauler's faction;
  - trading at a faction's worlds: a little up.

## Hunt and hide

- **Signature:** recalculated every turn. It's the range at which others can sense you.

  | State | Signature |
  |---|---|
  | Running dark: holding still (waiting or pinging) with the shield down | about 300 px |
  | Any move | about 700 px |
  | Raised shield | +500 |
  | Boosting | +500 |
  | Firing (that turn) | +900 |
  | Full hold (scaled by how full) | up to +400 |

- **Area ping:** `ping` with no name, or the P key. It costs 1 turn.
  - A ring of glyph dots spreads out from your ship, and anything it crosses blinks.
  - Unknown ships within about 6000 px appear as `?` blips, each with a bearing wedge (a translucent cone toward it, narrower when closer) that fades over a few turns.
  - Every privateer within that same range hears it and learns your bearing.
  - `ping <planet>` keeps working as it does today.
- **Enemy pings:** a hunting privateer area-pings about every 4 turns. Its ring rolls across your screen and leaves a wedge pointing back at it, so you know you're being hunted and from roughly where.
- **Dodging a ping:** an enemy ping travels 1000 m per turn, so you see it coming. A warning gives its range, direction, turns until it arrives, and the quietest change that dodges it. It catches you only if you're within its catch range when it arrives: 3000 m running dark, sliding up to 6000 m at signal 1200 or louder (moving with the shield down, at 700, is caught within about 4300 m). Then a notice says `PINGED - DOMINION HAS YOUR POSITION` or `PING MISSED YOU`, and a `HUNTED` HUD tag stays up while any privateer is after you. Your own area ping reports each contact's rough range.
- **Running dark** works both ways: a ship running dark doesn't show until it's within a few tiles, or until an area ping catches it.
- **Sun glare:** inside the sun's heat zone nobody can lock, ping or scan, in either direction. You vanish from their sensors and they vanish from yours, while the heat eats your shield and hull.
- **Patrol zones:** within about 2500 px of Assembly worlds and Nexum Astra, privateers break off. The HUD shows ASSEMBLY PATROL.
- **Losing you:** a privateer that loses track of you flies to where it last saw you, area-pings, and gives up after about 12 turns.

## Contacts

| Level | What you know |
|---|---|
| Blip | A `?` and a bearing, from an area ping or an enemy ping. |
| Contact | Its position; it's within sight and not running dark. |
| Scanned | Sponsor, ship class, hull and shield, and its intent each turn. |

A scan costs 1 turn, reaches about 20 tiles, and doesn't work in glare. Scanned status lasts for the encounter.

## Fights (all on the turn clock)

- **Privateer ships:** actors on the turn clock, at these speeds:

  | Class | Speed | |
  |---|---|---|
  | Cutter | 150 | fast, fragile |
  | Raider | 100 | |
  | Gunship | 75 | slow, hits hard |

  They boost like you do (double speed, double fuel) to chase or flee.
- **Your actions:**
  - move, boost and wait as now;
  - fire: 1 turn;
  - scan: 1 turn;
  - area ping: 1 turn;
  - shield toggle: free.
- **Instant hits by range** (light weapon):

  | Range | Distance | Hit chance | Damage |
  |---|---|---|---|
  | Close | up to 4 tiles | 90% | 10 |
  | Effective | up to 8 tiles | 65% | 7 |
  | Long | up to 12 tiles | 35% | 4 |

  Damage goes through the existing shield-then-hull system.
- **Shield as battery:**
  - a shot costs 12 shield charge, is loud, and counts as taking damage, so the shield doesn't recharge that turn;
  - with the shield lowered you can still fire from stored charge, but you're exposed;
  - privateers follow the same rules, so a scanned enemy's charge tells you whether it can shoot.
- **Intent glyphs** (scanned enemies only, drawn above the ship in TeleSys):

  | Glyph | Meaning |
  |---|---|
  | `>>` | closing in |
  | `(*)` | firing next turn, with its hit chance |
  | `<<` | retreating |
  | `?` | searching |
  | `((` | pinging |

- **Glare** blocks locks both ways, so diving toward the sun breaks off a firefight.
- **Retreat:** below 30% hull a privateer boosts for home. Chasing it costs your fuel.
- **Wrecks:** a destroyed privateer leaves a wreck that lasts about 40 turns. Approach it, press E and `salvage` it for goods from its sponsor's worlds and some credits.
- **Bounties:** kills are logged. Assembly docking terminals pay them out with a `bounty` command, and the news reports them.
- **Losing:** hull 0 still means the tow.

## Rumors, blips and lures

- **Raids are real:** the existing `Pirate Raids Reported` economy event spawns a raid group, with one of the outer factions as sponsor, around that world for the event's duration.
  - The news story is the rumor; out there they show up as blips.
  - Wiping out the group ends the event early ("raids subside"), easing prices.
- **Background patrols:** a few privateers stay near their own faction's worlds.
- **Distress beacons:** they always broadcast, so they show up as SOS blips.
  - About 70% are traps: privateers running dark nearby spring the ambush when you come within about 12 tiles.
  - The rest are genuine stranded haulers you can `refuel` for credits and standing with their faction.
  - Scanning from just outside the trap's trigger range (scans reach 20 tiles) tells you which kind it is.

## Look

- **Privateer ships:** 48×48 glyph sprites in the barge's style, colored by faction from the portrait palette: Dominion red `#b3424e`, Cohort green `#5bae70`, Caravaneer orange `#cc733f`. They get the same damage tint and blocky shield shell as your ship.
- **Shots:** a one-frame chunky beam in the shooter's color. A miss ends in a spark short of the target.
- **Area ping ring:** a coarse dotted ring built like the shield shell, spreading out over about 0.6 seconds of real time. Your rings are cyan and enemy rings amber.
- **HUD:** a signature meter (QUIET to LOUD), a target panel (name, sponsor, class, hull and shield, hit chance), and GLARE and ASSEMBLY PATROL tags.

## Caravaneer people

A planet's faction in space comes from `sol.json`, but the people on its surface come from its map file, and only the Assembly has an NPC set today. Etheora is the only reassigned world with a surface map, so this step makes its people Caravaneers. Cosmopolara will use the same set once it has a map.

The pieces, following the Assembly's set:

- **`entities/npcs/caravaneers_npc.py`:** job classes, name lists and hobbies. `npc_generator` already loads a faction's set by name, so nothing else changes there.
- **Jobs (proposal, confirm when we get here):**

  | Caravaneer | Like the Assembly's |
  |---|---|
  | Caravan Master | Foreman |
  | Trader | |
  | Navigator | |
  | Rigger (mechanic) | |
  | Outrider (escort and security) | Security |

- **Sprites:** a 24×24 sprite per job in `assets/img/objects/`, recolored from the existing miner and foreman sprites in Caravaneer orange.
- **Portraits:** an outfit per job, drawn by `tools/gen_portrait_placeholders.py` and listed in the portrait manifest. The Caravaneer accent color `#cc733f` is already there.
- **Dialogue:** goods and job lines per job in `dialogue/topics.py`, plus Etheora's tech-goods bias.
- **Etheora's map:** `guild` set to `caravaneers`, `npc_jobs` set to the new jobs, and the job posts moved to match. The map spec or the `.tmx` posts need updating.
- **Tests:** rolling a Caravaneer roster, building each job, portraits picking the right outfits, and landing on Etheora.

## Build order (each step is usable on its own)

1. **Factions:** territory, the stance table, reputation changes, hail and scan text.
2. **Sensors:** signature, contact levels, area ping and wedges, enemy pings, glare, patrol zones. Testable with a dummy drone actor before pirates exist.
3. **Privateer behaviour on the clock:** patrol, hunt, engage, search, retreat, waving friends by. Faction sprites.
4. **Combat:** weapon, targeting, scanning to reveal intents, shield as battery, hit model, wrecks and salvage.
5. **World hooks:** raid events, bounties and news, distress beacons.
6. **Caravaneer people:** the NPC set above. It only depends on step 1, so it can move earlier without blocking anything.

## Open questions

- **Neutral standing:** do privateers hunt a hauler with zero standing everywhere? Default: yes, unless you're friendly with their sponsor.
- **Keys:** default F to fire, Tab to cycle targets, R to scan a target, P to area-ping. S (shield) and Space (wait) are taken.
- **Assembly patrols:** visible ships, or just a zone for now?
