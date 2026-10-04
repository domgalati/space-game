import pygame
from util.config import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, resolve_game_path
from util.keys import held_direction
from modes.transitions import Depart
from .logger import Logger
from .map_manager import MapManager
from .ui_planetary import UI_Planetary
from .interaction_manager import InteractionManager
from .terminal import Terminal, bezel_path
from util.economy.economy import Economy
from util.economy.news_feed import NewsFeed
from dialogue.conversation import Conversation
from world.roster import NPCRoster
from world.world_state import WorldState
from .npc_manager import NPCManager
from .dialogue_panel import DialoguePanel

CAMERA_DEADZONE = 0.3  # share of the view the player can roam before the camera follows
MOVE_REPEAT = 0.12  # seconds between steps while a direction key is held

class PlanetaryMode:
    def __init__(self, selected_planet, player, world_state=None):
        self.planet = selected_planet
        self.player = player
        player.location.body = selected_planet.id
        self.world_state = world_state or WorldState()
        self.player_sprite = pygame.image.load(
            resolve_game_path("space/assets/img/objects/player.png")
        ).convert_alpha()
        self.ui_planetary = UI_Planetary()  # Create an instance of UI_Planetary       
        # Windraw Aesthetic for the event log (personal-use license).
        # https://www.1001fonts.com/windraw-aesthetic-font.html
        # Cairopixel fills in punctuation Windraw does not ship.
        log_font_path = resolve_game_path("space/assets/fonts/Windraw Aesthetic Italic.ttf")
        self.font = pygame.font.Font(log_font_path, 16)
        log_fallback = pygame.font.Font(
            resolve_game_path("space/assets/fonts/Cairopixel.ttf"), 16
        )
        self.logger = Logger(
            log_height=200,
            screen_width=SCREEN_WIDTH,
            font=self.font,
            fallback_font=log_fallback,
            font_path=log_font_path,
        )
        self.camera = pygame.Rect(0, 0, SCREEN_WIDTH - self.ui_planetary.sidebar_width, SCREEN_HEIGHT - self.logger.log_height)
        self.map_surface = pygame.Surface((SCREEN_WIDTH - self.ui_planetary.sidebar_width, SCREEN_HEIGHT - self.logger.log_height))
        self.map_manager = MapManager(self.planet.map_path)
        self.log_messages = []
        self.player_position = self._player_start()
        self._center_camera()
        self.map_manager.initialize_animation_data()
        self.news_feed = NewsFeed(self.world_state)
        self.economy = Economy(
            selected_planet.id, self.world_state.markets_data(), feed=self.news_feed, events=self.world_state.events
        )
        self.economy.set_log_callback(self.logger.add_log_message)
        self.news_feed.advance()
        self.economy.market_news()
        self.news_feed.observe(selected_planet.id, self.economy.goods())
        self.npc_manager = NPCManager(self.map_manager, selected_planet, NPCRoster(self.world_state))
        self.interaction_manager = InteractionManager(
            self.map_manager, self.npc_manager, self.logger, economy=self.economy
        )
        self.interaction_manager.set_terminal_callback(self.activate_terminal)
        self.interaction_manager.set_conversation_callback(self.start_conversation)
        self.terminal = None
        self.conversation_panel = None
        self.pending = None  # transition for update() to hand back, e.g. Depart from the docking terminal
        self.elapsed = 0.0  # seconds this mode has been updated; paces held keys
        self.next_move_time = 0
        self._blocked_move_logged = False

        self.npc_layer = pygame.surface.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.player_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.interaction_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.interaction_active = False  # Flag to indicate if an interaction layer is active


    def _player_start(self):
        """Generated maps mark a "Player Start" spawn; hand-made ones use the planet's start_pos."""
        try:
            spawns = self.map_manager.tmx_data.get_layer_by_name("Spawns")
        except ValueError:
            return list(self.planet.start_pos)
        for obj in spawns:
            if obj.name == "Player Start":
                return [int(obj.x), int(obj.y)]
        return list(self.planet.start_pos)

    def is_tile_walkable(self, row, col):
        """True where the "walkable" layer has a tile. The layer is stored rows first."""
        return self.map_manager.tmx_data.get_layer_by_name("walkable").data[row][col] != 0

    def _player_center(self):
        return self.player_position[0] + TILE_SIZE // 2, self.player_position[1] + TILE_SIZE // 2

    def _center_camera(self):
        self.camera.center = self._player_center()
        self._clamp_camera()

    def update_camera(self):
        """Follow the player once they leave a dead zone around the view's center."""
        px, py = self._player_center()
        zone = self.camera.inflate(
            -int(self.camera.width * (1 - CAMERA_DEADZONE)),
            -int(self.camera.height * (1 - CAMERA_DEADZONE)),
        )
        if px < zone.left:
            self.camera.x -= zone.left - px
        elif px >= zone.right:
            self.camera.x += px - zone.right + 1
        if py < zone.top:
            self.camera.y -= zone.top - py
        elif py >= zone.bottom:
            self.camera.y += py - zone.bottom + 1
        self._clamp_camera()

    def _clamp_camera(self):
        """Keep the view on the map; a map smaller than the view is centered in it."""
        data = self.map_manager.tmx_data
        map_w, map_h = data.width * data.tilewidth, data.height * data.tileheight
        if map_w <= self.camera.width:
            self.camera.x = (map_w - self.camera.width) // 2
        else:
            self.camera.x = max(0, min(self.camera.x, map_w - self.camera.width))
        if map_h <= self.camera.height:
            self.camera.y = (map_h - self.camera.height) // 2
        else:
            self.camera.y = max(0, min(self.camera.y, map_h - self.camera.height))

    def _try_move(self, dx, dy):
        new_position = [self.player_position[0] + dx, self.player_position[1] + dy]
        tile_x, tile_y = new_position[0] // TILE_SIZE, new_position[1] // TILE_SIZE
        if self.is_tile_walkable(tile_y, tile_x):
            self.player_position = new_position
            self._blocked_move_logged = False
            self.update_camera()
            player_tile = (tile_x, tile_y)
            # Advance NPC turns first; adjacent NPCs freeze so E stays valid.
            self.npc_manager.update(
                self.camera.x,
                self.camera.y,
                self.camera.width,
                self.camera.height,
                player_tile=player_tile,
            )
            self.interaction_manager.check_for_adjacent_interactables(
                self.player_position, TILE_SIZE
            )
            return True

        if not self._blocked_move_logged:
            self.logger.add_log_message("Your path is blocked")
            self._blocked_move_logged = True
        return False

    def handle_input(self, events):
        if self.terminal and self.terminal.active:
            for event in events:
                if event.type == pygame.KEYDOWN:
                    self.terminal.process_input(event)
                elif event.type == pygame.MOUSEWHEEL:
                    if event.y > 0:
                        self.terminal.scroll_up()
                    elif event.y < 0:
                        self.terminal.scroll_down()
            return

        if self.conversation_panel:
            for event in events:
                self.conversation_panel.handle_event(event)
            if self.conversation_panel.closed:
                self.end_conversation()
            # A movement key held through the conversation shouldn't step the moment it closes.
            self.next_move_time = self.elapsed + MOVE_REPEAT
            return

        for event in events:
            if event.type == pygame.MOUSEWHEEL:
                self.logger.log_scroll_position -= event.y * 20
                self.logger.log_scroll_position = max(0, min(self.logger.log_scroll_position, self.logger.max_log_scroll))
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_e:
                self.interaction_manager.interact(self.player_position, TILE_SIZE)
                if self.conversation_panel or (self.terminal and self.terminal.active):
                    return

        dx, dy = held_direction(pygame.key.get_pressed())
        dx, dy = dx * TILE_SIZE, dy * TILE_SIZE
        if dx == 0 and dy == 0:
            self.next_move_time = 0  # allow an immediate step on the next press
            self._blocked_move_logged = False
            return

        if self.elapsed >= self.next_move_time:
            self._try_move(dx, dy)
            self.next_move_time = self.elapsed + MOVE_REPEAT

    def update(self, events, dt):
        """One frame, `dt` seconds long. Returns a transition (modes.transitions) or None."""
        self.elapsed += dt
        self.map_manager.update_animations(dt * 1000)  # Tiled frame durations are in ms
        if self.terminal and self.terminal.active:
            self.terminal.update(dt)
        if self.conversation_panel:
            self.conversation_panel.update(dt)
        self.handle_input(events)
        self.update_camera()
        self.ui_planetary.update_player_stats(self.player)
        transition, self.pending = self.pending, None
        return transition

    def draw_player(self):
        self.player_layer.fill((0, 0, 0, 0))
        player_x = self.player_position[0] - self.camera.x
        player_y = self.player_position[1] - self.camera.y
        self.player_layer.blit(self.player_sprite, (player_x, player_y))

    def draw(self, screen):
        screen.fill((0, 0, 0))
        self.map_manager.draw_map(self.map_surface, self.camera)

        self.npc_manager.draw(self.npc_layer, self.camera)
        self.map_surface.blit(self.npc_layer, (0, 0))  # Draw the NPC layer onto the map surface

        self.draw_player()
        self.map_surface.blit(self.player_layer, (0, 0))

        if self.interaction_active:
            self.map_surface.blit(self.interaction_layer, (0, 0))

        if self.conversation_panel:
            self.conversation_panel.draw(self.map_surface)

        self.ui_planetary.draw_sidebar()
        self.logger.draw_log()
        screen.blit(self.map_surface, (0, 0))
        screen.blit(self.ui_planetary.sidebar_surface, (SCREEN_WIDTH - self.ui_planetary.sidebar_width, 0))
        screen.blit(self.logger.log_surface, (0, SCREEN_HEIGHT - self.logger.log_height))
        
        if self.terminal and self.terminal.active:
            self.terminal.display(screen)

    def notice(self, text):
        """A message for the player from outside this mode, such as "Game saved"."""
        self.logger.add_log_message(text)

    def return_to_star_system_mode(self):
        self.pending = Depart(self.planet)

    def activate_terminal(self, terminal_type="docking"):
        self.interaction_layer.fill((0, 0, 0, 0))
        terminal_image = pygame.image.load(bezel_path(terminal_type)).convert_alpha()
        self.interaction_layer.blit(terminal_image, (0, 0))
        self.interaction_active = True
        self.terminal = Terminal(terminal_type=terminal_type, planetary_mode=self, planet_name=self.planet)
        self.terminal.activate()

    def start_conversation(self, npc):
        conversation = Conversation(
            npc, self.player, self.world_state, economy=self.economy, location=self.planet.name
        )
        self.conversation_panel = DialoguePanel(conversation, self.map_surface.get_size())
        if self.conversation_panel.closed:
            self.end_conversation()

    def end_conversation(self):
        for line in self.conversation_panel.conversation.summary_lines():
            self.logger.add_log_message(line)
        self.conversation_panel = None

    def deactivate_terminal(self):
        self.terminal = None
        self.interaction_active = False