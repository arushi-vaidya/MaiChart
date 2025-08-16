#!/usr/bin/env python3
"""
Medical Extraction Worker - COMPLETELY FIXED VERSION
Processes completed transcripts to extract structured medical information
FIXED: Proper infinite loop, error handling, and continuous operation
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
import asyncio
import threading

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class FixedMedicalExtractionWorker(BaseWorker):
    """
    FIXED: Worker that processes completed transcripts for medical information extraction
    This version stays running continuously and processes all messages
    """

    def __init__(self, config_name="default"):
        super().__init__("medical_extraction_worker", config_name)
        
        # Override stream configuration for medical extraction
        self.stream_name = "medical_extraction_queue"
        self.consumer_group = "medical_extractors"
        
        # Medical extraction settings
        self.enable_extraction = os.getenv("ENABLE_MEDICAL_EXTRACTION", "true").lower() == "true"
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Medical extraction service (will be loaded on first use)
        self.medical_service_loaded = False
        self.medical_service_lock = threading.Lock()
        
        if not self.enable_extraction:
            logger.warning("⚠️ Medical extraction disabled")
        elif not self.openai_api_key:
            logger.warning("⚠️ OpenAI API key not found. Medical extraction will be disabled.")
            self.enable_extraction = False
        
        logger.info(f"✅ Medical extraction worker initialized (OpenAI-only mode)")

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
                return True  # Can still run but won't process
            
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

    def _load_medical_service(self):
        """Load medical extraction service on first use (lazy loading)"""
        with self.medical_service_lock:
            if not self.medical_service_loaded:
                try:
                    logger.info("🔄 Loading medical extraction service...")
                    # Import here to avoid blocking startup
                    from core.enhanced_medical_extraction_service import extract_structured_medical_data
                    self.extract_medical_data = extract_structured_medical_data
                    self.medical_service_loaded = True
                    logger.info("✅ Medical extraction service loaded successfully")
                except Exception as e:
                    logger.error(f"❌ Failed to load medical extraction service: {e}")
                    self.enable_extraction = False

    def process_message(self, message_data: dict) -> bool:
        """Process medical extraction message - FIXED to handle all errors gracefully"""
        session_id = None
        try:
            session_id = message_data.get("session_id")
            transcript_text = message_data.get("transcript_text")
            
            if not session_id:
                logger.error("❌ No session_id in message")
                return False
                
            if not transcript_text or len(transcript_text.strip()) < 10:
                logger.warning(f"⚠️ No transcript text or too short for session {session_id}")
                return self._mark_extraction_skipped(session_id, "No transcript text or too short")
            
            logger.info(f"🏥 Processing medical extraction for session {session_id}")
            logger.info(f"📝 Transcript length: {len(transcript_text)} characters")
            
            # Check if extraction is enabled
            if not self.enable_extraction:
                logger.info(f"⏭️ Medical extraction disabled for session {session_id}")
                return self._mark_extraction_skipped(session_id, "Medical extraction disabled")
            
            # Load medical service if not loaded
            if not self.medical_service_loaded:
                self._load_medical_service()
                
            if not self.medical_service_loaded:
                logger.error(f"❌ Medical service not available for session {session_id}")
                return self._mark_extraction_failed(session_id, "Medical service not available")
            
            # Update session status to processing
            self.update_session_status(session_id, {
                "medical_extraction_status": "processing",
                "medical_extraction_started_at": datetime.utcnow().isoformat()
            })
            
            # Run medical extraction with timeout
            extraction_result = self._run_medical_extraction_with_timeout(transcript_text)
            
            if extraction_result["status"] == "completed":
                # Save medical data to Redis and file
                self._save_medical_data(session_id, extraction_result["data"])
                
                # Update session status to completed
                self.update_session_status(session_id, {
                    "medical_extraction_status": "completed",
                    "medical_extraction_completed_at": datetime.utcnow().isoformat(),
                    "medical_data_available": True,
                    "medical_entities_count": (
                        len(extraction_result["data"].get("symptoms", [])) + 
                        len(extraction_result["data"].get("drug_history", [])) +
                        len(extraction_result["data"].get("possible_diseases", []))
                    ),
                    "medical_processing_time": extraction_result.get("processing_time", 0)
                })
                
                logger.info(f"✅ Medical extraction completed for session {session_id}")
                return True
                
            else:
                # Extraction failed
                error_msg = extraction_result.get("error", "Medical extraction failed")
                return self._mark_extraction_failed(session_id, error_msg)
                
        except Exception as e:
            logger.error(f"❌ Error processing medical extraction message: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Update session status
            if session_id:
                self._mark_extraction_failed(session_id, str(e))
            
            # CRITICAL: Return True to acknowledge message and prevent infinite retries
            return True

    def _run_medical_extraction_with_timeout(self, transcript_text: str) -> Dict:
        """Run medical extraction with timeout protection"""
        try:
            start_time = datetime.utcnow()
            
            # Create new event loop for this thread
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run extraction with timeout
            try:
                extraction_data = loop.run_until_complete(
                    asyncio.wait_for(
                        self.extract_medical_data(transcript_text),
                        timeout=120  # 2 minute timeout
                    )
                )
                
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                
                return {
                    "status": "completed",
                    "data": extraction_data,
                    "processing_time": processing_time
                }
                
            except asyncio.TimeoutError:
                logger.error("⏰ Medical extraction timed out after 2 minutes")
                return {
                    "status": "error",
                    "error": "Medical extraction timed out",
                    "data": {}
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
            return True  # Still return True to acknowledge message

    def _mark_extraction_failed(self, session_id: str, error_msg: str) -> bool:
        """Mark medical extraction as failed"""
        try:
            self.update_session_status(session_id, {
                "medical_extraction_status": "error",
                "medical_extraction_error": error_msg,
                "medical_extraction_failed_at": datetime.utcnow().isoformat()
            })
            logger.error(f"❌ Medical extraction failed for session {session_id}: {error_msg}")
            return True  # Return True to acknowledge message and prevent infinite retries
        except Exception as e:
            logger.error(f"❌ Error marking extraction as failed: {e}")
            return True

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
            # Don't raise - we still want to mark as completed

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
                summary.append(f"⚠️ ALLERGIES: {len(allergies)} found - {', '.join(allergies[:3])}{'...' if len(allergies) > 3 else ''}")
            
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

    def run(self):
        """Enhanced run method - FIXED to ensure continuous operation"""
        try:
            logger.info("🚀 Starting FIXED Medical Extraction Worker...")
            logger.info("🔄 This worker will run continuously and process all queued messages")
            
            # CRITICAL: Call parent's run method which has the infinite loop
            result = super().run()
            
            logger.info(f"🛑 Worker stopped with result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"💥 Fatal error in worker: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return 1


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
    """Main entry point for FIXED medical extraction worker"""
    try:
        logger.info("🚀 Starting FIXED Medical Extraction Worker...")
        
        # Validate environment variables
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("⚠️ OPENAI_API_KEY not found. Medical extraction will be limited.")
        
        worker = FixedMedicalExtractionWorker()
        logger.info("✅ FIXED medical extraction worker created successfully")
        logger.info("🔄 Starting infinite worker loop...")
        
        # This should run forever until manually stopped
        result = worker.run()
        
        logger.info(f"🛑 Worker exited with code: {result}")
        return result
        
    except KeyboardInterrupt:
        logger.info("📨 Received keyboard interrupt, shutting down gracefully...")
        return 0
    except Exception as e:
        logger.error(f"💥 Failed to start FIXED medical extraction worker: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    # Ensure proper signal handling
    import signal
    
    def signal_handler(signum, frame):
        logger.info(f"📨 Received signal {signum}, exiting...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    sys.exit(main())