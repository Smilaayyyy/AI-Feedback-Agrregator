from collector.social_media_collector import SocialMediaCollector
from collector.review_site_collector import ReviewSiteCollector
from collector.survey_form_collector import SurveyFormCollector
from processor.data_processor import DataProcessor
from analyzer.analysis_agent import AnalysisAgent
from dashboard.dashboard_agent import DashboardAgent
from alerting.alert_agent import AlertAgent
from reporting.report_agent import ReportAgent
import os
import json
import argparse
from datetime import datetime

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Feedback Analysis System')
    parser.add_argument('--config', type=str, default='config.json',
                        help='Path to configuration file')
    parser.add_argument('--output-dir', type=str, default='output',
                        help='Directory to save output files')
    parser.add_argument('--mode', type=str, default='all',
                        choices=['collect', 'process', 'analyze', 'dashboard', 'all'],
                        help='Pipeline execution mode')
    parser.add_argument('--survey-files-dir', type=str, default=None,
                        help='Directory containing survey files to process')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    return parser.parse_args()

def load_config(config_path):
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"Configuration loaded from {config_path}")
        return config
    except Exception as e:
        print(f"Error loading configuration: {str(e)}")
        # Return default configuration
        return {
            "social": {
                "platform": "Twitter",
                "hashtags": ["#feedback"],
                "date_range": "last_30_days"
            },
            "review": {
                "websites": ["Google", "Yelp"],
                "date_range": "last_30_days"
            },
            "survey": {
                "form_id": "default_form",
                "files_dir": "data/survey_files",
                "api_endpoints": []
            }
        }

def prepare_output_directory(output_dir):
    """Create output directory if it doesn't exist."""
    try:
        os.makedirs(output_dir, exist_ok=True)
        # Create subdirectories for different outputs
        os.makedirs(os.path.join(output_dir, 'data'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'analysis'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'dashboards'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'reports'), exist_ok=True)
        print(f"Output directories created at {output_dir}")
    except Exception as e:
        print(f"Error creating output directories: {str(e)}")

def save_output(data, output_dir, filename):
    """Save output data to file."""
    try:
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Output saved to {filepath}")
        return filepath
    except Exception as e:
        print(f"Error saving output: {str(e)}")
        return None

def collect_data(config, survey_files_dir=None):
    """Collect data from various sources."""
    print("\n--- Data Collection Phase ---")
    
    # Prepare data for each collector agent
    social_input = {"social_data": prepare_dummy_social_data(config.get("social", {}))}
    review_input = {"review_data": prepare_dummy_review_data(config.get("review", {}))}
    
    # Prepare survey input with both direct data and API data if available
    survey_config = config.get("survey", {})
    survey_input = {
        "survey_data": prepare_dummy_survey_data(survey_config),
        "api_data": {"survey_responses": []}  # Will be populated with real API data if available
    }
    
    # Add API endpoints if defined in config
    api_endpoints = survey_config.get("api_endpoints", [])
    if api_endpoints:
        print(f"Found {len(api_endpoints)} API endpoints for survey data")
        # In a real implementation, you would fetch data from these endpoints
        # For now, we'll just log them
        for endpoint in api_endpoints:
            print(f"API endpoint found: {endpoint}")
    
    # Initialize collector agents
    social_agent = SocialMediaCollector(
        platform=config.get("social", {}).get("platform", "Twitter")
    )
    review_agent = ReviewSiteCollector(
        websites=config.get("review", {}).get("websites", ["Google", "Yelp"])
    )
    
    # Use either command-line specified directory or config-specified directory
    files_dir = survey_files_dir or survey_config.get("files_dir")
    survey_agent = SurveyFormCollector(file_dir=files_dir)
    
    # Run collectors
    print("Running social media collector...")
    social_data = social_agent.run(social_input)
    
    print("Running review site collector...")
    review_data = review_agent.run(review_input)
    
    print("Running survey collector...")
    survey_data = survey_agent.run(survey_input)
    
    # Combine all collected data
    combined_data = {
        "social_data": social_data,
        "review_data": review_data,
        "survey_data": survey_data,
        "timestamp": datetime.now().isoformat()
    }
    
    # Define helper function for extracting survey count
    def extract_count_from_survey_data(survey_data):
        """Helper function to safely extract the count of survey responses"""
        count = 0
        
        # Case 1: survey_data is a dictionary with the expected structure
        if isinstance(survey_data, dict):
            # Check for data.survey_data.total_responses structure
            if "data" in survey_data:
                data = survey_data["data"]
                if isinstance(data, dict) and "survey_data" in data:
                    survey_items = data["survey_data"]
                    if isinstance(survey_items, dict) and "total_responses" in survey_items:
                        return survey_items["total_responses"]
                    elif isinstance(survey_items, list):
                        return len(survey_items)
                
                # Check for data.total_responses structure
                if isinstance(data, dict) and "total_responses" in data:
                    return data["total_responses"]
            
            # Check for direct total_responses
            if "total_responses" in survey_data:
                return survey_data["total_responses"]
            
            # Check for direct survey_data list
            if "survey_data" in survey_data:
                survey_items = survey_data["survey_data"]
                if isinstance(survey_items, list):
                    return len(survey_items)
        
        # Case 2: survey_data is a list
        elif isinstance(survey_data, list):
            return len(survey_data)
        
        return count
    
    # Calculate collection statistics
    social_count = len(social_data.get("data", {}).get("social_data", []))
    review_count = len(review_data.get("data", {}).get("review_data", []))
    survey_count = extract_count_from_survey_data(survey_data)
    
    print(f"Collected data from {social_count} social posts, " +
          f"{review_count} reviews, and " +
          f"{survey_count} survey responses.")
    
    return combined_data

def process_data(collected_data):
    """Process and clean the collected data."""
    print("\n--- Data Processing Phase ---")
    
    # Initialize data processor
    data_processor = DataProcessor()
    
    # Process the data
    print("Processing collected data...")
    processed_data = data_processor.run(collected_data)
    
    # Extract cleaned data for reporting
    cleaned_data = processed_data.get("data", {}).get("cleaned_data", [])
    print(f"Processed {len(cleaned_data)} data items")
    
    return processed_data

def analyze_data(processed_data):
    """Analyze the processed data."""
    print("\n--- Data Analysis Phase ---")
    
    # Initialize analysis agent
    analysis_agent = AnalysisAgent()
    
    # Analyze the data
    print("Running analysis agent...")
    analysis_result = analysis_agent.run(processed_data)
    
    # Extract analysis metrics for reporting
    sentiment_summary = analysis_result.get("data", {}).get("sentiment_summary", {})
    top_issues = analysis_result.get("data", {}).get("top_issues", {})
    
    print(f"Analysis complete with sentiment distribution: {sentiment_summary}")
    print(f"Top identified issues: {top_issues}")
    
    return analysis_result

def generate_dashboard(analysis_result):
    """Generate dashboard from analysis results."""
    print("\n--- Dashboard Generation Phase ---")
    
    # Initialize dashboard agent
    dashboard_agent = DashboardAgent()
    
    # Generate dashboard
    print("Generating dashboard...")
    dashboard_result = dashboard_agent.run(analysis_result)
    
    # Extract dashboard metrics for reporting
    chart_count = len(dashboard_result.get("data", {}).get("charts", {}))
    alert_count = len(dashboard_result.get("data", {}).get("alerts", []))
    
    print(f"Dashboard generated with {chart_count} visualizations and {alert_count} alerts")
    
    return dashboard_result

def generate_alerts(dashboard_result):
    """Generate alerts based on dashboard data."""
    print("\n--- Alert Generation Phase ---")
    
    # Initialize alert agent
    alert_agent = AlertAgent() if 'AlertAgent' in globals() else None
    
    if alert_agent:
        # Generate alerts
        print("Generating alerts...")
        alert_result = alert_agent.run(dashboard_result)
        
        # Extract alert metrics for reporting
        alert_count = len(alert_result.get("data", {}).get("alerts", []))
        high_priority = sum(1 for alert in alert_result.get("data", {}).get("alerts", []) 
                           if alert.get("severity") == "high")
        
        print(f"Generated {alert_count} alerts ({high_priority} high priority)")
        return alert_result
    else:
        print("AlertAgent not available, skipping alert generation")
        return {"data": {"alerts": dashboard_result.get("data", {}).get("alerts", [])}}

def generate_report(analysis_result, dashboard_result, alert_result):
    """Generate comprehensive report."""
    print("\n--- Report Generation Phase ---")
    
    # Initialize report agent
    report_agent = ReportAgent() if 'ReportAgent' in globals() else None
    
    if report_agent:
        # Combine all results for reporting
        report_input = {
            "analysis": analysis_result,
            "dashboard": dashboard_result,
            "alerts": alert_result
        }
        
        # Generate report
        print("Generating comprehensive report...")
        report_result = report_agent.run(report_input)
        
        print(f"Report generated successfully")
        return report_result
    else:
        print("ReportAgent not available, skipping report generation")
        return {"data": {"report": "Report generation skipped"}}

def main():
    """Main execution function."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Load configuration
    config = load_config(args.config)
    
    # Prepare output directory
    prepare_output_directory(args.output_dir)
    
    # Initialize execution results
    collected_data = None
    processed_data = None
    analysis_result = None
    dashboard_result = None
    alert_result = None
    report_result = None
    
    # Execute pipeline based on mode
    if args.mode in ['collect', 'all']:
        collected_data = collect_data(config, args.survey_files_dir)
        save_output(collected_data, os.path.join(args.output_dir, 'data'), 'collected_data.json')
    
    if args.mode in ['process', 'all'] and (collected_data or args.mode == 'process'):
        # Load collected data if not already available
        if not collected_data and os.path.exists(os.path.join(args.output_dir, 'data', 'collected_data.json')):
            with open(os.path.join(args.output_dir, 'data', 'collected_data.json'), 'r') as f:
                collected_data = json.load(f)
        
        if collected_data:
            processed_data = process_data(collected_data)
            save_output(processed_data, os.path.join(args.output_dir, 'data'), 'processed_data.json')
    
    if args.mode in ['analyze', 'all'] and (processed_data or args.mode == 'analyze'):
        # Load processed data if not already available
        if not processed_data and os.path.exists(os.path.join(args.output_dir, 'data', 'processed_data.json')):
            with open(os.path.join(args.output_dir, 'data', 'processed_data.json'), 'r') as f:
                processed_data = json.load(f)
        
        if processed_data:
            analysis_result = analyze_data(processed_data)
            save_output(analysis_result, os.path.join(args.output_dir, 'analysis'), 'analysis_result.json')
    
    if args.mode in ['dashboard', 'all'] and (analysis_result or args.mode == 'dashboard'):
        # Load analysis result if not already available
        if not analysis_result and os.path.exists(os.path.join(args.output_dir, 'analysis', 'analysis_result.json')):
            with open(os.path.join(args.output_dir, 'analysis', 'analysis_result.json'), 'r') as f:
                analysis_result = json.load(f)
        
        if analysis_result:
            dashboard_result = generate_dashboard(analysis_result)
            save_output(dashboard_result, os.path.join(args.output_dir, 'dashboards'), 'dashboard_result.json')
            
            # Save any generated HTML dashboards
            if 'charts' in dashboard_result.get('data', {}):
                dashboard_html = dashboard_result.get('data', {}).get('html', None)
                if dashboard_html:
                    html_path = os.path.join(args.output_dir, 'dashboards', 'dashboard.html')
                    with open(html_path, 'w') as f:
                        f.write(dashboard_html)
                    print(f"Dashboard HTML saved to {html_path}")
            
            # Generate alerts based on dashboard
            alert_result = generate_alerts(dashboard_result)
            save_output(alert_result, os.path.join(args.output_dir, 'dashboards'), 'alerts.json')
            
            # Generate comprehensive report
            report_result = generate_report(analysis_result, dashboard_result, alert_result)
            save_output(report_result, os.path.join(args.output_dir, 'reports'), 'report.json')
    
    print("\n--- Pipeline Execution Complete ---")
    return


def prepare_dummy_social_data(config):
    """Generate dummy social media data based on config"""
    platform = config.get("platform", "Twitter")
    hashtags = config.get("hashtags", ["#Default"])
    
    # Create dummy data
    return [
        {
            "user_id": "user123",  # This will be removed during sanitization
            "user_name": "John Doe",  # This will be removed during sanitization
            "platform": platform,
            "text": f"I really love this product! {' '.join(hashtags)}",
            "timestamp": "2023-01-15 10:30:00",
            "likes": 25,
            "shares": 5
        },
        {
            "user_id": "user456",
            "user_name": "Jane Smith",
            "platform": platform,
            "text": f"Not happy with my purchase. {' '.join(hashtags)}",
            "timestamp": "2023-01-16 14:20:00",
            "likes": 3,
            "shares": 0
        },
        {
            "user_id": "user789",
            "user_name": "Sam Wilson",
            "platform": platform,
            "text": f"This is an average product. {' '.join(hashtags)}",
            "timestamp": "2023-01-17 09:15:00",
            "likes": 10,
            "shares": 2
        }
    ]

def prepare_dummy_review_data(config):
    """Generate dummy review data based on config"""
    websites = config.get("websites", ["Google", "Yelp"])
    
    # Create dummy data
    data = []
    for website in websites:
        data.extend([
            {
                "reviewer_name": "Alex Johnson",  # This will be removed during sanitization
                "email": "alex@example.com",      # This will be removed during sanitization
                "platform": website,
                "rating": 4,
                "text": "Great product with minor issues",
                "timestamp": "2023-01-10 08:45:00"
            },
            {
                "reviewer_name": "Chris Brown",
                "email": "chris@example.com",
                "platform": website,
                "rating": 5,
                "text": "Absolutely love it!",
                "timestamp": "2023-01-12 16:30:00"
            },
            {
                "reviewer_name": "Taylor Swift",
                "email": "taylor@example.com",
                "platform": website,
                "rating": 2,
                "text": "Disappointed with quality",
                "timestamp": "2023-01-14 11:20:00"
            }
        ])
    
    return data

def prepare_dummy_survey_data(config):
    """Generate dummy survey data based on config"""
    form_id = config.get("form_id", "default_form")
    
    # Create dummy data
    return [
        {
            "name": "Mike Johnson",  # This will be removed during sanitization
            "email": "mike@example.com",  # This will be removed during sanitization
            "rating": 4,
            "feedback": "The product meets my expectations",
            "timestamp": "2023-01-20 09:30:00",
            "form_id": form_id
        },
        {
            "name": "Lisa Garcia",
            "email": "lisa@example.com",
            "rating": 3,
            "feedback": "Average product, could be improved",
            "timestamp": "2023-01-21 14:15:00",
            "form_id": form_id
        },
        {
            "name": "Robert Chen",
            "email": "robert@example.com",
            "rating": 5,
            "feedback": "Excellent product, highly recommend",
            "timestamp": "2023-01-22 11:45:00",
            "form_id": form_id
        }
    ]

if __name__ == "__main__":
    main()