"""Space mode HUD mockup: one frame with every piece of the UI overhaul, for review.

The ship and enemy panels are the real ones, drawn over a real flight scene: docked in
Etheora's corridor, hunted, in a fight with a scanned Dominion raider about to fire. The
alert banner, ping strip, event log, action strip and vignette are previews built from the
same kit (space/src/modes/star_system_mode/ui) until their build steps land.

Run from the repository root: python tools/ui/space_hud_mockup.py [out.png]
Writes space/assets/img/_style_samples/space_ui/mockup.png by default.
"""
import os
import random
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "space" / "src"))

import pygame  # noqa: E402

OUT = REPO / "space" / "assets" / "img" / "_style_samples" / "space_ui" / "mockup.png"
LONG_AGO = 10_000  # ms; pushes panel wipes and count-downs into the past so they rest


def scene(screen):
    """A real StarSystemMode, staged for the frame."""
    from entities.player import Player
    from modes.star_system_mode import star_system_mode
    from modes.star_system_mode.privateers import Privateer
    from util.config import TILE_SIZE

    star_system_mode.draw_prompt = lambda *args, **kwargs: None  # the old centre prompts give way to previews
    mode = star_system_mode.StarSystemMode(Player(), "sol")
    etheora = next(p for p in mode.selected_system.planets if p.name == "Etheora")
    port = etheora.beacon_points()[0]
    mode.x_position, mode.y_position = int(port[0]) // TILE_SIZE + 2, int(port[1]) // TILE_SIZE + 1
    mode.player.currency = 1500
    ship = mode.player.ship
    ship.shield_up = True
    ship.cargo.add_item("Ore", 12)

    x, y = mode.ship_center()
    raider = Privateer("raider", "dominion", (x + 170, y + 60), mode, rng=random.Random(4))
    gunship = Privateer("gunship", "caravaneers", (x - 330, y - 150), mode, rng=random.Random(5))
    cutter = Privateer("cutter", "cohort", (x + 380, y - 300), mode, rng=random.Random(6))
    for vessel in (raider, gunship, cutter):
        vessel.ship.shield_up = True
        mode.add_vessel(vessel)
    mode.spend_turns(1)
    mode.target, raider.scanned = raider, True
    raider.ship.hull, raider.ship.shield = 29, 6
    ship.hull, ship.shield, ship.fuel = 41, 64, 640
    mode.notice = None

    mode.handle_continuous_updates()
    mode.draw(screen)
    for owner in (mode.ship_panel, mode.enemy_panel):
        owner.panel.opened_at -= LONG_AGO
        owner.hull.started_at -= LONG_AGO
        owner.shield.started_at -= LONG_AGO
    wait_for_lit()
    mode.draw(screen)
    return mode


def wait_for_lit():
    """Hold until blinks are on and pulses near their peak, so the still shows the lit state."""
    from modes.star_system_mode.ui.theme import blink, pulse

    while not (blink(pygame.time.get_ticks()) and pulse(pygame.time.get_ticks()) >= 0.75):
        pygame.time.wait(5)


def vignette(screen, colour, depth=44, strength=90):
    """Preview: the screen edges glowing, for hull damage, heat or a ping."""
    width, height = screen.get_size()
    glow = pygame.Surface((width, height), pygame.SRCALPHA)
    for i in range(depth):
        alpha = int(strength * (1 - i / depth) ** 2)
        pygame.draw.rect(glow, (*colour, alpha), (i, i, width - 2 * i, height - 2 * i), 1)
    screen.blit(glow, (0, 0))


def alert_banner(screen, now_ms):
    """Preview: the top-centre alert, TeleSys at 2x with glow, framed by severity."""
    from modes.star_system_mode.ui.glyphs import draw_text, text_width
    from modes.star_system_mode.ui.panel import Panel
    from modes.star_system_mode.ui.theme import CELL_H, DANGER, shade

    text = "HULL HIT - 9"
    banner = Panel(len(text) * 2 + 6, 4)
    banner.open(now_ms - LONG_AGO)
    banner.begin("DANGER", shade(DANGER, 0.35), DANGER)
    x = (banner.width - text_width(text, 2)) // 2
    draw_text(banner.surface, (x, CELL_H), text, DANGER, scale=2, glow=True)
    left = (screen.get_width() - banner.width) // 2
    banner.blit(screen, (left, 8), now_ms)
    return 8 + banner.height


def ping_strip(screen, top, now_ms):
    """Preview: the pinned incoming-ping strip under the banner."""
    from modes.star_system_mode.ui.glyphs import draw_text
    from modes.star_system_mode.ui.panel import Panel
    from modes.star_system_mode.ui.theme import LABEL, VALUE, WARN, shade

    strip = Panel(36, 4)
    strip.open(now_ms - LONG_AGO)
    strip.begin("INCOMING PING", shade(WARN, 0.4), WARN)
    x, y = strip.at(2, 1)
    x += draw_text(strip.surface, (x, y), "(( ", WARN, glow=True)
    x += draw_text(strip.surface, (x, y), "4000 m NW", VALUE)
    draw_text(strip.surface, (x + 16, y), "3 TURNS", WARN, glow=True)
    draw_text(strip.surface, strip.at(2, 2), "DODGE: HOLD STILL, SHIELD UP", LABEL)
    strip.blit(screen, ((screen.get_width() - strip.width) // 2, top + 4), now_ms)


def event_log(screen):
    """Preview: the last five events, lower left, newest at the bottom, older ones fading.
    The plates stay dark, so a fading line still reads over a planet."""
    from modes.star_system_mode.ui.glyphs import draw_text, text_width
    from modes.star_system_mode.ui.theme import CELL_H, CELL_W, DANGER, FILL, LABEL, VALUE, WARN, shade

    events = [
        ("SCANNED DOMINION RAIDER", LABEL),
        ("PINGED - DOMINION HAS YOUR POSITION", WARN),
        ("COHORT CUTTER IN SIGHT", VALUE),
        ("HIT - 14 DAMAGE", LABEL),
        ("HULL HIT - 9", DANGER),
    ]
    top = screen.get_height() - 12 - len(events) * CELL_H
    for age, (text, colour) in enumerate(reversed(events)):
        y = top + (len(events) - 1 - age) * CELL_H
        line = f"> {text}"
        plate = pygame.Surface((text_width(line) + CELL_W, CELL_H), pygame.SRCALPHA)
        plate.fill(FILL)
        screen.blit(plate, (8, y))
        draw_text(screen, (12, y), line, shade(colour, 0.15 * age), glow=age == 0)


def action_strip(screen, now_ms):
    """Preview: what you can do here, bottom centre: a pulsing keycap and the body's name."""
    from modes.star_system_mode.ui.glyphs import draw_key, draw_text, key_width, text_width
    from modes.star_system_mode.ui.panel import Panel
    from modes.star_system_mode.ui.theme import FACTIONS, VALUE, shade

    colour = FACTIONS["caravaneers"]
    words, name = " DOCK · ", "ETHEORA"
    cols = (key_width("E") + text_width(words + name)) // 8 + 4
    strip = Panel(cols, 3)
    strip.open(now_ms - LONG_AGO)
    strip.begin("", shade(colour, 0.4))
    x, y = strip.at(2, 1)
    x += draw_key(strip.surface, (x, y), "E", colour, now_ms, pulse=True)
    x += draw_text(strip.surface, (x, y), words, VALUE)
    draw_text(strip.surface, (x, y), name, colour, glow=True)
    strip.blit(screen, ((screen.get_width() - strip.width) // 2, screen.get_height() - 8 - strip.height), now_ms)


def main(out=OUT):
    from util.config import SCREEN_HEIGHT, SCREEN_WIDTH
    from modes.star_system_mode.ui.theme import DANGER

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    scene(screen)
    now = pygame.time.get_ticks()
    vignette(screen, DANGER)
    bottom = alert_banner(screen, now)
    ping_strip(screen, bottom, now)
    event_log(screen)
    action_strip(screen, now)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(screen, str(out))
    print(f"wrote {out}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
