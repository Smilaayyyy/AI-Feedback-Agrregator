from utils.ooda import OODAAgent

class SocialMediaCollector(OODAAgent):
    def __init__(self, platform, format='text'):
        super().__init__("SocialMediaCollector")
        self.platform = platform if platform else "Default"
        self.format = format

    def observe(self, data):
        print(f"[{self.name}] Observing social media data from {self.platform}...")
        
        # Check if data is in expected format
        social_data = data.get("social_data", [])
        if not social_data:
            print(f"[{self.name}] No social media data found in input")
            return {"social_data": [], "platform": self.platform, "format": self.format}
            
        sanitized_data = self.sanitize_data(social_data)
        return self.standardize_format(sanitized_data)

    def sanitize_data(self, data):
        sanitized_data = []
        for item in data:
            if isinstance(item, dict):
                # Create a copy to avoid modifying the original
                clean_item = item.copy()
                # Remove sensitive information
                clean_item.pop('user_name', None)
                clean_item.pop('user_id', None)
                clean_item.pop('email', None)
                clean_item.pop('phone_number', None)
                clean_item.pop('location', None)
                clean_item.pop('media_url', None)
                
                # If media data exists, standardize it
                if 'media' in clean_item:
                    clean_item['media'] = self.convert_media_to_text(clean_item['media'])
                    
                sanitized_data.append(clean_item)
            else:
                print(f"[{self.name}] Skipping item: {item} (not a dictionary)")
                
        print(f"[{self.name}] Sanitized {len(sanitized_data)} social media items")
        return sanitized_data

    def convert_media_to_text(self, media):
        if isinstance(media, str):
            return media
        else:
            return "Media content not available in text format"

    def standardize_format(self, data):
        return {
            "social_data": data,
            "platform": self.platform,
            "format": self.format
        }

    def orient(self, data):
        print(f"[{self.name}] Orienting social media data...")
        return data

    def decide(self, data):
        print(f"[{self.name}] Analyzing social media data...")
        # Process and categorize data here if needed
        return data

    def act(self, analysis_result):
        print(f"[{self.name}] Processing complete for social media data")
        return analysis_result
