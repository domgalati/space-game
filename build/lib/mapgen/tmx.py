"""Writes a Grid out as a Tiled .tmx the game (and Tiled) can open."""
import os
from xml.sax.saxutils import quoteattr

from util.config import TILE_SIZE, resolve_game_path

from .tiles import TILESETS

WALKABLE_GID = 1  # any non-zero gid marks a walkable cell; the layer is hidden


def _csv(width, height, cells):
    rows = []
    for y in range(height):
        rows.append(",".join(str(cells.get((x, y), 0)) for x in range(width)))
    return ",\n".join(rows)


def _tile_layer(layer_id, name, width, height, cells, visible=True, properties=None):
    lines = [f' <layer id="{layer_id}" name={quoteattr(name)} width="{width}" height="{height}"'
             + ("" if visible else ' visible="0"') + ">"]
    if properties:
        lines.append("  <properties>")
        for key, (kind, value) in properties.items():
            lines.append(f'   <property name={quoteattr(key)} type="{kind}" value={quoteattr(value)}/>')
        lines.append("  </properties>")
    lines.append('  <data encoding="csv">')
    lines.append(_csv(width, height, cells))
    lines.append("</data>")
    lines.append(" </layer>")
    return lines


def _object_group(group_id, name, entries, next_object_id):
    lines = [f' <objectgroup id="{group_id}" name={quoteattr(name)} visible="0">']
    for label, x, y in entries:
        lines.append(
            f'  <object id="{next_object_id}" name={quoteattr(label)} '
            f'x="{x * TILE_SIZE}" y="{y * TILE_SIZE}" width="{TILE_SIZE}" height="{TILE_SIZE}"/>'
        )
        next_object_id += 1
    lines.append(" </objectgroup>")
    return lines, next_object_id


def write(grid, background, path, properties):
    """background: (x, y) -> gid for the bottom layer (floors, stars, hull fill)."""
    w, h = grid.width, grid.height
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<map version="1.10" tiledversion="1.10.2" orientation="orthogonal" renderorder="right-down" '
        f'width="{w}" height="{h}" tilewidth="{TILE_SIZE}" tileheight="{TILE_SIZE}" infinite="0" '
        f'backgroundcolor="#000000" nextlayerid="9" nextobjectid="__NEXT_OBJECT__">',
        " <properties>",
    ]
    for key, value in properties.items():
        out.append(f"  <property name={quoteattr(key)} value={quoteattr(str(value))}/>")
    out.append(" </properties>")
    tileset_dir = resolve_game_path("space/assets/Tilesheet Files")
    for source, firstgid in TILESETS:
        relative = os.path.relpath(os.path.join(tileset_dir, source), os.path.dirname(os.path.abspath(path)))
        out.append(f' <tileset firstgid="{firstgid}" source={quoteattr(relative.replace(os.sep, "/"))}/>')

    walkable = {cell: WALKABLE_GID for cell in grid.walkable_cells()}
    out += _tile_layer(1, "Background", w, h, background)
    out += _tile_layer(2, "Walls", w, h, grid.wall_gids())
    out += _tile_layer(3, "Decor", w, h, grid.decor)
    out += _tile_layer(4, "Props", w, h, grid.props)
    out += _tile_layer(5, "walkable", w, h, walkable, visible=False,
                       properties={"walkable": ("bool", "true")})

    next_id = 1
    for group_id, name, entries in (
        (6, "Objects", grid.objects),
        (7, "NPC Posts", grid.posts),
        (8, "Spawns", [("Player Start", *grid.spawn)] if grid.spawn else []),
    ):
        lines, next_id = _object_group(group_id, name, entries, next_id)
        out += lines
    out.append("</map>")

    text = "\n".join(out).replace("__NEXT_OBJECT__", str(next_id)) + "\n"
    with open(path, "w", encoding="utf-8") as file:
        file.write(text)
