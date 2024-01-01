import pygame

class Terminal:
    def __init__(self, terminal_type):
        self.terminal_type = terminal_type
        self.input_buffer = ""
        self.output_buffer = []
        self.active = False
        self.cursor_visible = True
        self.blink_timer = 0
        self.blink_interval = 50  # milliseconds
        self.max_lines = 13  # Adjust as needed for your map_surface size

    def activate(self):
        self.active = True
        # Clear buffers or set up terminal-specific data

    def deactivate(self):
        self.active = False

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

    def execute_command(self, command):
        # Add the entered command to the output_buffer
        self.output_buffer.append(f"> {command}")
        
        # Process the command
        # For example, let's just echo the command back
        result = f"Executed: {command}"
        self.output_buffer.append(result)
        # ... actual command execution logic ...

        if len(self.output_buffer) > self.max_lines:
            self.output_buffer = self.output_buffer[-self.max_lines:]

    def update(self, dt):
        if self.active:
            self.blink_timer += dt
            if self.blink_timer * 200 >= self.blink_interval:
                self.blink_timer = 0
                self.cursor_visible = not self.cursor_visible

    def display(self, surface):
        if self.active:
            font = pygame.font.Font("space/assets/fonts/TeleSys.ttf", 16)

            y_position = 100  # Adjust as needed

            for line in self.output_buffer:
                text_surface = font.render(line, True, (46, 139, 87))
                surface.blit(text_surface, (100, y_position))
                y_position += text_surface.get_height() + 5

            # Combine the input buffer text with the cursor for rendering
            input_text = f"> {self.input_buffer}"
            if self.cursor_visible:
                input_text += "_"  # Append the cursor symbol

            input_surface = font.render(input_text, True, (107, 142, 35))
            surface.blit(input_surface, (100, y_position))
