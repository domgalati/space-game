import pygame
from util.config import SCREEN_HEIGHT, resolve_game_path

# Sidebar palette — dark panel with soft labels, vivid bars
_BG = (6, 8, 12)
_PANEL = (14, 16, 22)
_BORDER = (52, 60, 74)
_BORDER_SOFT = (36, 42, 52)
_LABEL = (148, 158, 172)
_VALUE = (232, 236, 242)
_CURRENCY = (230, 196, 96)
_HEALTH = (78, 196, 108)
_HEALTH_BG = (28, 40, 32)
_ENERGY = (80, 176, 228)
_ENERGY_BG = (26, 38, 52)
_FUEL = (232, 150, 64)
_FUEL_BG = (52, 36, 22)
_CARGO = (176, 144, 220)
_CARGO_BG = (40, 32, 52)


def _money_icon(scale=2):
    """Pixel money stack: three offset bills + a coin (no asset file)."""
    # O outline | F face | D dark bill | G band | C coin | H coin highlight | S shadow
    pixels = [
        "..................",
        "....OOOOOOOO......",
        "...OFFGGGGFFO.....",
        "...OFFFFFFFFO.....",
        "..OOFFFFFFFFOO....",
        ".ODDGGGGGGDDDO....",
        ".ODDDDDDDDDDDO....",
        "OOFFFFFFFFFFFFOO..",
        "OFFGGGGGGGGGGFFO..",
        "OFFFFFFFFFFFFFFO..",
        "OFFFFFFFFFFFFFFO..",
        "OOOOOOOOOOOOOOOO..",
        ".......SSSS.......",
        "......OCCCCO......",
        ".....OCCHHCCO.....",
        ".....OCH$$HCO.....",
        ".....OCCHHCCO.....",
        "......OCCCCO......",
        ".......OOOO.......",
    ]
    colors = {
        "O": (40, 32, 12),
        "F": (214, 186, 78),
        "D": (168, 140, 48),
        "G": (64, 120, 60),
        "C": (236, 196, 72),
        "H": (252, 232, 150),
        "S": (28, 22, 10),
        "$": (40, 32, 12),
    }
    h, w = len(pixels), len(pixels[0])
    surf = pygame.Surface((w * scale, h * scale), pygame.SRCALPHA)
    for y, row in enumerate(pixels):
        for x, ch in enumerate(row):
            if ch in colors:
                surf.fill(colors[ch], (x * scale, y * scale, scale, scale))
    return surf


class UI_Planetary:
    def __init__(self):
        self.sidebar_width = 200
        self.sidebar_surface = pygame.Surface((self.sidebar_width, SCREEN_HEIGHT - 200))
        # Cairopixel: crisp technical pixel type for HUD stats.
        # https://www.1001fonts.com/cairopixel-font.html (SIL OFL)
        font_path = resolve_game_path("space/assets/fonts/Cairopixel.ttf")
        self.label_font = pygame.font.Font(font_path, 16)
        self.value_font = pygame.font.Font(font_path, 20)
        self.money_icon = _money_icon(scale=2)
        self.player_stats = None
        self.max_health = 100
        self.max_energy = 100

    def update_player_stats(self, player):
        self.max_health = max(getattr(player, "max_health", 100), player.health, 1)
        self.max_energy = max(getattr(player, "max_energy", 100), player.energy, 1)
        ship = player.ship
        self.player_stats = {
            "currency": player.currency,
            "health": player.health,
            "energy": player.energy,
            "fuel": ship.fuel,
            "max_fuel": ship.max_fuel,
            "cargo": ship.cargo.get_total_quantity(),
            "cargo_capacity": ship.cargo.capacity,
        }

    def _draw_bar(self, x, y, width, height, ratio, fill, empty):
        ratio = max(0.0, min(1.0, ratio))
        pygame.draw.rect(self.sidebar_surface, _BORDER, (x, y, width, height), border_radius=2)
        inner = pygame.Rect(x + 1, y + 1, width - 2, height - 2)
        pygame.draw.rect(self.sidebar_surface, empty, inner, border_radius=1)
        fill_w = int(inner.width * ratio)
        if fill_w > 0:
            fill_rect = pygame.Rect(inner.x, inner.y, fill_w, inner.height)
            pygame.draw.rect(self.sidebar_surface, fill, fill_rect, border_radius=1)
            if fill_w > 2 and inner.height > 3:
                highlight = tuple(min(255, c + 40) for c in fill)
                pygame.draw.rect(
                    self.sidebar_surface,
                    highlight,
                    (inner.x + 1, inner.y + 1, max(1, fill_w - 2), 1),
                )

    def _draw_stat_block(self, y, label, value, maximum, fill, empty):
        pad = 14
        label_surf = self.label_font.render(label.upper(), False, _LABEL)
        value_surf = self.label_font.render(f"{int(value)}/{int(maximum)}", False, _VALUE)
        self.sidebar_surface.blit(label_surf, (pad, y))
        self.sidebar_surface.blit(
            value_surf, (self.sidebar_width - pad - value_surf.get_width(), y)
        )
        bar_y = y + label_surf.get_height() + 5
        self._draw_bar(
            pad, bar_y, self.sidebar_width - pad * 2, 11, value / maximum, fill, empty
        )
        return bar_y + 11 + 18

    def draw_sidebar(self):
        self.sidebar_surface.fill(_BG)
        panel = pygame.Rect(8, 12, self.sidebar_width - 16, 300)
        pygame.draw.rect(self.sidebar_surface, _PANEL, panel, border_radius=4)
        pygame.draw.rect(self.sidebar_surface, _BORDER_SOFT, panel, width=1, border_radius=4)

        if not self.player_stats:
            return

        pad = 14
        y = 26

        icon = self.money_icon
        self.sidebar_surface.blit(icon, (pad, y))
        amount = self.value_font.render(f"${self.player_stats['currency']}", False, _CURRENCY)
        amount_x = pad + icon.get_width() + 8
        amount_y = y + (icon.get_height() - amount.get_height()) // 2
        self.sidebar_surface.blit(amount, (amount_x, amount_y))

        y = max(y + icon.get_height(), amount_y + amount.get_height()) + 12
        pygame.draw.line(
            self.sidebar_surface,
            _BORDER_SOFT,
            (pad, y),
            (self.sidebar_width - pad, y),
            1,
        )
        y += 14

        y = self._draw_stat_block(
            y,
            "Health",
            self.player_stats["health"],
            self.max_health,
            _HEALTH,
            _HEALTH_BG,
        )
        y = self._draw_stat_block(
            y,
            "Energy",
            self.player_stats["energy"],
            self.max_energy,
            _ENERGY,
            _ENERGY_BG,
        )
        y = self._draw_stat_block(
            y,
            "Fuel",
            self.player_stats["fuel"],
            self.player_stats["max_fuel"],
            _FUEL,
            _FUEL_BG,
        )
        self._draw_stat_block(
            y,
            "Cargo",
            self.player_stats["cargo"],
            self.player_stats["cargo_capacity"],
            _CARGO,
            _CARGO_BG,
        )
