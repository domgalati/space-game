import os
import random

import yaml

from util.config import resolve_game_path
from util.economy.news import event_price

BASE_DATA = "space/src/util/economy/economy.yaml"
GENERATED_DATA = "space/src/util/economy/economy_generated.yaml"

NEWS_CHANCE = 0.35  # per market, per landing
SETTLE_RATE = 0.5  # share of the gap to base price closed per landing


def _read_yaml(path):
    with open(path, "r") as file:
        return yaml.safe_load(file) or {}


def load_market_data(base_path=None, snapshot_path=None):
    """Base goods and events.

    Pass ``snapshot_path`` only in tests. The game keeps live prices in memory for the
    session and does not read or write the generated snapshot yet.
    """
    data = _read_yaml(base_path or resolve_game_path(BASE_DATA))
    if not snapshot_path:
        return data
    snapshot = _read_yaml(snapshot_path) if os.path.exists(snapshot_path) else {}
    for place, market in data.items():
        saved = ((snapshot.get(place) or {}).get("goods")) or {}
        for good, info in ((market or {}).get("goods") or {}).items():
            price = (saved.get(good) or {}).get("currentPrice")
            if price is not None:
                info["currentPrice"] = round(price, 2)
    return data


class Economy:
    def __init__(self, planet_name, economy_data, feed=None):
        self.planet_name = planet_name
        self.data = economy_data
        self.feed = feed
        self.log_callback = None

    def set_log_callback(self, callback):
        self.log_callback = callback

    def goods(self):
        """This location's goods, or {} when it has no market."""
        return (self.data.get(self.planet_name) or {}).get("goods") or {}

    def apply_price_change(self, item, price_change, place=None):
        info = self.data[place or self.planet_name]['goods'][item]
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
            headlines.append(f"News from {place}: {event}.")
        if self.log_callback:
            for headline in headlines:
                self.log_callback(headline)
        return headlines

    def save(self, outfile=GENERATED_DATA):
        """No-op until save slots exist. Prices live on the in-memory market data."""
        return
