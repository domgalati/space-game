import os

import pygame

from entities.planet import Planet
from modes.planetary_mode.terminal import Terminal
from util.config import SCREEN_WIDTH, SCREEN_HEIGHT, resolve_game_path
from util.economy.economy import load_market_data
from util.economy.news import render_news

from .scan_art import BRIGHT, DIM, MID, caption_for, render_scan_art

HELP_TEXT = "Available commands:\n help\n scan\n dock\n hail\n ping <planet>\n news\n exit"
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


def market_lines(target):
    goods = load_market_data().get(target.name, {}).get("goods", {})
    if not goods:
        return ["Market: no data"]
    ranked = sorted(goods.items(), key=lambda item: item[1]["currentPrice"], reverse=True)
    lines = ["Market (highest prices):"]
    for good, info in ranked[:MAX_MARKET_LINES]:
        lines.append(f"  {good}: ${info['currentPrice']:.0f}")
    return lines


def scan_readout(target):
    if target is None:
        return ["SHIP COMPUTER", NO_TARGET, "Type 'help' for commands."]
    lines = [f"SCAN RESULT: {target.name}"]
    if isinstance(target, Planet):
        lines.append(f"Class: Planet ({target.planet_type})")
        lines.append(f"Guild: {target.planet_guild.capitalize()}")
        landing = "CLEARED" if has_landing_map(target) else "NO DOCKING FACILITY"
        lines.append(f"Landing: {landing}")
        lines.extend(market_lines(target))
    else:
        lines.append(f"Class: {target.obj_type}")
        if target.planet_guild:
            lines.append(f"Guild: {target.planet_guild.capitalize()}")
        lines.append("Landing: BAYS OPEN" if has_landing_map(target) else "Landing: DOCKING BAYS CLOSED")
        lines.extend(market_lines(target))
    lines.append("Type 'help' for commands.")
    return lines


def hail_response(target):
    if not isinstance(target, Planet):
        if has_landing_map(target):
            return (f'{target.name} Dockmaster: "Welcome in, hauler. Bays are open and customs '
                    f'is light today. Send \'dock\' when ready."')
        return f'{target.name}: "Docking bays are closed to independent haulers for now."'
    if has_landing_map(target):
        guild = target.planet_guild.capitalize()
        return f'{target.name} Traffic Control: "Vessel acknowledged. {guild} lanes are open. Send \'dock\' when ready."'
    return f"Static. Nobody on {target.name} answers your hail."


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
        self.background = pygame.image.load(
            resolve_game_path("space/assets/img/objects/terminal_screen.png")
        ).convert_alpha()
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

    def activate(self):
        super().activate()
        for line in scan_readout(self.target):
            self.say(line)
        nav = self.star_system_mode.nav
        if isinstance(self.target, Planet) and not nav.is_charted(self.target):
            nav.chart(self.target.name)
            self.say(f"Nav chart updated: {self.target.name}.")

    def deactivate(self):
        self.active = False
        self.star_system_mode.close_scan_terminal()

    def update(self, dt):
        super().update(dt)
        self.art_time += dt

    def process_input(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and not self.pager:
            self.deactivate()
            return
        super().process_input(event)

    def argument_candidates(self, verb):
        if verb == "ping" and self.star_system_mode is not None:
            system = getattr(self.star_system_mode, "selected_system", None)
            if system is not None:
                return [planet.name for planet in system.planets]
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
        elif verb == "news":
            self.show(render_news(load_market_data()))
        elif verb == "exit":
            self.deactivate()
        elif verb in ("scan", "hail", "dock") and self.target is None:
            self.say(NO_TARGET)
        elif verb == "scan":
            self.art_time = 0.0
            for line in scan_readout(self.target):
                self.say(line)
        elif verb == "hail":
            self.say(hail_response(self.target))
        elif verb == "dock":
            if has_landing_map(self.target):
                self.star_system_mode.request_landing(self.target)
            else:
                self.say(f"Docking denied: {self.target.name} has no docking facility.")
        elif verb:
            self.say("Unknown command. Type 'help' for available commands.")

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
