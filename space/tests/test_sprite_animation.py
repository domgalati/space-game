import os

import pygame
import pytest

from util.config import resolve_game_path
from util.sprite_animation import AnimatedSprite, _DIRECTION_ANGLES

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


@pytest.fixture(scope="module", autouse=True)
def _pygame():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


@pytest.fixture
def barge():
    path = resolve_game_path("space/assets/img/barge6frame.png")
    return AnimatedSprite(path, (48, 48), 6, animation_cooldown_ms=90)


def test_barge_sheet_loads_six_frames(barge):
    assert barge.num_frames == 6
    assert len(barge.frames) == 6
    assert barge.frames[0].get_size() == (48, 48)


@pytest.mark.parametrize("direction", list(_DIRECTION_ANGLES))
def test_all_directions_produce_visible_frames(barge, direction):
    barge.current_frame = 2
    frame = barge.get_frame(direction)
    bounds = frame.get_bounding_rect()
    assert bounds.width > 10
    assert bounds.height > 10


@pytest.mark.parametrize("direction", list(_DIRECTION_ANGLES))
def test_rotated_frames_stay_centered_on_source_rect(barge, direction):
    barge.current_frame = 2
    top_left = (100, 200)
    frame, blit_pos = barge.blit_position(direction, top_left)
    rect = frame.get_rect(topleft=blit_pos)
    assert rect.center == (100 + 24, 200 + 24)


def test_exhaust_frames_differ(barge):
    barge.current_frame = 0
    dim = pygame.image.tostring(barge.get_frame("north"), "RGBA")
    barge.current_frame = 2
    bright = pygame.image.tostring(barge.get_frame("north"), "RGBA")
    assert dim != bright
