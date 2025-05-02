import matplotlib
matplotlib.use('Agg')

from utils.ooda import OODAAgent
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from datetime import datetime, timedelta
import json

class DashboardAgent(OODAAgent):
    def __init__(self):
        super().__init__("DashboardAgent")
        # Configure plotting for better visualization
        plt.style.use('ggplot')
        self.charts = {}  # Store generated charts

    def observe(self, analysis_result):
        print(f"[{self.name}] Observing analysis results...")
        
        # Validate the input data structure
        if not analysis_result or "data" not in analysis_result:
            print(f"[{self.name}] Warning: Expected analysis_result not found in input")
            return self.create_empty_dashboard_data()
            
        data = analysis_result["data"]
        if not data or "feedback_data" not in data:
            print(f"[{self.name}] Warning: Missing feedback_data in analysis result")
            return self.create_empty_dashboard_data()
            
        print(f"[{self.name}] Received analysis results for dashboard generation")
        return data

    def orient(self, analysis_data):
        print(f"[{self.name}] Orienting dashboard data...")
        
        try:
            # Extract and organize feedback data
            feedback_data = analysis_data.get('feedback_data', [])
            
            # Convert timestamps from ISO strings back to datetime objects for processing
            feedback_data = self.process_timestamps(feedback_data)
            
            # Calculate KPIs
            kpis = self.calculate_kpis(feedback_data)
            
            # Categorize feedback
            categorized_data = self.categorize_feedback(feedback_data)
            
            # Extract trends
            trends = self.extract_trends(analysis_data)
            
            # Organize data for dashboard
            dashboard_data = {
                "kpis": kpis,
                "feedback_categories": categorized_data,
                "trends": trends,
                "feedback_data": feedback_data,
                "sentiment_summary": analysis_data.get('sentiment_summary', {}),
                "top_issues": analysis_data.get('top_issues', {}),
                "trend_keywords": analysis_data.get('trend_keywords', []),
                "time_trends": analysis_data.get('time_trends', []),
                "anomalies": analysis_data.get('anomalies', {})
            }
            
            print(f"[{self.name}] Dashboard data organization complete")
            return dashboard_data
            
        except Exception as e:
            print(f"[{self.name}] Error during dashboard data orientation: {str(e)}")
            return self.create_empty_dashboard_data()

    def decide(self, dashboard_data):
        print(f"[{self.name}] Preparing dashboard components...")
        # For dashboard, decision is about layout and visualization choices
        return dashboard_data

    def act(self, dashboard_data):
        print(f"[{self.name}] Generating dashboard visualizations...")
        
        try:
            # Clear previous charts
            self.charts = {}
            
            # Generate all chart visualizations and store them
            if dashboard_data.get('kpis'):
                self.charts['kpi_summary'] = self.generate_kpi_charts(dashboard_data['kpis'])
            
            if dashboard_data.get('trends'):
                self.charts['issue_trends'] = self.generate_issue_trends_chart(dashboard_data['trends'])
                self.charts['sentiment_trends'] = self.generate_sentiment_trends_chart(dashboard_data['trends'])
            
            if dashboard_data.get('feedback_categories'):
                self.charts['categories'] = self.generate_feedback_categories_chart(dashboard_data['feedback_categories'])
            
            if dashboard_data.get('time_trends'):
                try:
                    self.charts['time_trends'] = self.generate_time_trends_chart(dashboard_data['time_trends'])
                except Exception as e:
                    print(f"[{self.name}] Missing required columns in time trends data")
            
            # Generate alerts based on anomalies and urgent feedback
            alerts = self.generate_alerts(dashboard_data['feedback_data'], dashboard_data.get('anomalies', {}))
            
            # Ensure everything is JSON serializable before returning
            final_dashboard = {
                "charts": self.charts,
                "alerts": alerts,
                "kpis": dashboard_data['kpis'],
                "trends": self.ensure_serializable(dashboard_data['trends']),
                "top_issues": dashboard_data.get('top_issues', {}),
                "trend_keywords": dashboard_data.get('trend_keywords', [])
            }
            
            # Test if the output is JSON serializable
            try:
                # This will raise an error if there are non-serializable objects
                json.dumps(final_dashboard)
                print(f"[{self.name}] Successfully verified dashboard is JSON serializable")
            except TypeError as e:
                print(f"[{self.name}] Warning: Dashboard contains non-serializable objects: {str(e)}")
                # Apply fixes to make it serializable
                final_dashboard = self.ensure_serializable(final_dashboard)
            
            print(f"[{self.name}] Dashboard generation complete with {len(self.charts)} visualizations")
            return final_dashboard
            
        except Exception as e:
            print(f"[{self.name}] Error during dashboard generation: {str(e)}")
            return {"error": str(e), "charts": {}, "alerts": []}

    # --- Helper Methods ---
    
    def process_timestamps(self, feedback_data):
        """Convert ISO timestamp strings back to datetime objects for processing"""
        processed_data = []
        
        for item in feedback_data:
            processed_item = dict(item)  # Create a copy
            
            # Convert timestamp string to datetime if it exists
            if 'timestamp' in processed_item and isinstance(processed_item['timestamp'], str):
                try:
                    processed_item['timestamp'] = pd.to_datetime(processed_item['timestamp'])
                except Exception as e:
                    print(f"[{self.name}] Error converting timestamp: {str(e)}")
                    processed_item['timestamp'] = pd.Timestamp.now()
                    
            processed_data.append(processed_item)
            
        return processed_data
    
    def ensure_serializable(self, obj):
        """Recursively ensure all objects are JSON serializable"""
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        elif isinstance(obj, (datetime, pd.Timestamp)):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {str(k): self.ensure_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self.ensure_serializable(item) for item in obj]
        elif hasattr(obj, 'to_dict'):
            # Handle pandas objects with to_dict method
            return self.ensure_serializable(obj.to_dict())
        elif pd.isna(obj):
            # Handle NaN/NaT values
            return None
        else:
            # Convert any other types to string
            return str(obj)
    
    def create_empty_dashboard_data(self):
        """Create an empty dashboard data structure"""
        return {
            "kpis": {},
            "feedback_categories": {},
            "trends": {},
            "feedback_data": [],
            "sentiment_summary": {},
            "top_issues": {},
            "trend_keywords": [],
            "time_trends": [],
            "anomalies": {}
        }

    def calculate_kpis(self, feedback_data):
        """Calculate key performance indicators"""
        try:
            if not feedback_data:
                return {
                    "total_feedbacks": 0,
                    "positive_feedbacks": 0,
                    "negative_feedbacks": 0,
                    "neutral_feedbacks": 0,
                    "urgent_issues": 0,
                    "feature_requests": 0,
                    "bugs_reported": 0
                }
                
            kpis = {
                "total_feedbacks": len(feedback_data),
                "positive_feedbacks": sum(1 for item in feedback_data if item.get('sentiment') == 'positive'),
                "negative_feedbacks": sum(1 for item in feedback_data if item.get('sentiment') == 'negative'),
                "neutral_feedbacks": sum(1 for item in feedback_data if item.get('sentiment') == 'neutral'),
                "urgent_issues": sum(1 for item in feedback_data if item.get('urgency') == 'high'),
                "feature_requests": sum(1 for item in feedback_data if item.get('category') == 'feature_request'),
                "bugs_reported": sum(1 for item in feedback_data if item.get('category') == 'bug')
            }
            
            # Calculate percentages
            if kpis["total_feedbacks"] > 0:
                kpis["positive_percentage"] = round(kpis["positive_feedbacks"] / kpis["total_feedbacks"] * 100, 1)
                kpis["negative_percentage"] = round(kpis["negative_feedbacks"] / kpis["total_feedbacks"] * 100, 1)
                kpis["neutral_percentage"] = round(kpis["neutral_feedbacks"] / kpis["total_feedbacks"] * 100, 1)
            else:
                kpis["positive_percentage"] = 0
                kpis["negative_percentage"] = 0
                kpis["neutral_percentage"] = 0
                
            return kpis
            
        except Exception as e:
            print(f"[{self.name}] Error calculating KPIs: {str(e)}")
            return {}

    def categorize_feedback(self, feedback_data):
        """Organize feedback into categories"""
        try:
            if not feedback_data:
                return {
                    "bugs": [],
                    "feature_requests": [],
                    "ux_issues": [],
                    "positive_feedback": [],
                    "other": []
                }
                
            categorized_data = {
                "bugs": [],
                "feature_requests": [],
                "ux_issues": [],
                "positive_feedback": [],
                "other": []
            }

            for item in feedback_data:
                category = item.get('category', 'other')
                
                if category == 'bug':
                    categorized_data["bugs"].append(item)
                elif category == 'feature_request':
                    categorized_data["feature_requests"].append(item)
                elif category == 'ux_issue':
                    categorized_data["ux_issues"].append(item)
                elif category == 'positive_feedback':
                    categorized_data["positive_feedback"].append(item)
                else:
                    categorized_data["other"].append(item)

            return categorized_data
            
        except Exception as e:
            print(f"[{self.name}] Error categorizing feedback: {str(e)}")
            return {}

    def extract_trends(self, analysis_data):
        """Extract trend information from analysis data"""
        try:
            # Get sentiment and category distributions
            sentiment_summary = analysis_data.get('sentiment_summary', {})
            top_issues = analysis_data.get('top_issues', {})
            
            # Create trends summary
            trends = {
                "sentiment_trends": sentiment_summary,
                "issue_trends": top_issues
            }
            
            # Add time-based trends if available
            time_trends = analysis_data.get('time_trends', [])
            if time_trends:
                trends["time_trends"] = time_trends
                
            return trends
            
        except Exception as e:
            print(f"[{self.name}] Error extracting trends: {str(e)}")
            return {}

    def generate_kpi_charts(self, kpis):
        """Generate KPI summary chart"""
        try:
            if not kpis:
                return None
                
            # Create a Figure with subplots
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
            fig.suptitle('Feedback Summary', fontsize=16)
            
            # Sentiment distribution chart
            sentiment_labels = ['Positive', 'Neutral', 'Negative']
            sentiment_values = [kpis.get('positive_feedbacks', 0), 
                               kpis.get('neutral_feedbacks', 0), 
                               kpis.get('negative_feedbacks', 0)]
            colors = ['#4CAF50', '#FFC107', '#F44336']  # Green, Yellow, Red
            
            if sum(sentiment_values) > 0:  # Only create pie chart if there's data
                ax1.pie(sentiment_values, labels=sentiment_labels, colors=colors, 
                       autopct='%1.1f%%', startangle=90)
                ax1.set_title('Sentiment Distribution')
            else:
                ax1.text(0.5, 0.5, 'No sentiment data available', 
                        horizontalalignment='center', verticalalignment='center')
                        
            # Feedback category distribution
            categories = ['Bugs', 'Feature Requests', 'UX Issues', 'Positive', 'Other']
            category_values = [
                kpis.get('bugs_reported', 0),
                kpis.get('feature_requests', 0),
                kpis.get('ux_issues', 0) if 'ux_issues' in kpis else 0,
                kpis.get('positive_feedbacks', 0),
                kpis.get('total_feedbacks', 0) - 
                    (kpis.get('bugs_reported', 0) + 
                     kpis.get('feature_requests', 0) + 
                     (kpis.get('ux_issues', 0) if 'ux_issues' in kpis else 0) + 
                     kpis.get('positive_feedbacks', 0))
            ]
            
            if sum(category_values) > 0:  # Only create bar chart if there's data
                ax2.bar(categories, category_values, color='#2196F3')
                ax2.set_title('Feedback Categories')
                ax2.set_ylabel('Count')
                plt.xticks(rotation=45)
            else:
                ax2.text(0.5, 0.5, 'No category data available', 
                        horizontalalignment='center', verticalalignment='center')
                
            plt.tight_layout(rect=[0, 0, 1, 0.95])  # Adjust for title
            
            # Convert plot to base64 image
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close(fig)  # Close figure to prevent display in notebooks
            
            # Encode the image to base64 string
            b64_img = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            return {
                "image": f"data:image/png;base64,{b64_img}",
                "summary": {
                    "total_feedbacks": kpis.get('total_feedbacks', 0),
                    "positive_percentage": kpis.get('positive_percentage', 0),
                    "negative_percentage": kpis.get('negative_percentage', 0),
                    "neutral_percentage": kpis.get('neutral_percentage', 0)
                }
            }
                
        except Exception as e:
            print(f"[{self.name}] Error generating KPI charts: {str(e)}")
            return None

    def generate_issue_trends_chart(self, trends):
        """Generate chart showing issue category trends"""
        try:
            issue_trends = trends.get('issue_trends', {})
            
            if not issue_trends:
                return None
                
            # Create visualization
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Sort the issues by count for better visualization
            sorted_issues = sorted(issue_trends.items(), key=lambda x: x[1], reverse=True)
            categories = [item[0].replace('_', ' ').title() for item in sorted_issues]
            counts = [item[1] for item in sorted_issues]
            
            # Limit to top 10 categories
            if len(categories) > 10:
                categories = categories[:10]
                counts = counts[:10]
                
            ax.bar(categories, counts, color='#3F51B5')
            ax.set_title('Top Issue Categories', fontsize=14)
            ax.set_ylabel('Count', fontsize=12)
            ax.set_xlabel('Category', fontsize=12)
            plt.xticks(rotation=45, ha='right')
            
            plt.tight_layout()
            
            # Convert plot to base64 image
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close(fig)  # Close figure to prevent display in notebooks
            
            # Encode the image to base64 string
            b64_img = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            return {
                "image": f"data:image/png;base64,{b64_img}",
                "summary": {
                    "top_issue": categories[0] if categories else None,
                    "top_issue_count": counts[0] if counts else 0,
                    "issue_counts": dict(zip(categories, counts))
                }
            }
                
        except Exception as e:
            print(f"[{self.name}] Error generating issue trends chart: {str(e)}")
            return None

    def generate_sentiment_trends_chart(self, trends):
        """Generate chart showing sentiment trends"""
        try:
            sentiment_trends = trends.get('sentiment_trends', {})
            
            if not sentiment_trends:
                return None
                
            # Create visualization
            fig, ax = plt.subplots(figsize=(8, 8))
            
            # Plot sentiment distribution
            labels = ['Positive', 'Neutral', 'Negative']
            values = [
                sentiment_trends.get('positive', 0),
                sentiment_trends.get('neutral', 0),
                sentiment_trends.get('negative', 0)
            ]
            colors = ['#4CAF50', '#FFC107', '#F44336']  # Green, Yellow, Red
            
            if sum(values) > 0:  # Only create pie chart if there's data
                wedges, texts, autotexts = ax.pie(
                    values, 
                    labels=labels, 
                    colors=colors,
                    autopct='%1.1f%%', 
                    startangle=90,
                    wedgeprops={'width': 0.5, 'edgecolor': 'w'},
                    textprops={'fontsize': 12}
                )
                
                # Equal aspect ratio ensures that pie is drawn as a circle
                ax.set_aspect('equal')
                ax.set_title('Sentiment Distribution', fontsize=14)
                
                # Make labels and percentages easier to read
                for text, autotext in zip(texts, autotexts):
                    text.set_fontsize(12)
                    autotext.set_fontsize(12)
                    
            else:
                ax.text(0.5, 0.5, 'No sentiment data available', 
                       horizontalalignment='center', verticalalignment='center')
            
            plt.tight_layout()
            
            # Convert plot to base64 image
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close(fig)  # Close figure to prevent display in notebooks
            
            # Encode the image to base64 string
            b64_img = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            # Calculate dominant sentiment
            dominant_idx = values.index(max(values)) if sum(values) > 0 else -1
            dominant_sentiment = labels[dominant_idx] if dominant_idx >= 0 else 'None'
            
            return {
                "image": f"data:image/png;base64,{b64_img}",
                "summary": {
                    "dominant_sentiment": dominant_sentiment,
                    "positive_count": values[0],
                    "neutral_count": values[1],
                    "negative_count": values[2],
                    "total_count": sum(values)
                }
            }
                
        except Exception as e:
            print(f"[{self.name}] Error generating sentiment trends chart: {str(e)}")
            return None

    def generate_feedback_categories_chart(self, categorized_data):
        """Generate chart showing feedback categories"""
        try:
            if not categorized_data:
                return None
                
            # Count items in each category
            categories = ['Bugs', 'Feature Requests', 'UX Issues', 'Positive Feedback', 'Other']
            counts = [
                len(categorized_data.get('bugs', [])),
                len(categorized_data.get('feature_requests', [])),
                len(categorized_data.get('ux_issues', [])),
                len(categorized_data.get('positive_feedback', [])),
                len(categorized_data.get('other', []))
            ]
            
            if sum(counts) == 0:
                return None
                
            # Create visualization
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Create colorful horizontal bar chart
            colors = ['#F44336', '#2196F3', '#FF9800', '#4CAF50', '#9C27B0']
            bars = ax.barh(categories, counts, color=colors)
            
            # Add values at the end of each bar
            for bar in bars:
                width = bar.get_width()
                ax.text(width + 0.1, bar.get_y() + bar.get_height()/2, 
                        str(int(width)), va='center')
            
            ax.set_title('Feedback by Category', fontsize=14)
            ax.set_xlabel('Count', fontsize=12)
            
            plt.tight_layout()
            
            # Convert plot to base64 image
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close(fig)  # Close figure to prevent display in notebooks
            
            # Encode the image to base64 string
            b64_img = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            # Find the largest category
            largest_idx = counts.index(max(counts)) if sum(counts) > 0 else -1
            largest_category = categories[largest_idx] if largest_idx >= 0 else 'None'
            
            return {
                "image": f"data:image/png;base64,{b64_img}",
                "summary": {
                    "largest_category": largest_category,
                    "largest_category_count": max(counts) if counts else 0,
                    "category_counts": dict(zip(categories, counts))
                }
            }
                
        except Exception as e:
            print(f"[{self.name}] Error generating feedback categories chart: {str(e)}")
            return None

    def generate_time_trends_chart(self, time_trends):
        """Generate chart showing trends over time"""
        try:
            if not time_trends or not isinstance(time_trends, list) or len(time_trends) == 0:
                print(f"[{self.name}] No time trend data available")
                return None
                
            # Convert to DataFrame for easier handling
            df = pd.DataFrame(time_trends)
            
            # Check if required columns exist
            if 'timestamp' not in df.columns or 'count' not in df.columns:
                raise ValueError("Missing required columns in time trends data")
                
            # Make sure timestamps are datetime objects
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Sort by timestamp
            df = df.sort_values('timestamp')
            
            # Create visualization
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Plot trends over time
            if 'sentiment' in df.columns:
                # Plot sentiment categories if available
                for sentiment, color in zip(['positive', 'neutral', 'negative'], 
                                          ['#4CAF50', '#FFC107', '#F44336']):
                    sentiment_data = df[df['sentiment'] == sentiment]
                    if not sentiment_data.empty:
                        ax.plot(sentiment_data['timestamp'], sentiment_data['count'], 
                               marker='o', linewidth=2, label=sentiment.title(), color=color)
                
                ax.set_title('Sentiment Trends Over Time', fontsize=14)
                ax.legend()
            else:
                # Simple trend line
                ax.plot(df['timestamp'], df['count'], marker='o', linewidth=2, color='#2196F3')
                ax.set_title('Feedback Trends Over Time', fontsize=14)
            
            # Format x-axis to show dates nicely
            ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)
            
            ax.set_xlabel('Date', fontsize=12)
            ax.set_ylabel('Count', fontsize=12)
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Convert plot to base64 image
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close(fig)  # Close figure to prevent display in notebooks
            
            # Encode the image to base64 string
            b64_img = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            # Calculate trend metrics
            trend_summary = {}
            
            # Calculate if trend is increasing or decreasing
            if len(df) >= 2:
                first_half_avg = df.iloc[:len(df)//2]['count'].mean()
                second_half_avg = df.iloc[len(df)//2:]['count'].mean()
                trend_direction = "increasing" if second_half_avg > first_half_avg else "decreasing"
                
                trend_summary = {
                    "direction": trend_direction,
                    "change_percent": round((second_half_avg - first_half_avg) / first_half_avg * 100, 1) if first_half_avg > 0 else 0,
                    "start_value": int(df.iloc[0]['count']),
                    "end_value": int(df.iloc[-1]['count']),
                    "time_range": f"{df['timestamp'].min().date()} to {df['timestamp'].max().date()}"
                }
            
            return {
                "image": f"data:image/png;base64,{b64_img}",
                "summary": trend_summary
            }
                
        except Exception as e:
            print(f"[{self.name}] Error generating time trends chart: {str(e)}")
            return None

    def generate_alerts(self, feedback_data, anomalies):
        """Generate alerts based on feedback data and anomalies"""
        alerts = []
        
        try:
            # Add alerts for anomalies
            for anomaly_type, anomaly_details in anomalies.items():
                if isinstance(anomaly_details, dict) and anomaly_details.get('detected', False):
                    alerts.append({
                        "title": f"Anomaly detected: {anomaly_type.replace('_', ' ').title()}",
                        "description": anomaly_details.get('description', 'Unusual pattern detected in feedback data'),
                        "severity": "high",
                        "timestamp": datetime.now().isoformat()
                    })
            
            # Add alerts for urgent negative feedback
            urgent_threshold = 3  # Alert if there are more than this many urgent negative feedbacks
            urgent_negative = [
                item for item in feedback_data 
                if item.get('urgency') == 'high' and item.get('sentiment') == 'negative'
            ]
            
            if len(urgent_negative) >= urgent_threshold:
                alerts.append({
                    "title": f"High number of urgent negative feedback ({len(urgent_negative)})",
                    "description": "Multiple customers have reported urgent negative issues",
                    "severity": "high",
                    "timestamp": datetime.now().isoformat()
                })
                
            # Check for significant sentiment changes over time
            # This would require time series data, which we might not have here
            # To be implemented when time trends data is available
            
            return alerts
            
        except Exception as e:
            print(f"[{self.name}] Error generating alerts: {str(e)}")
            return []