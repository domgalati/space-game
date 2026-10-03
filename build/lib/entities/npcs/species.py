"""Playable-world species. Vessari and Muroth are placeholders until the lore is written."""

SPECIES = {
    "human": {
        "name": "Human",
        "weight": 70,
    },
    "vessari": {
        "name": "Vessari",
        "weight": 15,
        "first_names": [
            "Ilvenne", "Soraeth", "Caelith", "Vyrenne", "Othalis", "Serevan",
            "Liomae", "Esquen", "Aurelis", "Nymeth", "Thaelo", "Ivesse",
        ],
        "last_names": ["Sorr", "Vael", "Ithren", "Maelis", "Quen", "Tessaly", "Oreth", "Lume"],
    },
    "muroth": {
        "name": "Muroth",
        "weight": 15,
        "first_names": [
            "Grask", "Hesk", "Borra", "Tunn", "Durga", "Makk",
            "Ruvok", "Osk", "Brenna", "Kholl", "Varga", "Thodd",
        ],
        "last_names": ["Durran", "Okkar", "Brask", "Gorrum", "Haldt", "Vukkar", "Rhenn", "Tollo"],
    },
}


def species_name(species_id):
    return SPECIES.get(species_id, {}).get("name", (species_id or "Unknown").title())


def roll_species(rng):
    ids = list(SPECIES)
    return rng.choices(ids, weights=[SPECIES[s]["weight"] for s in ids])[0]
