from utils.ooda import OODAAgent

class ReviewSiteCollector(OODAAgent):
    def __init__(self, websites):
        super().__init__("ReviewSiteCollector")
        self.websites = websites if websites else ["Default"]

    def observe(self, data):
        print(f"[{self.name}] Observing review data...")
        
        # Check if data is in expected format
        review_data = data.get("review_data", [])
        if not review_data:
            print(f"[{self.name}] No review data found in input")
            return []
            
        # General compliance for review sites, anonymize sensitive data
        return self.anonymize_data(review_data)

    def anonymize_data(self, data):
        anonymized_data = []
        for item in data:
            if isinstance(item, dict):
                # Create a copy to avoid modifying the original
                clean_item = item.copy()
                # Remove any personal information from reviews
                clean_item.pop('reviewer_name', None)
                clean_item.pop('email', None)
                anonymized_data.append(clean_item)
            else:
                print(f"[{self.name}] Skipping item: {item} (not a dictionary)")
        
        print(f"[{self.name}] Anonymized {len(anonymized_data)} review items")
        return anonymized_data

    def orient(self, data):
        print(f"[{self.name}] Orienting review data...")
        if not data:
            return []
        return data

    def decide(self, data):
        print(f"[{self.name}] Analyzing review data...")
        if not data:
            return {"status": "warning", "message": "No data to analyze"}
            
        # Categorize feedback and summarize by platform
        result = {}
        for website in self.websites:
            site_data = [item for item in data if item.get('platform') == website]
            
            if not site_data:
                result[website] = {
                    "average_rating": 0,
                    "feedback_count": 0,
                    "status": "no_data"
                }
                continue
                
            result[website] = {
                "average_rating": sum([item.get('rating', 0) for item in site_data]) / len(site_data),
                "feedback_count": len(site_data),
                "status": "success"
            }
            
        return result

    def act(self, analysis_result):
        print(f"[{self.name}] Processing complete for review data")
        return analysis_result