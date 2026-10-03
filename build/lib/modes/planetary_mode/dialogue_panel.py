"""Conversation UI drawn over the map viewport: portrait and nameplate left, dialogue right.

Skins: "inperson" for face-to-face talk, "comm" (the CRT terminal frame) for remote calls.
"""
import pygame

from dialogue.runner import End, Line, Options
from entities.npcs.portrait import portrait_surface
from util.config import resolve_game_path

CHARS_PER_SECOND = 55
OPTION_KEYS = {getattr(pygame, f"K_{n}"): n - 1 for n in range(1, 10)}
OPTION_KEYS.update({getattr(pygame, f"K_KP{n}"): n - 1 for n in range(1, 10)})
CONTINUE_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_e)
SELECT_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)

DISPOSITION_COLORS = {
    "Hostile": (224, 84, 84),
    "Wary": (226, 164, 84),
    "Neutral": (182, 188, 198),
    "Friendly": (124, 212, 134),
    "Trusted": (112, 202, 232),
}

FRAME_LIGHT = (168, 200, 168)
FRAME_MID = (64, 88, 104)
FRAME_DARK = (24, 28, 56)
SCREEN = (8, 10, 18)


class Skin:
    def __init__(self, font, sizes, portrait, nameplate, column, hint, colors, frame=None, scanlines=False):
        self.font = font
        self.sizes = sizes  # {"name", "text", "small"}
        self.portrait = pygame.Rect(portrait)
        self.nameplate = nameplate
        self.column = pygame.Rect(column)
        self.hint = hint
        self.colors = colors
        self.frame = frame  # image path, or None to draw the in-person frame
        self.scanlines = scanlines


SKINS = {
    "inperson": Skin(
        font="space/assets/fonts/Modern Pixel.otf",
        sizes={"name": 24, "text": 20, "small": 16},
        portrait=(36, 36, 256, 256),
        nameplate=(36, 306),
        column=(336, 36, 512, 436),
        hint=(336, 482),
        colors={
            "name": (236, 244, 236),
            "speaker": FRAME_LIGHT,
            "text": (224, 230, 224),
            "dim": (120, 136, 148),
            "option": (190, 204, 196),
            "selected": (255, 255, 255),
            "highlight": FRAME_DARK,
            "portrait_bg": (26, 32, 56),
        },
    ),
    "comm": Skin(
        font="space/assets/fonts/TeleSys.ttf",
        sizes={"name": 18, "text": 16, "small": 14},
        portrait=(112, 104, 176, 176),
        nameplate=(112, 290),
        column=(316, 100, 452, 300),
        hint=(222, 478),
        colors={
            "name": (170, 240, 180),
            "speaker": (120, 220, 140),
            "text": (96, 204, 128),
            "dim": (46, 120, 80),
            "option": (150, 200, 80),
            "selected": (226, 255, 206),
            "highlight": (16, 48, 28),
            "portrait_bg": (6, 20, 14),
        },
        frame="space/assets/img/objects/terminal_screen.png",
        scanlines=True,
    ),
}

_fonts = {}
_frames = {}


def _font(path, size):
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = pygame.font.Font(resolve_game_path(path), size)
    return _fonts[key]


def wrap(font, text, width):
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        current = ""
        for word in words:
            candidate = f"{current} {word}" if current else word
            if font.size(candidate)[0] <= width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


class DialoguePanel:
    def __init__(self, conversation, size, skin="inperson"):
        self.conversation = conversation
        self.skin = SKINS[skin]
        self.size = size
        self.surface = pygame.Surface(size, pygame.SRCALPHA)
        fonts = self.skin.sizes
        self.name_font = _font(self.skin.font, fonts["name"])
        self.text_font = _font(self.skin.font, fonts["text"])
        self.small_font = _font(self.skin.font, fonts["small"])
        self.line = None
        self.revealed = 0.0
        self.options = None
        self.selected = 0
        self.pending = None  # the event after the current line, fetched once it is fully shown
        self.last_choice = None
        self.notice = None
        self.closed = False
        self._show(conversation.start())

    # State

    @property
    def typing(self):
        return self.line is not None and self.revealed < len(self.line.text)

    def _show(self, event):
        self.notice = None
        self.pending = None
        if isinstance(event, Line):
            self.line = event
            self.revealed = 0.0
            self.options = None
        elif isinstance(event, Options):
            self._offer(event)
        else:
            self.closed = True

    def _offer(self, event):
        self.options = event.choices
        self.selected = 0

    def _line_finished(self):
        self.revealed = float(len(self.line.text))
        event = self.conversation.advance()
        if isinstance(event, Options):
            self._offer(event)
        else:
            self.pending = event

    def _choose(self, index):
        if not self.options or not 0 <= index < len(self.options):
            return
        self.last_choice = self.options[index]
        self.options = None
        self.line = None
        self._show(self.conversation.choose(index))

    def _leave(self):
        if self.conversation.can_exit or isinstance(self.pending, End):
            self.closed = True
        else:
            self.notice = "You can't walk away from this yet."

    # Loop hooks

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.closed:
            return
        if event.key == pygame.K_ESCAPE:
            self._leave()
            return
        if self.typing:
            self._line_finished()
            return
        if self.options:
            if event.key in OPTION_KEYS:
                self._choose(OPTION_KEYS[event.key])
            elif event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.options)
            elif event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.options)
            elif event.key in SELECT_KEYS:
                self._choose(self.selected)
            return
        if event.key in CONTINUE_KEYS:
            if isinstance(self.pending, Line):
                self._show(self.pending)
            else:
                self.closed = True

    def update(self, dt):
        if self.typing:
            self.revealed += dt * CHARS_PER_SECOND
            if self.revealed >= len(self.line.text):
                self._line_finished()

    # Drawing

    def draw(self, target):
        surface = self.surface
        self._draw_frame(surface)
        self._draw_portrait(surface)
        self._draw_nameplate(surface)
        self._draw_column(surface)
        self._draw_hint(surface)
        target.blit(surface, (0, 0))

    def _draw_frame(self, surface):
        width, height = self.size
        if self.skin.frame:
            if self.skin.frame not in _frames:
                _frames[self.skin.frame] = pygame.image.load(resolve_game_path(self.skin.frame)).convert_alpha()
            surface.fill((0, 0, 0, 255))
            surface.blit(_frames[self.skin.frame], (0, 0))
            return
        surface.fill(FRAME_DARK)
        inner = pygame.Rect(10, 10, width - 20, height - 20)
        pygame.draw.rect(surface, SCREEN, inner)
        pygame.draw.rect(surface, FRAME_MID, inner, 2)
        pygame.draw.line(surface, FRAME_LIGHT, inner.topleft, (inner.right - 1, inner.top))
        pygame.draw.line(surface, FRAME_LIGHT, inner.topleft, (inner.left, inner.bottom - 1))
        divider_x = self.skin.column.left - 18
        pygame.draw.line(surface, FRAME_MID, (divider_x, inner.top + 14), (divider_x, inner.bottom - 14), 2)

    def _draw_portrait(self, surface):
        rect = self.skin.portrait
        border = rect.inflate(8, 8)
        pygame.draw.rect(surface, FRAME_MID, border)
        pygame.draw.rect(surface, FRAME_LIGHT, border, 1)
        pygame.draw.rect(surface, self.skin.colors["portrait_bg"], rect)
        npc = self.conversation.npc
        if npc.portrait_recipe:
            image = portrait_surface(npc.portrait_recipe, rect.width)
        elif getattr(npc, "sprite_image", None):
            image = pygame.transform.scale(npc.sprite_image, rect.size)
        else:
            image = None
        if image:
            surface.blit(image, rect.topleft)
        if self.skin.scanlines:
            lines = pygame.Surface(rect.size, pygame.SRCALPHA)
            for y in range(0, rect.height, 3):
                pygame.draw.line(lines, (0, 0, 0, 90), (0, y), (rect.width, y))
            lines.fill((40, 255, 120, 28), special_flags=pygame.BLEND_RGBA_ADD)
            surface.blit(lines, rect.topleft)

    def _draw_nameplate(self, surface):
        colors = self.skin.colors
        x, y = self.skin.nameplate
        npc = self.conversation.npc
        surface.blit(self.name_font.render(self.conversation.name.upper(), False, colors["name"]), (x, y))
        y += self.name_font.get_linesize() + 2
        guild = (npc.guild or "independent").title()
        job = npc.job_title or "Resident"
        surface.blit(self.small_font.render(f"{job}  |  {guild}", False, colors["dim"]), (x, y))
        y += self.small_font.get_linesize() + 2
        species = self.small_font.render(f"{self.conversation.species}  |  ", False, colors["dim"])
        surface.blit(species, (x, y))
        word = self.conversation.disposition
        surface.blit(self.small_font.render(word, False, DISPOSITION_COLORS[word]), (x + species.get_width(), y))

    def _draw_column(self, surface):
        colors = self.skin.colors
        column = self.skin.column
        y = column.top
        text_height = self.text_font.get_linesize()

        if self.last_choice:
            for text in wrap(self.small_font, f"> {self.last_choice}", column.width):
                surface.blit(self.small_font.render(text, False, colors["dim"]), (column.left, y))
                y += self.small_font.get_linesize()
            y += 8

        option_rows = self._option_rows(column.width)
        options_top = column.bottom - len(option_rows) * text_height

        if self.line:
            if self.line.speaker:
                surface.blit(self.name_font.render(self.line.speaker, False, colors["speaker"]), (column.left, y))
                y += self.name_font.get_linesize() + 4
            shown = self.line.text[: int(self.revealed)]
            color = colors["text"] if self.line.speaker else colors["dim"]
            for text in wrap(self.text_font, shown, column.width):
                if y + text_height > options_top - 8:
                    break
                surface.blit(self.text_font.render(text, False, color), (column.left, y))
                y += text_height

        y = options_top
        for index, text, first in option_rows:
            selected = index == self.selected
            if selected and first:
                bar = pygame.Rect(column.left - 8, y - 2, column.width + 16, text_height)
                pygame.draw.rect(surface, colors["highlight"], bar)
            color = colors["selected"] if selected else colors["option"]
            surface.blit(self.text_font.render(text, False, color), (column.left, y))
            y += text_height

    def _option_rows(self, width):
        if not self.options:
            return []
        rows = []
        for index, choice in enumerate(self.options[:9]):
            for n, text in enumerate(wrap(self.text_font, f"{index + 1}. {choice}", width - 16)):
                rows.append((index, text if n == 0 else f"    {text}", n == 0))
        return rows

    def _draw_hint(self, surface):
        colors = self.skin.colors
        if self.notice:
            text, color = self.notice, DISPOSITION_COLORS["Wary"]
        elif self.options:
            text, color = "1-9 or Up/Down + Enter: choose", colors["dim"]
            if self.conversation.can_exit:
                text += "    Esc: leave"
        elif self.typing:
            text, color = "Any key: skip", colors["dim"]
        elif isinstance(self.pending, Line):
            text, color = "Enter: continue", colors["option"]
        else:
            text, color = "Enter: end conversation", colors["option"]
        surface.blit(self.small_font.render(text, False, color), self.skin.hint)
