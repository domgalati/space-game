"""The run: the player, the world, and whichever mode is on screen.

Modes report where the player wants to go as a transition (modes.transitions); Game builds
or resumes the next mode. Flight modes are kept per system, so a system's ships, wrecks and
sensor state are still there when you come back to it.
"""
from modes.planetary_mode.planetary_mode import PlanetaryMode
from modes.star_system_mode.star_system_mode import StarSystemMode
from modes.transitions import Depart, Land
from world.save import load_game, save_game


class Game:
    def __init__(self, player, world_state, system_id=None):
        """A run in `system_id`, or wherever `player.location` says, which for a loaded save
        may be ashore."""
        self.player = player
        self.world_state = world_state
        self.events = world_state.events
        self.save_to = None  # save file path; when set, docking autosaves there
        self.flights = {}  # system id -> StarSystemMode
        self.mode = self.flight(system_id or player.location.system)
        self.handlers = {Land: self.land, Depart: self.depart}
        if player.location.body:
            self.mode = PlanetaryMode(self.mode.selected_system.body(player.location.body), player, world_state)

    @classmethod
    def load(cls, path=None):
        """The run in a save file. Raises world.save.SaveError if it can't be read."""
        game = cls(*load_game(path))
        game.save_to = path
        return game

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

    def save(self, path=None):
        """Write the run to `path`, or the save file it was loaded from or told to use."""
        written = save_game(self.player, self.world_state, path or self.save_to)
        self.mode.notice("Game saved.")
        return written

    def land(self, transition):
        body = transition.body
        self.mode = PlanetaryMode(body, self.player, self.world_state)
        self.events.emit("docked", body=body.id, system=self.player.location.system)
        if self.save_to:
            self.save()

    def depart(self, transition):
        flight = self.flight(self.player.location.system)
        flight.undock(transition.body)
        self.mode = flight
        self.events.emit("departed", body=transition.body.id, system=self.player.location.system)
