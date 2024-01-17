import yaml
import random

class Economy:
    def __init__(self, planet_name, economy_data):
        self.planet_name = planet_name
        self.data = economy_data
        self.log_callback = None

    def set_log_callback(self, callback):
        self.log_callback = callback

    def apply_price_change(self, item, price_change):
        base_price = self.data[self.planet_name]['goods'][item]['basePrice']
        change_factor = int(price_change.replace('%', '')) / 100

        if '+' in price_change:
            new_price = base_price * (1 + change_factor)
        elif '-' in price_change:
            new_price = base_price * (1 - change_factor)
        else:
            new_price = base_price

        self.data[self.planet_name]['goods'][item]['currentPrice'] = new_price

    def fire_event(self):
        if random.uniform(0, 100) < 1.5:  # 2% chance to trigger an event
            event = random.choice(list(self.data[self.planet_name]['events']))
            print(f"Prices on {self.planet_name} have changed due to {event}")
            event_message = f"Prices on {self.planet_name} have changed due to {event}"
            if self.log_callback:
                self.log_callback(event_message)

            for item, change in self.data[self.planet_name]['events'][event].items():
                self.apply_price_change(item, change['priceChange'])
                print(f"{item} price updated.")

    def dump_updated_data(self, outfile):
        with open(outfile, 'w') as file:
            yaml.dump(self.data, file, default_flow_style=False)
            print(f"Updated economy data dumped to {outfile}")

# Usage
with open('space/src/util/economy/economy_generated.yaml', 'r') as file:
    data = yaml.safe_load(file)

economy = Economy('Terramonta', data)
economy.fire_event()
economy.dump_updated_data('space/src/util/economy/economy_generated.yaml')
