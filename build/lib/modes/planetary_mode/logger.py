import pygame
import pygame.freetype

from util.config import SCREEN_WIDTH


class Logger:
    def __init__(self, log_height, screen_width, font, fallback_font=None, font_path=None):
        self.log_messages = []
        self.log_height = log_height
        self.log_scroll_position = 0
        self.max_log_scroll = 0
        self.font = font
        self.fallback_font = fallback_font or font
        self.log_surface = pygame.Surface((screen_width, log_height))
        # Windraw (and similar display faces) omit most punctuation; fall back per glyph.
        self._missing = set()
        if font_path and fallback_font is not None:
            ft = pygame.freetype.Font(font_path, font.get_height())
            for code in range(32, 127):
                ch = chr(code)
                metrics = ft.get_metrics(ch)
                if not metrics or metrics[0] is None:
                    self._missing.add(ch)

    def _font_for(self, ch):
        return self.fallback_font if ch in self._missing else self.font

    def _text_width(self, text):
        return sum(self._font_for(ch).size(ch)[0] for ch in text)

    def _blit_text(self, text, color, x, y):
        for ch in text:
            glyph = self._font_for(ch).render(ch, False, color)
            self.log_surface.blit(glyph, (x, y))
            x += glyph.get_width()

    def add_log_message(self, message):
        self.log_messages.append(message)
        line_height = max(20, self.font.get_linesize() + 4)
        total_line_count = sum(
            len(self.wrap_text(msg, SCREEN_WIDTH - 220)) for msg in self.log_messages
        )
        self.max_log_scroll = max(0, total_line_count * line_height - self.log_height)
        self.log_scroll_position = self.max_log_scroll

    def wrap_text(self, text, max_width):
        """Split text into lines that fit within max_width."""
        words = text.split(" ")
        lines = []
        current_line = ""

        for word in words:
            candidate = current_line + word + " "
            if self._text_width(candidate) <= max_width or not current_line:
                current_line = candidate
            else:
                lines.append(current_line)
                current_line = "    " + word + " "

        lines.append(current_line)
        return lines

    def draw_log(self):
        self.log_surface.fill((0, 0, 0))

        line_height = max(20, self.font.get_linesize() + 4)
        max_line_width = SCREEN_WIDTH - 220
        color = (255, 255, 255)

        current_line = 0
        for message in self.log_messages:
            for line in self.wrap_text(message, max_line_width):
                y = current_line * line_height - self.log_scroll_position
                if 0 <= y < self.log_height:
                    self._blit_text(line, color, 10, y)
                current_line += 1
