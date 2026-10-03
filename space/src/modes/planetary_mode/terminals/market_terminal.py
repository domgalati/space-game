from util.economy import trade


def handle_command(command, mode):
    verb, _, argument = command.strip().lower().partition(" ")
    commands = {
        "help": "List of available commands:\n help\n info\n" + trade.TRADE_HELP + "\n exit",
        "info": f"{mode.planet.name} Exchange. Current prices for registered haulers.",
        "exit": "",
    }
    result = trade.handle(verb, argument, mode.player, mode.economy, mode.planet.planet_guild)
    if result is not None:
        return result
    return commands.get(verb, "Unknown command. Type 'help' for available commands.")
