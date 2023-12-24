import pygame

class InteractionMenu:
    def __init__(self, options, position, font, font_size=30, font_color=(255, 255, 255)):
        self.options = options
        self.selected_index = 0
        self.position = position
        self.font = pygame.font.Font(font, font_size)
        self.font_color = font_color
        self.menu_items = self.create_menu_items()
        self.active = False
        self.selected_action = None

    def create_menu_items(self):
        menu_items = []
        for option in self.options:
            text_surface = self.font.render(option, True, self.font_color)
            menu_items.append(text_surface)
        return menu_items

    def navigate(self, direction):
        if direction == "up":
            self.selected_index = max(0, self.selected_index - 1)
        elif direction == "down":
            self.selected_index = min(len(self.options) - 1, self.selected_index + 1)

    def draw(self, screen):
        if not self.active:
            return

        for i, menu_item in enumerate(self.menu_items):
            item_pos = (self.position[0], self.position[1] + i * 40)
            screen.blit(menu_item, item_pos)
            if i == self.selected_index:
                pygame.draw.rect(screen, self.font_color, (*item_pos, menu_item.get_width(), menu_item.get_height()), 2)

    def update(self, event):
        if not self.active:
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.navigate("up")
            elif event.key == pygame.K_DOWN:
                self.navigate("down")
            elif event.key == pygame.K_RETURN:
                self.selected_action = self.options[self.selected_index]
                self.active = False
                return self.selected_action
        return None

    def activate(self):
        self.active = True
        self.selected_index = 0
