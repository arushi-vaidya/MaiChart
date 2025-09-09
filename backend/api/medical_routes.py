
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, FileResponse
import logging
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Create enhanced medical router
enhanced_medical_router = APIRouter()

def get_config_dep(request: Request):
    """Dependency to get config"""
    return request.app.state.config

def get_storage_client(request: Request):
    """Dependency to get appropriate storage client"""
    # Try hybrid client first, fallback to Redis
    if hasattr(request.app.state, 'hybrid_client') and request.app.state.hybrid_client:
        return request.app.state.hybrid_client
    elif hasattr(request.app.state, 'redis_client'):
        return request.app.state.redis_client
    else:
        raise HTTPException(status_code=503, detail="Storage client not available")

def get_mongodb_client(request: Request):
    """Dependency to get MongoDB client"""
    if not hasattr(request.app.state, 'mongodb_client') or not request.app.state.mongodb_client:
        raise HTTPException(status_code=503, detail="MongoDB not available")
    return request.app.state.mongodb_client

@enhanced_medical_router.get("/medical_data/{session_id}")
async def get_medical_data_enhanced(session_id: str, request: Request, config=Depends(get_config_dep)):
    """Get extracted medical data with MongoDB fallback"""
    try:
        storage_client = get_storage_client(request)
        
        # Use hybrid client method if available
        if hasattr(storage_client, 'get_medical_data'):
            medical_data = storage_client.get_medical_data(session_id)
        else:
            # Fallback to Redis-only approach
            medical_data_key = f"medical_data:{session_id}"
            data = storage_client.client.hgetall(medical_data_key)
            if data and data.get("medical_data"):
                medical_data = json.loads(data["medical_data"])
            else:
                medical_data = None
        
        if not medical_data:
            raise HTTPException(status_code=404, detail="Medical data not found")
        
        # Add storage metadata
        storage_info = {
            "mongodb_enabled": hasattr(request.app.state, 'mongodb_client') and request.app.state.mongodb_client is not None,
            "hybrid_storage": hasattr(storage_client, 'get_medical_data')
        }
        
        return JSONResponse(content={
            "success": True,
            "session_id": session_id,
            "medical_data": medical_data,
            "storage_info": storage_info
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting enhanced medical data: {str(e)}")
        raise HTTPException(status_code=500, detail="Medical data retrieval failed")

@enhanced_medical_router.get("/medical_alerts/{session_id}")
async def get_medical_alerts_enhanced(session_id: str, request: Request, config=Depends(get_config_dep)):
    """Get medical alerts with MongoDB support"""
    try:
        # Try MongoDB first if available
        if hasattr(request.app.state, 'mongodb_client') and request.app.state.mongodb_client:
            mongodb_client = request.app.state.mongodb_client
            alerts = mongodb_client.get_medical_alerts(session_id)
            
            if alerts:
                return JSONResponse(content={
                    "success": True,
                    "session_id": session_id,
                    "alerts": alerts,
                    "source": "mongodb"
                })
        
        # Fallback to extracting alerts from medical data
        storage_client = get_storage_client(request)
        
        if hasattr(storage_client, 'get_medical_data'):
            medical_data = storage_client.get_medical_data(session_id)
        else:
            medical_data_key = f"medical_data:{session_id}"
            data = storage_client.client.hgetall(medical_data_key)
            if data and data.get("medical_data"):
                medical_data = json.loads(data["medical_data"])
            else:
                medical_data = None
        
        if not medical_data:
            raise HTTPException(status_code=404, detail="Medical data not found")
        
        # Generate alerts from medical data
        alerts = generate_medical_alerts_from_data(medical_data)
        
        return JSONResponse(content={
            "success": True,
            "session_id": session_id,
            "alerts": alerts,
            "source": "generated"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting enhanced medical alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Medical alerts retrieval failed")

@enhanced_medical_router.get("/medical_analytics/summary")
async def get_medical_analytics_summary(request: Request, config=Depends(get_config_dep)):
    """Get comprehensive medical analytics summary from MongoDB"""
    try:
        mongodb_client = get_mongodb_client(request)
        stats = mongodb_client.get_medical_statistics()
        
        return JSONResponse(content={
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "analytics_summary": stats,
            "data_source": "mongodb"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting medical analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Medical analytics retrieval failed")

@enhanced_medical_router.get("/patients/by_condition/{condition}")
async def search_patients_by_condition(
    condition: str, 
    limit: int = 20, 
    request: Request = None, 
    config=Depends(get_config_dep)
):
    """Search patients by medical condition using MongoDB"""
    try:
        mongodb_client = get_mongodb_client(request)
        patients = mongodb_client.search_patients_by_condition(condition, limit)
        
        return JSONResponse(content={
            "success": True,
            "condition": condition,
            "patient_count": len(patients),
            "patients": patients
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching patients by condition: {str(e)}")
        raise HTTPException(status_code=500, detail="Patient search failed")

@enhanced_medical_router.get("/patients/with_allergies")
async def get_allergy_patients(
    allergy_type: Optional[str] = None,
    request: Request = None, 
    config=Depends(get_config_dep)
):
    """Get patients with allergies from MongoDB"""
    try:
        mongodb_client = get_mongodb_client(request)
        patients = mongodb_client.get_patients_with_allergies(allergy_type)
        
        return JSONResponse(content={
            "success": True,
            "allergy_filter": allergy_type,
            "patient_count": len(patients),
            "patients": patients
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting allergy patients: {str(e)}")
        raise HTTPException(status_code=500, detail="Allergy patient search failed")


def generate_medical_alerts_from_data(medical_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate medical alerts from extracted medical data - FIXED"""
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
            # FIXED: Handle None values properly
            severity = complaint.get("severity") or ""
            if isinstance(severity, str):  # FIXED: Check if severity is string
                severity_lower = severity.lower()
                if ("high" in severity_lower or 
                    any(num in severity for num in ["8", "9", "10"]) or
                    "severe" in severity_lower):
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
        
        # Multiple medications
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
        logger.error(f"Error generating medical alerts: {e}")
        return [{
            "type": "error",
            "priority": "high",
            "title": "❌ ALERT GENERATION ERROR",
            "message": f"Error processing medical alerts: {str(e)}",
            "details": [],
            "action_required": "Manual review required"
        }]