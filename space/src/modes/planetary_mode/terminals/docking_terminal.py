def handle_command(command):
    commands = {
        "help": "List of available commands: help, info, take off...",
        "info": "Docking Terminal v1.0. Use this terminal for managing docking operations.",
        "map" : "This will display a minimap soon.",
        "exit": "Thanks for stopping by",
        # Add more commands and their descriptions here
    }

    return commands.get(command, "Unknown command. Type 'help' for available commands.")
