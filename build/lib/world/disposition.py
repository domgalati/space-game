MOOD_MIN = -100
MOOD_MAX = 100

# (lowest mood for this word, word), highest first.
_THRESHOLDS = (
    (60, "Trusted"),
    (20, "Friendly"),
    (-19, "Neutral"),
    (-59, "Wary"),
)


def clamp_mood(value):
    return max(MOOD_MIN, min(MOOD_MAX, int(round(value))))


def disposition_word(mood):
    for floor, word in _THRESHOLDS:
        if mood >= floor:
            return word
    return "Hostile"


def starting_mood(player_reputation, guild):
    """Half the player's standing with the NPC's guild."""
    return clamp_mood((player_reputation or {}).get(guild, 0) / 2)
