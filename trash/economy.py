import yaml
import random

outfile = 'space/src/util/economy/economy_generated.yaml'
with open('space/src/util/economy/economy.yaml', 'r') as file:
    data = yaml.safe_load(file)



class Economy:
    def __init__(self):
        self.planet_name = 'Terramonta' ## Just for while writing this file, irl the game will pass this.
        
    def fire_event(self, data):
        planet_name = 'Terramonta' ## Just for while writing this file, irl the game will pass this.

        #if random.randint(0,100) < 36:
        if True:
            event = random.choice(list(data[planet_name]['events']))
            print(event)
            
            item_to_pricechange = random.choice(list(data[planet_name]['events'][event]))
            pricechange = data[planet_name]['events'][event][item_to_pricechange]['priceChange']

            if '+' in pricechange:
                print(f'increasing price of {item_to_pricechange} by {pricechange["priceChange"]}')
                baseprice = data[planet_name]['goods'][item_to_pricechange]['basePrice']
                data[planet_name]['goods'][item_to_pricechange]['currentPrice'] = baseprice + (baseprice * int(pricechange.replace('%', '').replace('+', '')) / 100)

            if '-' in pricechange: 
                print(f'decreasing price of {item_to_pricechange} by {pricechange["priceChange"]}')
                
           
            print(pricechange)
            newdata = '' #data with pricechanges
            with open('space/src/util/economy/economy_generated.yaml', 'w') as outfile:
                yaml.dump(newdata, outfile, default_flow_style=False)


Economy.fire_event(data, data)
