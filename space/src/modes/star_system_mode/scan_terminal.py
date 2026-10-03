import math
import os

import pygame

from entities.planet import Planet
from modes.planetary_mode.terminal import Terminal, bezel_path
from util.config import SCREEN_WIDTH, SCREEN_HEIGHT, resolve_game_path
from util.economy.news import render_news
from world.disposition import disposition_word
from world.factions import FACTIONS, faction_name, flies_assembly_colours, licenses_raiders, waves_by

from .scan_art import BRIGHT, DIM, MID, caption_for, render_scan_art

HELP_TEXT = "Available commands:\n help\n scan\n dock\n hail\n ping (area: 1 turn, gives you away)\n ping <name>\n shield on|off|status\n news\n exit"
NO_TARGET = "No target in scan range."
MAX_MARKET_LINES = 3

# Left text column must stay clear of the imaging panel (TeleSys 16 is 8px per char).
TEXT_WRAP = 52
ART_PANEL = pygame.Rect(528, 96, 248, 244)
ART_FONT_SIZE = 12
ROW_REVEAL_SECONDS = 0.05
SWEEP_PERIOD_SECONDS = 5.0
SWEEP_DURATION_SECONDS = 1.6


def has_landing_map(target):
    return os.path.exists(resolve_game_path(f"space/assets/maps/{target.name}.tmx"))


def market_lines(target, markets):
    goods = (markets.get(target.name) or {}).get("goods", {})
    if not goods:
        return ["Market: no data"]
    ranked = sorted(goods.items(), key=lambda item: item[1]["currentPrice"], reverse=True)
    lines = ["Market (highest prices):"]
    for good, info in ranked[:MAX_MARKET_LINES]:
        lines.append(f"  {good}: ${info['currentPrice']:.0f}")
    return lines


def faction_lines(faction, reputation):
    """Who holds a body, how they see you, and whether they license raiders."""
    if not faction:
        return []
    lines = [f"Faction: {faction_name(faction)}"]
    if reputation is not None:
        standing = reputation.get(faction, 0)
        lines.append(f"Your standing: {disposition_word(standing)} ({standing:+d})")
    if licenses_raiders(faction):
        lines.append("Licenses privateers against Assembly shipping.")
    return lines


def scan_readout(target, markets=None, reputation=None):
    if target is None:
        return ["SHIP COMPUTER", NO_TARGET, "Type 'help' for commands."]
    markets = markets or {}
    lines = [f"SCAN RESULT: {target.name}"]
    if isinstance(target, Planet):
        lines.append(f"Class: Planet ({target.planet_type})")
        lines.extend(faction_lines(target.planet_guild, reputation))
        landing = "CLEARED" if has_landing_map(target) else "NO DOCKING FACILITY"
        lines.append(f"Landing: {landing}")
        lines.extend(market_lines(target, markets))
    else:
        lines.append(f"Class: {target.obj_type}")
        lines.extend(faction_lines(target.planet_guild, reputation))
        lines.append("Landing: BAYS OPEN" if has_landing_map(target) else "Landing: DOCKING BAYS CLOSED")
        lines.extend(market_lines(target, markets))
    lines.append("Type 'help' for commands.")
    return lines


GREETINGS = {
    "assembly": "Vessel acknowledged. Assembly lanes are open.",
    "dominion": "Transponder logged. Keep to your assigned lane.",
    "cohort": "Welcome, traveller. The Commons keeps an open sky.",
    "caravaneers": "Ho, hauler. The Moot trades fair with those who trade fair.",
}


def hail_response(target, reputation=None):
    reputation = reputation or {}
    faction = target.planet_guild
    if not isinstance(target, Planet):
        if has_landing_map(target):
            return (f'{target.name} Dockmaster: "Welcome in, hauler. Bays are open and customs '
                    f'is light today. Send \'dock\' when ready."')
        return f'{target.name}: "Docking bays are closed to independent haulers for now."'
    voice = FACTIONS.get(faction, {}).get("voice", "Traffic Control")
    greeting = GREETINGS.get(faction, "Vessel acknowledged.")
    berth = "Send 'dock' when ready." if has_landing_map(target) else "We've no berth for independents."
    words = f"{greeting} {berth}"
    if licenses_raiders(faction):
        if waves_by(reputation, faction):
            words += " Our privateers have your registry. They'll let you pass."
        elif flies_assembly_colours(reputation):
            words += " You fly Assembly colours. Our privateers have noticed."
    return f'{target.name} {voice}: "{words}"'


def _crt_scanlines(size):
    overlay = pygame.Surface(size, pygame.SRCALPHA)
    for y in range(0, size[1], 3):
        pygame.draw.line(overlay, (0, 0, 0, 70), (0, y), (size[0], y))
    return overlay


class ScanTerminal(Terminal):
    """Ship-computer terminal for star system mode; target is the body in scan range, if any."""

    columns = TEXT_WRAP

    def __init__(self, target, star_system_mode):
        super().__init__(terminal_type="scan", planetary_mode=None, planet_name=target)
        self.target = target
        self.star_system_mode = star_system_mode
        self.background = pygame.image.load(bezel_path("scan")).convert_alpha()
        self.surface = pygame.Surface(self.background.get_size(), pygame.SRCALPHA)

        art_font = pygame.font.Font(resolve_game_path("space/assets/fonts/TeleSys.ttf"), ART_FONT_SIZE)
        self.art_font = art_font
        self.art_line_height = art_font.get_linesize()
        self.art_surface = render_scan_art(target, art_font)
        self.art_time = 0.0
        self.scanlines = _crt_scanlines(ART_PANEL.size)
        self.sweep = pygame.Surface((ART_PANEL.width - 2, 2), pygame.SRCALPHA)
        self.sweep.fill((*BRIGHT, 45))

    def say(self, text):
        for line in text.split("\n"):
            self.output_buffer.extend(self.wrap_text(line, TEXT_WRAP))

    def markets(self):
        world = getattr(self.star_system_mode, "world_state", None)
        return world.markets_data() if world is not None else {}

    def observe_market(self):
        """A scan doubles as a news check: the target's market and stories reach the wire."""
        feed = getattr(self.star_system_mode, "news_feed", None)
        if self.target is None or feed is None:
            return
        goods = (self.markets().get(self.target.name) or {}).get("goods") or {}
        if goods:
            feed.observe(self.target.name, goods)
            self.say("Market data synced to the news wire.")

    def activate(self):
        super().activate()
        for line in scan_readout(self.target, self.markets(), self.star_system_mode.player.reputation):
            self.say(line)
        self.observe_market()
        nav = self.star_system_mode.nav
        if self.target is not None and getattr(self.target, "name", None) and not nav.is_charted(self.target):
            nav.chart(self.target.name)
            self.say(f"Nav chart updated: {self.target.name}.")

    def deactivate(self):
        self.active = False
        self.star_system_mode.close_scan_terminal()

    def update(self, dt):
        super().update(dt)
        self.art_time += dt

    def process_input(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and not self.pager and not self.boot:
            self.deactivate()
            return
        super().process_input(event)

    def argument_candidates(self, verb):
        if verb == "ping" and self.star_system_mode is not None:
            system = getattr(self.star_system_mode, "selected_system", None)
            if system is not None:
                names = [planet.name for planet in system.planets]
                names.extend(obj.name for obj in system.objects)
                return names
        return super().argument_candidates(verb)

    def show_matches(self, matches):
        self.say("  " + "  ".join(matches))

    def execute_command(self, command):
        command = command.strip().lower()
        self.output_buffer.append(f"> {command}")
        verb, _, argument = command.partition(" ")

        if verb == "help":
            self.say(HELP_TEXT)
        elif verb == "ping":
            for line in self.star_system_mode.ping(argument.strip()):
                self.say(line)
        elif verb == "shield":
            self.say(self.shield_command(argument.strip()))
        elif verb == "news":
            self.show(render_news(getattr(self.star_system_mode, "news_feed", None), self.markets()))
        elif verb == "exit":
            self.deactivate()
        elif verb in ("scan", "hail", "dock") and self.target is None:
            self.say(NO_TARGET)
        elif verb == "scan":
            self.art_time = 0.0
            for line in scan_readout(self.target, self.markets(), self.star_system_mode.player.reputation):
                self.say(line)
            self.observe_market()
        elif verb == "hail":
            self.say(hail_response(self.target, self.star_system_mode.player.reputation))
        elif verb == "dock":
            if has_landing_map(self.target):
                self.star_system_mode.request_landing(self.target)
            else:
                self.say(f"Docking denied: {self.target.name} has no docking facility.")
        elif verb:
            self.say("Unknown command. Type 'help' for available commands.")

    def shield_command(self, argument):
        ship = self.star_system_mode.player.ship
        if argument in ("on", "up"):
            self.star_system_mode.set_shield(True)
        elif argument in ("off", "down"):
            self.star_system_mode.set_shield(False)
        elif argument not in ("", "status"):
            return "Usage: shield on|off|status"
        state = "UP" if ship.shield_up else "DOWN"
        return f"Shield {state}: {int(ship.shield)}/{ship.max_shield}. Hull {math.ceil(ship.hull)}/{ship.max_hull}."

    def draw_art_panel(self, surface):
        if self.art_surface is None:
            return
        panel = ART_PANEL
        pygame.draw.rect(surface, DIM, panel, 1)
        for x, y in (panel.topleft, panel.topright, panel.bottomleft, panel.bottomright):
            pygame.draw.rect(surface, BRIGHT, (x - 2, y - 2, 4, 4))

        title = self.art_font.render(f"IMAGING // {self.target.name.upper()}", True, MID)
        surface.blit(title, (panel.x + 8, panel.y + 6))
        divider_y = panel.y + 6 + title.get_height() + 4
        pygame.draw.line(surface, DIM, (panel.x + 6, divider_y), (panel.right - 7, divider_y))

        art_w, art_h = self.art_surface.get_size()
        art_x = panel.x + (panel.width - art_w) // 2
        art_y = divider_y + 8
        rows_total = art_h // self.art_line_height
        rows_shown = min(rows_total, int(self.art_time / ROW_REVEAL_SECONDS))
        if rows_shown:
            surface.blit(self.art_surface, (art_x, art_y), (0, 0, art_w, rows_shown * self.art_line_height))

        if rows_shown < rows_total:
            bar_y = art_y + rows_shown * self.art_line_height
            pygame.draw.line(surface, BRIGHT, (panel.x + 1, bar_y), (panel.right - 2, bar_y), 2)
        else:
            phase = (self.art_time - rows_total * ROW_REVEAL_SECONDS) % SWEEP_PERIOD_SECONDS
            if phase < SWEEP_DURATION_SECONDS:
                surface.blit(self.sweep, (panel.x + 1, art_y + int(art_h * phase / SWEEP_DURATION_SECONDS)))

        caption = self.art_font.render(caption_for(self.target), True, DIM)
        surface.blit(caption, (panel.x + 8, panel.bottom - caption.get_height() - 6))
        surface.blit(self.scanlines, panel.topleft)

    def display(self, screen):
        if not self.active:
            return
        self.surface.fill((0, 0, 0, 0))
        self.surface.blit(self.background, (0, 0))
        super().display(self.surface)
        self.draw_art_panel(self.surface)
        offset = (
            (SCREEN_WIDTH - self.surface.get_width()) // 2,
            (SCREEN_HEIGHT - self.surface.get_height()) // 2,
        )
        screen.blit(self.surface, offset)
