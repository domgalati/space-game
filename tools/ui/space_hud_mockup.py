"""Space mode HUD mockup: one frame with the UI overhaul's pieces, for review.

Everything is the real HUD over a real flight scene, staged through the game: docked in
Etheora's corridor, hunted, a ping on its way, a few events in the log, and a fight with a
scanned Dominion raider about to fire just after it hit the hull. Markers and the full-screen
moments (step 6) are still the old ones.

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
LONG_AGO = 10_000  # ms; pushes wipes and count-downs into the past so they rest
BANNER_AGE = 600  # ms the hull-hit alert has been up: past its flash, before it fades


def scene(screen):
    from entities.player import Player
    from modes.star_system_mode.privateers import Privateer
    from modes.star_system_mode.star_system_mode import StarSystemMode
    from modes.star_system_mode.ui.alerts import DANGER_LEVEL, NOTE, WARNING
    from modes.star_system_mode.vessels import Drone
    from util.config import TILE_SIZE

    mode = StarSystemMode(Player(), "sol")
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
    pinger = Drone((x - 4000, y - 600), mode)
    mode.add_vessel(pinger)
    mode.vessel_ping(pinger)
    mode.target, raider.scanned = raider, True
    raider.ship.hull, raider.ship.shield = 29, 6
    ship.hull, ship.shield, ship.fuel = 41, 64, 640

    mode.events.entries.clear()
    mode.banner.alerts.queue.clear()
    mode.banner.alerts.current = None
    mode.notify("SCANNED DOMINION RAIDER")
    mode.notify("PINGED - DOMINION HAS YOUR POSITION", WARNING)
    mode.notify("COHORT CUTTER IN SIGHT", NOTE)
    mode.notify("HIT - 14 DAMAGE", NOTE)
    mode.notify("HULL HIT - 9", DANGER_LEVEL)

    mode.handle_continuous_updates()
    mode.draw(screen)
    for owner in (mode.ship_panel, mode.enemy_panel):
        owner.panel.opened_at -= LONG_AGO
        owner.hull.started_at -= LONG_AGO
        owner.shield.started_at -= LONG_AGO
    for panel in mode.action_strip._panels.values():
        panel.opened_at -= LONG_AGO
    wait_for_lit()
    now = pygame.time.get_ticks()
    mode.banner.alerts.current.shown_at = now - BANNER_AGE
    mode.vignette.started_at = now - 150  # the glow partway through its fade
    mode.shake.until = 0  # a still can't shake
    mode.draw(screen)
    return mode


def wait_for_lit():
    """Hold until blinks are on and pulses near their peak, so the still shows the lit state."""
    from modes.star_system_mode.ui.theme import blink, pulse

    while not (blink(pygame.time.get_ticks()) and pulse(pygame.time.get_ticks()) >= 0.75):
        pygame.time.wait(5)


def main(out=OUT):
    from util.config import SCREEN_HEIGHT, SCREEN_WIDTH

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    scene(screen)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(screen, str(out))
    print(f"wrote {out}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
