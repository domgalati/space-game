import pygame
from .terminals import docking_terminal

class Terminal:
    def __init__(self, terminal_type, planetary_mode, planet_name):
        self.terminal_type = terminal_type
        self.planetary_mode = planetary_mode
        self.planet_name = planet_name  # Store the planet name
        self.input_buffer = ""
        self.output_buffer = []
        self.active = False
        self.cursor_visible = True
        self.blink_timer = 0
        self.blink_interval = 50  # milliseconds
        self.max_lines = 13  # Adjust as needed for your map_surface size
        self.scroll_position = 0

    def activate(self):
        self.active = True
        # Clear buffers or set up terminal-specific data

    def deactivate(self):
        self.active = False
        ## Call deactivate_terminal() from PlanetaryMode
        if self.planetary_mode:
            self.planetary_mode.deactivate_terminal()

    def depart(self):
        if self.planetary_mode:
            self.planetary_mode.return_to_star_system_mode()

    def process_input(self, event):
        if self.active:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    # Execute the command in the input buffer
                    self.execute_command(self.input_buffer)
                    self.input_buffer = ""  # Clear the buffer after execution
                elif event.key == pygame.K_BACKSPACE:
                    # Handle backspace for deleting the last character
                    self.input_buffer = self.input_buffer[:-1]
                else:
                    # Add the character to the input buffer
                    # You might want to filter which characters are allowed
                    self.input_buffer += event.unicode

    def wrap_text(self, text, max_length):
        wrapped_lines = []
        while len(text) > max_length:
            # Find the nearest space before the max_length
            if text.find('\n') > 0: #if text contains \n
                split_index = text.rfind('\n', 0, max_length)
            else:
                split_index = text.rfind(' ', 0, max_length)
            if split_index == -1:  # No spaces found, force split
                split_index = max_length

            # Split the line and add to the list
            wrapped_lines.append(text[:split_index])
            text = text[split_index:].lstrip()  # Remove leading spaces from the rest

        wrapped_lines.append(text)  # Add the last part of the text
        return wrapped_lines

    def execute_command(self, command):
        self.output_buffer.append(f"> {command}")
        # Process the command based on terminal type
        if self.terminal_type == "docking":
            result = docking_terminal.handle_command(command, self.planet_name)
        else:
            # Default or other terminal types
            result = "Command not recognized in this terminal."

        if command == "exit":
            self.deactivate()
       
        if command == "depart":
            self.depart()

        max_line_length = 80  # Set your desired maximum line length here
        wrapped_result = self.wrap_text(result, max_line_length)
        self.output_buffer.extend(wrapped_result)


    def update(self, dt):
        if self.active:
            self.blink_timer += dt
            if self.blink_timer * 200 >= self.blink_interval:
                self.blink_timer = 0
                self.cursor_visible = not self.cursor_visible

    def flatten_output_buffer(self):
        # Flatten the output buffer with respect to newline characters
        flattened_output = []
        for line in self.output_buffer:
            flattened_output.extend(line.split('\n'))
        return flattened_output

    def display(self, surface):
        if self.active:
            font = pygame.font.Font("space/assets/fonts/TeleSys.ttf", 16)
            y_position = 100  # Adjust as needed

            flattened_output = self.flatten_output_buffer()
            total_line_count = len(flattened_output)

            start_line = max(0, total_line_count - self.max_lines - self.scroll_position)
            end_line = min(start_line + self.max_lines, total_line_count)

            for line in flattened_output[start_line:end_line]:
                text_surface = font.render(line, True, (46, 139, 87))
                surface.blit(text_surface, (100, y_position))
                y_position += text_surface.get_height() + 5

            # Combine the input buffer text with the cursor for rendering
            input_text = f"> {self.input_buffer}"
            if self.cursor_visible:
                input_text += "_"  # Append the cursor symbol

            input_surface = font.render(input_text, True, (107, 142, 35))
            surface.blit(input_surface, (100, y_position))

    def scroll_up(self):
        self.scroll_position = min(self.scroll_position + 1, max(0, len(self.flatten_output_buffer()) - self.max_lines))

    def scroll_down(self):
        self.scroll_position = max(self.scroll_position - 1, 0)
