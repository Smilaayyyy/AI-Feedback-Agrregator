from fastapi import FastAPI, HTTPException, BackgroundTasks, Body, File, UploadFile, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json
import os
import shutil
from datetime import datetime

# Import your existing agents
from collector.social_media_collector import SocialMediaCollector
from collector.review_site_collector import ReviewSiteCollector
from collector.survey_form_collector import SurveyFormCollector
from processor.data_processor import DataProcessor
from analyzer.analysis_agent import AnalysisAgent
from dashboard.dashboard_agent import DashboardAgent
from alerting.alert_agent import AlertAgent
from reporting.report_agent import ReportAgent

app = FastAPI(
    title="Feedback Analysis API",
    description="API for collecting, processing, analyzing, and visualizing feedback data from various sources",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create output directories
os.makedirs("output/data", exist_ok=True)
os.makedirs("output/analysis", exist_ok=True)
os.makedirs("output/dashboards", exist_ok=True)
os.makedirs("output/reports", exist_ok=True)
os.makedirs("temp/uploads", exist_ok=True)

# --- Pydantic Models for Request/Response ---

class SocialMediaConfig(BaseModel):
    platform: str = "Twitter"
    hashtags: List[str] = ["#feedback"]
    date_range: str = "last_30_days"

class ReviewSiteConfig(BaseModel):
    websites: List[str] = ["Google", "Yelp"]
    date_range: str = "last_30_days"

class SurveyConfig(BaseModel):
    form_id: str = "default_form"
    files_dir: Optional[str] = None
    api_endpoints: List[str] = []

class FeedbackConfig(BaseModel):
    social: SocialMediaConfig = SocialMediaConfig()
    review: ReviewSiteConfig = ReviewSiteConfig()
    survey: SurveyConfig = SurveyConfig()

class CollectionRequest(BaseModel):
    config: FeedbackConfig = FeedbackConfig()

class TaskStatus(BaseModel):
    task_id: str
    status: str
    message: str
    timestamp: str

class CollectionResponse(BaseModel):
    task_id: str
    status: str
    sources: Dict[str, int] = {"social": 0, "review": 0, "survey": 0}
    timestamp: str

class AnalysisResponse(BaseModel):
    task_id: str
    status: str
    sentiment_summary: Optional[Dict[str, Any]] = None
    top_issues: Optional[Dict[str, Any]] = None
    timestamp: str

class DashboardResponse(BaseModel):
    task_id: str
    status: str
    chart_count: int = 0
    alert_count: int = 0
    dashboard_url: Optional[str] = None
    timestamp: str

# --- Task storage ---
tasks = {}

def save_output(data, output_dir, filename):
    """Save output data to file."""
    try:
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return filepath
    except Exception as e:
        print(f"Error saving output: {str(e)}")
        return None

# --- Background tasks ---
def run_collection_task(task_id: str, config: FeedbackConfig, survey_files=None):
    try:
        # Update task status
        tasks[task_id] = {
            "status": "collecting",
            "message": "Collecting data from sources",
            "timestamp": datetime.now().isoformat()
        }
        
        # Prepare input data for each collector
        social_input = {"social_data": prepare_dummy_social_data(config.social.dict())}
        review_input = {"review_data": prepare_dummy_review_data(config.review.dict())}
        survey_input = {"survey_data": prepare_dummy_survey_data(config.survey.dict())}
        
        # Initialize collector agents
        social_agent = SocialMediaCollector(platform=config.social.platform)
        review_agent = ReviewSiteCollector(websites=config.review.websites)
        
        # Use either uploaded files or config-specified directory
        files_dir = survey_files or config.survey.files_dir
        survey_agent = SurveyFormCollector(file_dir=files_dir)
        
        # Run collectors
        social_data = social_agent.run(social_input)
        review_data = review_agent.run(review_input)
        survey_data = survey_agent.run(survey_input)
        
        # Combine collected data
        combined_data = {
            "social_data": social_data,
            "review_data": review_data,
            "survey_data": survey_data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save collected data
        save_output(combined_data, "output/data", f"collected_data_{task_id}.json")
        
        # Extract counts for response
        social_count = len(social_data.get("data", {}).get("social_data", []))
        review_count = len(review_data.get("data", {}).get("review_data", []))
        survey_count = extract_count_from_survey_data(survey_data)
        
        # Update task status
        tasks[task_id] = {
            "status": "completed",
            "message": "Data collection completed",
            "sources": {
                "social": social_count,
                "review": review_count,
                "survey": survey_count
            },
            "data_path": f"output/data/collected_data_{task_id}.json",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        tasks[task_id] = {
            "status": "failed",
            "message": f"Collection failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

def run_processing_task(task_id: str, collection_data_path: str):
    try:
        # Update task status
        tasks[task_id] = {
            "status": "processing",
            "message": "Processing collected data",
            "timestamp": datetime.now().isoformat()
        }
        
        # Load collected data
        with open(collection_data_path, 'r') as f:
            collected_data = json.load(f)
        
        # Initialize processor
        data_processor = DataProcessor()
        
        # Process data
        processed_data = data_processor.run(collected_data)
        
        # Save processed data
        output_path = save_output(processed_data, "output/data", f"processed_data_{task_id}.json")
        
        # Update task status
        tasks[task_id] = {
            "status": "completed",
            "message": "Data processing completed",
            "data_path": output_path,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        tasks[task_id] = {
            "status": "failed",
            "message": f"Processing failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

def run_analysis_task(task_id: str, processed_data_path: str):
    try:
        # Update task status
        tasks[task_id] = {
            "status": "analyzing",
            "message": "Analyzing processed data",
            "timestamp": datetime.now().isoformat()
        }
        
        # Load processed data
        with open(processed_data_path, 'r') as f:
            processed_data = json.load(f)
        
        # Initialize analyzer
        analysis_agent = AnalysisAgent()
        
        # Analyze data
        analysis_result = analysis_agent.run(processed_data)
        
        # Save analysis results
        output_path = save_output(analysis_result, "output/analysis", f"analysis_result_{task_id}.json")
        
        # Extract metrics for response
        sentiment_summary = analysis_result.get("data", {}).get("sentiment_summary", {})
        top_issues = analysis_result.get("data", {}).get("top_issues", {})
        
        # Update task status
        tasks[task_id] = {
            "status": "completed",
            "message": "Data analysis completed",
            "data_path": output_path,
            "sentiment_summary": sentiment_summary,
            "top_issues": top_issues,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        tasks[task_id] = {
            "status": "failed",
            "message": f"Analysis failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

def run_dashboard_task(task_id: str, analysis_result_path: str, include_alerts=True, include_report=True):
    try:
        # Update task status
        tasks[task_id] = {
            "status": "generating_dashboard",
            "message": "Generating dashboard from analysis results",
            "timestamp": datetime.now().isoformat()
        }
        
        # Load analysis data
        with open(analysis_result_path, 'r') as f:
            analysis_result = json.load(f)
        
        # Initialize dashboard agent
        dashboard_agent = DashboardAgent()
        
        # Generate dashboard
        dashboard_result = dashboard_agent.run(analysis_result)
        
        # Save dashboard results
        dashboard_path = save_output(dashboard_result, "output/dashboards", f"dashboard_result_{task_id}.json")
        
        # Save HTML dashboard if available
        html_path = None
        if 'charts' in dashboard_result.get('data', {}):
            dashboard_html = dashboard_result.get('data', {}).get('html', None)
            if dashboard_html:
                html_path = os.path.join("output/dashboards", f"dashboard_{task_id}.html")
                with open(html_path, 'w') as f:
                    f.write(dashboard_html)
        
        # Generate alerts if requested
        alert_result = None
        if include_alerts:
            # Initialize alert agent
            alert_agent = AlertAgent()
            
            # Generate alerts
            alert_result = alert_agent.run(dashboard_result)
            
            # Save alert results
            save_output(alert_result, "output/dashboards", f"alerts_{task_id}.json")
        
        # Generate report if requested
        if include_report:
            # Initialize report agent
            report_agent = ReportAgent()
            
            # Combine results for reporting
            report_input = {
                "analysis": analysis_result,
                "dashboard": dashboard_result,
                "alerts": alert_result
            }
            
            # Generate report
            report_result = report_agent.run(report_input)
            
            # Save report
            save_output(report_result, "output/reports", f"report_{task_id}.json")
        
        # Extract metrics for response
        chart_count = len(dashboard_result.get("data", {}).get("charts", {}))
        alert_count = len(dashboard_result.get("data", {}).get("alerts", []) if alert_result else [])
        
        # Update task status
        tasks[task_id] = {
            "status": "completed",
            "message": "Dashboard generation completed",
            "data_path": dashboard_path,
            "html_path": html_path,
            "chart_count": chart_count,
            "alert_count": alert_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        tasks[task_id] = {
            "status": "failed",
            "message": f"Dashboard generation failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

# Helper functions from main.py
def prepare_dummy_social_data(config):
    """Generate dummy social media data based on config"""
    platform = config.get("platform", "Twitter")
    hashtags = config.get("hashtags", ["#Default"])
    
    # Create dummy data
    return [
        {
            "user_id": "user123",
            "user_name": "John Doe",
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
                "reviewer_name": "Alex Johnson",
                "email": "alex@example.com",
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
            "name": "Mike Johnson",
            "email": "mike@example.com",
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

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Welcome to the Feedback Analysis API", "version": "1.0.0"}

@app.post("/api/v1/collect", response_model=CollectionResponse)
async def collect_data(
    background_tasks: BackgroundTasks,
    request: CollectionRequest = Body(...),
):
    # Generate task ID
    task_id = f"collect_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Initialize task status
    tasks[task_id] = {
        "status": "pending",
        "message": "Data collection task created",
        "timestamp": datetime.now().isoformat()
    }
    
    # Run collection in background
    background_tasks.add_task(run_collection_task, task_id, request.config)
    
    return CollectionResponse(
        task_id=task_id,
        status="pending",
        timestamp=datetime.now().isoformat()
    )

@app.post("/api/v1/collect/survey-files", response_model=CollectionResponse)
async def collect_data_with_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    config: str = Body(...),  # JSON string of FeedbackConfig
):
    # Parse config
    config_obj = FeedbackConfig.parse_raw(config)
    
    # Generate task ID
    task_id = f"collect_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Create directory for uploaded files
    upload_dir = os.path.join("temp/uploads", task_id)
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save uploaded files
    for file in files:
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    
    # Initialize task status
    tasks[task_id] = {
        "status": "pending",
        "message": "Data collection task created with uploaded files",
        "timestamp": datetime.now().isoformat()
    }
    
    # Run collection in background with uploaded files
    background_tasks.add_task(run_collection_task, task_id, config_obj, upload_dir)
    
    return CollectionResponse(
        task_id=task_id,
        status="pending",
        timestamp=datetime.now().isoformat()
    )

@app.post("/api/v1/process/{collection_task_id}", response_model=TaskStatus)
async def process_data(
    background_tasks: BackgroundTasks,
    collection_task_id: str,
):
    # Check if collection task exists and is completed
    if collection_task_id not in tasks:
        raise HTTPException(status_code=404, detail="Collection task not found")
    
    collection_task = tasks[collection_task_id]
    if collection_task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Collection task not yet completed")
    
    # Generate task ID
    task_id = f"process_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Initialize task status
    tasks[task_id] = {
        "status": "pending",
        "message": "Data processing task created",
        "timestamp": datetime.now().isoformat()
    }
    
    # Get path to collected data
    collection_data_path = collection_task.get("data_path")
    
    # Run processing in background
    background_tasks.add_task(run_processing_task, task_id, collection_data_path)
    
    return TaskStatus(
        task_id=task_id,
        status="pending",
        message="Processing task created",
        timestamp=datetime.now().isoformat()
    )

@app.post("/api/v1/analyze/{processing_task_id}", response_model=AnalysisResponse)
async def analyze_data(
    background_tasks: BackgroundTasks,
    processing_task_id: str,
):
    # Check if processing task exists and is completed
    if processing_task_id not in tasks:
        raise HTTPException(status_code=404, detail="Processing task not found")
    
    processing_task = tasks[processing_task_id]
    if processing_task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Processing task not yet completed")
    
    # Generate task ID
    task_id = f"analyze_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Initialize task status
    tasks[task_id] = {
        "status": "pending",
        "message": "Data analysis task created",
        "timestamp": datetime.now().isoformat()
    }
    
    # Get path to processed data
    processed_data_path = processing_task.get("data_path")
    
    # Run analysis in background
    background_tasks.add_task(run_analysis_task, task_id, processed_data_path)
    
    return AnalysisResponse(
        task_id=task_id,
        status="pending",
        timestamp=datetime.now().isoformat()
    )

@app.post("/api/v1/dashboard/{analysis_task_id}", response_model=DashboardResponse)
async def generate_dashboard(
    background_tasks: BackgroundTasks,
    analysis_task_id: str,
    include_alerts: bool = Query(True, description="Include alert generation"),
    include_report: bool = Query(True, description="Include report generation"),
):
    # Check if analysis task exists and is completed
    if analysis_task_id not in tasks:
        raise HTTPException(status_code=404, detail="Analysis task not found")
    
    analysis_task = tasks[analysis_task_id]
    if analysis_task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Analysis task not yet completed")
    
    # Generate task ID
    task_id = f"dashboard_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Initialize task status
    tasks[task_id] = {
        "status": "pending",
        "message": "Dashboard generation task created",
        "timestamp": datetime.now().isoformat()
    }
    
    # Get path to analysis results
    analysis_result_path = analysis_task.get("data_path")
    
    # Run dashboard generation in background
    background_tasks.add_task(
        run_dashboard_task, 
        task_id, 
        analysis_result_path, 
        include_alerts, 
        include_report
    )
    
    return DashboardResponse(
        task_id=task_id,
        status="pending",
        timestamp=datetime.now().isoformat()
    )

@app.get("/api/v1/task/{task_id}", response_model=Dict[str, Any])
async def get_task_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_info = tasks[task_id]
    
    # Add task_id to response
    response = {
        "task_id": task_id,
        **task_info
    }
    
    return response

@app.get("/api/v1/dashboard/{task_id}/html", response_class=HTMLResponse)
async def get_dashboard_html(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Dashboard task not found")
    
    task_info = tasks[task_id]
    if task_info["status"] != "completed":
        raise HTTPException(status_code=400, detail="Dashboard generation not yet completed")
    
    html_path = task_info.get("html_path")
    if not html_path or not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="Dashboard HTML not found")
    
    with open(html_path, "r") as f:
        html_content = f.read()
    
    return HTMLResponse(content=html_content)

@app.get("/api/v1/report/{dashboard_task_id}")
async def get_report(dashboard_task_id: str):
    if dashboard_task_id not in tasks:
        raise HTTPException(status_code=404, detail="Dashboard task not found")
    
    dashboard_task = tasks[dashboard_task_id]
    if dashboard_task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Dashboard generation not yet completed")
    
    # Load report data
    report_path = os.path.join("output/reports", f"report_{dashboard_task_id}.json")
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")
    
    with open(report_path, "r") as f:
        report_data = json.load(f)
    
    return report_data
@app.post("/api/v1/pipeline", response_model=Dict[str, Any])
async def run_complete_pipeline(
    background_tasks: BackgroundTasks,
    request: CollectionRequest = Body(...),
):
    """Run the complete feedback analysis pipeline from collection to dashboard."""
    
    # Step 1: Data Collection
    collect_task_id = f"collect_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Initialize task status
    tasks[collect_task_id] = {
        "status": "pending",
        "message": "Data collection task created",
        "timestamp": datetime.now().isoformat()
    }
    
    # Run collection (not in background since we need to chain tasks)
    run_collection_task(collect_task_id, request.config)
    
    # Check if collection completed successfully
    if tasks[collect_task_id]["status"] != "completed":
        return {
            "error": "Collection task failed",
            "details": tasks[collect_task_id],
        }
    
    # Step 2: Data Processing
    process_task_id = f"process_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    tasks[process_task_id] = {
        "status": "pending",
        "message": "Data processing task created",
        "timestamp": datetime.now().isoformat()
    }
    
    # Get path to collected data
    collection_data_path = tasks[collect_task_id].get("data_path")
    
    # Run processing
    run_processing_task(process_task_id, collection_data_path)
    
    # Check if processing completed successfully
    if tasks[process_task_id]["status"] != "completed":
        return {
            "error": "Processing task failed",
            "details": tasks[process_task_id],
        }
    
    # Step 3: Data Analysis
    analysis_task_id = f"analyze_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    tasks[analysis_task_id] = {
        "status": "pending",
        "message": "Data analysis task created",
        "timestamp": datetime.now().isoformat()
    }
    
    # Get path to processed data
    processed_data_path = tasks[process_task_id].get("data_path")
    
    # Run analysis
    run_analysis_task(analysis_task_id, processed_data_path)
    
    # Check if analysis completed successfully
    if tasks[analysis_task_id]["status"] != "completed":
        return {
            "error": "Analysis task failed",
            "details": tasks[analysis_task_id],
        }
    
    # Step 4: Dashboard Generation
    dashboard_task_id = f"dashboard_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    tasks[dashboard_task_id] = {
        "status": "pending",
        "message": "Dashboard generation task created",
        "timestamp": datetime.now().isoformat()
    }
    
    # Get path to analysis results
    analysis_result_path = tasks[analysis_task_id].get("data_path")
    
    # Run dashboard generation
    run_dashboard_task(dashboard_task_id, analysis_result_path, True, True)
    
    # Collect all task IDs and statuses for the response
    pipeline_result = {
        "collection": {
            "task_id": collect_task_id,
            "status": tasks[collect_task_id]["status"],
            "source_counts": tasks[collect_task_id].get("sources", {})
        },
        "processing": {
            "task_id": process_task_id,
            "status": tasks[process_task_id]["status"]
        },
        "analysis": {
            "task_id": analysis_task_id,
            "status": tasks[analysis_task_id]["status"],
            "sentiment_summary": tasks[analysis_task_id].get("sentiment_summary", {})
        },
        "dashboard": {
            "task_id": dashboard_task_id,
            "status": tasks[dashboard_task_id]["status"],
            "chart_count": tasks[dashboard_task_id].get("chart_count", 0),
            "dashboard_url": f"/api/v1/dashboard/{dashboard_task_id}/html" if tasks[dashboard_task_id].get("html_path") else None
        }
    }
    
    return pipeline_result

@app.delete("/api/v1/task/{task_id}")
async def delete_task(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Remove task from tasks dictionary
    task_info = tasks.pop(task_id)
    
    # Remove associated files
    data_path = task_info.get("data_path")
    if data_path and os.path.exists(data_path):
        os.remove(data_path)
    
    html_path = task_info.get("html_path")
    if html_path and os.path.exists(html_path):
        os.remove(html_path)
    
    # Clean up uploaded files if they exist
    upload_dir = os.path.join("temp/uploads", task_id)
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)
    
    return {"message": f"Task {task_id} and associated files deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
