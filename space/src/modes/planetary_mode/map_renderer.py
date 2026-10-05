import pytmx


class MapRenderer:
    """Draws a GroundMap's tile layers and runs their Tiled animations."""

    def __init__(self, ground):
        self.tmx = ground.tmx
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

    def draw(self, surface, camera):
        surface.fill((0, 0, 0))
        tmx = self.tmx
        for layer in tmx.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid in layer:
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
