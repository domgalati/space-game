import math

import pytmx


class MapRenderer:
    """Draws a GroundMap's tile layers and runs their Tiled animations."""

    def __init__(self, ground):
        self.tmx = ground.tmx
        self.layers = [layer for layer in self.tmx.visible_layers if isinstance(layer, pytmx.TiledTileLayer)]
        # A tile image can be bigger than its cell (some are 2x3 cells) and is drawn from the
        # cell's top-left, so cells up to this many columns left / rows above the view still show.
        widest = max((image.get_width() for image in self.tmx.images if image), default=self.tmx.tilewidth)
        tallest = max((image.get_height() for image in self.tmx.images if image), default=self.tmx.tileheight)
        self.reach = (math.ceil(widest / self.tmx.tilewidth) - 1, math.ceil(tallest / self.tmx.tileheight) - 1)
        self.animations = {}  # tile GID -> frames, durations (ms) and where it's up to
        for gid, properties in self.tmx.tile_properties.items():
            frames = properties.get("frames") or []
            if frames:
                self.animations[gid] = {
                    "frames": [frame.gid for frame in frames],
                    "durations": [frame.duration for frame in frames],
                    "current_frame": 0,
                    "timer": 0,
                }

    def visible_cells(self, camera):
        """(first column, first row, last column + 1, last row + 1) of the cells that can show in `camera`."""
        tmx, (reach_x, reach_y) = self.tmx, self.reach
        return (
            max(0, camera.left // tmx.tilewidth - reach_x),
            max(0, camera.top // tmx.tileheight - reach_y),
            min(tmx.width, -(-camera.right // tmx.tilewidth)),
            min(tmx.height, -(-camera.bottom // tmx.tileheight)),
        )

    def draw(self, surface, camera):
        """Draw the cells in view, each layer in turn, rows top to bottom, as Tiled stacks them."""
        surface.fill((0, 0, 0))
        tmx = self.tmx
        left, top, right, bottom = self.visible_cells(camera)
        for layer in self.layers:
            for y in range(top, bottom):
                row = layer.data[y]
                for x in range(left, right):
                    gid = row[x]
                    if not gid:
                        continue
                    animation = self.animations.get(gid)
                    if animation:
                        gid = animation["frames"][animation["current_frame"]]
                    tile = tmx.get_tile_image_by_gid(gid)
                    if tile:
                        surface.blit(tile, (x * tmx.tilewidth - camera.x, y * tmx.tileheight - camera.y))

    def update(self, dt_ms):
        for animation in self.animations.values():
            animation["timer"] += dt_ms
            if animation["timer"] > animation["durations"][animation["current_frame"]]:
                animation["timer"] -= animation["durations"][animation["current_frame"]]
                animation["current_frame"] = (animation["current_frame"] + 1) % len(animation["frames"])
