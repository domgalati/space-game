import random

import yaml

from entities.player import FUEL_PER_STEP, Player
from util.economy import trade
from util.economy.economy import Economy, load_market_data


def market(**goods):
    return {name: {"basePrice": price, "currentPrice": price} for name, price in goods.items()}


def economy(here="Terramonta", **goods):
    data = {
        here: {"goods": market(**goods), "events": {}},
        "Etheora": {
            "goods": market(Steel=270),
            "events": {"Boom": {"Steel": {"priceChange": "+50%"}}},
        },
    }
    return Economy(here, data)


def rich_player(credits=10_000):
    player = Player()
    player.currency = credits
    return player


def test_buy_charges_per_unit_and_pushes_price_up():
    player = rich_player()
    econ = economy(Steel=200)
    result = trade.buy(player, econ, "3 steel")
    assert player.ship.cargo.items == {"Steel": 3}
    assert player.currency == 10_000 - (200 + 201 + 202)
    assert trade.price(econ.goods()["Steel"]) == 203
    assert result.startswith("Bought 3 Steel for $603")


def test_buy_all_stops_at_credits_and_cargo_room():
    player = rich_player(credits=450)
    econ = economy(Steel=200)
    trade.buy(player, econ, "all steel")
    assert player.ship.cargo.items == {"Steel": 2}

    player = rich_player()
    player.ship.cargo.add_item("Rations", 98)
    trade.buy(player, economy(Steel=200), "max steel")
    assert player.ship.cargo.get_total_quantity() == 100


def test_buy_refuses_when_broke_or_unknown():
    player = rich_player(credits=50)
    econ = economy(Steel=200)
    assert "can't afford" in trade.buy(player, econ, "steel")
    assert "Nobody here trades" in trade.buy(player, econ, "1 gems")
    assert player.ship.cargo.items == {}


def test_sell_pays_the_posted_price_and_pushes_it_down():
    player = rich_player(credits=0)
    player.ship.cargo.add_item("Steel", 2)
    econ = economy(Steel=200)
    trade.sell(player, econ, "all steel")
    assert player.currency == 200 + 199
    assert player.ship.cargo.items == {}
    assert trade.price(econ.goods()["Steel"]) == 198


def test_sell_reports_goods_with_no_buyer():
    player = rich_player()
    player.ship.cargo.add_item("Rare Gems", 1)
    assert trade.sell(player, economy(Steel=200), "rare") == "Nobody here buys Rare Gems."


def test_parse_order_forms():
    assert trade.parse_order("5 steel") == (5, "steel")
    assert trade.parse_order("raw minerals 5") == (5, "raw minerals")
    assert trade.parse_order("all steel") == ("all", "steel")
    assert trade.parse_order("steel") == (1, "steel")


def test_prefix_matching_needs_one_match():
    goods = market(**{"Steel": 1, "Ship Parts": 1, "Software Suites": 1})
    assert trade.find_good(goods, "st") == ("Steel", None)
    assert trade.find_good(goods, "parts") == ("Ship Parts", None)
    name, error = trade.find_good(goods, "s")
    assert name is None and error.startswith("Which one?")


def test_round_trip_profits():
    player = rich_player(credits=1500)
    etheora = Economy("Etheora", {"Etheora": {"goods": market(**{"Advanced Electronics": 100})}})
    terramonta = Economy("Terramonta", {"Terramonta": {"goods": market(**{"Advanced Electronics": 160})}})
    trade.buy(player, etheora, "all advanced")
    trade.sell(player, terramonta, "all advanced")
    assert player.currency > 1500


def test_refuel_prices_off_fuel_cells_and_fills_partially_when_short():
    player = rich_player(credits=5760)
    player.ship.fuel = 40.5
    station = economy("Nexum Astra", **{"fuel-cells": 150})
    assert trade.fuel_price(station) == 6
    trade.refuel(player, station)
    assert player.ship.fuel == 1000
    assert player.currency == 0

    player = rich_player(credits=80)
    player.ship.fuel = 0
    result = trade.refuel(player, economy(Steel=200))
    assert player.ship.fuel == 10 and player.currency == 0
    assert "Partial fill" in result


def test_ship_burns_fuel_and_goes_on_reserve():
    ship = Player().ship
    ship.burn_fuel(10)
    assert ship.fuel == ship.max_fuel - 10 * FUEL_PER_STEP
    assert not ship.on_reserve
    ship.burn_fuel(10_000)
    assert ship.fuel == 0 and ship.on_reserve


def test_negative_event_sets_price_below_base():
    econ = economy(Steel=200)
    econ.apply_price_change("Steel", "-10%")
    assert econ.goods()["Steel"]["currentPrice"] == 180


def test_market_news_settles_and_fires_events():
    econ = economy(Steel=200)
    econ.data["Terramonta"]["goods"]["Steel"]["currentPrice"] = 300
    headlines = econ.market_news(rng=random.Random(1))
    assert econ.goods()["Steel"]["currentPrice"] == 250
    assert headlines == ["News from Etheora: Boom."]
    assert econ.data["Etheora"]["goods"]["Steel"]["currentPrice"] == 405


def test_market_news_records_fired_events_in_the_feed():
    from util.economy.news_feed import NewsFeed
    from world.world_state import WorldState

    feed = NewsFeed(WorldState())
    econ = economy(Steel=200)
    econ.feed = feed
    econ.market_news(rng=random.Random(1))
    (story,) = feed.stories
    assert (story["place"], story["event"]) == ("Etheora", "Boom")
    assert story["moves"] == [{"good": "Steel", "price": 405, "change": "+50%"}]


def test_saved_prices_lay_over_the_base_goods(tmp_path):
    base = tmp_path / "base.yaml"
    base.write_text(yaml.safe_dump({"Terramonta": {"goods": market(Steel=200, Rations=95)}}))
    saved = {"Terramonta": {"Steel": 260.4, "Unobtainium": 9000}, "Gone": {"Steel": 1}}
    data = load_market_data(str(base), saved)
    assert data["Terramonta"]["goods"]["Steel"]["currentPrice"] == 260.4
    assert data["Terramonta"]["goods"]["Rations"]["currentPrice"] == 95
