#!/usr/bin/env python3
"""
Redis Queue Cleanup Utility
Fixes stuck Redis streams and consumer groups
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from core.redis_client import RedisClient
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedisCleanup:
    """Redis cleanup utility for MaiChart"""
    
    def __init__(self, config_name="default"):
        self.config = config[config_name]
        
        # Initialize Redis client
        self.redis_client = RedisClient(
            host=self.config.REDIS_HOST,
            port=self.config.REDIS_PORT,
            password=self.config.REDIS_PASSWORD,
            db=self.config.REDIS_DB,
        )
        
        self.streams = [
            self.config.AUDIO_INPUT_STREAM,
            self.config.AUDIO_CHUNK_STREAM,
            "medical_extraction_queue"
        ]
        
        self.consumer_groups = [
            self.config.CONSUMER_GROUP,
            self.config.CHUNK_CONSUMER_GROUP,
            "medical_extractors"
        ]
    
    def cleanup_all(self):
        """Clean up all Redis streams and consumer groups"""
        logger.info("🧹 Starting comprehensive Redis cleanup...")
        
        try:
            # 1. Clean up pending messages
            self.cleanup_pending_messages()
            
            # 2. Clean up stuck sessions
            self.cleanup_stuck_sessions()
            
            # 3. Clean up consumer groups
            self.cleanup_consumer_groups()
            
            # 4. Optional: Clear all streams (use with caution)
            # self.clear_all_streams()
            
            logger.info("✅ Redis cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")
            raise
    
    def cleanup_pending_messages(self):
        """Clean up pending messages in all consumer groups"""
        logger.info("🔄 Cleaning up pending messages...")
        
        for stream in self.streams:
            for group in self.consumer_groups:
                try:
                    # Get pending messages
                    pending = self.redis_client.client.xpending_range(
                        stream, group, "-", "+", 1000
                    )
                    
                    if pending:
                        logger.info(f"📝 Found {len(pending)} pending messages in {stream}:{group}")
                        
                        # Acknowledge all pending messages
                        message_ids = [msg["message_id"] for msg in pending]
                        if message_ids:
                            acknowledged = self.redis_client.client.xack(stream, group, *message_ids)
                            logger.info(f"✅ Acknowledged {acknowledged} messages in {stream}:{group}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error cleaning {stream}:{group}: {e}")
    
    def cleanup_stuck_sessions(self):
        """Clean up sessions stuck in processing state"""
        logger.info("🔄 Cleaning up stuck sessions...")
        
        try:
            # Find all session status keys
            session_keys = self.redis_client.client.keys("session_status:*")
            
            stuck_count = 0
            for key in session_keys:
                try:
                    status_data = self.redis_client.client.hgetall(key)
                    
                    if status_data and status_data.get("status") == "processing":
                        session_id = key.split(":")[-1]
                        
                        # Reset to queued state
                        self.redis_client.client.hset(key, mapping={
                            "status": "queued",
                            "reset_by_cleanup": "true",
                            "reset_at": "2025-01-20T00:00:00Z"
                        })
                        
                        stuck_count += 1
                        logger.info(f"🔄 Reset stuck session: {session_id}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error processing session {key}: {e}")
            
            logger.info(f"✅ Reset {stuck_count} stuck sessions")
            
        except Exception as e:
            logger.error(f"❌ Error cleaning stuck sessions: {e}")
    
    def cleanup_consumer_groups(self):
        """Recreate consumer groups to fix any corruption"""
        logger.info("🔄 Recreating consumer groups...")
        
        for stream in self.streams:
            for group in self.consumer_groups:
                try:
                    # Delete existing consumer group
                    try:
                        self.redis_client.client.xgroup_destroy(stream, group)
                        logger.info(f"🗑️ Deleted consumer group {stream}:{group}")
                    except Exception:
                        pass  # Group might not exist
                    
                    # Recreate consumer group
                    try:
                        self.redis_client.client.xgroup_create(
                            stream, group, id="0", mkstream=True
                        )
                        logger.info(f"✅ Created consumer group {stream}:{group}")
                    except Exception as e:
                        if "BUSYGROUP" not in str(e):
                            logger.warning(f"⚠️ Could not create {stream}:{group}: {e}")
                
                except Exception as e:
                    logger.warning(f"⚠️ Error with consumer group {stream}:{group}: {e}")
    
    def clear_all_streams(self):
        """DANGEROUS: Clear all stream data (use only in development)"""
        logger.warning("⚠️ CLEARING ALL STREAM DATA - USE WITH CAUTION!")
        
        for stream in self.streams:
            try:
                # Get stream length first
                length = self.redis_client.client.xlen(stream)
                if length > 0:
                    logger.warning(f"🗑️ Clearing {length} messages from {stream}")
                    
                    # Delete the entire stream
                    self.redis_client.client.delete(stream)
                    logger.warning(f"🗑️ Stream {stream} cleared")
                
            except Exception as e:
                logger.warning(f"⚠️ Error clearing stream {stream}: {e}")
    
    def get_redis_stats(self):
        """Get current Redis statistics"""
        logger.info("📊 Getting Redis statistics...")
        
        stats = {}
        
        for stream in self.streams:
            try:
                # Stream info
                stream_info = self.redis_client.client.xinfo_stream(stream)
                stats[stream] = {
                    "length": stream_info.get("length", 0),
                    "groups": stream_info.get("groups", 0),
                    "last_generated_id": stream_info.get("last-generated-id", "0-0")
                }
                
                # Consumer group info
                for group in self.consumer_groups:
                    try:
                        pending = self.redis_client.client.xpending_range(
                            stream, group, "-", "+", 1
                        )
                        stats[f"{stream}:{group}"] = {
                            "pending_messages": len(pending)
                        }
                    except Exception:
                        pass
                        
            except Exception as e:
                logger.warning(f"⚠️ Could not get stats for {stream}: {e}")
        
        # Session stats
        try:
            session_keys = self.redis_client.client.keys("session_status:*")
            session_stats = {}
            for key in session_keys:
                try:
                    status = self.redis_client.client.hget(key, "status")
                    if status:
                        session_stats[status] = session_stats.get(status, 0) + 1
                except Exception:
                    pass
            
            stats["sessions"] = session_stats
            
        except Exception as e:
            logger.warning(f"⚠️ Could not get session stats: {e}")
        
        return stats
    
    def print_stats(self):
        """Print current Redis statistics"""
        stats = self.get_redis_stats()
        
        logger.info("📊 Current Redis Statistics:")
        logger.info("=" * 50)
        
        for key, value in stats.items():
            logger.info(f"{key}: {value}")


def main():
    """Main cleanup utility"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Redis Queue Cleanup Utility for MaiChart")
    parser.add_argument("--action", choices=["cleanup", "stats", "clear"], 
                       default="cleanup", help="Action to perform")
    parser.add_argument("--force", action="store_true", 
                       help="Force clear all streams (DANGEROUS)")
    
    args = parser.parse_args()
    
    try:
        cleanup = RedisCleanup()
        
        if args.action == "stats":
            cleanup.print_stats()
            
        elif args.action == "clear" and args.force:
            logger.warning("⚠️ FORCE CLEARING ALL STREAMS!")
            response = input("Are you sure? Type 'YES' to confirm: ")
            if response == "YES":
                cleanup.clear_all_streams()
                logger.info("✅ All streams cleared")
            else:
                logger.info("❌ Operation cancelled")
                
        else:  # cleanup
            cleanup.cleanup_all()
            logger.info("🎉 Cleanup completed!")
            
            # Show stats after cleanup
            cleanup.print_stats()
    
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())