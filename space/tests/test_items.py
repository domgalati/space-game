from entities.player import Player
from util.economy import trade
from util.economy.economy import Economy, load_market_data
from world.items import CATEGORIES, find_item, item, item_name


def test_every_market_good_and_event_is_a_known_item():
    for place, market in load_market_data().items():
        for good in market.get("goods") or {}:
            assert item(good), f"economy.yaml: {place} sells unknown item {good!r}"
        for event, moves in (market.get("events") or {}).items():
            for good in moves:
                assert item(good), f"economy.yaml: {place} event {event!r} moves unknown item {good!r}"


def test_items_have_names_and_categories():
    steel = item("steel")
    assert steel["name"] == "Steel" and steel["category"] in CATEGORIES
    assert item("mining-permit")["category"] == "quest"


def test_names_find_ids_and_unknown_text_passes_through():
    assert find_item("Raw Minerals") == "raw-minerals"
    assert find_item("raw minerals") == "raw-minerals"
    assert find_item("raw-minerals") == "raw-minerals"
    assert find_item("Unobtainium") == "Unobtainium"
    assert item_name("raw-minerals") == "Raw Minerals"
    assert item_name("Unobtainium") == "Unobtainium"


def test_trading_real_goods_stores_ids_and_says_names():
    markets = load_market_data()
    economy = Economy("sol/terramonta", markets)
    player = Player()
    player.currency = 5000
    assert trade.handle("buy", "2 raw min", player, economy).startswith("Bought 2 Raw Minerals")
    assert player.ship.cargo.items == {"raw-minerals": 2}
    assert " Raw Minerals: 2 " in trade.handle("cargo", "", player, economy)
    assert "Raw Minerals" in trade.handle("prices", "", player, economy)
