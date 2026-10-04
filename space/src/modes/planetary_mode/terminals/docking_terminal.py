from util.economy import trade


def handle_command(command, mode):
    verb, _, argument = command.strip().lower().partition(" ")
    commands = {
        "help": "List of available commands:\n help\n info\n" + trade.TRADE_HELP + "\n refuel\n repair\n depart\n exit",
        "info": "Docking Terminal v1.0. Use this terminal for managing docking operations.",
        "depart": "",
        "exit": "",
    }
    if verb == "refuel":
        return trade.refuel(mode.player, mode.economy)
    if verb == "repair":
        return trade.repair(mode.player)
    result = trade.handle(verb, argument, mode.player, mode.economy, mode.planet.planet_guild)
    if result is not None:
        return result
    return commands.get(verb, "Unknown command. Type 'help' for available commands.")
