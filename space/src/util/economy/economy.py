import random

import yaml

from util.config import resolve_game_path
from util.economy.news import event_price
from world.atlas import place_name

BASE_DATA = "space/src/util/economy/economy.yaml"

NEWS_CHANCE = 0.35  # per market, per landing
SETTLE_RATE = 0.5  # share of the gap to base price closed per landing


def _read_yaml(path):
    with open(path, "r") as file:
        return yaml.safe_load(file) or {}


def load_market_data(base_path=None, prices=None):
    """Base goods and events, with `prices` ({place: {good: price}}, from a save) laid over
    them. Goods the yaml has added since keep their base price; ones it dropped are ignored."""
    data = _read_yaml(base_path or resolve_game_path(BASE_DATA))
    for place, market in data.items():
        saved = (prices or {}).get(place) or {}
        for good, info in ((market or {}).get("goods") or {}).items():
            if saved.get(good) is not None:
                info["currentPrice"] = round(saved[good], 2)
    return data


class Economy:
    def __init__(self, place, economy_data, feed=None, events=None):
        self.place = place  # body id this market belongs to; see world.atlas
        self.data = economy_data
        self.feed = feed
        self.events = events  # world.events.Events, to announce trades; optional
        self.log_callback = None

    def emit(self, name, **details):
        if self.events is not None:
            self.events.emit(name, place=self.place, **details)

    def set_log_callback(self, callback):
        self.log_callback = callback

    def goods(self):
        """This location's goods, or {} when it has no market."""
        return (self.data.get(self.place) or {}).get("goods") or {}

    def apply_price_change(self, item, price_change, place=None):
        info = self.data[place or self.place]['goods'][item]
        info['currentPrice'] = event_price(info['basePrice'], price_change)

    def market_news(self, rng=random):
        """Time passes between landings: prices settle toward base, and some markets get news."""
        headlines = []
        for place, market in self.data.items():
            goods = (market or {}).get("goods") or {}
            for info in goods.values():
                gap = info["basePrice"] - info["currentPrice"]
                info["currentPrice"] = round(info["currentPrice"] + gap * SETTLE_RATE, 2)
            events = (market or {}).get("events") or {}
            if not events or rng.random() >= NEWS_CHANCE:
                continue
            event = rng.choice(sorted(events))
            moves = []
            for item, change in events[event].items():
                if item in goods:
                    self.apply_price_change(item, change['priceChange'], place)
                    moves.append({
                        "good": item,
                        "price": int(round(goods[item]["currentPrice"])),
                        "change": change['priceChange'],
                    })
            if self.feed is not None:
                self.feed.record(place, event, moves)
            headlines.append(f"News from {place_name(place)}: {event}.")
        if self.log_callback:
            for headline in headlines:
                self.log_callback(headline)
        return headlines
