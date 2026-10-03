"""Buying, selling, and refueling against a location's market."""
import math

from util.economy.news import render_news

SELL_RATE = 0.9  # traders buy from you below their asking price
PRICE_IMPACT = 0.005  # each unit bought raises the price this much; each unit sold lowers it
PRICE_CEILING = 2.0  # times base price
PRICE_FLOOR = 0.3
FUEL_CELL = "Fuel Cells"
FUEL_UNITS_PER_CELL = 25
DEFAULT_FUEL_PRICE = 8  # per unit, where the market doesn't stock Fuel Cells

TRADE_HELP = " prices\n buy <qty> <good>\n sell <qty> <good>\n cargo\n news"


def ask_price(info):
    return int(round(info["currentPrice"]))


def sell_price(info):
    return int(info["currentPrice"] * SELL_RATE)


def _nudge(info, factor):
    base = info["basePrice"]
    price = info["currentPrice"] * factor
    info["currentPrice"] = round(min(base * PRICE_CEILING, max(base * PRICE_FLOOR, price)), 2)


def find_good(goods, query):
    """Return (name, None) for a unique case-insensitive match, or (None, error)."""
    query = query.strip().lower()
    if not query:
        return None, "Which good?"
    exact = [g for g in goods if g.lower() == query]
    if exact:
        return exact[0], None
    matches = [g for g in goods if g.lower().startswith(query)]
    matches = matches or [g for g in goods if query in g.lower()]
    if not matches:
        return None, f"Nobody here trades in '{query}'."
    if len(matches) > 1:
        return None, "Which one? " + ", ".join(matches)
    return matches[0], None


def parse_order(argument):
    """'5 steel', 'steel 5', 'all steel', or 'steel' -> (quantity or 'all', good query)."""
    words = argument.split()
    for index in (0, -1):
        if words and (words[index].isdigit() or words[index] in ("all", "max")):
            amount = words.pop(index)
            return (amount if not amount.isdigit() else int(amount)), " ".join(words)
    return 1, " ".join(words)


def buy(player, economy, argument):
    goods = economy.goods()
    if not goods:
        return "No market at this location."
    quantity, query = parse_order(argument)
    good, error = find_good(goods, query)
    if error:
        return error
    info = goods[good]
    cargo = player.ship.cargo
    room = cargo.capacity - cargo.get_total_quantity()
    wanted = room if quantity in ("all", "max") else quantity
    if wanted <= 0:
        return "Cargo hold is full." if room <= 0 else "Buy how many?"

    bought = cost = 0
    while bought < min(wanted, room) and player.currency >= cost + ask_price(info):
        cost += ask_price(info)
        bought += 1
        _nudge(info, 1 + PRICE_IMPACT)
    if not bought:
        if room <= 0:
            return "Cargo hold is full."
        return f"You can't afford {good} at ${ask_price(info)}."
    player.currency -= cost
    cargo.add_item(good, bought)
    note = "" if quantity in ("all", "max") or bought == wanted else f" (wanted {wanted})"
    return f"Bought {bought} {good} for ${cost}{note}. Credits: ${player.currency}."


def sell(player, economy, argument):
    goods = economy.goods()
    if not goods:
        return "No market at this location."
    quantity, query = parse_order(argument)
    cargo = player.ship.cargo
    good, error = find_good(goods, query)
    if error:
        held, _ = find_good(cargo.items, query)
        return f"Nobody here buys {held}." if held else error
    held = cargo.items.get(good, 0)
    if not held:
        return f"You have no {good} aboard."
    count = held if quantity in ("all", "max") else min(quantity, held)
    if count <= 0:
        return "Sell how many?"

    info = goods[good]
    earned = 0
    for _ in range(count):
        earned += sell_price(info)
        _nudge(info, 1 - PRICE_IMPACT)
    cargo.remove_item(good, count)
    player.currency += earned
    return f"Sold {count} {good} for ${earned}. Credits: ${player.currency}."


def fuel_price(economy):
    cell = economy.goods().get(FUEL_CELL)
    if cell:
        return max(1, round(cell["currentPrice"] / FUEL_UNITS_PER_CELL))
    return DEFAULT_FUEL_PRICE


def refuel(player, economy):
    ship = player.ship
    needed = math.ceil(ship.max_fuel - ship.fuel)
    if needed <= 0:
        return "Tanks are already full."
    price = fuel_price(economy)
    units = min(needed, player.currency // price)
    if units <= 0:
        return f"Fuel is ${price}/unit and you can't afford any."
    player.currency -= units * price
    ship.fuel = min(ship.max_fuel, ship.fuel + units)
    note = "" if units == needed else " Partial fill: not enough credits."
    return f"Took on {units} fuel for ${units * price}. Tank: {int(ship.fuel)}/{ship.max_fuel}.{note}"


def price_board(player, economy):
    goods = economy.goods()
    if not goods:
        return "No economic data available here."
    cargo = player.ship.cargo
    lines = [f"{'GOOD':<24}{'BUY':>7}{'SELL':>7}{'HOLD':>6}"]
    for good, info in goods.items():
        lines.append(
            f"{good:<24}{ask_price(info):>7}{sell_price(info):>7}{cargo.items.get(good, 0):>6}"
        )
    lines.append(f"Fuel ${fuel_price(economy)}/unit at the docking terminal. Credits: ${player.currency}.")
    return "\n".join(lines)


def cargo_report(player, economy):
    cargo = player.ship.cargo
    header = f"Cargo {cargo.get_total_quantity()}/{cargo.capacity}. Credits: ${player.currency}."
    if not cargo.items:
        return header + "\nThe hold is empty."
    goods = economy.goods()
    lines = [header]
    for good, count in sorted(cargo.items.items()):
        offer = f"sells here ${sell_price(goods[good])}" if good in goods else "no buyer here"
        lines.append(f" {good}: {count} ({offer})")
    return "\n".join(lines)


def handle(verb, argument, player, economy):
    """Shared trade commands; returns None for verbs that aren't trade commands."""
    if verb == "prices":
        return price_board(player, economy)
    if verb == "buy":
        return buy(player, economy, argument)
    if verb == "sell":
        return sell(player, economy, argument)
    if verb == "cargo":
        return cargo_report(player, economy)
    if verb == "news":
        return render_news(economy.data)
    return None
