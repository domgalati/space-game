import pygame

_images = {}


def load_image(path):
    """Load a PNG once. Flight bodies are thousands of pixels square and several share a file."""
    if path not in _images:
        image = pygame.image.load(path)
        # convert_alpha needs a display mode; tests build star systems without one.
        _images[path] = image.convert_alpha() if pygame.display.get_surface() else image
    return _images[path]
