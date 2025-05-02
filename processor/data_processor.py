from utils.ooda import OODAAgent

import pandas as pd
from datetime import datetime

class DataProcessor(OODAAgent):
    def __init__(self):
        super().__init__("DataProcessor")

    def observe(self, combined_data):
        print(f"[{self.name}] Observing combined data...")
        
        # Validate and extract data from each source
        social_data = combined_data.get("social_data", {}).get("data", {}).get("social_data", [])
        review_data = combined_data.get("review_data", {}).get("data", {})
        survey_data = combined_data.get("survey_data", {}).get("data", {})
        
        # Flatten and prepare data for processing
        processed_data = []
        
        # Process social media data
        if social_data:
            for item in social_data:
                if isinstance(item, dict):
                    item['source'] = 'social'
                    processed_data.append(item)
        
        # Process review site data (need to flatten the nested structure)
        for website, data in review_data.items():
            if isinstance(data, dict) and data.get("status") != "no_data":
                processed_data.append({
                    'source': 'review',
                    'platform': website,
                    'average_rating': data.get('average_rating', 0),
                    'feedback_count': data.get('feedback_count', 0)
                })
        
        # Process survey data
        if survey_data:
            processed_data.append({
                'source': 'survey',
                'average_rating': survey_data.get('average_rating', 0),
                'total_responses': survey_data.get('total_responses', 0)
            })
        
        print(f"[{self.name}] Processed {len(processed_data)} data items from all sources")
        
        # If no data found, return empty DataFrame to avoid errors
        if not processed_data:
            print(f"[{self.name}] Warning: No data found from any source")
            return pd.DataFrame()
            
        # Convert to DataFrame
        df = pd.DataFrame(processed_data)
        
        # Add missing columns if needed
        if 'text' not in df.columns:
            df['text'] = 'No text available'
        if 'timestamp' not in df.columns:
            df['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if 'platform' not in df.columns:
            df['platform'] = 'Unknown'
            
        # Handle complex data types
        for col in df.columns:
            if df[col].apply(lambda x: isinstance(x, (list, dict))).any():
                print(f"[{self.name}] Converting complex column to string: {col}")
                df[col] = df[col].astype(str)
                
        return df

    def orient(self, df):
        print(f"[{self.name}] Orienting data...")
        if df.empty:
            return df
            
        try:
            # Standardize text if it exists
            if 'text' in df.columns:
                df['text'] = df['text'].astype(str).str.lower()
                
            # Convert timestamps to datetime format if possible
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                
            # Standardize platform values
            if 'platform' in df.columns:
                df['platform'] = df['platform'].astype(str).str.strip().str.lower()
                
            return df
            
        except Exception as e:
            print(f"[{self.name}] Error during data orientation: {str(e)}")
            return df

    def decide(self, df):
        print(f"[{self.name}] Making decisions based on data...")
        if df.empty:
            return df
            
        # Add a simple sentiment score for demonstration
        if 'text' in df.columns:
            df['sentiment'] = df['text'].apply(lambda x: self.simple_sentiment_analysis(x))
            
        return df
        
    def simple_sentiment_analysis(self, text):
        """Very simple sentiment analysis for demonstration"""
        positive_words = ['good', 'great', 'excellent', 'amazing', 'love', 'like']
        negative_words = ['bad', 'poor', 'terrible', 'awful', 'hate', 'dislike']
        
        text = str(text).lower()
        pos_count = sum(1 for word in positive_words if word in text)
        neg_count = sum(1 for word in negative_words if word in text)
        
        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        else:
            return 'neutral'

    def act(self, df):
        print(f"[{self.name}] Finalizing data processing...")
        if df.empty:
            return {"cleaned_data": []}
            
        # Convert DataFrame to a dictionary, handling datetime objects
        try:
            # Convert datetime columns to string format to make them JSON serializable
            for col in df.select_dtypes(include=['datetime64']).columns:
                df[col] = df[col].astype(str)
            
            cleaned_data = df.to_dict(orient='records')
            print(f"[{self.name}] Successfully processed {len(cleaned_data)} data records")
            return {"cleaned_data": cleaned_data}
        except Exception as e:
            print(f"[{self.name}] Error during final data conversion: {str(e)}")
            return {"cleaned_data": [], "error": str(e)}