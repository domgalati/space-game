"""The run: the player, the world, and whichever mode is on screen.

Modes report where the player wants to go as a transition (modes.transitions); Game builds
or resumes the next mode. Flight modes are kept per system, so a system's ships, wrecks and
sensor state are still there when you come back to it.
"""
from modes.planetary_mode.planetary_mode import PlanetaryMode
from modes.star_system_mode.star_system_mode import StarSystemMode
from modes.transitions import Depart, Land


class Game:
    def __init__(self, player, world_state, system_id):
        self.player = player
        self.world_state = world_state
        self.flights = {}  # system id -> StarSystemMode
        self.mode = self.flight(system_id)
        self.handlers = {Land: self.land, Depart: self.depart}

    def flight(self, system_id):
        """The flight mode for `system_id`, built on first visit."""
        if system_id not in self.flights:
            self.flights[system_id] = StarSystemMode(self.player, system_id, self.world_state)
        return self.flights[system_id]

    def update(self, events, dt):
        """One frame: `dt` seconds have passed. Switches mode if the current one asks to."""
        transition = self.mode.update(events, dt)
        if transition is not None:
            self.handlers[type(transition)](transition)

    def draw(self, screen):
        self.mode.draw(screen)

    def land(self, transition):
        self.mode = PlanetaryMode(transition.body, self.player, self.world_state)

    def depart(self, transition):
        flight = self.flight(self.player.location.system)
        flight.undock(transition.body)
        self.mode = flight
