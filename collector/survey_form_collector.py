from utils.ooda import OODAAgent
import os
import json
import pandas as pd
import csv

class SurveyFormCollector(OODAAgent):
    def __init__(self, file_dir=None):
        super().__init__("SurveyFormCollector")
        self.file_dir = file_dir or os.path.join(os.getcwd(), "data", "survey_files")
        os.makedirs(self.file_dir, exist_ok=True)
        
    def observe(self, data):
        print(f"[{self.name}] Observing survey data...")
        
        collected_data = []
        
        # Process survey data from input
        survey_data = data.get("survey_data", [])
        if survey_data:
            print(f"[{self.name}] Processing {len(survey_data)} survey items from input")
            collected_data.extend(survey_data)
        
        # Process files if they exist in specified directory
        file_data = self._process_survey_files()
        if file_data:
            print(f"[{self.name}] Processed {len(file_data)} survey items from files")
            collected_data.extend(file_data)
            
        # Process API data if provided
        api_data = data.get("api_data", {}).get("survey_responses", [])
        if api_data:
            print(f"[{self.name}] Processing {len(api_data)} survey items from API")
            collected_data.extend(api_data)
            
        if not collected_data:
            print(f"[{self.name}] No survey data found in any source")
            return []
            
        return self.sanitize_data(collected_data)

    def _process_survey_files(self):
        """Process survey files from the file directory."""
        combined_data = []
        
        if not os.path.exists(self.file_dir):
            print(f"[{self.name}] Survey file directory not found: {self.file_dir}")
            return combined_data
            
        print(f"[{self.name}] Checking for survey files in: {self.file_dir}")
        
        # List all files in the directory
        try:
            files = os.listdir(self.file_dir)
            for file in files:
                file_path = os.path.join(self.file_dir, file)
                if not os.path.isfile(file_path):
                    continue
                    
                print(f"[{self.name}] Processing file: {file}")
                try:
                    if file.endswith('.json'):
                        with open(file_path, 'r') as f:
                            file_data = json.load(f)
                            if isinstance(file_data, list):
                                combined_data.extend(file_data)
                            elif isinstance(file_data, dict) and "survey_responses" in file_data:
                                combined_data.extend(file_data["survey_responses"])
                    
                    elif file.endswith('.csv'):
                        # Use pandas to read CSV
                        df = pd.read_csv(file_path)
                        file_data = df.to_dict('records')
                        combined_data.extend(file_data)
                        
                    elif file.endswith('.xlsx') or file.endswith('.xls'):
                        # Use pandas to read Excel
                        df = pd.read_excel(file_path)
                        file_data = df.to_dict('records')
                        combined_data.extend(file_data)
                        
                except Exception as e:
                    print(f"[{self.name}] Error processing file {file}: {str(e)}")
        
        except Exception as e:
            print(f"[{self.name}] Error accessing survey files: {str(e)}")
            
        return combined_data

    def sanitize_data(self, data):
        sanitized_data = []
        for item in data:
            if isinstance(item, dict):
                # Create a copy to avoid modifying the original
                clean_item = item.copy()
                # Remove personal information
                clean_item.pop('name', None)
                clean_item.pop('email', None)
                clean_item.pop('personal_info', None)
                clean_item.pop('phone', None)
                clean_item.pop('address', None)
                clean_item.pop('user_id', None)
                
                # Convert rating to numeric if possible
                if 'rating' in clean_item and not isinstance(clean_item['rating'], (int, float)):
                    try:
                        clean_item['rating'] = float(clean_item['rating'])
                    except (ValueError, TypeError):
                        # If conversion fails, set a default value
                        clean_item['rating'] = 0
                
                sanitized_data.append(clean_item)
            else:
                print(f"[{self.name}] Skipping item: {item} (not a dictionary)")
                
        print(f"[{self.name}] Sanitized {len(sanitized_data)} survey items")
        return sanitized_data

    def orient(self, data):
        print(f"[{self.name}] Orienting survey data...")
        if not data:
            return []
            
        # Additional data organization/categorization can be done here
        # For example, group by form_id, timestamp, etc.
        
        return data

    def decide(self, data):
        print(f"[{self.name}] Analyzing survey data...")
        if not data:
            return {
                "average_rating": 0,
                "total_responses": 0,
                "status": "no_data"
            }
            
        try:
            # Get all items with valid ratings
            items_with_ratings = [item for item in data if 'rating' in item and isinstance(item.get('rating'), (int, float))]
            
            if not items_with_ratings:
                return {
                    "average_rating": 0,
                    "total_responses": len(data),
                    "status": "no_ratings"
                }
                
            average = sum(item.get('rating', 0) for item in items_with_ratings) / len(items_with_ratings)
            
            # Group feedback by form_id if available
            feedback_by_form = {}
            for item in data:
                form_id = item.get('form_id', 'default')
                if form_id not in feedback_by_form:
                    feedback_by_form[form_id] = []
                feedback_by_form[form_id].append(item)
            
            return {
                "average_rating": round(average, 2),
                "total_responses": len(data),
                "responses_with_ratings": len(items_with_ratings),
                "form_distribution": {form_id: len(items) for form_id, items in feedback_by_form.items()},
                "status": "success"
            }
        except Exception as e:
            print(f"[{self.name}] Error calculating survey metrics: {str(e)}")
            return {
                "average_rating": 0,
                "total_responses": len(data) if isinstance(data, list) else 0,
                "status": "error",
                "message": str(e)
            }

    def act(self, analysis_result):
        print(f"[{self.name}] Processing complete for survey data")
        
        # Standardize the return format
        if isinstance(analysis_result, dict) and "data" in analysis_result:
            # If analysis_result already has data structure, use it
            data = analysis_result["data"]
        else:
            # Otherwise, use analysis_result as the data
            data = analysis_result
            
        # Make sure survey_data is included in a consistent way
        return {
            "data": {
                "survey_data": data
            },
            "metadata": {
                "timestamp": self._get_current_timestamp(),
                "source": "survey_form_collector"
            }
        }
        
    def _get_current_timestamp(self):
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()

    def run(self, data):
        """Run the full OODA loop for survey data collection."""
        print(f"[{self.name}] Starting survey data collection")
        
        # Handle various input formats
        input_data = data
        if isinstance(data, dict) and "data" in data:
            input_data = data["data"]
            
        observed_data = self.observe(input_data)
        oriented_data = self.orient(observed_data)
        analysis_result = self.decide(oriented_data)
        
        # For the act phase, include both the data and the analysis
        combined_data = {
            "data": oriented_data,
            "analysis": analysis_result,
            "total_responses": len(oriented_data) if isinstance(oriented_data, list) else 0
        }
        
        result = self.act(combined_data)
        
        print(f"[{self.name}] Survey data collection complete")
        return result