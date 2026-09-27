import os

import pygame
import yaml

from entities.planet import Planet
from modes.planetary_mode.terminal import Terminal
from util.config import SCREEN_WIDTH, SCREEN_HEIGHT, resolve_game_path

HELP_TEXT = "Available commands:\n help\n scan\n dock\n hail\n ping <planet>\n exit"
NO_TARGET = "No target in scan range."
MAX_MARKET_LINES = 3


def has_landing_map(target):
    if not isinstance(target, Planet):
        return False
    return os.path.exists(resolve_game_path(f"space/assets/maps/{target.name}.tmx"))


def market_lines(target):
    with open(resolve_game_path("space/src/util/economy/economy_generated.yaml"), "r") as file:
        data = yaml.safe_load(file) or {}
    goods = data.get(target.name, {}).get("goods", {})
    if not goods:
        return ["Market: no data"]
    ranked = sorted(goods.items(), key=lambda item: item[1]["currentPrice"], reverse=True)
    lines = ["Market (highest prices):"]
    for good, info in ranked[:MAX_MARKET_LINES]:
        lines.append(f"  {good}: ${info['currentPrice']:g}")
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
        lines.append("Landing: DOCKING BAYS CLOSED")
    lines.append("Type 'help' for commands.")
    return lines


def hail_response(target):
    if not isinstance(target, Planet):
        return f'{target.name}: "Docking bays are closed to independent haulers for now."'
    if has_landing_map(target):
        guild = target.planet_guild.capitalize()
        return f'{target.name} Traffic Control: "Vessel acknowledged. {guild} lanes are open. Send \'dock\' when ready."'
    return f"Static. Nobody on {target.name} answers your hail."


class ScanTerminal(Terminal):
    """Ship-computer terminal for star system mode; target is the body in scan range, if any."""

    def __init__(self, target, star_system_mode):
        super().__init__(terminal_type="scan", planetary_mode=None, planet_name=target)
        self.target = target
        self.star_system_mode = star_system_mode
        self.background = pygame.image.load(
            resolve_game_path("space/assets/img/objects/terminal_screen.png")
        ).convert_alpha()
        self.surface = pygame.Surface(self.background.get_size(), pygame.SRCALPHA)

    def activate(self):
        super().activate()
        self.output_buffer.extend(scan_readout(self.target))
        nav = self.star_system_mode.nav
        if isinstance(self.target, Planet) and not nav.is_charted(self.target):
            nav.chart(self.target.name)
            self.output_buffer.append(f"Nav chart updated: {self.target.name}.")

    def deactivate(self):
        self.active = False
        self.star_system_mode.close_scan_terminal()

    def process_input(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.deactivate()
            return
        super().process_input(event)

    def execute_command(self, command):
        command = command.strip().lower()
        self.output_buffer.append(f"> {command}")
        verb, _, argument = command.partition(" ")

        if verb == "help":
            self.output_buffer.append(HELP_TEXT)
        elif verb == "ping":
            for line in self.star_system_mode.ping(argument.strip()):
                self.output_buffer.extend(self.wrap_text(line, 80))
        elif verb == "exit":
            self.deactivate()
        elif verb in ("scan", "hail", "dock") and self.target is None:
            self.output_buffer.append(NO_TARGET)
        elif verb == "scan":
            self.output_buffer.extend(scan_readout(self.target))
        elif verb == "hail":
            self.output_buffer.extend(self.wrap_text(hail_response(self.target), 80))
        elif verb == "dock":
            if has_landing_map(self.target):
                self.star_system_mode.request_landing(self.target)
            else:
                self.output_buffer.append(f"Docking denied: {self.target.name} has no docking facility.")
        elif verb:
            self.output_buffer.append("Unknown command. Type 'help' for available commands.")

    def display(self, screen):
        if not self.active:
            return
        self.surface.fill((0, 0, 0, 0))
        self.surface.blit(self.background, (0, 0))
        super().display(self.surface)
        offset = (
            (SCREEN_WIDTH - self.surface.get_width()) // 2,
            (SCREEN_HEIGHT - self.surface.get_height()) // 2,
        )
        screen.blit(self.surface, offset)
