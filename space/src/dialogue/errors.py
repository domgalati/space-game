class DialogueError(Exception):
    """A problem in a .yarn script, reported with the file and line it came from."""

    def __init__(self, message, source=None, line=None):
        self.message = message
        self.source = source
        self.line = line
        where = ""
        if source and line:
            where = f"{source}:{line}: "
        elif source:
            where = f"{source}: "
        super().__init__(f"{where}{message}")
