# backend/core/mongodb_client.py - FIXED VERSION
"""
FIXED MongoDB Client for Medical Data Storage
FIXED: Single database connection, no multiple database creation
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pymongo import MongoClient, IndexModel, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, PyMongoError
import json
from bson import ObjectId

logger = logging.getLogger(__name__)

class MongoDBClient:
    """
    FIXED MongoDB client - ensures single database usage
    """
    
    def __init__(self, connection_string=None, database_name="maichart_medical"):
        self.connection_string = connection_string or os.getenv("MONGODB_CONNECTION_STRING")
        self.database_name = os.getenv("MONGODB_DATABASE_NAME", "maichart_medical")
        self.client = None
        self.db = None
        
        if not self.connection_string:
            raise ValueError("MongoDB connection string must be provided")
        
        # FIXED: Ensure we don't create multiple databases
        if self.database_name != database_name and database_name == "maichart_medical":
            logger.info(f"Using database name from environment: {self.database_name}")
        
        self._connect()
        self._setup_collections()
    
    def _connect(self):
        """Connect to MongoDB and setup database - FIXED to use single database"""
        try:
            # FIXED: Ensure connection string doesn't have database name in URL
            clean_connection_string = self.connection_string
            if '/maichart_medical' in clean_connection_string:
                clean_connection_string = clean_connection_string.replace('/maichart_medical', '')
                logger.warning("⚠️ Removed database name from connection string to prevent multiple DB creation")
            
            self.client = MongoClient(
                clean_connection_string,
                serverSelectionTimeoutMS=int(os.getenv("MONGODB_CONNECT_TIMEOUT_MS", 10000)),
                connectTimeoutMS=int(os.getenv("MONGODB_CONNECT_TIMEOUT_MS", 10000)),
                socketTimeoutMS=int(os.getenv("MONGODB_SOCKET_TIMEOUT_MS", 20000)),
                maxPoolSize=int(os.getenv("MONGODB_MAX_POOL_SIZE", 50))
            )
            
            # Test connection
            self.client.admin.command('ping')
            
            # FIXED: Use the specific database name from environment
            self.db = self.client[self.database_name]
            
            logger.info(f"✅ Connected to MongoDB database: {self.database_name}")
            logger.info(f"🏥 Using single database for all medical data: {self.database_name}")
            
        except ConnectionFailure as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error connecting to MongoDB: {e}")
            raise
    
    def _setup_collections(self):
        """Setup collections and indexes - FIXED to ensure single database"""
        try:
            logger.info(f"📋 Setting up collections in database: {self.database_name}")
            
            # Sessions collection indexes
            sessions_indexes = [
                IndexModel([("session_id", ASCENDING)], unique=True),
                IndexModel([("uploaded_at", DESCENDING)]),
                IndexModel([("status", ASCENDING)]),
                IndexModel([("processing_strategy", ASCENDING)]),
                IndexModel([("uploaded_at", DESCENDING), ("status", ASCENDING)])
            ]
            self.db.sessions.create_indexes(sessions_indexes)
            logger.info("✅ Sessions collection indexes created")
            
            # Transcripts collection indexes
            transcripts_indexes = [
                IndexModel([("session_id", ASCENDING)], unique=True),
                IndexModel([("created_at", DESCENDING)]),
                IndexModel([("confidence", DESCENDING)]),
                IndexModel([("word_count", DESCENDING)]),
                IndexModel([("transcript_text", "text")])  # Full text search
            ]
            self.db.transcripts.create_indexes(transcripts_indexes)
            logger.info("✅ Transcripts collection indexes created")
            
            # Medical extractions collection indexes
            medical_indexes = [
                IndexModel([("session_id", ASCENDING)], unique=True),
                IndexModel([("extracted_at", DESCENDING)]),
                IndexModel([("patient_details.name", ASCENDING)]),
                IndexModel([("patient_details.age", ASCENDING)]),
                IndexModel([("allergies", ASCENDING)]),
                IndexModel([("chronic_diseases", ASCENDING)]),
                IndexModel([("possible_diseases", ASCENDING)]),
                IndexModel([("extraction_metadata.method", ASCENDING)])
            ]
            self.db.medical_extractions.create_indexes(medical_indexes)
            logger.info("✅ Medical extractions collection indexes created")
            
            # Medical alerts collection indexes
            alerts_indexes = [
                IndexModel([("session_id", ASCENDING)]),
                IndexModel([("created_at", DESCENDING)]),
                IndexModel([("priority", ASCENDING)]),
                IndexModel([("alert_type", ASCENDING)]),
                IndexModel([("session_id", ASCENDING), ("priority", ASCENDING)])
            ]
            self.db.medical_alerts.create_indexes(alerts_indexes)
            logger.info("✅ Medical alerts collection indexes created")
            
            # Compound indexes for analytics
            self.db.medical_extractions.create_index([
                ("extracted_at", DESCENDING), 
                ("allergies", ASCENDING)
            ])
            self.db.medical_extractions.create_index([
                ("patient_details.age", ASCENDING), 
                ("chronic_diseases", ASCENDING)
            ])
            
            logger.info(f"✅ All collections and indexes setup completed in database: {self.database_name}")
            
            # FIXED: Log which database we're actually using
            collections = self.db.list_collection_names()
            logger.info(f"📊 Active collections in {self.database_name}: {collections}")
            
        except Exception as e:
            logger.error(f"❌ Error setting up MongoDB collections: {e}")
            raise
    
    def health_check(self) -> bool:
        """Check if MongoDB connection is healthy"""
        try:
            self.client.admin.command('ping')
            # FIXED: Also check if we can access our specific database
            self.db.command('ping')
            return True
        except Exception as e:
            logger.error(f"❌ MongoDB health check failed: {e}")
            return False
    
    def close_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info(f"📤 MongoDB connection closed for database: {self.database_name}")
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get information about the current database - FIXED"""
        try:
            db_stats = self.db.command("dbStats")
            collections = self.db.list_collection_names()
            
            return {
                "database_name": self.database_name,
                "collections": collections,
                "collection_count": len(collections),
                "data_size": db_stats.get("dataSize", 0),
                "storage_size": db_stats.get("storageSize", 0),
                "index_size": db_stats.get("indexSize", 0),
                "document_count": db_stats.get("objects", 0)
            }
        except Exception as e:
            logger.error(f"❌ Error getting database info: {e}")
            return {"database_name": self.database_name, "error": str(e)}
    
    # ==========================================
    # SESSION MANAGEMENT - FIXED
    # ==========================================
    
    def store_session(self, session_data: Dict[str, Any]) -> bool:
        """Store or update session data in the correct database"""
        try:
            session_id = session_data.get("session_id")
            if not session_id:
                logger.error("❌ Session ID required for storage")
                return False
            
            # Add/update MongoDB metadata
            now = datetime.now(timezone.utc)
            session_data.update({
                "updated_at": now,
                "_created_at": session_data.get("_created_at", now),
                "_database": self.database_name  # FIXED: Track which database
            })
            
            # Upsert session data
            result = self.db.sessions.update_one(
                {"session_id": session_id},
                {"$set": session_data},
                upsert=True
            )
            
            action = "updated" if result.matched_count > 0 else "created"
            logger.info(f"✅ Session {action} in {self.database_name}: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error storing session data: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data by ID from the correct database"""
        try:
            session = self.db.sessions.find_one(
                {"session_id": session_id},
                {"_id": 0}  # Exclude MongoDB ObjectId
            )
            if session:
                logger.debug(f"📖 Retrieved session from {self.database_name}: {session_id}")
            return session
        except Exception as e:
            logger.error(f"❌ Error retrieving session {session_id}: {e}")
            return None
    
    def update_session_status(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update specific fields in session"""
        try:
            updates.update({
                "updated_at": datetime.now(timezone.utc),
                "_database": self.database_name
            })
            
            result = self.db.sessions.update_one(
                {"session_id": session_id},
                {"$set": updates}
            )
            
            if result.matched_count > 0:
                logger.debug(f"✅ Session {session_id} updated in {self.database_name}")
                return True
            else:
                logger.warning(f"⚠️ Session {session_id} not found for update in {self.database_name}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating session {session_id}: {e}")
            return False
    
    # ==========================================
    # MEDICAL EXTRACTION MANAGEMENT - FIXED
    # ==========================================
    
    def store_medical_extraction(self, session_id: str, medical_data: Dict[str, Any]) -> bool:
        """Store medical extraction data in the correct database"""
        try:
            now = datetime.now(timezone.utc)
            
            # Prepare medical document
            medical_doc = {
                "session_id": session_id,
                "extracted_at": now,
                "updated_at": now,
                "_database": self.database_name  # FIXED: Track database
            }
            
            # Add all medical data fields
            medical_fields = [
                "patient_details", "chief_complaints", "chief_complaint_details",
                "past_history", "chronic_diseases", "lifestyle", "drug_history",
                "family_history", "allergies", "symptoms", "possible_diseases",
                "extraction_metadata"
            ]
            
            for field in medical_fields:
                if field in medical_data:
                    medical_doc[field] = medical_data[field]
            
            # Store in MongoDB
            result = self.db.medical_extractions.update_one(
                {"session_id": session_id},
                {"$set": medical_doc},
                upsert=True
            )
            
            action = "updated" if result.matched_count > 0 else "created"
            logger.info(f"✅ Medical extraction {action} in {self.database_name}: {session_id}")
            
            # Generate and store alerts
            self._generate_and_store_alerts(session_id, medical_data)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error storing medical extraction for {session_id}: {e}")
            return False
    
    def get_medical_extraction(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve medical extraction by session ID from correct database"""
        try:
            medical_data = self.db.medical_extractions.find_one(
                {"session_id": session_id},
                {"_id": 0}
            )
            if medical_data:
                logger.debug(f"📖 Retrieved medical data from {self.database_name}: {session_id}")
            return medical_data
        except Exception as e:
            logger.error(f"❌ Error retrieving medical extraction for {session_id}: {e}")
            return None
    
    def _generate_and_store_alerts(self, session_id: str, medical_data: Dict[str, Any]):
        """Generate and store medical alerts in the correct database"""
        try:
            alerts = []
            now = datetime.now(timezone.utc)
            
            # Critical allergies alert
            allergies = medical_data.get("allergies", [])
            if allergies:
                alerts.append({
                    "session_id": session_id,
                    "alert_type": "allergies",
                    "priority": "critical",
                    "title": "⚠️ ALLERGIES IDENTIFIED",
                    "message": f"Patient has {len(allergies)} known allergies",
                    "details": allergies,
                    "action_required": "Verify before prescribing medications",
                    "created_at": now,
                    "_database": self.database_name
                })
            
            # High severity symptoms
            complaint_details = medical_data.get("chief_complaint_details", [])
            high_severity_complaints = []
            for complaint in complaint_details:
                severity = complaint.get("severity", "")
                if isinstance(severity, str) and ("high" in severity.lower() or 
                    any(num in severity for num in ["8", "9", "10"]) or
                    "severe" in severity.lower()):
                    high_severity_complaints.append(complaint)
            
            if high_severity_complaints:
                alerts.append({
                    "session_id": session_id,
                    "alert_type": "high_severity",
                    "priority": "high",
                    "title": "🚨 HIGH SEVERITY SYMPTOMS",
                    "message": f"{len(high_severity_complaints)} high-severity complaints identified",
                    "details": [c.get("complaint", "Unknown") for c in high_severity_complaints],
                    "action_required": "Immediate medical attention may be required",
                    "created_at": now,
                    "_database": self.database_name
                })
            
            # Multiple chronic diseases
            chronic_diseases = medical_data.get("chronic_diseases", [])
            if len(chronic_diseases) > 2:
                alerts.append({
                    "session_id": session_id,
                    "alert_type": "multiple_chronic",
                    "priority": "medium",
                    "title": "📋 MULTIPLE CHRONIC CONDITIONS",
                    "message": f"Patient has {len(chronic_diseases)} chronic conditions",
                    "details": chronic_diseases,
                    "action_required": "Consider drug interactions and comprehensive care plan",
                    "created_at": now,
                    "_database": self.database_name
                })
            
            # Store alerts if any were generated
            if alerts:
                # First delete existing alerts for this session
                self.db.medical_alerts.delete_many({"session_id": session_id})
                
                # Insert new alerts
                self.db.medical_alerts.insert_many(alerts)
                logger.info(f"✅ Generated {len(alerts)} medical alerts in {self.database_name} for {session_id}")
            
        except Exception as e:
            logger.error(f"❌ Error generating alerts for {session_id}: {e}")
    
    def get_medical_alerts(self, session_id: str) -> List[Dict[str, Any]]:
        """Get medical alerts for a session from correct database"""
        try:
            alerts = list(self.db.medical_alerts.find(
                {"session_id": session_id},
                {"_id": 0}
            ).sort("created_at", DESCENDING))
            
            # Add priority ordering for sorting
            priority_map = {"critical": 1, "high": 2, "medium": 3, "low": 4}
            for alert in alerts:
                alert["priority_order"] = priority_map.get(alert.get("priority", "medium"), 3)
            
            return sorted(alerts, key=lambda x: x["priority_order"])
        except Exception as e:
            logger.error(f"❌ Error retrieving alerts for {session_id}: {e}")
            return []
    
    # ==========================================
    # ANALYTICS AND REPORTING - FIXED
    # ==========================================
    
    def get_medical_statistics(self) -> Dict[str, Any]:
        """Get comprehensive medical extraction statistics from correct database"""
        try:
            stats = {"database_name": self.database_name}
            
            # Total counts
            stats["total_sessions"] = self.db.sessions.count_documents({})
            stats["total_transcripts"] = self.db.transcripts.count_documents({})
            stats["total_medical_extractions"] = self.db.medical_extractions.count_documents({})
            stats["total_alerts"] = self.db.medical_alerts.count_documents({})
            
            # Status distribution
            status_pipeline = [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            status_dist = list(self.db.sessions.aggregate(status_pipeline))
            stats["status_distribution"] = {item["_id"]: item["count"] for item in status_dist}
            
            # Alert priority distribution
            alert_pipeline = [
                {"$group": {"_id": "$priority", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            alert_dist = list(self.db.medical_alerts.aggregate(alert_pipeline))
            stats["alert_distribution"] = {item["_id"]: item["count"] for item in alert_dist}
            
            # Most common conditions
            conditions_pipeline = [
                {"$unwind": "$possible_diseases"},
                {"$group": {"_id": "$possible_diseases", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            common_conditions = list(self.db.medical_extractions.aggregate(conditions_pipeline))
            stats["common_conditions"] = {item["_id"]: item["count"] for item in common_conditions}
            
            # Most common medications
            medications_pipeline = [
                {"$unwind": "$drug_history"},
                {"$group": {"_id": "$drug_history", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            common_meds = list(self.db.medical_extractions.aggregate(medications_pipeline))
            stats["common_medications"] = {item["_id"]: item["count"] for item in common_meds}
            
            # Patients with allergies count
            stats["patients_with_allergies"] = self.db.medical_extractions.count_documents({
                "allergies": {"$exists": True, "$not": {"$size": 0}}
            })
            
            # Recent activity (last 7 days)
            from datetime import timedelta
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            stats["recent_sessions"] = self.db.sessions.count_documents({
                "uploaded_at": {"$gte": week_ago}
            })
            
            # Average confidence score
            confidence_pipeline = [
                {"$group": {"_id": None, "avg_confidence": {"$avg": "$confidence"}}}
            ]
            avg_conf = list(self.db.transcripts.aggregate(confidence_pipeline))
            stats["average_confidence"] = round(avg_conf[0]["avg_confidence"], 3) if avg_conf else 0
            
            logger.info(f"📊 Generated statistics for database: {self.database_name}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting medical statistics: {e}")
            return {"database_name": self.database_name, "error": str(e)}
    
    def search_patients_by_condition(self, condition: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search patients by medical condition in correct database"""
        try:
            query = {
                "$or": [
                    {"possible_diseases": {"$regex": condition, "$options": "i"}},
                    {"chronic_diseases": {"$regex": condition, "$options": "i"}},
                    {"chief_complaints": {"$regex": condition, "$options": "i"}}
                ]
            }
            
            results = list(self.db.medical_extractions.find(
                query,
                {"_id": 0}
            ).limit(limit))
            
            return results
        except Exception as e:
            logger.error(f"❌ Error searching patients by condition {condition}: {e}")
            return []
    
    def get_patients_with_allergies(self, allergy: str = None) -> List[Dict[str, Any]]:
        """Get patients with specific allergy or all patients with allergies from correct database"""
        try:
            if allergy:
                query = {"allergies": {"$regex": allergy, "$options": "i"}}
            else:
                query = {"allergies": {"$exists": True, "$not": {"$size": 0}}}
            
            results = list(self.db.medical_extractions.find(
                query,
                {"_id": 0, "session_id": 1, "patient_details": 1, "allergies": 1, "extracted_at": 1}
            ).sort("extracted_at", DESCENDING))
            
            return results
        except Exception as e:
            logger.error(f"❌ Error retrieving patients with allergies: {e}")
            return []


# FIXED: Factory function with proper database name handling
def get_mongodb_client() -> MongoDBClient:
    """Factory function to create MongoDB client instance with consistent database name"""
    try:
        # FIXED: Always use the same database name from environment
        database_name = os.getenv("MONGODB_DATABASE_NAME", "maichart_medical")
        connection_string = os.getenv("MONGODB_CONNECTION_STRING")
        
        if not connection_string:
            raise ValueError("MONGODB_CONNECTION_STRING environment variable is required")
        
        client = MongoDBClient(
            connection_string=connection_string,
            database_name=database_name
        )
        logger.info(f"✅ Created MongoDB client for database: {database_name}")
        return client
    except Exception as e:
        logger.error(f"❌ Failed to create MongoDB client: {e}")
        raise


# FIXED: Integration with existing Redis client
class HybridStorageClient:
    """
    FIXED Hybrid storage client that uses both Redis (for real-time operations) 
    and MongoDB (for persistent storage) - ensures single database usage
    """
    
    def __init__(self, redis_client, mongodb_client):
        self.redis_client = redis_client
        self.mongodb_client = mongodb_client
        
        # FIXED: Log which database we're using
        db_info = self.mongodb_client.get_database_info()
        logger.info(f"🔄 Hybrid storage initialized with database: {db_info.get('database_name')}")
    
    def store_session_data(self, session_id: str, session_data: Dict[str, Any]):
        """Store session data in both Redis and MongoDB"""
        # Store in Redis for real-time access
        self.redis_client.set_session_status(session_id, session_data)
        
        # Store in MongoDB for persistence
        self.mongodb_client.store_session(session_data)
    
    def store_medical_data(self, session_id: str, medical_data: Dict[str, Any]):
        """Store medical extraction data in both systems"""
        # Store in Redis for quick access
        medical_data_key = f"medical_data:{session_id}"
        self.redis_client.client.hset(
            medical_data_key,
            mapping={
                "medical_data": json.dumps(medical_data),
                "extracted_at": datetime.now(timezone.utc).isoformat(),
                "session_id": session_id
            }
        )
        
        # Store in MongoDB for persistent analytics
        self.mongodb_client.store_medical_extraction(session_id, medical_data)
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session status, prioritizing Redis for speed"""
        # Try Redis first for real-time data
        redis_data = self.redis_client.get_session_status(session_id)
        if redis_data:
            return redis_data
        
        # Fallback to MongoDB
        return self.mongodb_client.get_session(session_id)
    
    def get_medical_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get medical data, checking both sources"""
        # Try Redis first
        try:
            medical_data_key = f"medical_data:{session_id}"
            data = self.redis_client.client.hgetall(medical_data_key)
            if data and data.get("medical_data"):
                return json.loads(data["medical_data"])
        except Exception:
            pass
        
        # Fallback to MongoDB
        mongo_data = self.mongodb_client.get_medical_extraction(session_id)
        if mongo_data:
            # Remove MongoDB-specific fields for compatibility
            mongo_data.pop("extracted_at", None)
            mongo_data.pop("updated_at", None)
            mongo_data.pop("session_id", None)
            mongo_data.pop("_database", None)  # FIXED: Remove database tracking field
            return mongo_data
        
        return None