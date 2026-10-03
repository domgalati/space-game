"""Connects Yarn scripts to game state: variables, functions, and commands.

Variables named $this_* belong to the NPC being spoken to; every other $variable is a
global story flag. ``visited()`` counts are per NPC as well. Unset variables read as false.

Functions (use in {braces} or conditions):
    visited("Node") visited_count("Node") dice(sides) random() random_range(low, high)
    has_item("Item", n) item_count("Item") currency() rep("faction") mood() disposition()
    npc_name() npc_first() npc_last() npc_job() npc_guild() npc_species()
    npc_has_hobby("Hobby") npc_hobby() location() job_line() goods_opinion() rumor()

Commands:
    <<give "Item" n>> <<take "Item" n>> <<pay n>> <<charge n>> <<rep faction delta>>
    <<mood delta>> (disposition, clamped to -100..100) <<wait n>> (ignored)
"""
import random

from entities.npcs.species import species_name
from world.disposition import clamp_mood, disposition_word

from . import topics
from .errors import DialogueError

NPC_VAR_PREFIX = "this_"


def _count(n):
    return max(0, int(n))


class GameContext:
    def __init__(self, npc, npc_state, player, world_state, economy=None, location=None, rng=None):
        self.npc = npc
        self.npc_state = npc_state
        self.player = player
        self.world_state = world_state
        self.economy = economy
        self.location = location or (economy.planet_name if economy else None)
        self.rng = rng or random.Random()
        self.changes = []  # human-readable notes for the exit summary
        self._functions = {
            "visited": lambda node: self.npc_state["visited"].get(node, 0) > 0,
            "visited_count": lambda node: self.npc_state["visited"].get(node, 0),
            "dice": lambda sides: self.rng.randint(1, int(sides)),
            "random": lambda: self.rng.random(),
            "random_range": lambda low, high: self.rng.randint(int(low), int(high)),
            "has_item": self._has_item,
            "item_count": lambda item: self._inventory().items.get(item, 0),
            "currency": lambda: self.player.currency,
            "rep": lambda faction: self.player.reputation.get(str(faction).lower(), 0),
            "mood": lambda: self.npc_state["mood"],
            "disposition": lambda: disposition_word(self.npc_state["mood"]),
            "npc_name": lambda: f"{npc.firstname} {npc.lastname}",
            "npc_first": lambda: npc.firstname,
            "npc_last": lambda: npc.lastname,
            "npc_job": lambda: npc.job_title or "",
            "npc_guild": lambda: npc.guild or "",
            "npc_species": lambda: species_name(getattr(npc, "species", "human")),
            "npc_has_hobby": self._has_hobby,
            "npc_hobby": lambda: self.rng.choice(npc.hobbies) if npc.hobbies else "keeping busy",
            "location": lambda: self.location or "",
            "job_line": lambda: topics.job_line(npc, self.rng),
            "goods_opinion": lambda: topics.goods_opinion(npc, economy, self.rng) or "Can't complain. Can't afford to.",
            "rumor": lambda: topics.market_rumor(
                self.location, self.rng, self.economy.data if self.economy else None
            ),
        }
        self._commands = {
            "give": self._give,
            "take": self._take,
            "pay": self._pay,
            "charge": self._charge,
            "rep": self._rep,
            "mood": self._mood,
            "wait": lambda *args: None,
        }

    def _inventory(self):
        return self.player.inventory

    # Runner interface

    def _scope(self, name):
        if name.startswith(NPC_VAR_PREFIX):
            return self.npc_state["vars"]
        return self.world_state.globals

    def get_var(self, name):
        return self._scope(name).get(name, False)

    def set_var(self, name, value):
        self._scope(name)[name] = value

    def has_var(self, name):
        return name in self._scope(name)

    def call(self, name, args):
        function = self._functions.get(name)
        if function is None:
            raise DialogueError(f"Unknown function {name}()")
        return function(*args)

    def run_command(self, name, args):
        command = self._commands.get(name)
        if command is None:
            raise DialogueError(f"Unknown command <<{name}>>")
        command(*args)

    def mark_visited(self, node):
        visited = self.npc_state["visited"]
        visited[node] = visited.get(node, 0) + 1

    # Functions

    def _has_item(self, item, quantity=1):
        return self._inventory().items.get(item, 0) >= _count(quantity)

    def _has_hobby(self, hobby):
        wanted = str(hobby).lower()
        return any(h.lower() == wanted for h in self.npc.hobbies)

    # Commands

    def _give(self, item, quantity=1):
        quantity = _count(quantity)
        if self._inventory().add_item(item, quantity):
            self.changes.append(f"Received {quantity} {item}.")
        else:
            self.changes.append(f"No room for {quantity} {item}; you left it behind.")

    def _take(self, item, quantity=1):
        quantity = _count(quantity)
        held = self._inventory().items.get(item, 0)
        taken = min(held, quantity)
        if taken:
            self._inventory().remove_item(item, taken)
            self.changes.append(f"Handed over {taken} {item}.")

    def _pay(self, amount):
        amount = _count(amount)
        self.player.currency += amount
        self.changes.append(f"Received ${amount}.")

    def _charge(self, amount):
        amount = min(_count(amount), self.player.currency)
        if amount:
            self.player.currency -= amount
            self.changes.append(f"Paid ${amount}.")

    def _rep(self, faction, delta):
        faction = str(faction).lower()
        delta = int(delta)
        self.player.reputation[faction] = self.player.reputation.get(faction, 0) + delta
        self.changes.append(f"{faction.title()} reputation {delta:+d}.")

    def _mood(self, delta):
        self.npc_state["mood"] = clamp_mood(self.npc_state["mood"] + float(delta))
