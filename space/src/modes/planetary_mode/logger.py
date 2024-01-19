import pygame
from util.config import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE

class Logger:
    def __init__(self, log_height, screen_width, font):
        self.log_messages = []
        self.log_height = log_height
        self.log_scroll_position = 0
        self.max_log_scroll = 0
        self.font = font
        self.log_surface = pygame.Surface((screen_width, log_height))

    def add_log_message(self, message):
        self.log_messages.append(message)
        total_line_count = sum(len(self.wrap_text(msg, SCREEN_WIDTH - 20, self.font)) for msg in self.log_messages)
        self.max_log_scroll = max(0, total_line_count * 20 - self.log_height)
        self.log_scroll_position = self.max_log_scroll

    def wrap_text(self, text, max_width, font):
        """
        Splits the text into lines so that each line fits within the max_width.
        Returns a list of lines.
        """
        words = text.split(' ')
        lines = []
        current_line = ""

        for word in words:
            # Check the width of the line with the new word added
            line_width = font.size(current_line + word)[0]
            if line_width <= max_width:
                current_line += word + " "
            else:
                # If the line is too long, start a new line
                lines.append(current_line)
                current_line = "    " + word + " "  # Indent wrapped lines

        # Add the last line
        lines.append(current_line)
        return lines

    def draw_log(self):
        self.log_surface.fill((0, 0, 0))  # Clear the log surface

        font = pygame.font.Font("space/assets/fonts/OfficeCodePro-Light.ttf", 16)
        line_height = 20  # Adjust as needed for your font size
        max_line_width = SCREEN_WIDTH - 20  # Adjust as needed for your sidebar size

        current_line = 0
        for message in self.log_messages:
            wrapped_lines = self.wrap_text(message, max_line_width, font)
            for line in wrapped_lines:
                if current_line * line_height >= self.log_scroll_position and current_line * line_height < self.log_scroll_position + self.log_height:
                    text_surface = font.render(line, True, (255, 255, 255))
                    self.log_surface.blit(text_surface, (10, current_line * line_height - self.log_scroll_position))
                current_line += 1
