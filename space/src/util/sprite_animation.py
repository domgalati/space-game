import pygame

class AnimatedSprite:
    def __init__(self, image_path, frame_dimensions, num_frames):
        self.sprite_sheet = pygame.image.load(image_path).convert_alpha()
        self.frame_width, self.frame_height = frame_dimensions
        self.num_frames = num_frames
        self.current_frame = 0
        self.frames = self.load_frames()
        self.current_direction = "north"

    def load_frames(self):
        frames = []
        for i in range(self.num_frames):
            frame = self.sprite_sheet.subsurface((i * self.frame_width, 0, self.frame_width, self.frame_height))
            frames.append(frame)
        return frames

    def update(self):
        self.current_frame = (self.current_frame + 1) % self.num_frames

    def update_direction(self, direction):
        if direction != "none":
            self.current_direction = direction

    def get_frame(self, direction):
        frame = self.frames[self.current_frame]
        if direction == "north":
            return frame
        elif direction == "south":
            return pygame.transform.flip(frame, False, True)
        elif direction == "west":
            return pygame.transform.rotate(frame, 90)
        elif direction == "east":
            return pygame.transform.rotate(frame, -90)
        # Add transformations for diagonal directions
        elif direction == "northwest":
            return pygame.transform.rotate(frame, 45)
        elif direction == "northeast":
            return pygame.transform.rotate(frame, -45)
        elif direction == "southwest":
            return pygame.transform.rotate(frame, 135)
        elif direction == "southeast":
            return pygame.transform.rotate(frame, -135)
        else:
            return frame
        

        