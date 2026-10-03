"""Sol's factions: who holds what, who licenses raiders against whom, and the player's standing.

Everyone is against the Assembly. The Dominion, Cohort and Caravaneers license privateers
against Assembly-friendly shipping; the Assembly is the law, runs patrols and pays bounties.
Planet ownership lives in the star system file (each body's "guild").
"""
import math

STANDING_MIN, STANDING_MAX = -100, 100
WAVE_BY = 30  # standing with a privateer's sponsor at which its raiders let you pass
TRADE_STEP = 1000  # credits traded at a faction's world per point of standing
TRADE_CAP = 40  # trade alone lifts standing this far, no further
KILL_SPONSOR_STANDING = -5  # destroying a privateer, with its sponsor
KILL_LAW_STANDING = 3  # and with the Assembly

FACTIONS = {
    "assembly": {"name": "Assembly", "voice": "Assembly Traffic Control"},
    "dominion": {"name": "Dominion", "voice": "Dominion Port Authority"},
    "cohort": {"name": "Cohort", "voice": "Cohort Commons Relay"},
    "caravaneers": {"name": "Caravaneers", "voice": "Caravaneer Moot"},
}
LAW = "assembly"
RAIDER_SPONSORS = ("dominion", "cohort", "caravaneers")


def faction_name(faction):
    return FACTIONS.get(faction, {}).get("name", (faction or "Independent").title())


def licenses_raiders(faction):
    return faction in RAIDER_SPONSORS


def waves_by(reputation, sponsor):
    """True when `sponsor`'s privateers would let this ship pass."""
    return reputation.get(sponsor, 0) >= WAVE_BY


def flies_assembly_colours(reputation):
    """Friendly enough with the Assembly that raiders take an interest."""
    return reputation.get(LAW, 0) >= WAVE_BY


def adjust_standing(reputation, faction, delta):
    """Move standing within its limits; returns how much it actually changed."""
    before = reputation.get(faction, 0)
    reputation[faction] = max(STANDING_MIN, min(STANDING_MAX, before + delta))
    return reputation[faction] - before


def record_kill(player, sponsor, kind):
    """A privateer destroyed: logged for bounties, and standing moves. Returns a short summary."""
    player.kill_log.append({"sponsor": sponsor, "kind": kind})
    lost = adjust_standing(player.reputation, sponsor, KILL_SPONSOR_STANDING)
    gained = adjust_standing(player.reputation, LAW, KILL_LAW_STANDING)
    return f"{faction_name(sponsor).upper()} {lost:+d}, {faction_name(LAW).upper()} {gained:+d}"


def credit_trade(player, faction, credits):
    """Trade at `faction`'s world earns a point of standing per TRADE_STEP credits, up to TRADE_CAP.

    Returns the standing gained. Credits below a full step carry over to the next trade.
    """
    if faction not in FACTIONS or credits <= 0:
        return 0
    before = player.trade_ledger.get(faction, 0)
    after = before + credits
    player.trade_ledger[faction] = after
    points = math.floor(after / TRADE_STEP) - math.floor(before / TRADE_STEP)
    room = TRADE_CAP - player.reputation.get(faction, 0)
    if points <= 0 or room <= 0:
        return 0
    return adjust_standing(player.reputation, faction, min(points, room))
