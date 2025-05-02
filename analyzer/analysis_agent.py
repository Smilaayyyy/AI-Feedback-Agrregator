from utils.ooda import OODAAgent
from sklearn.feature_extraction.text import TfidfVectorizer
from datetime import datetime, date
import pandas as pd
import re
from collections import Counter
import json

class AnalysisAgent(OODAAgent):
    def __init__(self):
        super().__init__("AnalysisAgent")
        # Initialize NLP components with proper error handling
        try:
            import nltk
            from textblob import TextBlob
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            self.nlp_available = True
            print(f"[{self.name}] NLP libraries successfully loaded")
        except ImportError as e:
            print(f"[{self.name}] Warning: NLP libraries not available - {str(e)}")
            self.nlp_available = False

    def observe(self, cleaned_data):
        print(f"[{self.name}] Observing cleaned data...")
        
        # Validate the input data structure
        if not cleaned_data or "cleaned_data" not in cleaned_data.get("data", {}):
            print(f"[{self.name}] Warning: Expected cleaned_data not found in input")
            return []
            
        data = cleaned_data["data"]["cleaned_data"]
        if not data:
            print(f"[{self.name}] Warning: Empty data received")
            return []
            
        print(f"[{self.name}] Received {len(data)} data points for analysis")
        return data

    def orient(self, data):
        print(f"[{self.name}] Orienting data for analysis...")
        if not data:
            return pd.DataFrame()
            
        try:
            # Convert data to DataFrame
            df = pd.DataFrame(data)
            
            # Add required columns if missing
            if 'text' not in df.columns:
                print(f"[{self.name}] Warning: 'text' column missing, adding default values")
                df['text'] = 'No text available'
                
            if 'timestamp' not in df.columns:
                print(f"[{self.name}] Warning: 'timestamp' column missing, adding current timestamp")
                df['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
            if 'platform' not in df.columns:
                print(f"[{self.name}] Warning: 'platform' column missing, adding default values")
                df['platform'] = 'Unknown'
                
            # Convert columns to appropriate types
            df['text'] = df['text'].astype(str)
            
            try:
                # Ensure timestamp is datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                # Handle any NaT values
                df['timestamp'] = df['timestamp'].fillna(pd.Timestamp.now())
            except Exception as e:
                print(f"[{self.name}] Error converting timestamps: {str(e)}")
                df['timestamp'] = pd.Timestamp.now()
                
            return df
            
        except Exception as e:
            print(f"[{self.name}] Error during data orientation: {str(e)}")
            return pd.DataFrame()

    def decide(self, df):
        print(f"[{self.name}] Analyzing data...")
        if df.empty:
            print(f"[{self.name}] Warning: Empty DataFrame, skipping analysis")
            return self.create_empty_analysis_result()
            
        try:
            # Perform sentiment analysis
            df['sentiment'] = df['text'].apply(self.analyze_sentiment)
            
            # Categorize feedback
            df['category'] = df['text'].apply(self.categorize_feedback)
            
            # Add urgency tag (for dashboard alerts)
            df['urgency'] = df.apply(self.determine_urgency, axis=1)
            
            # Extract keywords and trends
            try:
                trend_keywords = self.extract_keywords(df['text'])
            except Exception as e:
                print(f"[{self.name}] Error extracting keywords: {str(e)}")
                trend_keywords = []
                
            try:
                time_trends = self.detect_trends(df)
            except Exception as e:
                print(f"[{self.name}] Error detecting time trends: {str(e)}")
                time_trends = []
                
            try:
                anomalies = self.detect_anomalies(df)
            except Exception as e:
                print(f"[{self.name}] Error detecting anomalies: {str(e)}")
                anomalies = {}
            
            # Create analysis result with JSON-serializable types
            analysis_result = {
                "feedback_data": self.dataframe_to_serializable(df),
                "sentiment_summary": df['sentiment'].value_counts().to_dict(),
                "top_issues": df['category'].value_counts().to_dict(),
                "trend_keywords": trend_keywords,
                "time_trends": self.make_time_trends_serializable(time_trends),
                "anomalies": self.make_anomalies_serializable(anomalies)
            }
            
            print(f"[{self.name}] Analysis complete with {len(df)} records")
            return analysis_result
            
        except Exception as e:
            print(f"[{self.name}] Error during analysis: {str(e)}")
            return self.create_empty_analysis_result()

    def act(self, analysis_result):
        print(f"[{self.name}] Processing analysis results...")
        return analysis_result

    # --- Helper Methods ---
    
    def dataframe_to_serializable(self, df):
        """Convert DataFrame to JSON-serializable dict with proper timestamp handling"""
        if df.empty:
            return []
        
        # Make a copy to avoid modifying the original
        df_copy = df.copy()
        
        # Convert timestamps to ISO format strings
        if 'timestamp' in df_copy.columns:
            df_copy['timestamp'] = df_copy['timestamp'].apply(lambda x: x.isoformat() if pd.notna(x) else None)
            
        # Convert to records format (list of dicts)
        return df_copy.to_dict(orient='records')
    
    def make_time_trends_serializable(self, time_trends):
        """Make time trends data JSON-serializable"""
        if not time_trends:
            return []
        
        # Handle different time trends structures
        if isinstance(time_trends, dict):
            result = {}
            
            # Process daily count if it exists
            if 'daily_count' in time_trends:
                daily_data = time_trends['daily_count']
                if isinstance(daily_data, list):
                    result['daily_count'] = []
                    for item in daily_data:
                        if isinstance(item, dict):
                            serialized_item = {}
                            for k, v in item.items():
                                # Convert datetime objects to strings
                                if isinstance(v, (pd.Timestamp, datetime, date)):
                                    serialized_item[k] = v.isoformat() if hasattr(v, 'isoformat') else str(v)
                                else:
                                    serialized_item[k] = v
                            result['daily_count'].append(serialized_item)
                
            # Process sentiment trend if it exists
            if 'sentiment_trend' in time_trends:
                result['sentiment_trend'] = self.convert_timestamps_in_list(time_trends['sentiment_trend'])
                
            # Process category trend if it exists
            if 'category_trend' in time_trends:
                result['category_trend'] = self.convert_timestamps_in_list(time_trends['category_trend'])
                
            return result
        elif isinstance(time_trends, list):
            return self.convert_timestamps_in_list(time_trends)
        else:
            return []
    
    def convert_timestamps_in_list(self, data_list):
        """Convert any timestamps in a list of dicts to ISO format strings"""
        result = []
        for item in data_list:
            if isinstance(item, dict):
                serialized_item = {}
                for k, v in item.items():
                    # Convert datetime objects to strings
                    if isinstance(v, (pd.Timestamp, datetime, date)):
                        serialized_item[k] = v.isoformat() if hasattr(v, 'isoformat') else str(v)
                    else:
                        serialized_item[k] = v
                result.append(serialized_item)
            else:
                result.append(item)
        return result
    
    def make_anomalies_serializable(self, anomalies):
        """Make anomalies data JSON-serializable"""
        if not anomalies:
            return {}
        
        result = {}
        for key, value in anomalies.items():
            if isinstance(value, dict):
                # Process dictionary of anomalies
                serialized_dict = {}
                for k, v in value.items():
                    # Convert datetime keys to strings
                    if isinstance(k, (pd.Timestamp, datetime, date)):
                        str_key = k.isoformat() if hasattr(k, 'isoformat') else str(k)
                    else:
                        str_key = str(k)
                    
                    # Convert datetime values to strings
                    if isinstance(v, (pd.Timestamp, datetime, date)):
                        serialized_dict[str_key] = v.isoformat() if hasattr(v, 'isoformat') else str(v)
                    else:
                        serialized_dict[str_key] = v
                result[key] = serialized_dict
            else:
                result[key] = value
                
        return result
    
    def create_empty_analysis_result(self):
        """Create an empty analysis result structure"""
        return {
            "feedback_data": [],
            "sentiment_summary": {},
            "top_issues": {},
            "trend_keywords": [],
            "time_trends": [],
            "anomalies": {}
        }

    def analyze_sentiment(self, text):
        """Analyze sentiment of text"""
        if not self.nlp_available:
            # Fallback simple sentiment analysis if TextBlob not available
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
        
        try:
            from textblob import TextBlob
            blob = TextBlob(str(text))
            polarity = blob.sentiment.polarity
            
            if polarity > 0.1:
                return "positive"
            elif polarity < -0.1:
                return "negative"
            else:
                return "neutral"
        except Exception as e:
            print(f"[{self.name}] Error in sentiment analysis: {str(e)}")
            return "neutral"

    def extract_keywords(self, texts, top_n=10):
        """Extract keywords using TF-IDF"""
        try:
            if len(texts) < 3:  # Need some minimum amount of text for meaningful TF-IDF
                # Fallback to simple word frequency for small datasets
                all_text = ' '.join(texts)
                words = re.findall(r'\b\w+\b', all_text.lower())
                # Filter out common words
                common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were'}
                words = [word for word in words if word not in common_words and len(word) > 2]
                return [word for word, _ in Counter(words).most_common(top_n)]
                
            # Use TF-IDF for larger datasets
            tfidf = TfidfVectorizer(stop_words='english', max_features=top_n)
            X = tfidf.fit_transform(texts)
            return tfidf.get_feature_names_out().tolist()
            
        except Exception as e:
            print(f"[{self.name}] Error extracting keywords: {str(e)}")
            return []

    def categorize_feedback(self, text):
        """Categorize feedback based on text content"""
        text = str(text).lower()
        
        if re.search(r"(bug|error|crash|issue|not working|broken|fails|failure)", text):
            return "bug"
        elif re.search(r"(feature|add|can you make|wishlist|would be nice|please include)", text):
            return "feature_request"
        elif re.search(r"(slow|bad ux|confusing|difficult|hard to use|complicated)", text):
            return "ux_issue"
        elif re.search(r"(great|love|awesome|happy|excellent|amazing|good)", text):
            return "positive_feedback"
        else:
            return "other"

    def determine_urgency(self, row):
        """Determine the urgency of a feedback item"""
        text = str(row['text']).lower()
        sentiment = row['sentiment']
        category = row['category']
        
        # Critical bugs, very negative sentiment, or specific urgent terms
        if (category == 'bug' and 
            (re.search(r"(crash|urgent|critical|emergency|severe|blocked)", text) or 
             sentiment == 'negative')):
            return 'high'
        # Regular bugs or UX issues with negative sentiment    
        elif (category in ['bug', 'ux_issue'] and sentiment == 'negative'):
            return 'medium'
        else:
            return 'low'

    def detect_trends(self, df):
        """Detect trends in feedback over time"""
        if 'timestamp' not in df.columns or df.empty:
            return []
            
        try:
            # Verify timestamp column is datetime type
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                print(f"[{self.name}] Warning: timestamp column is not datetime type, converting...")
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                # Handle any NaT values
                df['timestamp'] = df['timestamp'].fillna(pd.Timestamp.now())
            
            # Add a day column for aggregation (as string to avoid JSON serialization issues)
            df['day'] = df['timestamp'].dt.date.astype(str)
            
            # Count feedback by day
            trend = df.groupby('day').size().reset_index(name='count')
            
            # Count sentiment by day
            sentiment_trend = df.groupby(['day', 'sentiment']).size().reset_index(name='count')
            sentiment_pivot = sentiment_trend.pivot(index='day', columns='sentiment', values='count').fillna(0).reset_index()
            
            # Count categories by day
            category_trend = df.groupby(['day', 'category']).size().reset_index(name='count')
            category_pivot = category_trend.pivot(index='day', columns='category', values='count').fillna(0).reset_index()
            
            # Combine trends
            time_trends = {
                'daily_count': trend.to_dict(orient='records'),
                'sentiment_trend': sentiment_pivot.to_dict(orient='records'),
                'category_trend': category_pivot.to_dict(orient='records')
            }
            
            return time_trends
            
        except Exception as e:
            print(f"[{self.name}] Error detecting trends: {str(e)}")
            return []

    def detect_anomalies(self, df):
        """Detect anomalies in the feedback data"""
        if 'timestamp' not in df.columns or df.empty:
            return {}
            
        try:
            # Verify timestamp column is datetime type
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                print(f"[{self.name}] Warning: timestamp column is not datetime type, converting...")
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                # Handle any NaT values
                df['timestamp'] = df['timestamp'].fillna(pd.Timestamp.now())
            
            # Convert timestamps to string dates to avoid serialization issues
            day_column = df['timestamp'].dt.date.astype(str)
            
            # Count by day
            day_counts = df.groupby(day_column).size()
            
            if len(day_counts) < 3:  # Need some history for meaningful anomaly detection
                return {}
                
            # Simple statistical anomaly detection (mean + 2*std)
            mean = day_counts.mean()
            std = day_counts.std() if len(day_counts) > 1 else 0
            
            # Find days with feedback count more than 2 standard deviations from the mean
            anomalies = day_counts[day_counts > mean + 2 * std]
            
            # Convert index to string for JSON serialization (already string, but keep for clarity)
            anomalies_dict = {str(date): int(count) for date, count in anomalies.items()}
            
            # Also look for spikes in negative sentiment
            negative_df = df[df['sentiment'] == 'negative']
            if not negative_df.empty:
                negative_counts = negative_df.groupby(negative_df['timestamp'].dt.date.astype(str)).size()
                negative_mean = negative_counts.mean() if not negative_counts.empty else 0
                negative_std = negative_counts.std() if len(negative_counts) > 1 else 0
                
                negative_anomalies = negative_counts[negative_counts > negative_mean + 2 * negative_std] if not negative_counts.empty else pd.Series()
                
                # Convert index to string for JSON serialization (already string, but keep for clarity)
                negative_anomalies_dict = {str(date): int(count) for date, count in negative_anomalies.items()}
            else:
                negative_anomalies_dict = {}
            
            return {
                'volume_anomalies': anomalies_dict,
                'negative_sentiment_anomalies': negative_anomalies_dict
            }
            
        except Exception as e:
            print(f"[{self.name}] Error detecting anomalies: {str(e)}")
            return {}