from .docking_terminal import get_planet_goods


def handle_command(command, location):
    commands = {
        "help": "List of available commands:\n help\n info\n prices\n exit",
        "info": f"{location.name} Exchange. Current prices for registered haulers.",
        "prices": get_planet_goods(location),
        "exit": "",
    }
    return commands.get(command, "Unknown command. Type 'help' for available commands.")
