"""What's left of a destroyed privateer: it breaks up after a while and can be salvaged once."""
import pygame

from util.sprite_animation import TINT_LEVELS
from util.turns import SPEED
from world.factions import faction_name

WRECK_TURNS = 40
APPROACH_RADIUS = 64  # fly this close and press E to scan it and salvage
# Salvage by class: (fewest goods, most goods, fewest credits, most credits).
SALVAGE = {"cutter": (2, 4, 40, 80), "raider": (3, 6, 80, 150), "gunship": (5, 10, 150, 300)}
FALLBACK_GOOD = "Ship Parts"
DEBRIS = ((-22, -14, "*"), (20, -18, "'"), (-16, 20, "."), (24, 16, ":"), (2, -28, "."))


def roll_salvage(kind, sponsor_goods, rng):
    """Goods from the sponsor's worlds and some credits, more for bigger ships."""
    low, high, least, most = SALVAGE[kind]
    good = rng.choice(sorted(sponsor_goods)) if sponsor_goods else FALLBACK_GOOD
    return {good: rng.randint(low, high)}, rng.randint(least, most)


class Wreck:
    speed = SPEED
    obj_type = "Wreck"
    planet_guild = None

    def __init__(self, privateer, cargo, credits, on_gone):
        self.id = None  # debris: never charted, no market
        self.name = f"{faction_name(privateer.sponsor)} {privateer.kind} wreck"
        self.kind = privateer.kind
        self.sponsor = privateer.sponsor
        self.position = privateer.position
        self.heading = privateer.heading
        self.source = privateer
        self.cargo = dict(cargo)
        self.credits = credits
        self.turns_left = WRECK_TURNS
        self.on_gone = on_gone

    def take_turn(self):
        self.turns_left -= 1
        if self.turns_left <= 0:
            self.on_gone(self)

    def empty(self):
        return not self.cargo and not self.credits

    def approach_rects(self):
        x, y = self.position
        return [pygame.Rect(x - APPROACH_RADIUS, y - APPROACH_RADIUS, APPROACH_RADIUS * 2, APPROACH_RADIUS * 2)]

    def draw(self, screen, centre, font):
        sprite = self.source.sprite()
        sprite.current_frame = 0  # engines out
        frame = sprite.get_frame(self.heading, TINT_LEVELS - 1)
        frame = frame.copy()
        frame.set_alpha(170)
        screen.blit(frame, frame.get_rect(center=centre))
        for dx, dy, char in DEBRIS:
            glyph = font.render(char, True, (233, 159, 16))
            screen.blit(glyph, glyph.get_rect(center=(centre[0] + dx, centre[1] + dy)))
