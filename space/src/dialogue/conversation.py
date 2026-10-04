"""One conversation with one NPC: picks the script, runs it, and reports what changed."""
import os

from entities.npcs.species import species_name
from util.config import resolve_game_path
from world.disposition import disposition_word, starting_mood

from .context import GameContext
from .errors import DialogueError
from .runner import DialogueRunner, End
from .yarn_parser import load_yarn

GENERIC_DIALOGUE = "space/dialogue/generic.yarn"

_programs = {}  # path -> (mtime, program); edits to a .yarn file load on the next conversation


def load_program(relative_path):
    path = resolve_game_path(relative_path)
    mtime = os.path.getmtime(path)
    cached = _programs.get(path)
    if cached is None or cached[0] != mtime:
        _programs[path] = (mtime, load_yarn(path))
    return _programs[path][1]


class Conversation:
    def __init__(self, npc, player, world_state, economy=None, location=None):
        self.npc = npc
        default_mood = npc.base_mood if npc.base_mood is not None else starting_mood(player.reputation, npc.guild)
        self.npc_state = world_state.npc_state(npc.npc_id or f"unnamed/{id(npc)}", default_mood)
        self.context = GameContext(npc, self.npc_state, player, world_state, economy=economy, location=location)
        world_state.events.emit("talked", npc=npc.npc_id)
        self.error = None
        self.runner = None
        try:
            self.runner = DialogueRunner(load_program(npc.dialogue_file or GENERIC_DIALOGUE), self.context)
        except (OSError, DialogueError) as exc:
            self._fail(exc)

    @property
    def name(self):
        return f"{self.npc.firstname} {self.npc.lastname}".strip()

    @property
    def species(self):
        return species_name(self.npc.species)

    @property
    def disposition(self):
        return disposition_word(self.npc_state["mood"])

    @property
    def can_exit(self):
        return self.runner is None or self.error is not None or self.runner.can_exit

    def start(self):
        if self.runner is None:
            return End()
        try:
            self.runner.start(self.npc.start_node or "Start")
        except DialogueError as exc:
            self._fail(exc)
            return End()
        return self.advance()

    def advance(self):
        if self.runner is None or self.error:
            return End()
        try:
            return self.runner.advance()
        except DialogueError as exc:
            self._fail(exc)
            return End()

    def choose(self, index):
        self.runner.select(index)
        return self.advance()

    def _fail(self, exc):
        self.error = str(exc)
        print(f"[dialogue] {self.error}")

    def summary_lines(self):
        lines = [f"Spoke with {self.name}. {self.npc.firstname} seems {self.disposition}."]
        lines.extend(self.context.changes)
        if self.error:
            lines.append(f"[dialogue error] {self.error}")
        return lines
