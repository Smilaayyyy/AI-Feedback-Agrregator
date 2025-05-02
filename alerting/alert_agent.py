from utils.ooda import OODAAgent

class AlertAgent(OODAAgent):
    def __init__(self):
        super().__init__("AlertAgent")

    def observe(self, analysis):
        return analysis

    def orient(self, analysis):
        return analysis

    def decide(self, analysis):
        return "ALERT: Spike in complaints!"

    def act(self, alert):
        return {"alert": alert}