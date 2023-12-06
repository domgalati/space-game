import pygame

class AnimatedSprite:
    def __init__(self, image_path, frame_dimensions, num_frames):
        self.sprite_sheet = pygame.image.load(image_path).convert_alpha()
        self.frame_width, self.frame_height = frame_dimensions
        self.num_frames = num_frames
        self.current_frame = 0
        self.frames = self.load_frames()

    def load_frames(self):
        frames = []
        for i in range(self.num_frames):
            frame = self.sprite_sheet.subsurface((i * self.frame_width, 0, self.frame_width, self.frame_height))
            frames.append(frame)
        return frames

    def update(self):
        self.current_frame = (self.current_frame + 1) % self.num_frames

    def get_frame(self):
        return self.frames[self.current_frame]
