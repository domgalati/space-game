"""What a mode asks for when the player leaves it.

A mode's ``update(events, dt)`` returns one of these, or None to stay. ``game.Game`` acts on
it, so modes never build each other. New ways to move (a wormhole jump to another system,
a ground fight) are a new transition here plus a handler in ``Game``.
"""
from dataclasses import dataclass


@dataclass
class Land:
    """Dock at a body in this system and go ashore."""
    body: object


@dataclass
class Depart:
    """Leave the body you're docked at and fly again."""
    body: object
