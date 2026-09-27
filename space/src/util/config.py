from pathlib import Path

SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 720
TILE_SIZE = 24


def game_root() -> Path:
    """Directory that contains ``src/``, ``assets/``, and ``star_systems/``."""
    return Path(__file__).resolve().parents[2]


def resolve_game_path(legacy_path: str) -> str:
    """
    Map paths like ``space/assets/...`` (historically relative to the git repo root) to
    real paths under :func:`game_root`, so the game runs regardless of current working directory.
    """
    p = Path(legacy_path)
    if p.is_absolute():
        return str(p)
    parts = p.parts
    if parts and parts[0] == "space" and len(parts) > 1:
        return str(game_root().joinpath(*parts[1:]))
    return str(game_root() / p)