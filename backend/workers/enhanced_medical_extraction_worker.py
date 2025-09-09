#!/usr/bin/env python3
"""
FIXED Enhanced Medical Extraction Worker with MongoDB Storage
Processes completed transcripts and stores results in MongoDB
FIXED: Proper stream configuration and error handling
"""

import os
import sys
import logging
import time
import json
from datetime import datetime, timezone
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

# Try to import MongoDB clients
try:
    from core.mongodb_client import MongoDBClient, HybridStorageClient
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    MongoDBClient = None
    HybridStorageClient = None

logger = logging.getLogger(__name__)


class EnhancedMedicalExtractionWorker(BaseWorker):
    """
    FIXED Enhanced worker with MongoDB integration for medical extraction
    Stores results in both Redis (for speed) and MongoDB (for persistence)
    """

    def __init__(self, config_name="default"):
        super().__init__("enhanced_medical_extraction_worker", config_name)
        
        # FIXED: Override stream configuration for medical extraction
        self.stream_name = "medical_extraction_queue"
        self.consumer_group = "medical_extractors"
        
        # Medical extraction settings
        self.enable_extraction = os.getenv("ENABLE_MEDICAL_EXTRACTION", "true").lower() == "true"
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.enable_mongodb = os.getenv("ENABLE_MONGODB", "true").lower() == "true"
        
        # Initialize MongoDB client if enabled
        self.mongodb_client = None
        self.hybrid_client = None
        
        if self.enable_mongodb and MONGODB_AVAILABLE:
            try:
                mongodb_connection = os.getenv("MONGODB_CONNECTION_STRING")
                mongodb_database = os.getenv("MONGODB_DATABASE_NAME", "maichart_medical")
                
                if mongodb_connection:
                    self.mongodb_client = MongoDBClient(
                        connection_string=mongodb_connection,
                        database_name=mongodb_database
                    )
                    
                    # Create hybrid client for dual storage
                    self.hybrid_client = HybridStorageClient(
                        self.redis_client, 
                        self.mongodb_client
                    )
                    
                    logger.info("✅ MongoDB client initialized for medical extraction worker")
                else:
                    logger.warning("⚠️ MongoDB connection string not provided")
                    self.enable_mongodb = False
            except Exception as e:
                logger.error(f"❌ Failed to initialize MongoDB: {e}")
                logger.warning("⚠️ Continuing with Redis-only storage")
                self.enable_mongodb = False
        
        # Medical extraction service (lazy loading)
        self.medical_service_loaded = False
        self.medical_service_lock = threading.Lock()
        
        if not self.enable_extraction:
            logger.warning("⚠️ Medical extraction disabled")
        elif not self.openai_api_key:
            logger.warning("⚠️ OpenAI API key not found. Medical extraction will be disabled.")
            self.enable_extraction = False
        
        logger.info(f"✅ Enhanced medical extraction worker initialized (MongoDB: {self.enable_mongodb})")

    def check_dependencies(self) -> bool:
        """Check if medical extraction dependencies are available"""
        try:
            logger.info("🔍 Checking enhanced medical extraction dependencies...")
            
            if not self.enable_extraction:
                logger.info("⚠️ Medical extraction disabled in configuration")
                return True
            
            # Check OpenAI API key
            if not self.openai_api_key:
                logger.warning("⚠️ OpenAI API key not found")
                return True
            
            # Check OpenAI library
            try:
                import openai
                logger.info("✅ OpenAI library available")
            except ImportError:
                logger.error("❌ OpenAI library not installed")
                return False
            
            # Check MongoDB connection if enabled
            if self.enable_mongodb and self.mongodb_client:
                if not self.mongodb_client.health_check():
                    logger.warning("⚠️ MongoDB health check failed, continuing with Redis-only")
                    self.enable_mongodb = False
                else:
                    logger.info("✅ MongoDB connection healthy")
            
            logger.info("✅ All enhanced medical extraction dependencies available")
            return True
            
        except Exception as e:
            logger.error(f"❌ Dependency check failed: {e}")
            return False

    def _load_medical_service(self):
        """Load medical extraction service on first use"""
        with self.medical_service_lock:
            if not self.medical_service_loaded:
                try:
                    logger.info("🔄 Loading enhanced medical extraction service...")
                    from core.enhanced_medical_extraction_service import extract_structured_medical_data
                    self.extract_medical_data = extract_structured_medical_data
                    self.medical_service_loaded = True
                    logger.info("✅ Enhanced medical extraction service loaded successfully")
                except Exception as e:
                    logger.error(f"❌ Failed to load medical extraction service: {e}")
                    self.enable_extraction = False

    def process_message(self, message_data: dict) -> bool:
        """Process medical extraction message with MongoDB storage"""
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
            
            logger.info(f"🏥 Processing enhanced medical extraction for session {session_id}")
            logger.info(f"📝 Transcript length: {len(transcript_text)} characters")
            logger.info(f"💾 MongoDB enabled: {self.enable_mongodb}")
            
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
            self._update_session_status(session_id, {
                "medical_extraction_status": "processing",
                "medical_extraction_started_at": datetime.now(timezone.utc).isoformat(),
                "storage_mode": "mongodb" if self.enable_mongodb else "redis_only"
            })
            
            # Run medical extraction with timeout
            extraction_result = self._run_medical_extraction_with_timeout(transcript_text)
            
            if extraction_result["status"] == "completed":
                # Store medical data using hybrid approach
                success = self._store_medical_data_enhanced(session_id, extraction_result["data"])
                
                if success:
                    # Update session status to completed
                    self._update_session_status(session_id, {
                        "medical_extraction_status": "completed",
                        "medical_extraction_completed_at": datetime.now(timezone.utc).isoformat(),
                        "medical_data_available": True,
                        "medical_entities_count": (
                            len(extraction_result["data"].get("symptoms", [])) + 
                            len(extraction_result["data"].get("drug_history", [])) +
                            len(extraction_result["data"].get("possible_diseases", []))
                        ),
                        "medical_processing_time": extraction_result.get("processing_time", 0),
                        "stored_in_mongodb": self.enable_mongodb
                    })
                    
                    logger.info(f"✅ Enhanced medical extraction completed for session {session_id}")
                    return True
                else:
                    return self._mark_extraction_failed(session_id, "Failed to store medical data")
                
            else:
                # Extraction failed
                error_msg = extraction_result.get("error", "Medical extraction failed")
                return self._mark_extraction_failed(session_id, error_msg)
                
        except Exception as e:
            logger.error(f"❌ Error processing enhanced medical extraction message: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Update session status
            if session_id:
                self._mark_extraction_failed(session_id, str(e))
            
            return True  # Return True to acknowledge message

    def _run_medical_extraction_with_timeout(self, transcript_text: str) -> Dict:
        """Run medical extraction with timeout protection"""
        try:
            start_time = datetime.now(timezone.utc)
            
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
                        timeout=180  # 3 minute timeout
                    )
                )
                
                processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                return {
                    "status": "completed",
                    "data": extraction_data,
                    "processing_time": processing_time
                }
                
            except asyncio.TimeoutError:
                logger.error("⏰ Medical extraction timed out after 3 minutes")
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

    def _store_medical_data_enhanced(self, session_id: str, medical_data: Dict) -> bool:
        """Store medical data using enhanced hybrid approach"""
        try:
            success = True
            
            # Store in Redis for quick access (existing behavior)
            try:
                medical_data_key = f"medical_data:{session_id}"
                self.redis_client.client.hset(
                    medical_data_key,
                    mapping={
                        "medical_data": json.dumps(medical_data),
                        "extracted_at": datetime.now(timezone.utc).isoformat(),
                        "session_id": session_id
                    }
                )
                self.redis_client.client.expire(medical_data_key, self.config.SESSION_EXPIRE_TIME)
                logger.info(f"💾 Medical data stored in Redis for session {session_id}")
            except Exception as e:
                logger.error(f"❌ Error storing in Redis: {e}")
                success = False
            
            # Store in MongoDB if enabled
            if self.enable_mongodb and self.mongodb_client:
                try:
                    mongo_success = self.mongodb_client.store_medical_extraction(session_id, medical_data)
                    if mongo_success:
                        logger.info(f"🗄️ Medical data stored in MongoDB for session {session_id}")
                    else:
                        logger.warning(f"⚠️ Failed to store in MongoDB for session {session_id}")
                        # Don't fail the entire process if MongoDB fails
                except Exception as e:
                    logger.error(f"❌ MongoDB storage error for {session_id}: {e}")
                    # Continue with Redis-only storage
            
            # Store in file for backwards compatibility
            try:
                medical_file_path = self.config.TRANSCRIPTS_FOLDER / f"{session_id}_medical_data.json"
                with open(medical_file_path, 'w', encoding='utf-8') as f:
                    json.dump(medical_data, f, indent=2, ensure_ascii=False)
                logger.info(f"📄 Medical data backup saved to file for session {session_id}")
            except Exception as e:
                logger.warning(f"⚠️ File backup failed for {session_id}: {e}")
                # Don't fail for file storage issues
            
            # Log extraction summary
            self._log_extraction_summary(session_id, medical_data)
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error in enhanced medical data storage: {e}")
            return False

    def _update_session_status(self, session_id: str, updates: Dict):
        """Update session status in both Redis and MongoDB"""
        try:
            # Update Redis
            self.redis_client.update_session_status(session_id, updates)
            
            # Update MongoDB if available
            if self.enable_mongodb and self.mongodb_client:
                try:
                    self.mongodb_client.update_session_status(session_id, updates)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to update MongoDB status: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error updating session status: {e}")

    def _mark_extraction_skipped(self, session_id: str, reason: str) -> bool:
        """Mark medical extraction as skipped"""
        try:
            self._update_session_status(session_id, {
                "medical_extraction_status": "skipped",
                "medical_extraction_skip_reason": reason,
                "medical_extraction_skipped_at": datetime.now(timezone.utc).isoformat()
            })
            logger.info(f"⏭️ Medical extraction skipped for session {session_id}: {reason}")
            return True
        except Exception as e:
            logger.error(f"❌ Error marking extraction as skipped: {e}")
            return True

    def _mark_extraction_failed(self, session_id: str, error_msg: str) -> bool:
        """Mark medical extraction as failed"""
        try:
            self._update_session_status(session_id, {
                "medical_extraction_status": "error",
                "medical_extraction_error": error_msg,
                "medical_extraction_failed_at": datetime.now(timezone.utc).isoformat()
            })
            logger.error(f"❌ Medical extraction failed for session {session_id}: {error_msg}")
            return True
        except Exception as e:
            logger.error(f"❌ Error marking extraction as failed: {e}")
            return True

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
                storage_info = "MongoDB + Redis" if self.enable_mongodb else "Redis only"
                logger.info(f"📋 Medical Summary for {session_id} ({storage_info}): {' | '.join(summary)}")
            else:
                logger.info(f"📋 No specific medical information extracted for {session_id}")
                
        except Exception as e:
            logger.warning(f"⚠️ Error logging extraction summary: {e}")

    def run(self):
        """Enhanced run method with MongoDB integration"""
        try:
            logger.info("🚀 Starting Enhanced Medical Extraction Worker with MongoDB...")
            logger.info(f"💾 Storage mode: {'Hybrid (Redis + MongoDB)' if self.enable_mongodb else 'Redis only'}")
            
            # Call parent's run method
            result = super().run()
            
            logger.info(f"🛑 Worker stopped with result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"💥 Fatal error in enhanced worker: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return 1
        finally:
            # Clean up MongoDB connection
            if self.mongodb_client:
                self.mongodb_client.close_connection()


def queue_for_medical_extraction(redis_client, session_id: str, transcript_text: str):
    """
    Utility function to queue a transcript for enhanced medical extraction
    """
    try:
        extraction_data = {
            "session_id": session_id,
            "transcript_text": transcript_text,
            "queued_at": datetime.now(timezone.utc).isoformat(),
            "type": "enhanced_medical_extraction",
            "mongodb_enabled": os.getenv("ENABLE_MONGODB", "true").lower() == "true"
        }
        
        stream_id = redis_client.add_to_stream("medical_extraction_queue", extraction_data)
        logger.info(f"📤 Queued enhanced medical extraction for session {session_id} -> {stream_id}")
        return stream_id
        
    except Exception as e:
        logger.error(f"❌ Error queuing enhanced medical extraction: {e}")
        return None


def main():
    """Main entry point for enhanced medical extraction worker"""
    try:
        logger.info("🚀 Starting Enhanced Medical Extraction Worker with MongoDB...")
        
        # Validate environment variables
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("⚠️ OPENAI_API_KEY not found. Medical extraction will be limited.")
        
        if not os.getenv("MONGODB_CONNECTION_STRING"):
            logger.warning("⚠️ MONGODB_CONNECTION_STRING not found. Using Redis-only mode.")
        
        worker = EnhancedMedicalExtractionWorker()
        logger.info("✅ Enhanced medical extraction worker created successfully")
        
        result = worker.run()
        
        logger.info(f"🛑 Worker exited with code: {result}")
        return result
        
    except KeyboardInterrupt:
        logger.info("📨 Received keyboard interrupt, shutting down gracefully...")
        return 0
    except Exception as e:
        logger.error(f"💥 Failed to start enhanced medical extraction worker: {e}")
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