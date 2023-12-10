import pygame
import math

class Planet:
    def __init__(self, name, planet_type, image_path, orbit_radius, angle, center_x, center_y):
        self.name = name
        self.planet_type = planet_type
        self.image = pygame.image.load(image_path)
        self.orbit_radius = orbit_radius
        self.angle = angle
        self.position = self.calculate_position(center_x, center_y)

    def calculate_position(self, center_x, center_y):
        x = center_x + int(self.orbit_radius * math.cos(self.angle))
        y = center_y + int(self.orbit_radius * math.sin(self.angle))
        return x, y

    def draw(self, surface):
        adjusted_pos = (self.position[0] - self.image.get_width() // 2, self.position[1] - self.image.get_height() // 2)
        surface.blit(self.image, adjusted_pos)
