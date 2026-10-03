import random
from types import SimpleNamespace

import pygame
import pytest

from entities.player import Player, Ship
from modes.star_system_mode.combat import SHOT_COST
from modes.star_system_mode.privateers import Privateer
from modes.star_system_mode.sensors import LOUD_AT, SIGNATURE_DARK
from modes.star_system_mode.ui.enemy_panel import BREAKING, LIVE, LOST, LOST_TURNS, EnemyPanel
from modes.star_system_mode.ui.glyphs import FULL, HEAVY, LIGHT, TRACK, bar_glyphs, scramble
from modes.star_system_mode.ui.panel import BREAK_MS, Meter
from modes.star_system_mode.ui.ship_panel import hull_colour, signal_colour, signature_word, status_chips
from modes.star_system_mode.ui.theme import (
    BLINK_MS, COUNT_MS, DANGER, FLASH_MS, GOOD, PULSE_MS, WARN, blink, pulse,
)
from util.config import SCREEN_HEIGHT, SCREEN_WIDTH, TILE_SIZE


def test_bars_fill_solid_with_a_shaded_edge_and_a_track():
    assert bar_glyphs(1.0, 10) == (FULL * 10, "", "")
    assert bar_glyphs(0.0, 10) == ("", "", TRACK * 10)
    assert bar_glyphs(0.64, 10) == (FULL * 6, HEAVY, TRACK * 3)
    assert bar_glyphs(0.62, 10) == (FULL * 6, LIGHT, TRACK * 3)
    assert bar_glyphs(0.001, 10) == ("", LIGHT, TRACK * 9)  # anything left shows
    for share in (0.0, 0.07, 0.33, 0.5, 0.99, 1.0, 1.5, -1):
        assert len("".join(bar_glyphs(share, 10))) == 10


def test_hull_turns_amber_below_half_and_red_below_a_quarter():
    assert hull_colour(1.0) == hull_colour(0.5) == GOOD
    assert hull_colour(0.49) == hull_colour(0.25) == WARN
    assert hull_colour(0.24) == DANGER


def test_signal_reads_dark_quiet_or_loud_and_reddens_toward_full_ping_range():
    assert signature_word(SIGNATURE_DARK) == "DARK"
    assert signature_word(LOUD_AT - 1) == "QUIET"
    assert signature_word(LOUD_AT) == "LOUD"
    halfway = (SIGNATURE_DARK + LOUD_AT) / 2
    assert signal_colour(SIGNATURE_DARK) == signal_colour(halfway - 1) not in (WARN, DANGER)
    assert signal_colour(halfway) == WARN
    assert signal_colour(LOUD_AT) == DANGER


def test_blinks_and_pulses_share_one_clock():
    assert blink(0) and not blink(BLINK_MS) and blink(2 * BLINK_MS)
    assert pulse(0) == 0 and pulse(PULSE_MS // 2) == 1 and pulse(PULSE_MS) == 0
    assert scramble(8, 0) == scramble(8, 0) != scramble(8, 1000)


def test_a_dropping_meter_counts_down_and_flashes_but_a_rise_jumps():
    meter = Meter(flashes=True)
    assert meter.update(100, 0) == 100 and not meter.flashing(0)
    assert meter.update(60, 1000) == 100 and meter.flashing(1000)
    assert 60 < meter.shown(1000 + COUNT_MS // 2) < 100
    assert not meter.flashing(1000 + FLASH_MS)
    assert meter.update(60, 1000 + COUNT_MS) == 60
    assert meter.update(80, 2000) == 80


def vessel():
    return SimpleNamespace(ship=Ship())


def test_the_enemy_panel_holds_after_contact_ends_then_closes():
    panel, raider = EnemyPanel(), vessel()
    assert panel.track(None, 0, 0) is None
    assert panel.track(raider, 0, 0) == LIVE and panel.panel.is_open
    assert panel.track(None, 1, 100) == LOST
    assert panel.track(raider, 2, 200) == LIVE  # back in sight before it closed
    assert panel.track(None, 3, 300) == LOST
    assert panel.track(None, 3 + LOST_TURNS - 0.5, 400) == LOST
    assert panel.track(None, 3 + LOST_TURNS, 500) is None and not panel.panel.is_open


def test_a_new_target_wipes_the_panel_open_again():
    panel, first, second = EnemyPanel(), vessel(), vessel()
    panel.track(first, 0, 0)
    assert panel.track(second, 0, 700) == LIVE and panel.shown is second and panel.panel.opened_at == 700


def test_a_kill_breaks_the_panel_up_before_the_next_target_opens():
    panel, dead, next_one = EnemyPanel(), vessel(), vessel()
    panel.track(dead, 0, 0)
    dead.ship.hull = 0
    assert panel.track(next_one, 1, 1000) == BREAKING
    assert panel.track(next_one, 1, 1000 + BREAK_MS - 1) == BREAKING
    assert panel.track(next_one, 1, 1000 + BREAK_MS) == LIVE
    assert panel.shown is next_one and panel.panel.opened_at == 1000 + BREAK_MS
    dead_alone = EnemyPanel()
    dead_alone.track(dead, 0, 0)
    assert dead_alone.track(None, 1, 0) == BREAKING and dead_alone.track(None, 1, BREAK_MS) is None


class Hit:
    def random(self):
        return 0.0

    def choice(self, items):
        return items[0]

    def randint(self, low, high):
        return low


@pytest.fixture
def mode():
    from modes.star_system_mode.star_system_mode import StarSystemMode

    pygame.init()
    pygame.display.set_mode((1, 1))
    flight = StarSystemMode(Player(), "sol")
    flight.rng = Hit()
    x, y = flight.map_center_x, flight.map_center_y + 15000  # open space, no patrol zone
    flight.x_position, flight.y_position = int(x) // TILE_SIZE, int(y) // TILE_SIZE
    flight.player.ship.shield_up = True
    return flight


def privateer(mode, dx, dy, kind="raider"):
    x, y = mode.ship_center()
    ship = Privateer(kind, "dominion", (x + dx, y + dy), mode, rng=random.Random(4))
    mode.add_vessel(ship)
    return ship


def place(mode, point):
    mode.x_position, mode.y_position = int(point[0]) // TILE_SIZE, int(point[1]) // TILE_SIZE


def test_status_chips_show_what_acts_on_you_most_urgent_first(mode):
    assert status_chips(mode) == []
    privateer(mode, 150, 0)
    mode.spend_turns(1)
    mode.boosting = True
    labels = [label for label, _, _ in status_chips(mode)]
    assert labels == ["HUNTED", "BOOST"]
    assert status_chips(mode)[0] == ("HUNTED", WARN, "pulse")
    place(mode, (mode.map_center_x, mode.map_center_y))  # the sun's glare
    assert "GLARE" in [label for label, _, _ in status_chips(mode)]
    place(mode, mode.selected_system.patrol_zones()[0])
    assert "PATROL" in [label for label, _, _ in status_chips(mode)]


def test_a_shot_that_lands_flashes_the_enemy_panel(mode):
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    target = privateer(mode, 150, 0)
    mode.draw(screen)
    assert mode.enemy_panel.shown is target
    mode.player_fire()
    assert mode.enemy_panel.panel.flash_until > pygame.time.get_ticks()


def test_the_panels_draw_in_every_state(mode):
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    ship = mode.player.ship
    mode.draw(screen)  # calm: no enemy panel
    assert mode.ship_panel.panel.is_open and not mode.enemy_panel.panel.is_open
    target = privateer(mode, 150, 0)
    mode.draw(screen)  # unscanned
    mode.spend_turns(1)
    target.scanned = True
    hull, shield = ship.hull, ship.shield
    ship.hull, ship.shield, ship.fuel = 10, SHOT_COST - 1, 0  # critical, no charge, on reserve
    mode.draw(screen)  # scanned, intent showing
    assert target.intent[0] == "fire"
    ship.hull, ship.shield = hull, shield
    target.ship.hull, target.ship.shield = 1, 0
    mode.player_fire()
    mode.draw(screen)  # breaking up
    assert mode.enemy_panel.panel.broken_at is not None


# Step 4: the action strip.
def planet(mode, name):
    return next(body for body in mode.selected_system.planets if body.name == name)


def wreck_at(mode, point, cargo=None):
    from modes.star_system_mode.wrecks import Wreck

    hulk = Privateer("raider", "dominion", point, mode, rng=random.Random(4))
    wreck = Wreck(hulk, {"Ore": 3} if cargo is None else cargo, 0, mode.remove_wreck)
    mode.wrecks.append(wreck)
    return wreck


def test_the_strip_offers_dock_then_salvage_then_scan(mode):
    from modes.star_system_mode.ui.action_strip import actions

    etheora = planet(mode, "Etheora")
    port = etheora.beacon_points()[0]
    place(mode, port)
    wreck = wreck_at(mode, mode.ship_center())
    (first, *_) = actions(mode, 2.0)
    assert (first.verb, first.name) == ("DOCK", "ETHEORA") and mode.check_collision() is etheora
    place(mode, (port[0] + 3000, port[1]))  # open space, and the wreck follows
    wreck.position = mode.ship_center()
    assert actions(mode, 2.0)[0].verb == "SALVAGE" and mode.check_collision() is wreck
    wreck.cargo = {}
    assert actions(mode, 2.0)[0].verb == "SCAN"


def test_the_strip_shows_atmosphere_and_solar_heat(mode):
    from modes.star_system_mode.ui.action_strip import actions

    assert actions(mode, 2.0) == []
    place(mode, planet(mode, "Etheora").position)
    (band,) = actions(mode, 2.0)
    assert (band.verb, band.name) == ("ATMOSPHERE", "FUEL x2")
    place(mode, (mode.map_center_x + 900, mode.map_center_y))
    (band,) = actions(mode, 2.0)
    assert band.verb == "SOLAR HEAT" and band.name.endswith("/ TURN")


# Step 5: alerts, the event log and the screen effects.
def test_alerts_show_the_most_severe_first_one_at_a_time():
    from modes.star_system_mode.ui.alerts import ALERT_MS, DANGER_LEVEL, INFO, WARNING, Alerts

    alerts = Alerts()
    alerts.post("SCANNED", INFO, 0)
    alerts.post("PINGED", WARNING, 0)
    alerts.post("HULL HIT - 9", DANGER_LEVEL, 0)
    shown = []
    for now in range(0, 4 * ALERT_MS, 100):
        alert = alerts.update(now)
        if alert and (not shown or shown[-1] != alert.text):
            shown.append(alert.text)
    assert shown == ["HULL HIT - 9", "PINGED", "SCANNED"]
    assert alerts.update(4 * ALERT_MS) is None


def test_worse_news_cuts_in_and_a_repeating_hazard_refreshes_its_alert():
    from modes.star_system_mode.ui.alerts import ALERT_MS, DANGER_LEVEL, INFO, Alerts

    alerts = Alerts()
    alerts.post("SCANNED", INFO, 0)
    assert alerts.update(0).text == "SCANNED"
    alerts.post("SOLAR HEAT - HULL -3", DANGER_LEVEL, 100, key="heat")
    assert alerts.update(100).text == "SOLAR HEAT - HULL -3"
    alerts.post("SOLAR HEAT - HULL -4", DANGER_LEVEL, ALERT_MS, key="heat")
    current = alerts.update(ALERT_MS)
    assert current.text == "SOLAR HEAT - HULL -4" and not alerts.queue  # refreshed, not queued again


def test_the_log_keeps_the_last_five_and_each_fades_out():
    from modes.star_system_mode.ui.alerts import LOG_MS, LOG_SIZE, NOTE, EventLog

    log = EventLog()
    for i in range(LOG_SIZE + 2):
        log.add(f"EVENT {i}", NOTE, i * 1000)
    assert log.texts() == [f"EVENT {i}" for i in range(2, LOG_SIZE + 2)]
    assert len(log.visible(LOG_MS + 2000)) == LOG_SIZE - 1  # EVENT 2 has faded
    assert log.latest() == f"EVENT {LOG_SIZE + 1}"


def test_long_alerts_split_into_a_headline_and_a_detail_line():
    from modes.star_system_mode.ui.alerts import split_headline

    assert split_headline("PINGED - DOMINION HAS YOUR POSITION") == ("PINGED", "DOMINION HAS YOUR POSITION")
    assert split_headline("AREA PING: 2 UNKNOWN CONTACTS.") == ("AREA PING", "2 UNKNOWN CONTACTS.")
    assert split_headline("MISS") == ("MISS", "")


def test_severity_sets_the_edge_glow_and_the_shake(mode):
    from modes.star_system_mode.ui.alerts import DANGER_LEVEL, NOTE, WARNING
    from modes.star_system_mode.ui.effects import SHAKE_MS, VIGNETTE_MS

    now = pygame.time.get_ticks()
    mode.notify("HIT - 14 DAMAGE", NOTE)
    assert mode.vignette.level(now) == 0 and mode.banner.alerts.update(now) is None
    mode.notify("PINGED - DOMINION HAS YOUR POSITION", WARNING)
    assert mode.vignette.colour == WARN and mode.shake.offset(now) == (0, 0)
    mode.notify("HULL HIT - 9", DANGER_LEVEL)
    assert mode.vignette.colour == DANGER and mode.shake.until > now
    assert mode.vignette.level(mode.vignette.started_at + VIGNETTE_MS) == 0
    assert mode.shake.offset(mode.shake.until + SHAKE_MS) == (0, 0)


def test_solar_heat_on_the_hull_raises_one_refreshing_alert_and_no_shake(mode):
    mode.player.ship.shield_up = False
    place(mode, (mode.map_center_x + 900, mode.map_center_y))
    mode.spend_turns(3)
    alerts = mode.banner.alerts
    alerts.update(pygame.time.get_ticks())
    assert alerts.current.key == "heat" and not alerts.queue
    assert mode.events.texts().count(mode.events.latest()) == 1 and len(mode.events.texts()) == 1
    assert mode.shake.until == 0


def test_the_hud_draws_banner_ping_strip_log_and_strip(mode):
    from modes.star_system_mode.vessels import Drone

    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    place(mode, planet(mode, "Etheora").beacon_points()[0])  # in a corridor, for the action strip
    x, y = mode.ship_center()
    drone = Drone((x + 4000, y), mode)
    mode.add_vessel(drone)
    mode.vessel_ping(drone)
    assert mode.ping_warning() is not None
    mode.notify("PINGED - DOMINION HAS YOUR POSITION", 1)
    mode.draw(screen)
    mode.spend_turns(5)  # the ping lands
    mode.draw(screen)
    assert mode.ping_strip.outcome is not None
