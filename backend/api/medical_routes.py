"""
Medical API Routes for Structured Medical Data Extraction
Add these routes to handle medical information extraction results
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, FileResponse
import logging
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List  # Only import List, use lowercase dict

logger = logging.getLogger(__name__)

# Create medical router
medical_router = APIRouter()

def get_config_dep(request: Request):
    """Dependency to get config"""
    return request.app.state.config

def get_medical_data_from_redis(redis_client, session_id: str) -> dict:
    """Get medical data from Redis or file"""
    try:
        # Try Redis first
        medical_data_key = f"medical_data:{session_id}"
        data = redis_client.client.hgetall(medical_data_key)
        
        if data and data.get("medical_data"):
            return json.loads(data["medical_data"])
        
        # Try file if not in Redis
        config_obj = redis_client.config if hasattr(redis_client, 'config') else None
        if config_obj:
            medical_file_path = config_obj.TRANSCRIPTS_FOLDER / f"{session_id}_medical_data.json"
            if medical_file_path.exists():
                with open(medical_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting medical data: {e}")
        return None

@medical_router.get("/medical_data/{session_id}")
async def get_medical_data(session_id: str, request: Request, config = Depends(get_config_dep)):
    """Get extracted medical data for a session"""
    try:
        redis_client = request.app.state.redis_client
        medical_data = get_medical_data_from_redis(redis_client, session_id)
        
        if not medical_data:
            raise HTTPException(status_code=404, detail="Medical data not found or extraction not completed")
        
        return JSONResponse(content={
            "success": True,
            "session_id": session_id,
            "medical_data": medical_data
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting medical data: {str(e)}")
        raise HTTPException(status_code=500, detail="Medical data retrieval failed")

@medical_router.get("/medical_data/{session_id}/download")
async def download_medical_data(session_id: str, request: Request, config = Depends(get_config_dep)):
    """Download medical data as JSON file"""
    try:
        redis_client = request.app.state.redis_client
        medical_data = get_medical_data_from_redis(redis_client, session_id)
        
        if not medical_data:
            raise HTTPException(status_code=404, detail="Medical data not found")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(medical_data, f, indent=2, ensure_ascii=False)
            temp_path = f.name
        
        return FileResponse(
            path=temp_path,
            filename=f"medical_data_{session_id[:8]}.json",
            media_type="application/json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading medical data: {str(e)}")
        raise HTTPException(status_code=500, detail="Medical data download failed")

@medical_router.get("/medical_summary/{session_id}")
async def get_medical_summary(session_id: str, request: Request, config = Depends(get_config_dep)):
    """Get a formatted medical summary for a session"""
    try:
        redis_client = request.app.state.redis_client
        medical_data = get_medical_data_from_redis(redis_client, session_id)
        
        if not medical_data:
            raise HTTPException(status_code=404, detail="Medical data not found")
        
        # Create formatted summary
        summary = create_medical_summary(medical_data)
        
        return JSONResponse(content={
            "success": True,
            "session_id": session_id,
            "medical_summary": summary
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting medical summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Medical summary generation failed")

@medical_router.get("/medical_alerts/{session_id}")
async def get_medical_alerts(session_id: str, request: Request, config = Depends(get_config_dep)):
    """Get medical alerts and critical information for a session"""
    try:
        redis_client = request.app.state.redis_client
        medical_data = get_medical_data_from_redis(redis_client, session_id)
        
        if not medical_data:
            raise HTTPException(status_code=404, detail="Medical data not found")
        
        # Extract critical alerts
        alerts = extract_medical_alerts(medical_data)
        
        return JSONResponse(content={
            "success": True,
            "session_id": session_id,
            "alerts": alerts
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting medical alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Medical alerts retrieval failed")

@medical_router.get("/medical_stats")
async def get_medical_extraction_stats(request: Request, config = Depends(get_config_dep)):
    """Get statistics about medical extractions"""
    try:
        redis_client = request.app.state.redis_client
        
        # Count medical extractions
        medical_keys = redis_client.client.keys("medical_data:*")
        total_extractions = len(medical_keys)
        
        # Analyze extraction data
        extraction_stats = {
            "total_medical_extractions": total_extractions,
            "common_conditions": {},
            "common_medications": {},
            "allergy_alerts": 0,
            "high_severity_cases": 0,
            "extraction_success_rate": 0.0
        }
        
        conditions_count = {}
        medications_count = {}
        successful_extractions = 0
        
        for key in medical_keys[:50]:  # Sample first 50 for performance
            try:
                data = redis_client.client.hgetall(key)
                if data and data.get("medical_data"):
                    medical_info = json.loads(data["medical_data"])
                    successful_extractions += 1
                    
                    # Count conditions
                    for condition in medical_info.get("possible_diseases", []):
                        conditions_count[condition] = conditions_count.get(condition, 0) + 1
                    
                    # Count medications
                    for med in medical_info.get("drug_history", []):
                        medications_count[med] = medications_count.get(med, 0) + 1
                    
                    # Count alerts
                    if medical_info.get("allergies"):
                        extraction_stats["allergy_alerts"] += 1
                    
                    # Count high severity
                    for complaint in medical_info.get("chief_complaint_details", []):
                        severity = complaint.get("severity", "")
                        if ("high" in severity.lower() or "severe" in severity.lower() or 
                            any(num in severity for num in ["8", "9", "10"])):
                            extraction_stats["high_severity_cases"] += 1
                            
            except Exception as e:
                logger.warning(f"Error processing medical stats for {key}: {e}")
        
        # Calculate success rate
        if total_extractions > 0:
            extraction_stats["extraction_success_rate"] = successful_extractions / total_extractions
        
        # Get top 5 most common
        extraction_stats["common_conditions"] = dict(sorted(conditions_count.items(), key=lambda x: x[1], reverse=True)[:5])
        extraction_stats["common_medications"] = dict(sorted(medications_count.items(), key=lambda x: x[1], reverse=True)[:5])
        
        return JSONResponse(content={
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "medical_extraction_stats": extraction_stats
        })
        
    except Exception as e:
        logger.error(f"Error getting medical extraction stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Medical stats retrieval failed")

def create_medical_summary(medical_data: dict) -> dict:
    """Create a formatted medical summary from extracted data"""
    try:
        summary = {
            "patient_overview": "",
            "key_findings": [],
            "medications_count": 0,
            "allergies_count": 0,
            "symptoms_count": 0,
            "critical_alerts": []
        }
        
        # Patient overview
        patient = medical_data.get("patient_details", {})
        if patient.get("name") or patient.get("age"):
            overview_parts = []
            if patient.get("name"):
                overview_parts.append(f"Patient: {patient['name']}")
            if patient.get("age"):
                overview_parts.append(f"Age: {patient['age']}")
            if patient.get("gender"):
                overview_parts.append(f"Gender: {patient['gender']}")
            summary["patient_overview"] = ", ".join(overview_parts)
        
        # Key findings
        findings = []
        
        # Chief complaints
        complaints = medical_data.get("chief_complaints", [])
        if complaints:
            findings.append(f"Chief complaints: {', '.join(complaints)}")
        
        # Chronic diseases
        chronic = medical_data.get("chronic_diseases", [])
        if chronic:
            findings.append(f"Chronic conditions: {', '.join(chronic)}")
        
        # Possible diseases
        diseases = medical_data.get("possible_diseases", [])
        if diseases:
            findings.append(f"Possible diagnoses: {', '.join(diseases)}")
        
        summary["key_findings"] = findings
        
        # Counts
        summary["medications_count"] = len(medical_data.get("drug_history", []))
        summary["allergies_count"] = len(medical_data.get("allergies", []))
        summary["symptoms_count"] = len(medical_data.get("symptoms", []))
        
        # Critical alerts
        alerts = []
        allergies = medical_data.get("allergies", [])
        if allergies:
            alerts.append({
                "type": "allergy",
                "severity": "high",
                "message": f"Patient has {len(allergies)} known allergies: {', '.join(allergies)}"
            })
        
        # Check for high-severity complaints
        complaint_details = medical_data.get("chief_complaint_details", [])
        for complaint in complaint_details:
            severity = complaint.get("severity", "")
            if "high" in severity.lower() or any(num in severity for num in ["8", "9", "10"]):
                alerts.append({
                    "type": "high_severity_symptom",
                    "severity": "high",
                    "message": f"High severity complaint: {complaint.get('complaint', 'Unknown')} (Severity: {severity})"
                })
        
        summary["critical_alerts"] = alerts
        
        return summary
        
    except Exception as e:
        logger.error(f"Error creating medical summary: {e}")
        return {"error": str(e)}

def extract_medical_alerts(medical_data: dict) -> List[dict]:
    """Extract critical medical alerts from structured data"""
    alerts = []
    
    try:
        # Critical allergies alert
        allergies = medical_data.get("allergies", [])
        if allergies:
            alerts.append({
                "type": "allergies",
                "priority": "critical",
                "title": "⚠️ ALLERGIES IDENTIFIED",
                "message": f"Patient has {len(allergies)} known allergies",
                "details": allergies,
                "action_required": "Verify before prescribing medications"
            })
        
        # High severity symptoms
        complaint_details = medical_data.get("chief_complaint_details", [])
        high_severity_complaints = []
        for complaint in complaint_details:
            severity = complaint.get("severity", "")
            if ("high" in severity.lower() or 
                any(num in severity for num in ["8", "9", "10"]) or
                "severe" in severity.lower()):
                high_severity_complaints.append(complaint)
        
        if high_severity_complaints:
            alerts.append({
                "type": "high_severity",
                "priority": "high",
                "title": "🚨 HIGH SEVERITY SYMPTOMS",
                "message": f"{len(high_severity_complaints)} high-severity complaints identified",
                "details": [c.get("complaint", "Unknown") for c in high_severity_complaints],
                "action_required": "Immediate medical attention may be required"
            })
        
        # Multiple chronic diseases
        chronic_diseases = medical_data.get("chronic_diseases", [])
        if len(chronic_diseases) > 2:
            alerts.append({
                "type": "multiple_chronic",
                "priority": "medium",
                "title": "📋 MULTIPLE CHRONIC CONDITIONS",
                "message": f"Patient has {len(chronic_diseases)} chronic conditions",
                "details": chronic_diseases,
                "action_required": "Consider drug interactions and comprehensive care plan"
            })
        
        # Lifestyle risk factors
        lifestyle = medical_data.get("lifestyle", [])
        risk_factors = []
        for habit in lifestyle:
            habit_name = habit.get("habit", "").lower()
            if "smok" in habit_name or "tobacco" in habit_name:
                risk_factors.append(f"Smoking: {habit.get('frequency', 'Unknown frequency')}")
            elif "alcohol" in habit_name or "drink" in habit_name:
                freq = habit.get("frequency", "")
                if "daily" in freq.lower() or "heavy" in freq.lower():
                    risk_factors.append(f"Heavy alcohol use: {freq}")
        
        if risk_factors:
            alerts.append({
                "type": "lifestyle_risks",
                "priority": "medium",
                "title": "⚠️ LIFESTYLE RISK FACTORS",
                "message": f"{len(risk_factors)} risk factors identified",
                "details": risk_factors,
                "action_required": "Consider counseling and risk reduction strategies"
            })
        
        # Drug interactions check (basic)
        medications = medical_data.get("drug_history", [])
        if len(medications) > 3:
            alerts.append({
                "type": "multiple_medications",
                "priority": "medium",
                "title": "💊 MULTIPLE MEDICATIONS",
                "message": f"Patient taking {len(medications)} medications",
                "details": medications,
                "action_required": "Review for potential drug interactions"
            })
        
        # No alerts case
        if not alerts:
            alerts.append({
                "type": "no_alerts",
                "priority": "low",
                "title": "✅ NO CRITICAL ALERTS",
                "message": "No immediate medical alerts identified",
                "details": [],
                "action_required": "Continue routine care"
            })
        
        return alerts
        
    except Exception as e:
        logger.error(f"Error extracting medical alerts: {e}")
        return [{
            "type": "error",
            "priority": "high",
            "title": "❌ ALERT EXTRACTION ERROR",
            "message": f"Error processing medical alerts: {str(e)}",
            "details": [],
            "action_required": "Manual review required"
        }]

@medical_router.post("/trigger_medical_extraction/{session_id}")
async def trigger_medical_extraction(session_id: str, request: Request, config = Depends(get_config_dep)):
    """Manually trigger medical extraction for a completed transcript"""
    try:
        redis_client = request.app.state.redis_client
        
        # Get session status
        session_data = redis_client.get_session_status(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session_data.get("status") != "completed":
            raise HTTPException(status_code=400, detail="Session must be completed before medical extraction")
        
        transcript_text = session_data.get("transcript_text", "")
        if not transcript_text or len(transcript_text.strip()) < 10:
            raise HTTPException(status_code=400, detail="No transcript text available for extraction")
        
        # Queue for medical extraction
        from workers.medical_extraction_worker import queue_for_medical_extraction
        stream_id = queue_for_medical_extraction(redis_client, session_id, transcript_text)
        
        if stream_id:
            # Update session status
            redis_client.update_session_status(session_id, {
                "medical_extraction_queued": True,
                "medical_extraction_stream_id": stream_id,
                "medical_extraction_triggered_manually": True,
                "medical_extraction_queued_at": datetime.utcnow().isoformat()
            })
            
            return JSONResponse(content={
                "success": True,
                "message": "Medical extraction queued successfully",
                "session_id": session_id,
                "stream_id": stream_id
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to queue medical extraction")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering medical extraction: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to trigger medical extraction")