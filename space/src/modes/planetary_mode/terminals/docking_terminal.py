from util.economy import trade


def handle_command(command, mode):
    verb, _, argument = command.strip().lower().partition(" ")
    commands = {
        "help": "List of available commands:\n help\n info\n" + trade.TRADE_HELP + "\n refuel\n depart\n map\n exit",
        "info": "Docking Terminal v1.0. Use this terminal for managing docking operations.",
        "map" : "Unable to fetch minimap at this tme",
        "long":"this is a test of a very long string this is a test of a very long string this is a test of a very long string this is a test of a very long string this is a test of a very long string this is a test of a very long string ",
        "depart": "",
        "exit":"",
        }
    if verb == "refuel":
        return trade.refuel(mode.player, mode.economy)
    result = trade.handle(verb, argument, mode.player, mode.economy)
    if result is not None:
        return result
    return commands.get(verb, "Unknown command. Type 'help' for available commands.")
