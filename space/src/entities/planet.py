import math

import pygame

from util.images import load_image

# Corridor around the painted starport. Radius, so the ship has to be on that rim.
APPROACH_RADIUS = 160
# Style A disks fill 268/288 of the image's half-width; the limb dots sit just outside.
DISK_FRACTION = 268 / 288
# Style A disks paint the pad on the lit rim (same vector the glyph generator uses).
_DOCK_LEN = math.hypot(0.62, 0.48)
DOCK_XY = (-0.62 / _DOCK_LEN * 0.84, -0.48 / _DOCK_LEN * 0.84)


class Planet:
    def __init__(self, body_id, name, planet_type, planet_guild, image_path, orbit_radius, angle, center_x, center_y,
                 start_pos=(0, 0), map_path=None):
        self.id = body_id  # "<system>/<body>"; see world.atlas
        self.name = name
        self.map_path = map_path  # landing map, or None
        self.planet_type = planet_type
        self.planet_guild = planet_guild
        self.image = load_image(image_path)
        self.radius = self.image.get_width() / 2 * DISK_FRACTION
        self.orbit_radius = orbit_radius
        self.angle = angle
        self.position = self.calculate_position(center_x, center_y)
        self.start_pos = start_pos

    def calculate_position(self, center_x, center_y):
        x = center_x + int(self.orbit_radius * math.cos(self.angle))
        y = center_y + int(self.orbit_radius * math.sin(self.angle))
        return x, y

    def get_rect(self):
        # Assuming the image's center is at the planet's position
        rect_x = self.position[0] - self.image.get_width() // 2
        rect_y = self.position[1] - self.image.get_height() // 2
        return pygame.Rect(rect_x, rect_y, self.image.get_width(), self.image.get_height())

    def contains(self, point):
        """True over the disk itself, not the empty corners of its image."""
        return math.dist(point, self.position) <= self.radius

    def beacon_points(self):
        """World position of the starport painted on the disk."""
        half = self.image.get_width() / 2
        return [(
            self.position[0] + DOCK_XY[0] * half,
            self.position[1] + DOCK_XY[1] * half,
        )]

    def approach_rects(self):
        rects = []
        for x, y in self.beacon_points():
            rects.append(pygame.Rect(x - APPROACH_RADIUS, y - APPROACH_RADIUS,
                                     APPROACH_RADIUS * 2, APPROACH_RADIUS * 2))
        return rects

    def draw(self, surface, camera):
        if not camera.colliderect(self.get_rect()):
            return
        adjusted_pos = (
            self.position[0] - self.image.get_width() // 2 - camera.x,
            self.position[1] - self.image.get_height() // 2 - camera.y,
        )
        surface.blit(self.image, adjusted_pos)
