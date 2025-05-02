from utils.ooda import OODAAgent

class ReportAgent(OODAAgent):
    def __init__(self):
        super().__init__("ReportAgent")

    def observe(self, analysis):
        return analysis

    def orient(self, analysis):
        return analysis

    def decide(self, analysis):
        return "Summary Report"

    def act(self, report):
        return {"report": report}