"""Small-talk text built from game state: what an NPC does, what things cost, what they've heard."""
import random

from util.economy.economy import load_market_data

# Job -> goods this person notices (must exist in planet economy YAML).
JOB_GOODS_BIAS = {
    "Miner": ("Raw Minerals", "Steel"),
    "Foreman": ("Mining Equipment", "Durable Tools"),
    "Dockworker": ("Fuel Cells", "Ship Parts", "Rations"),
    "Security": ("Medical Supplies", "Luxury Goods"),
    "Politician": ("Luxury Goods", "Advanced Electronics"),
}

# Planet -> job -> goods, for planets whose economy lacks the default goods above.
PLANET_JOB_GOODS_BIAS = {
    "Etheora": {
        "Miner": ("Virtual Reality Gear", "Nanotechnology"),
        "Foreman": ("Robotics Components", "Software Suites"),
        "Dockworker": ("Robotics Components", "Renewable Energy Tech"),
    },
}

JOB_DESCRIPTIONS = {
    "Miner": (
        "I work the rigs. Drill, haul, sleep, repeat.",
        "Mining. Somebody has to pull the rock out of the ground.",
    ),
    "Foreman": (
        "I keep the crews on schedule and the machines from eating anybody.",
        "Foreman. If a shift runs late, it's my name on the report.",
    ),
    "Dockworker": (
        "I load and unload whatever comes through the bays.",
        "Cargo handling. Crates in, crates out.",
    ),
    "Security": (
        "I keep the peace. Mostly by standing where people can see me.",
        "Station security. Behave and we'll get along fine.",
    ),
    "Politician": (
        "I serve the Assembly. Committees, mostly. So many committees.",
        "I represent this district's interests. Loudly, when required.",
    ),
}


def goods_for(npc, planet):
    return PLANET_JOB_GOODS_BIAS.get(planet, {}).get(npc.job_title) or JOB_GOODS_BIAS.get(npc.job_title)


def goods_opinion(npc, economy, rng=random):
    """A spoken line about a good this NPC's job cares about, or None if nothing applies."""
    if not economy:
        return None
    planet = economy.planet_name
    goods = goods_for(npc, planet)
    if not goods:
        return None
    catalog = economy.data.get(planet, {}).get("goods", {})
    available = [g for g in goods if g in catalog]
    if not available:
        return None
    item = rng.choice(available)
    entry = catalog[item]
    base = entry.get("basePrice")
    current = entry.get("currentPrice", base)
    if not base or current is None:
        return None
    ratio = current / base
    if ratio >= 1.15:
        return rng.choice((
            f"{item} has been running high lately.",
            f"Have you seen what {item} costs this week? Robbery.",
        ))
    if ratio <= 0.85:
        return rng.choice((
            f"{item} is cheap right now. Good time to stock up.",
            f"Nobody wants {item} this week. Prices are in the floor.",
        ))
    return rng.choice((
        f"{item} is about average right now.",
        f"{item} prices are steady. Boring, but steady.",
    ))


def market_rumor(here, rng=random):
    """A spoken line about prices somewhere other than ``here``."""
    markets = [
        (place, good, info)
        for place, data in load_market_data().items()
        if place != here
        for good, info in (data or {}).get("goods", {}).items()
    ]
    if not markets:
        return "Quiet week. Nobody's talking."
    place, good, info = rng.choice(markets)
    ratio = info["currentPrice"] / info["basePrice"] if info.get("basePrice") else 1
    if ratio >= 1.15:
        return f"Word is {good} is fetching a premium on {place}."
    if ratio <= 0.85:
        return f"Heard {good} is going cheap on {place}. Might be worth the trip."
    return f"Last I heard, {place} was paying ${info['currentPrice']:.0f} for {good}."


def job_line(npc, rng=random):
    """What the NPC does, plus what their current goal has them doing."""
    descriptions = JOB_DESCRIPTIONS.get(npc.job_title)
    if descriptions:
        line = rng.choice(descriptions)
    elif npc.job_title:
        line = f"I'm a {npc.job_title.lower()}. It pays."
    else:
        line = "A little of this, a little of that."
    activity = getattr(npc.goal, "activity", None)
    if activity:
        line += f" Right now I'm {activity}."
    return line
