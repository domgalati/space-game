"""Steps through a parsed Yarn program one event at a time."""
from .errors import DialogueError
from .yarn_parser import (
    CommandStmt,
    IfStmt,
    JumpStmt,
    LineStmt,
    OptionGroup,
    SetStmt,
    StopStmt,
)


class Line:
    def __init__(self, speaker, text):
        self.speaker = speaker
        self.text = text


class Options:
    def __init__(self, choices):
        self.choices = choices  # [str], only the options whose conditions passed


class End:
    pass


class DialogueRunner:
    """
    ``context`` provides get_var, set_var, has_var, call, run_command, mark_visited.
    Call ``advance()`` for the next event; after an ``Options`` event call ``select(i)`` first.
    """

    def __init__(self, program, context):
        self.program = program
        self.context = context
        self.node = None
        self._frames = []
        self._pending = None
        self._finished = False

    @property
    def can_exit(self):
        return self.node is None or "noexit" not in self.node.tags

    @property
    def finished(self):
        return self._finished

    def start(self, title="Start"):
        self._finished = False
        self._pending = None
        self._enter(title, line=None)

    def select(self, index):
        if self._pending is None:
            raise DialogueError("select() called with no options on screen", self.program.source)
        available = self._pending
        self._pending = None
        if not 0 <= index < len(available):
            raise DialogueError(f"Option {index} is out of range", self.program.source)
        self._frames.append([available[index].body, 0])

    def advance(self):
        if self._pending is not None:
            raise DialogueError("advance() called before an option was selected", self.program.source)
        while not self._finished:
            if not self._frames:
                self._finish()
                break
            frame = self._frames[-1]
            stmts, pc = frame
            if pc >= len(stmts):
                self._frames.pop()
                continue
            frame[1] += 1
            event = self._execute(stmts[pc])
            if event is not None:
                return event
        return End()

    def _execute(self, stmt):
        try:
            return self._execute_stmt(stmt)
        except DialogueError as exc:
            if exc.line is not None:
                raise
            raise DialogueError(exc.message, self.program.source, stmt.line) from exc
        except Exception as exc:
            raise DialogueError(str(exc), self.program.source, stmt.line) from exc

    def _execute_stmt(self, stmt):
        ctx = self.context
        if isinstance(stmt, LineStmt):
            speaker = stmt.speaker.render(ctx) if stmt.speaker else None
            return Line(speaker, stmt.text.render(ctx))
        if isinstance(stmt, OptionGroup):
            available = [
                option for option in stmt.options
                if option.condition is None or option.condition.evaluate(ctx)
            ]
            if not available:
                return None
            self._pending = available
            return Options([option.text.render(ctx) for option in available])
        if isinstance(stmt, IfStmt):
            for condition, body in stmt.branches:
                if condition is None or condition.evaluate(ctx):
                    self._frames.append([body, 0])
                    break
            return None
        if isinstance(stmt, SetStmt):
            if not (stmt.declare and ctx.has_var(stmt.name)):
                ctx.set_var(stmt.name, stmt.expr.evaluate(ctx))
            return None
        if isinstance(stmt, JumpStmt):
            self._enter(stmt.target, stmt.line)
            return None
        if isinstance(stmt, StopStmt):
            self._finish()
            return None
        if isinstance(stmt, CommandStmt):
            ctx.run_command(stmt.name, [arg.evaluate(ctx) for arg in stmt.args])
            return None
        raise DialogueError(f"Unknown statement {type(stmt).__name__}", self.program.source, stmt.line)

    def _enter(self, title, line):
        node = self.program.node(title)
        if node is None:
            raise DialogueError(f"No node titled {title!r}", self.program.source, line)
        self._leave_node()
        self.node = node
        self._frames = [[node.body, 0]]

    def _leave_node(self):
        if self.node is not None:
            self.context.mark_visited(self.node.title)

    def _finish(self):
        self._leave_node()
        self.node = None
        self._frames = []
        self._pending = None
        self._finished = True
