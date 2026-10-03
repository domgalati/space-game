---
name: Space mode UI overhaul
overview: Replace space mode's placeholder text with a glyph-built HUD in the ASCII roguelike style, with colour, glow, pulse, blink and flash. Ship stats top left, enemy status top right in battle, a bottom-centre action strip, a top-centre alert banner with a fading event log, and restyled markers.
todos:
  - id: kit
    content: Theme and widget kit (palette, TeleSys glyph frames, block bars, chips, keycaps, glow text, blink and pulse timing), plus a mockup frame to approve
    status: pending
  - id: ship-panel
    content: Always-on ship status panel, top left
    status: pending
  - id: enemy-panel
    content: Enemy status panel, top right, while engaged
    status: pending
  - id: action-strip
    content: Bottom-centre action strip for dock, scan, salvage, atmosphere and heat
    status: pending
  - id: alerts
    content: Alert banner by severity, fading event log, screen-edge vignette and shake
    status: pending
  - id: markers
    content: Restyle markers (nav arrows, beacons, ping blips, intents, target bracket) and full-screen moments (tow, kill)
    status: pending
isProject: false
---

# Space mode UI overhaul

## Today

- **Fonts:** three in use: OfficeCodePro (HUD, target panel, nav labels), pygame's default font (every centre prompt and notice), and TeleSys (ship computer, intent glyphs). Only the ship computer's bezel has real style.
- **Ship stats:** plain text lines on a dark rectangle, top left.
- **Target panel:** the same, top right, shown whenever an armed ship is in sight.
- **Prompts:** `[E] Scan`, SOLAR HEAT and ATMOSPHERE in the middle of the screen, on top of your ship.
- **Notices:** one slot. Hits, pings, tows, kills, salvage, standing changes and area-ping results overwrite each other, so information is lost.
- **Ping warning:** a long line of amber text above the notice.
- **Markers:** edge arrows with labels, charted beacons, ping `?` markers with ranges, intent glyphs and the target bracket all work but are flat.

## Decided

- **Look:** glyph frames. Panels and borders are drawn from TeleSys glyphs on the 8×16 grid, and bars from its block characters (`█▓▒░`),, like the terminal bezels, in the Qud palette.
- **Effects:** glow and pulse, blink and flash, a screen-edge vignette, and a small screen shake.
- **Events:** urgent things raise a top-centre alert coloured by severity, and everything also goes into a short fading event log, lower left.
- **Prompts:** a bottom-centre action strip, so the ship stays clear in the middle.

## Design language

- **One font:** TeleSys at its native 16 px for labels, values and frames, and at 2× for banners. Replaces OfficeCodePro and the default font in space mode.
- **Palette:** Qud colours already in the game.

  | Use | Colour |
  |---|---|
  | Frames and labels | dark teal `K`, light teal `C` |
  | Values | light grey `y`, white `Y` |
  | Shield and your weapon | blue `B`, cyan `C` |
  | Hull healthy / damaged / critical | green `G`, amber `O`, red `R` |
  | Warning | amber `O` |
  | Danger | red `R` |
  | Factions | Dominion `#b3424e`, Cohort `#5bae70`, Caravaneer `#cc733f` |

- **Panels:** a translucent dark fill inside a glyph border (`+--=--+`, `|` sides), with a header tab in the corner (`+-[ SHIP ]---`). They open with a quick scanline wipe.
- **Bars:** TeleSys block glyphs: a solid `█` fill, a shaded `▓` or `▒` edge on the last partly filled cell, and a dim `░` track, for example `██████▓░░░`. The fill colour ramps with the value; the track is a darker shade of it.
- **Chips:** small bracketed tags for status, for example `[GLARE]`, `[PATROL]`, `[HUNTED]`, `[BOOST]`, `[RING]`, `[RESERVE]`.
- **Keycaps:** `[E]` drawn as a little lit key that pulses while its action is available.
- **Motion** (shared timers, so everything blinks in step):
  - **Pulse:** brightness swells on a 1.2 s cycle. Used for the raised shield, a charged weapon, available actions and active alerts.
  - **Blink:** 2 Hz on and off. Used for critical values (hull under 25%, fuel under 20), an incoming ping's countdown, and an enemy's `(*)` when it fires next turn.
  - **Flash:** about 150 ms of white or red on a bar or panel the moment it changes. Used for hits on your shield or hull, and hits you land.
  - **Glow:** a halo drawn as the text again in a darker shade, offset a pixel each way. Used on key numbers and alert text.
  - **Count-down:** values that drop animate down over a few frames instead of jumping.
- **Vignette:** the screen edges glow red on hull damage, orange in solar heat and amber when a ping catches you. It fades over about half a second; heat holds while you're in it.
- **Shake:** 2–4 px for about 150 ms on hull hits and kills. Nothing else shakes.

## Pieces

### 1. Ship status, top left (always on)

```
+-[ BARGE ]-----------------------+
| HULL   ██████████ 100         |
| SHIELD ██████▓░░░  64  (UP)   |
| FUEL   ██████████ 1000        |
| SIGNAL ███▒░░░░░░ 700 QUIET   |
| $1500        CARGO 12/100       |
| [HUNTED] [PATROL]               |
+---------------------------------+
```

- **Hull:** the colour ramps green to amber to red, and it blinks under 25%. The bar flashes red when the hull takes damage.
- **Shield:** blue. `(UP)` pulses while raised. The bar flashes white when it absorbs a hit. Below one shot's charge (12) it shows `NO CHARGE` in amber.
- **Fuel:** amber under 20, and `RESERVE` blinking red when empty. `BOOST` and `RING` show as chips.
- **Signal:** the bar ramps teal to amber to red with the reading `DARK`, `QUIET` or `LOUD`. A `PING` or `FIRE` tag shows on loud action turns.
- **Status chips:** `GLARE` (orange), `PATROL` (green), `HUNTED` (amber, pulsing), `RESERVE` (red, blinking).

### 2. Enemy status, top right (while engaged)

It opens when a privateer is in sight and engaging or hunting you, or when you have a target. It closes a few turns after contact ends.

```
+-[ DOMINION RAIDER ]------------+
|  <ship icon>   RANGE 172 m     |
| HULL   █████░░░░░  41        |
| SHIELD █░░░░░░░░░   6  DOWN  |
| INTENT (*) FIRES NEXT  65%     |
| YOUR SHOT  65%  14 DMG         |
| [F] FIRE  [R] SCAN  [TAB] NEXT |
+--------------------------------+
```

- **Frame:** in the faction's colour, with a small icon of the ship's sprite in the header.
- **Unscanned:** the hull, shield and intent rows show scrambled glyphs (`?#:?`) that flicker, and `[R] SCAN` pulses.
- **Intent:** `(*) FIRES NEXT` blinks red. A shield too low to fire reads `RECHARGING` in amber, which is your opening.
- **Your shot:** shows hit chance and damage for the current range, or `OUT OF RANGE` dimmed. `[F]` pulses only when you're in range and charged.
- **Hits:** the panel flashes when you hit it. A kill plays a short break-up of the frame before it closes.
- **More than one hostile:** a small row of faction-coloured pips under the frame, one per contact in sight, with the target's pip lit.

### 3. Action strip, bottom centre

One slim bar for what you can do here and what's acting on you. It shows the most important item, with a second as a smaller row if there are two.

- **In a docking corridor:** `[E] DOCK · TERRAMONTA`. The keycap pulses, and the text is in the body's faction colour.
- **Other corridors:** `[E] SCAN · <name>` for a body that can't be docked at, and `[E] SALVAGE · DOMINION RAIDER WRECK` for a wreck.
- **Atmosphere:** an amber band, `ATMOSPHERE · FUEL x2`, with a slow pulse.
- **Solar heat:** an orange-red band, `SOLAR HEAT · -4 / TURN`, shimmering (glyph noise along its edges), with the per-turn damage live.
- **Glare:** `GLARE · SENSORS BLIND` in orange when no other heat band is up.

### 4. Alerts and the event log

- **Alert banner, top centre:** one at a time, queued by severity, each shown for about 2.5 seconds. TeleSys at 2× with glow, on a glyph-bordered strip.

  | Severity | Colour | Treatment | Examples |
  |---|---|---|---|
  | Info | cyan | fade in | ping results, salvage, `PING MISSED YOU`, waved by |
  | Warning | amber | blinks once, vignette | `PINGED - DOMINION HAS YOUR POSITION`, `SHIELD CHARGE TOO LOW`, out of range |
  | Danger | red | flash, vignette, shake | `HULL HIT - 9`, solar heat damage, `HULL FAILURE` |

- **Incoming ping:** its own pinned strip under the banner while a ping is on the way: a ring glyph, `INCOMING 4000 m NW`, a blinking turn count, and the dodge advice. It turns cyan as `MISSED` or amber as `CAUGHT` when it arrives.
- **Event log, lower left:** the last 5 events, newest at the bottom, each fading out over about 8 seconds. Every alert lands here too, plus things that don't need an alert: standing changes, your hits and misses, wrecks breaking up, docking. Colour-coded by severity.

### 5. Markers and big moments

- **Nav arrows:** chevrons in the body's faction colour with the name and distance (`TERRAMONTA 8.2 km`). Charted bodies only, as now.
- **Ping blips:** the `?` pulses as its wedge fades, with the range under it in the same glyph style.
- **Target bracket:** animated corners that close in when you select a target, white normally and red-blinking when it's about to fire.
- **Intent glyphs:** the same glyphs with a glow. `(*)` blinks red.
- **Contacts off screen:** faction-coloured chevrons that pulse while that ship is hunting you.
- **Tow:** a full-width danger banner (`HULL FAILURE - TOWED TO NEXUM ASTRA - FEE $150`) with a brief fade to black and back.
- **Kill:** a short faction-coloured banner (`DOMINION RAIDER DESTROYED`) with the standing change under it, plus shake.

## Build order

1. **Kit and mockup:** `modes/star_system_mode/ui/` with the theme (palette, TeleSys sizes, shared blink, pulse and flash timers), glyph frames, block bars, chips, keycaps and glow text. Render a mockup frame for approval before wiring anything.
2. **Ship status panel** replaces the current HUD block.
3. **Enemy status panel** replaces the target readout.
4. **Action strip** replaces the centre prompts.
5. **Alerts, ping strip, event log, vignette and shake** replace the notice slot. Every `show_notice` call gets a severity.
6. **Markers and big moments.**

Each step leaves the game playable. The ship computer (scan terminal) is already styled and stays as it is.

## Testing

- **Unit tests:** alert queue ordering and timing, event log length and fading, which action the strip picks (dock beats atmosphere, salvage beats scan), bar fill and colour thresholds, and when the enemy panel opens and closes.
- **Screenshots:** headless renders of each state (calm, docking, atmosphere, heat, incoming ping, fight unscanned and scanned, kill, tow) to review against the mockup.
- **Frame time:** stays well inside 16 ms with the panels, log and vignette on.
