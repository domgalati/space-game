def handle_command(command):
    commands = {
        "help": "List of available commands: help, info, take off...",
        "info": "Docking Terminal v1.0. Use this terminal for managing docking operations.",
        "map" : "This will display a minimap soon.",
        "depart":"",
        "exit":"",
        "longtest":"As you step onto the rugged terrain of Terramonta, you are entering a world that pulsates with the raw power of industry and the unyielding spirit of exploration. This planet, resembling an ancient mining town expanded to a planetary scale, stands as a testament to the relentless human endeavor in the most extreme conditions.",
        }
    return commands.get(command, "Unknown command. Type 'help' for available commands.")
