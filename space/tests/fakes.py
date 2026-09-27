from dialogue.errors import DialogueError


class FakeContext:
    """Minimal runner context: plain dicts for variables, recorded commands."""

    def __init__(self, functions=None):
        self.vars = {}
        self.visits = {}
        self.commands = []
        self.functions = {
            "visited": lambda node: self.visits.get(node, 0) > 0,
            "visited_count": lambda node: self.visits.get(node, 0),
        }
        self.functions.update(functions or {})

    def get_var(self, name):
        return self.vars.get(name, False)

    def set_var(self, name, value):
        self.vars[name] = value

    def has_var(self, name):
        return name in self.vars

    def call(self, name, args):
        if name not in self.functions:
            raise DialogueError(f"Unknown function {name}()")
        return self.functions[name](*args)

    def run_command(self, name, args):
        self.commands.append((name, args))

    def mark_visited(self, node):
        self.visits[node] = self.visits.get(node, 0) + 1


def run_until_input(runner):
    """Collect events until options are offered or the dialogue ends."""
    from dialogue import End, Line, Options

    events = []
    while True:
        event = runner.advance()
        events.append(event)
        if isinstance(event, (Options, End)):
            return events
        assert isinstance(event, Line)
