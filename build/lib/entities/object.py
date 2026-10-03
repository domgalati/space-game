import pygame

class SpaceObject:
    def __init__(self, name, obj_type, image_path, x, y, guild=None):
        self.name = name
        self.obj_type = obj_type
        self.planet_guild = guild
        self.image = pygame.image.load(image_path)
        self.position = (x, y)
        self.start_pos = (0, 0)

    def draw(self, surface, camera):
        if camera.colliderect(self.get_rect()):
            surface.blit(self.image, self.position)

    def get_rect(self):
        return pygame.Rect(self.position[0], self.position[1], self.image.get_width(), self.image.get_height())
