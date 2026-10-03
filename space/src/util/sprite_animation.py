import pygame

# Angles are pygame's counter-clockwise degrees from the north-facing source frame.
_DIRECTION_ANGLES = {
    "north": 0,
    "northwest": 45,
    "west": 90,
    "southwest": 135,
    "south": 180,
    "southeast": -135,
    "east": -90,
    "northeast": -45,
}


class AnimatedSprite:
    def __init__(self, image_path, frame_dimensions, num_frames, animation_cooldown_ms=0):
        self.sprite_sheet = pygame.image.load(image_path).convert_alpha()
        self.frame_width, self.frame_height = frame_dimensions
        self.num_frames = num_frames
        self.current_frame = 0
        self.frames = self.load_frames()
        self.current_direction = "north"
        self.animation_cooldown_ms = animation_cooldown_ms
        self._last_frame_ms = pygame.time.get_ticks()
        # Cache rotated frames so turning does not re-filter every draw.
        self._oriented = {}
        for index, frame in enumerate(self.frames):
            for direction, angle in _DIRECTION_ANGLES.items():
                key = (index, direction)
                self._oriented[key] = frame if angle == 0 else pygame.transform.rotate(frame, angle)

    def load_frames(self):
        frames = []
        for i in range(self.num_frames):
            frame = self.sprite_sheet.subsurface((i * self.frame_width, 0, self.frame_width, self.frame_height))
            frames.append(frame)
        return frames

    def update(self):
        if self.animation_cooldown_ms:
            now = pygame.time.get_ticks()
            if now - self._last_frame_ms < self.animation_cooldown_ms:
                return
            self._last_frame_ms = now
        self.current_frame = (self.current_frame + 1) % self.num_frames

    def update_direction(self, direction):
        if direction != "none":
            self.current_direction = direction

    def get_frame(self, direction):
        """Return the current animation frame oriented toward `direction`.

        Source art must face north. Cardinal and diagonal headings are produced
        by rotation so exhaust always trails the nose. Rotated surfaces may be
        larger than the source frame; use blit_position() to keep them centered.
        """
        if direction not in _DIRECTION_ANGLES:
            direction = "north"
        return self._oriented[(self.current_frame, direction)]

    def blit_position(self, direction, top_left):
        """Top-left for blitting a possibly expanded rotated frame, centered on the source rect."""
        frame = self.get_frame(direction)
        cx = top_left[0] + self.frame_width // 2
        cy = top_left[1] + self.frame_height // 2
        return frame, frame.get_rect(center=(cx, cy)).topleft
        

        