"""What just happened in the world, for whoever wants to know: quests, stats, achievements.

Game code announces things as they happen, ``events.emit("docked", body="sol/terramonta")``,
and listeners subscribe by name, ``events.on("docked", listener)``, or to everything with
ANY. A listener gets one Event and must not assume who else is listening.

Announced so far (details in brackets):
    docked, departed            [body, system]
    bought, sold                [good, quantity, credits, place]
    privateer_destroyed         [sponsor, kind, system]
    salvaged                    [wreck, goods, credits]
    towed                       [fee, system]
    talked                      [npc]
    dialogue: <<event name>>    [npc], announced under the name the script gives
"""
from collections import defaultdict
from dataclasses import dataclass, field

ANY = "*"


@dataclass
class Event:
    name: str
    details: dict = field(default_factory=dict)


class Events:
    def __init__(self):
        self._listeners = defaultdict(list)

    def on(self, name, listener):
        """Call `listener(event)` for each `name` event (ANY for all). Returns a function that unsubscribes."""
        self._listeners[name].append(listener)
        return lambda: self._listeners[name].remove(listener)

    def emit(self, name, **details):
        event = Event(name, details)
        # Copies, so a listener can unsubscribe (or subscribe others) while being called.
        for listener in [*self._listeners[name], *self._listeners[ANY]]:
            listener(event)
        return event
