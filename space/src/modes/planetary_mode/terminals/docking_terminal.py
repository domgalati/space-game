import yaml

def handle_command(command, planet_name):
    commands = {
        "help": "List of available commands: help, info, take off...",
        "info": "Docking Terminal v1.0. Use this terminal for managing docking operations.",
        "map" : "This will display a minimap soon.",
        "prices": get_planet_goods(planet_name),
        "long":"this is a test of a very long string this is a test of a very long string this is a test of a very long string this is a test of a very long string this is a test of a very long string this is a test of a very long string ",
        "depart": "",
        "exit":"",
        }
    return commands.get(command, "Unknown command. Type 'help' for available commands.")

def get_planet_goods(planet_name):
    with open('space/src/util/economy/economy.yaml', 'r') as file:
        data = yaml.safe_load(file)

    planet_data = data.get(planet_name.name, {})
    if not planet_data:
        return f"No economic data available for {planet_name.name}."

    goods_info = planet_data.get('goods', {})
    goods_list = "\n".join([f"{good}: {info['currentPrice']}" for good, info in goods_info.items()])
    return goods_list