class BaseGoal:
    activity = "getting on with my day"  # spoken as "Right now I'm <activity>."

    def __init__(self, npc):
        self.npc = npc

    def update(self):
        pass
