from overworld import OverworldState
from dungeon import DungeonState

class StateManager:
    def __init__(self):
        self.states = {
            "Overworld": OverworldState(),
            "Dungeon": DungeonState()
        }
        self.current_state = None

    def change_state(self, state_name):
        self.current_state = self.states.get(state_name)

    def update(self):
        if self.current_state:
            self.current_state.update()

    def render(self):
        if self.current_state:
            self.current_state.render()