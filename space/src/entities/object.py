import pygame

class SpaceObject:
    def __init__(self, name, obj_type, image_path, x, y):
        self.name = name
        self.obj_type = obj_type
        self.image = pygame.image.load(image_path)
        self.position = (x, y)

    def draw(self, surface, camera):
        if camera.colliderect(self.get_rect()):
            surface.blit(self.image, self.position)

    def get_rect(self):
        return pygame.Rect(self.position[0], self.position[1], self.image.get_width(), self.image.get_height())
