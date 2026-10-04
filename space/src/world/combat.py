"""What a fight does to the world, whichever fight it is: a dogfight now, a ground fight later.

Modes run the fight itself (positions, turns, shots, art). When the player brings someone
down, the mode calls kill() for the consequences and loot_goods() for what they carried.
"""
from world.factions import record_kill


def kill(player, world_state, faction, kind, law=None, **where):
    """The player killed a `kind` (e.g. "raider") belonging to `faction`. It's logged for
    bounties, standing moves with the faction and with `law` (the local law faction), and a
    "killed" event goes out with `where` (e.g. system="sol"). Returns the standing summary."""
    summary = record_kill(player, faction, kind, law)
    world_state.events.emit("killed", faction=faction, kind=kind, **where)
    return summary


def loot_goods(markets, bodies, faction):
    """Item ids a `faction` fighter might carry: what its worlds among `bodies` trade. If its
    worlds have no markets yet, anything on sale anywhere."""
    goods = set()
    for body in bodies:
        if body.planet_guild == faction:
            goods.update((markets.get(body.id) or {}).get("goods") or {})
    if not goods:
        for market in markets.values():
            goods.update((market or {}).get("goods") or {})
    return goods
