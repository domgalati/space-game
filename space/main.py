from state_manager import StateManager

def main():
    state_manager = StateManager()
    state_manager.change_state("Overworld")

    while True:
        state_manager.update()
        state_manager.render()

if __name__ == "__main__":
    main()