import pygame

from util.images import load_image

# Same corridor size as a planetary starport. `access` points are image-local.
APPROACH_RADIUS = 160

class SpaceObject:
    def __init__(self, body_id, name, obj_type, image_path, x, y, guild=None, access=None, map_path=None,
                 category="station"):
        self.id = body_id  # "<system>/<body>"; see world.atlas
        self.category = category  # what kind of body: "planet", "station" or "wreck"
        self.name = name
        self.map_path = map_path  # landing map, or None
        self.obj_type = obj_type
        self.planet_guild = guild
        self.image = load_image(image_path)
        self.position = (x, y)
        self.start_pos = (0, 0)
        self.access = [tuple(point) for point in (access or [])]

    def world_center(self):
        return (
            self.position[0] + self.image.get_width() / 2,
            self.position[1] + self.image.get_height() / 2,
        )

    def access_points(self):
        """World position of each bay. Image coords are from the sprite's top-left."""
        return [(self.position[0] + x, self.position[1] + y) for x, y in self.access]

    def approach_rects(self):
        rects = []
        for x, y in self.access_points():
            rects.append(pygame.Rect(x - APPROACH_RADIUS, y - APPROACH_RADIUS,
                                     APPROACH_RADIUS * 2, APPROACH_RADIUS * 2))
        return rects

    def draw(self, surface, camera):
        if camera.colliderect(self.get_rect()):
            surface.blit(self.image, (self.position[0] - camera.x, self.position[1] - camera.y))

    def get_rect(self):
        return pygame.Rect(self.position[0], self.position[1], self.image.get_width(), self.image.get_height())
