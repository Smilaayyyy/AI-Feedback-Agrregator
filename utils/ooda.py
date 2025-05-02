class OODAAgent:
    def __init__(self, name):
        self.name = name
    
    def observe(self, data):
        """Observe phase: data collection, filtering"""
        raise NotImplementedError("Observe method not implemented")
    
    def orient(self, data):
        """Orient phase: contextualize the data"""
        raise NotImplementedError("Orient method not implemented")
    
    def decide(self, data):
        """Decide phase: make decisions based on oriented data"""
        raise NotImplementedError("Decide method not implemented")
    
    def act(self, data):
        """Act phase: implement decisions"""
        raise NotImplementedError("Act method not implemented")
    
    def run(self, input_data):
        """Execute the full OODA loop with proper error handling"""
        try:
            print(f"[{self.name}] Starting OODA loop...")
            if not input_data:
                print(f"[{self.name}] Warning: Empty input data")
                return {"status": "warning", "message": "Empty input data", "data": []}
            
            # Execute the OODA loop
            observed_data = self.observe(input_data)
            oriented_data = self.orient(observed_data)
            decision = self.decide(oriented_data)
            action_result = self.act(decision)
            
            print(f"[{self.name}] OODA loop completed successfully")
            return {"status": "success", "data": action_result}
            
        except Exception as e:
            print(f"[{self.name}] Error in OODA loop: {str(e)}")
            return {"status": "error", "message": str(e), "data": []}
