import pygame
from .map_manager import MapManager
class InteractionManager:
    def __init__(self, map_manager, logger):
        self.map_manager = map_manager
        self.logger = logger
        self.interacted = False
    pass

    def is_interactable_at(self, position, TILE_SIZE):
        """
        Check if the tile at the given position is in the 'interactable' layer.
        add interactable objects layer in the map file, the layer must always be called "Objects".
        Then place tiles where you want the objects to live. Change the "Name" parameter of the object in tiled.
        """
        y, x = position
        tile_x, tile_y = x // TILE_SIZE, y // TILE_SIZE
        if 0 <= tile_x and 0 <= tile_y:
            objects_layer = self.map_manager.tmx_data.get_layer_by_name('Objects')
            for i in range(len(objects_layer)):
                if objects_layer[i].x == y and objects_layer[i].y == x:
                    objectname = objects_layer[i].name
                    return True, objectname
        return False, None


    def check_for_adjacent_interactables(self, player_position, TILE_SIZE):
        #Check adjacent tiles for interactable items and log a message if found.
        adjacent_positions = [
            (player_position[0], player_position[1] - TILE_SIZE),  # Up
            (player_position[0], player_position[1] + TILE_SIZE),  # Down
            (player_position[0] - TILE_SIZE, player_position[1]),  # Left
            (player_position[0] + TILE_SIZE, player_position[1])   # Right
        ]

        for pos in adjacent_positions:
            is_interactable, objectname = self.is_interactable_at(pos, TILE_SIZE)
            if is_interactable:
                self.logger.add_log_message(f"You approach a {objectname}. Press E to interact. Testing message display length. This message is really long.")
                break  # Add this if you only want one message per move
            
    def interact(self, player_position, TILE_SIZE):
        #Perform an interaction with an adjacent interactable object.
        ## Copies code from check_for_adjacent_interactables, needs to be optimized.
        adjacent_positions = [
                    (player_position[0], player_position[1] - TILE_SIZE),  # Up
                    (player_position[0], player_position[1] + TILE_SIZE),  # Down
                    (player_position[0] - TILE_SIZE, player_position[1]),  # Left
                    (player_position[0] + TILE_SIZE, player_position[1])   # Right
                ]
        for pos in adjacent_positions:
            is_interactable, objectname = self.is_interactable_at(pos, TILE_SIZE)
            if is_interactable:
                self.handle_interaction_with(objectname)

    def handle_interaction_with(self, objectname):
        """
        Handle specific interactions based on the object name.
        """
        if objectname == "Docking Terminal":
            self.docking_terminal()
            pass
        # Add more conditions for different objects

    def docking_terminal(self):
        # Load the docking terminal interface image
        terminal_image = pygame.image.load("space/assets/img/objects/terminal_screen.png").convert_alpha() 
        # Resize the image to fit the map_surface
        #terminal_image = pygame.transform.scale(terminal_image, (SCREEN_WIDTH - self.sidebar_width, SCREEN_HEIGHT - self.log_height))   
        # Draw the image onto the map_surface
        self.map_manager.map_surface.blit(terminal_image, (0, 0))
        self.interacted = True
        # Call method to handle player input and feedback (to be implemented)
        #self.handle_terminal_input()
        pass