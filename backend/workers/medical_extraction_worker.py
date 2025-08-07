#!/usr/bin/env python3
"""
Medical Extraction Worker
Processes completed transcripts to extract structured medical information
"""

import os
import sys
import logging
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from workers.base_worker import BaseWorker
from core.enhanced_medical_extraction_service import extract_structured_medical_data

logger = logging.getLogger(__name__)


class MedicalExtractionWorker(BaseWorker):
    """
    Worker that processes completed transcripts for medical information extraction
    """

    def __init__(self, config_name="default"):
        super().__init__("medical_extraction_worker", config_name)
        
        # Override stream configuration for medical extraction
        self.stream_name = "medical_extraction_queue"
        self.consumer_group = "medical_extractors"
        
        # Medical extraction settings
        self.enable_extraction = os.getenv("ENABLE_MEDICAL_EXTRACTION", "true").lower() == "true"
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.enable_extraction:
            logger.warning("⚠️ Medical extraction disabled")
        elif not self.openai_api_key:
            logger.warning("⚠️ OpenAI API key not found. Medical extraction will be limited.")
        
        logger.info(f"✅ Medical extraction worker initialized")

    def check_dependencies(self) -> bool:
        """Check if medical extraction dependencies are available"""
        try:
            logger.info("🔍 Checking medical extraction dependencies...")
            
            if not self.enable_extraction:
                logger.info("⚠️ Medical extraction disabled in configuration")
                return True  # Worker can still run, just won't extract
            
            # Check OpenAI API key
            if not self.openai_api_key:
                logger.warning("⚠️ OpenAI API key not found")
                return True  # Can still run with BioBERT only
            
            # Check if transformers is available
            try:
                import transformers
                logger.info("✅ Transformers library available")
            except ImportError:
                logger.error("❌ Transformers library not installed")
                return False
            
            # Check if OpenAI library is available
            try:
                import openai
                logger.info("✅ OpenAI library available")
            except ImportError:
                logger.error("❌ OpenAI library not installed")
                return False
            
            logger.info("✅ All medical extraction dependencies available")
            return True
            
        except Exception as e:
            logger.error(f"❌ Dependency check failed: {e}")
            return False

    def process_message(self, message_data: dict) -> bool:
        """Process medical extraction message"""
        try:
            session_id = message_data.get("session_id")
            transcript_text = message_data.get("transcript_text")
            
            if not session_id:
                logger.error("❌ No session_id in message")
                return False
                
            if not transcript_text:
                logger.warning(f"⚠️ No transcript text for session {session_id}")
                return self._mark_extraction_skipped(session_id, "No transcript text available")
            
            logger.info(f"🏥 Processing medical extraction for session {session_id}")
            logger.info(f"📝 Transcript length: {len(transcript_text)} characters")
            
            # Update session status
            self.update_session_status(session_id, {
                "medical_extraction_status": "processing",
                "medical_extraction_started_at": datetime.utcnow().isoformat()
            })
            
            # Run medical extraction
            extraction_result = self._run_medical_extraction(transcript_text)
            
            if extraction_result["status"] == "completed":
                # Save medical data to Redis and file
                self._save_medical_data(session_id, extraction_result["data"])
                
                # Update session status
                self.update_session_status(session_id, {
                    "medical_extraction_status": "completed",
                    "medical_extraction_completed_at": datetime.utcnow().isoformat(),
                    "medical_data_available": True,
                    "medical_entities_count": len(extraction_result["data"].get("symptoms", [])) + 
                                           len(extraction_result["data"].get("drug_history", [])) +
                                           len(extraction_result["data"].get("possible_diseases", [])),
                    "medical_processing_time": extraction_result.get("processing_time", 0)
                })
                
                logger.info(f"✅ Medical extraction completed for session {session_id}")
                return True
                
            else:
                # Extraction failed
                error_msg = extraction_result.get("error", "Medical extraction failed")
                self.update_session_status(session_id, {
                    "medical_extraction_status": "error",
                    "medical_extraction_error": error_msg,
                    "medical_extraction_failed_at": datetime.utcnow().isoformat()
                })
                
                logger.error(f"❌ Medical extraction failed for session {session_id}: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error processing medical extraction message: {e}")
            
            # Update session status
            session_id = message_data.get("session_id")
            if session_id:
                self.update_session_status(session_id, {
                    "medical_extraction_status": "error",
                    "medical_extraction_error": str(e),
                    "medical_extraction_failed_at": datetime.utcnow().isoformat()
                })
            
            return False

    def _run_medical_extraction(self, transcript_text: str) -> Dict:
        """Run the medical extraction process"""
        try:
            if not self.enable_extraction:
                return {
                    "status": "skipped", 
                    "message": "Medical extraction disabled",
                    "data": {}
                }
            
            start_time = datetime.utcnow()
            
            # Run async extraction
            import asyncio
            extraction_data = asyncio.run(extract_structured_medical_data(transcript_text))
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "status": "completed",
                "data": extraction_data,
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"❌ Error running medical extraction: {e}")
            return {
                "status": "error",
                "error": str(e),
                "data": {}
            }

    def _mark_extraction_skipped(self, session_id: str, reason: str) -> bool:
        """Mark medical extraction as skipped"""
        try:
            self.update_session_status(session_id, {
                "medical_extraction_status": "skipped",
                "medical_extraction_skip_reason": reason,
                "medical_extraction_skipped_at": datetime.utcnow().isoformat()
            })
            logger.info(f"⏭️ Medical extraction skipped for session {session_id}: {reason}")
            return True
        except Exception as e:
            logger.error(f"❌ Error marking extraction as skipped: {e}")
            return False

    def _save_medical_data(self, session_id: str, medical_data: Dict):
        """Save extracted medical data to Redis and file"""
        try:
            # Save to Redis with session data
            medical_data_key = f"medical_data:{session_id}"
            self.redis_client.client.hset(
                medical_data_key,
                mapping={
                    "medical_data": json.dumps(medical_data),
                    "extracted_at": datetime.utcnow().isoformat(),
                    "session_id": session_id
                }
            )
            self.redis_client.client.expire(medical_data_key, self.config.SESSION_EXPIRE_TIME)
            
            # Save to file for persistence
            medical_file_path = self.config.TRANSCRIPTS_FOLDER / f"{session_id}_medical_data.json"
            with open(medical_file_path, 'w', encoding='utf-8') as f:
                json.dump(medical_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Medical data saved for session {session_id}")
            
            # Log extraction summary
            self._log_extraction_summary(session_id, medical_data)
            
        except Exception as e:
            logger.error(f"❌ Error saving medical data: {e}")
            raise

    def _log_extraction_summary(self, session_id: str, medical_data: Dict):
        """Log a summary of extracted medical information"""
        try:
            summary = []
            
            # Patient details
            patient = medical_data.get("patient_details", {})
            if any(patient.values()):
                summary.append(f"Patient: {patient.get('name', 'Unknown')}, {patient.get('age', 'Unknown age')}")
            
            # Chief complaints
            complaints = medical_data.get("chief_complaints", [])
            if complaints:
                summary.append(f"Chief complaints: {len(complaints)} found")
            
            # Symptoms
            symptoms = medical_data.get("symptoms", [])
            if symptoms:
                summary.append(f"Symptoms: {len(symptoms)} identified")
            
            # Medications
            medications = medical_data.get("drug_history", [])
            if medications:
                summary.append(f"Medications: {len(medications)} found")
            
            # Allergies (critical)
            allergies = medical_data.get("allergies", [])
            if allergies:
                summary.append(f"⚠️ ALLERGIES: {len(allergies)} found - {', '.join(allergies)}")
            
            # Diseases
            diseases = medical_data.get("possible_diseases", [])
            if diseases:
                summary.append(f"Possible diseases: {len(diseases)} identified")
            
            if summary:
                logger.info(f"📋 Medical Summary for {session_id}: {' | '.join(summary)}")
            else:
                logger.info(f"📋 No specific medical information extracted for {session_id}")
                
        except Exception as e:
            logger.warning(f"⚠️ Error logging extraction summary: {e}")

    def get_medical_data(self, session_id: str) -> Optional[Dict]:
        """Get extracted medical data for a session"""
        try:
            medical_data_key = f"medical_data:{session_id}"
            data = self.redis_client.client.hgetall(medical_data_key)
            
            if data and data.get("medical_data"):
                return json.loads(data["medical_data"])
            
            # Try to load from file if not in Redis
            medical_file_path = self.config.TRANSCRIPTS_FOLDER / f"{session_id}_medical_data.json"
            if medical_file_path.exists():
                with open(medical_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting medical data: {e}")
            return None


def queue_for_medical_extraction(redis_client, session_id: str, transcript_text: str):
    """
    Utility function to queue a transcript for medical extraction
    Call this from the transcription worker after transcription completes
    """
    try:
        extraction_data = {
            "session_id": session_id,
            "transcript_text": transcript_text,
            "queued_at": datetime.utcnow().isoformat(),
            "type": "medical_extraction"
        }
        
        stream_id = redis_client.add_to_stream("medical_extraction_queue", extraction_data)
        logger.info(f"📤 Queued medical extraction for session {session_id} -> {stream_id}")
        return stream_id
        
    except Exception as e:
        logger.error(f"❌ Error queuing medical extraction: {e}")
        return None


def main():
    """Main entry point for medical extraction worker"""
    try:
        logger.info("🚀 Starting Medical Extraction Worker...")
        
        # Validate environment variables
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("⚠️ OPENAI_API_KEY not found. Some features will be limited.")
        
        worker = MedicalExtractionWorker()
        logger.info("✅ Medical extraction worker created successfully")
        
        return worker.run()
        
    except Exception as e:
        logger.error(f"💥 Failed to start medical extraction worker: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())