"""Drawing for fights: beams, the target bracket and intent glyphs over scanned ships.

The target's readout is the enemy panel (ui.enemy_panel)."""
import pygame

INTENT_GLYPHS = {
    "fire": "(*)", "close": ">>", "retreat": "<<", "search": "?", "ping": "((", "hold": "==", "patrol": "..",
}
INTENT_WORDS = {
    "fire": "FIRING NEXT TURN", "close": "CLOSING IN", "retreat": "RETREATING", "search": "SEARCHING",
    "ping": "PINGING NEXT TURN", "hold": "HOLDING RANGE", "patrol": "PATROLLING",
}
BRACKET = 30  # half-size of the target bracket
BRACKET_ARM = 9
BEAM_WIDTH = 3
SPARK = "*"


def _screen(point, camera):
    return int(point[0] - camera.x), int(point[1] - camera.y)


def draw_shots(screen, camera, shots, now_ms, font):
    for shot in shots:
        if now_ms > shot.until_ms:
            continue
        start, end = _screen(shot.start, camera), _screen(shot.end, camera)
        pygame.draw.line(screen, shot.colour, start, end, BEAM_WIDTH)
        if not shot.hit:
            spark = font.render(SPARK, True, shot.colour)
            screen.blit(spark, spark.get_rect(center=end))


def draw_bracket(screen, centre, colour):
    x, y = centre
    for sx in (-1, 1):
        for sy in (-1, 1):
            corner = (x + sx * BRACKET, y + sy * BRACKET)
            pygame.draw.line(screen, colour, corner, (corner[0] - sx * BRACKET_ARM, corner[1]), 2)
            pygame.draw.line(screen, colour, corner, (corner[0], corner[1] - sy * BRACKET_ARM), 2)


def intent_label(intent):
    kind, chance = intent
    glyph = INTENT_GLYPHS.get(kind, "..")
    return f"{glyph} {round(chance * 100)}%" if kind == "fire" and chance is not None else glyph


def draw_intent(screen, centre, intent, colour, font):
    label = font.render(intent_label(intent), True, colour)
    screen.blit(label, label.get_rect(midbottom=(centre[0], centre[1] - BRACKET - 4)))
