import json
from types import SimpleNamespace

from entities.planet import Planet
from entities.player import Player
from modes.star_system_mode.scan_terminal import hail_response, scan_readout
from util.config import resolve_game_path
from util.economy import trade
from util.economy.economy import Economy
from world.factions import (
    STANDING_MAX, TRADE_CAP, TRADE_STEP, WAVE_BY, Politics, adjust_standing, credit_trade, record_kill, waves_by,
)


def sol_data():
    with open(resolve_game_path("space/star_systems/sol.json")) as file:
        return json.load(file)


SOL = Politics.from_data(sol_data())


def test_sol_territory_matches_the_plan():
    data = sol_data()
    owners = {body["name"]: body["guild"] for body in data["planets"] + data["objects"]}
    assert owners == {
        "Governus Centralis": "assembly", "Terramonta": "assembly", "Nexum Astra": "assembly",
        "Ferrica": "dominion",
        "Ageria": "cohort", "Arboresia": "cohort",
        "Cosmopolara": "caravaneers", "Etheora": "caravaneers",
    }


def test_in_sol_everyone_licenses_raiders_except_the_assembly():
    assert SOL.law == "assembly"
    assert not SOL.licenses_raiders("assembly")
    assert all(SOL.licenses_raiders(f) for f in ("dominion", "cohort", "caravaneers"))


def test_a_lawless_system_has_no_raiders_and_no_bounties():
    lawless = Politics()
    assert not lawless.licenses_raiders("dominion")
    assert not lawless.flies_law_colours({"assembly": 100})
    player = Player()
    assert record_kill(player, "dominion", "raider") == "DOMINION -5"
    assert player.reputation["assembly"] == 0


def test_raiders_wave_friends_of_their_sponsor_by():
    assert not waves_by({"dominion": WAVE_BY - 1}, "dominion")
    assert waves_by({"dominion": WAVE_BY}, "dominion")
    assert not waves_by({"cohort": 90}, "dominion")


def test_standing_is_clamped_and_reports_the_real_change():
    reputation = {"cohort": STANDING_MAX - 2}
    assert adjust_standing(reputation, "cohort", 10) == 2
    assert reputation["cohort"] == STANDING_MAX


def test_trade_earns_a_point_per_step_and_carries_the_rest():
    player = Player()
    assert credit_trade(player, "dominion", TRADE_STEP - 1) == 0
    assert credit_trade(player, "dominion", 1) == 1
    assert credit_trade(player, "dominion", TRADE_STEP * 3) == 3
    assert player.reputation["dominion"] == 4


def test_trade_alone_stops_at_the_cap():
    player = Player()
    player.reputation["cohort"] = TRADE_CAP - 1
    assert credit_trade(player, "cohort", TRADE_STEP * 5) == 1
    assert credit_trade(player, "cohort", TRADE_STEP * 5) == 0
    assert credit_trade(player, "nobody", TRADE_STEP * 5) == 0


def market_at(here, **goods):
    data = {here: {"goods": {g: {"basePrice": p, "currentPrice": p} for g, p in goods.items()}, "events": {}}}
    return Economy(here, data)


def test_selling_at_a_faction_world_raises_standing_with_it():
    player = Player()
    player.ship.cargo.add_item("Steel", 10)
    result = trade.handle("sell", "10 steel", player, market_at("Ferrica", Steel=150), "dominion")
    assert player.reputation["dominion"] == 1
    assert result.endswith("Dominion standing +1.")
    unaffiliated = trade.handle("sell", "1 steel", Player(), market_at("Ferrica", Steel=150))
    assert "standing" not in unaffiliated


def body(name, faction, map_path=None):
    target = Planet.__new__(Planet)
    target.id, target.name, target.map_path = f"sol/{name.lower()}", name, map_path
    target.category = "planet"
    target.planet_guild, target.planet_type = faction, "Industrial"
    return target


def test_hails_speak_for_the_faction_and_hint_at_its_privateers():
    ferrica = body("Ferrica", "dominion")
    assert "Dominion Port Authority" in hail_response(ferrica, politics=SOL)
    assert "no berth" in hail_response(ferrica, politics=SOL)
    assert "let you pass" in hail_response(ferrica, {"dominion": WAVE_BY}, SOL)
    assert "Assembly colours" in hail_response(ferrica, {"assembly": WAVE_BY}, SOL)
    terramonta = body("Terramonta", "assembly", resolve_game_path("space/assets/maps/Terramonta.tmx"))
    assert "privateers" not in hail_response(terramonta, {"assembly": 90}, SOL)
    assert "Send 'dock'" in hail_response(terramonta, politics=SOL)


def test_scans_show_faction_standing_and_raider_licenses():
    lines = scan_readout(body("Ferrica", "dominion"), {}, {"dominion": 25}, SOL)
    assert "Faction: Dominion" in lines
    assert "Your standing: Friendly (+25)" in lines
    assert "Licenses privateers against Assembly shipping." in lines
    station = SimpleNamespace(id="sol/nexum-astra", category="station", name="Nexum Astra", obj_type="SpaceStation", planet_guild="assembly")
    lines = scan_readout(station, {}, {}, SOL)
    assert "Faction: Assembly" in lines
    assert not any("privateers" in line for line in lines)
