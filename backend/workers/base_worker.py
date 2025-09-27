import os
import signal
import sys
import time
import logging
from abc import ABC, abstractmethod
from datetime import datetime

from core.redis_client import RedisClient
from config import config

logger = logging.getLogger(__name__)


class BaseWorker(ABC):
    """Base class for all workers with enhanced error handling"""

    def __init__(self, worker_name=None, config_name="default"):
        self.config = config[config_name]
        self.worker_name = worker_name or self.__class__.__name__
        self.consumer_name = f"{self.worker_name}_{os.getpid()}"
        self.running = True

        # Redis connection with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.redis_client = RedisClient(
                    host=self.config.REDIS_HOST,
                    port=self.config.REDIS_PORT,
                    password=self.config.REDIS_PASSWORD, 
                    db=self.config.REDIS_DB,
                )
                logger.info(f"✅ Redis connected for worker {self.consumer_name}")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"❌ Failed to connect to Redis after {max_retries} attempts: {e}")
                    raise
                logger.warning(f"⚠️ Redis connection attempt {attempt + 1} failed: {e}")
                time.sleep(2**attempt)

        # Worker configuration
        self.stream_name = self.config.AUDIO_INPUT_STREAM
        self.consumer_group = self.config.CONSUMER_GROUP
        self.block_time = self.config.WORKER_BLOCK_TIME
        self.timeout = self.config.WORKER_TIMEOUT

        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        # Setup logging
        self.setup_logging()

        logger.info(f"Worker initialized: {self.consumer_name}")

    def setup_logging(self):
        """Setup worker-specific logging"""
        log_formatter = logging.Formatter(
            f"%(asctime)s - {self.worker_name} - %(levelname)s - %(message)s"
        )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_formatter)
        console_handler.setLevel(logging.INFO)

        # File handler if logs directory exists
        if self.config.LOGS_FOLDER.exists():
            log_file = self.config.LOGS_FOLDER / f"{self.worker_name}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(log_formatter)
            file_handler.setLevel(logging.INFO)

            # Add handlers to logger
            logger.addHandler(file_handler)

        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    @abstractmethod
    def process_message(self, message_data: dict) -> bool:
        """Process a single message. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def check_dependencies(self) -> bool:
        """Check if worker dependencies are available. Must be implemented by subclasses."""
        pass

    def update_session_status(self, session_id: str, updates: dict):
        """Update session status with worker info"""
        try:
            updates.update(
                {"worker": self.consumer_name, "last_update": datetime.utcnow().isoformat()}
            )
            self.redis_client.update_session_status(session_id, updates)
        except Exception as e:
            logger.error(f"❌ Error updating session status: {e}")

    def handle_message_error(self, session_id: str, error: Exception):
        """Handle message processing errors"""
        error_msg = str(error)
        logger.error(f"Error processing session {session_id}: {error_msg}")

        try:
            self.update_session_status(
                session_id,
                {
                    "status": "error",
                    "error": error_msg,
                    "error_timestamp": datetime.utcnow().isoformat(),
                },
            )
        except Exception as e:
            logger.error(f"❌ Error updating error status: {e}")

    def cleanup_consumer_group(self):
        """FIXED: Clean up pending messages in consumer group"""
        try:
            logger.info(f"🧹 Cleaning up consumer group {self.consumer_group}")
            
            # Get pending messages
            pending = self.redis_client.client.xpending_range(
                self.stream_name, self.consumer_group, "-", "+", 100
            )
            
            if pending:
                logger.info(f"🧹 Found {len(pending)} pending messages, cleaning up...")
                
                # Claim and acknowledge pending messages
                for msg in pending:
                    message_id = msg["message_id"]
                    try:
                        # FIXED: Use message_ids (list) instead of message_id
                        claimed = self.redis_client.client.xclaim(
                            self.stream_name,
                            self.consumer_group,
                            self.consumer_name,
                            min_idle_time=0,
                            message_ids=[message_id]  # FIXED: List instead of single ID
                        )
                        
                        if claimed:
                            # Acknowledge it
                            self.redis_client.acknowledge_message(
                                self.stream_name, self.consumer_group, message_id
                            )
                            logger.debug(f"🧹 Cleaned up pending message: {message_id}")
                            
                    except Exception as e:
                        logger.warning(f"⚠️ Could not clean up message {message_id}: {e}")
                        # Still try to acknowledge it to prevent blocking
                        try:
                            self.redis_client.acknowledge_message(
                                self.stream_name, self.consumer_group, message_id
                            )
                        except:
                            pass
                        
                logger.info(f"✅ Consumer group cleanup completed")
            else:
                logger.info(f"✅ No pending messages to clean up")
                
        except Exception as e:
            logger.warning(f"⚠️ Error during consumer group cleanup: {e}")

    def recover_stuck_messages(self):
        """Claim and process messages stuck for >5 minutes"""
        try:
            logger.info(f"🔄 Checking for stuck messages in {self.stream_name}...")
            
            stuck_messages = self.redis_client.claim_old_messages(
                self.stream_name,
                self.consumer_group,
                self.consumer_name,
                min_idle_time=300000  # 5 minutes
            )
            
            if not stuck_messages:
                logger.info("✅ No stuck messages found")
                return
            
            logger.info(f"🔄 Found {len(stuck_messages)} stuck messages, processing...")
            
            for message_id, fields in stuck_messages:
                try:
                    retry_count = self.redis_client.get_retry_count(fields)
                    
                    if retry_count >= 3:
                        # Max retries exceeded - send to DLQ
                        logger.warning(f"💀 Max retries for {message_id}, moving to DLQ")
                        self.send_to_dead_letter_queue(message_id, fields, "Max retries exceeded")
                        self.redis_client.acknowledge_message(
                            self.stream_name, self.consumer_group, message_id
                        )
                    else:
                        # Increment retry and process
                        fields = self.redis_client.increment_retry_count(fields)
                        logger.info(f"🔄 Retry {retry_count + 1}/3 for {message_id}")
                        
                        success = self.process_message(fields)
                        
                        if success:
                            self.redis_client.acknowledge_message(
                                self.stream_name, self.consumer_group, message_id
                            )
                            logger.info(f"✅ Recovered message {message_id}")
                        else:
                            logger.warning(f"⚠️ Recovery failed for {message_id}, will retry later")
                            
                except Exception as e:
                    logger.error(f"❌ Error recovering {message_id}: {e}")
                    
        except Exception as e:
            logger.warning(f"⚠️ Recovery process error: {e}")

    def send_to_dead_letter_queue(self, message_id, message_data, error):
        """Move failed messages to DLQ"""
        try:
            dlq_stream = f"{self.stream_name}_dlq"
            
            dlq_data = {
                "original_message_id": message_id,
                "original_stream": self.stream_name,
                "error": str(error),
                "failed_at": datetime.utcnow().isoformat(),
                "retry_count": message_data.get("retry_count", "0"),
            }
            
            # Add original data
            for key, value in message_data.items():
                dlq_data[f"original_{key}"] = value
            
            self.redis_client.add_to_stream(dlq_stream, dlq_data)
            logger.info(f"💀 Moved to DLQ: {message_id} -> {dlq_stream}")
            
        except Exception as e:
            logger.error(f"❌ DLQ error: {e}")

    def ensure_consumer_group_exists(self):
        """Ensure consumer group exists and is properly configured"""
        try:
            # Create consumer group if it doesn't exist
            self.redis_client.client.xgroup_create(
                self.stream_name, self.consumer_group, id="0", mkstream=True
            )
            logger.info(f"✅ Consumer group {self.consumer_group} ready")
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.info(f"✅ Consumer group {self.consumer_group} already exists")
            else:
                logger.error(f"❌ Error with consumer group: {e}")
                raise

    def recover_pending_messages(self):
        """Recover and reprocess pending messages older than 5 minutes"""
        try:
            # Get pending messages older than 5 minutes
            pending = self.redis_client.client.xpending_range(
                self.stream_name, self.consumer_group, "-", "+", 100
            )
            
            recovered = 0
            for msg in pending:
                message_id = msg["message_id"]
                idle_time = msg["time_since_delivered"]
                
                # If message is pending for more than 5 minutes, claim it
                if idle_time > 300000:  # 5 minutes in milliseconds
                    try:
                        claimed = self.redis_client.client.xclaim(
                            self.stream_name, self.consumer_group, self.consumer_name,
                            min_idle_time=300000, message_ids=[message_id]
                        )
                        
                        if claimed:
                            # Just acknowledge old stuck messages to clear the queue
                            self.redis_client.acknowledge_message(
                                self.stream_name, self.consumer_group, message_id
                            )
                            recovered += 1
                            logger.info(f"🔄 Recovered stuck message: {message_id}")
                            
                    except Exception as e:
                        logger.warning(f"⚠️ Could not recover message {message_id}: {e}")
            
            if recovered > 0:
                logger.info(f"🔄 Recovered {recovered} stuck messages from queue")
                
        except Exception as e:
            logger.warning(f"⚠️ Error during message recovery: {e}")

    def run(self):
        """FIXED: Enhanced run with recovery and proper acknowledgment"""
        logger.info(f"🚀 Starting {self.worker_name}...")

        if not self.check_dependencies():
            logger.error("❌ Dependency check failed")
            return 1

        self.ensure_consumer_group_exists()
        
        # Recover stuck messages on startup
        self.recover_stuck_messages()

        consecutive_errors = 0
        max_consecutive_errors = 5
        heartbeat_interval = 30
        last_heartbeat = time.time()

        logger.info(f"✅ {self.worker_name} ready")

        while self.running:
            try:
                current_time = time.time()
                if current_time - last_heartbeat >= heartbeat_interval:
                    logger.info(f"💓 Heartbeat - waiting for messages...")
                    last_heartbeat = current_time

                messages = self.redis_client.read_stream(
                    self.stream_name,
                    self.consumer_group,
                    self.consumer_name,
                    count=1,
                    block=self.block_time,
                )

                if not messages:
                    consecutive_errors = 0
                    continue

                for stream, stream_messages in messages:
                    for message_id, fields in stream_messages:
                        logger.info(f"📨 Processing {message_id}")

                        try:
                            # Check retry count
                            retry_count = self.redis_client.get_retry_count(fields)
                            
                            if retry_count >= 3:
                                logger.warning(f"💀 Max retries for {message_id}")
                                session_id = fields.get("session_id")
                                self.send_to_dead_letter_queue(
                                    message_id, fields, "Max retries exceeded"
                                )
                                self.redis_client.acknowledge_message(
                                    self.stream_name, self.consumer_group, message_id
                                )
                                continue
                            
                            # Increment retry count
                            if retry_count > 0:
                                fields = self.redis_client.increment_retry_count(fields)
                                logger.info(f"🔄 Retry {retry_count + 1}/3")
                            
                            # Process message
                            success = self.process_message(fields)

                            if success:
                                # Only acknowledge on success
                                self.redis_client.acknowledge_message(
                                    self.stream_name, self.consumer_group, message_id
                                )
                                logger.info(f"✅ Completed {message_id}")
                                consecutive_errors = 0
                            else:
                                # Don't acknowledge - let it retry
                                logger.error(f"❌ Failed {message_id}, will retry")

                        except Exception as e:
                            logger.error(f"❌ Processing error: {e}")
                            
                            session_id = fields.get("session_id")
                            if session_id:
                                try:
                                    self.handle_message_error(session_id, e)
                                except:
                                    pass
                            
                            # Don't acknowledge - let it retry
                            consecutive_errors += 1

            except KeyboardInterrupt:
                logger.info("📨 Keyboard interrupt")
                break
            except Exception as e:
                logger.error(f"❌ Loop error: {e}")
                consecutive_errors += 1
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"❌ Too many errors ({consecutive_errors}), exiting")
                    break
                    
                sleep_time = min(5 * consecutive_errors, 30)
                logger.info(f"⏳ Sleeping {sleep_time}s...")
                time.sleep(sleep_time)

        logger.info(f"🛑 {self.worker_name} stopped")
        return 0

    def get_worker_stats(self):
        """Get worker statistics"""
        return {
            "worker_name": self.worker_name,
            "consumer_name": self.consumer_name,
            "stream_name": self.stream_name,
            "consumer_group": self.consumer_group,
            "running": self.running,
            "pid": os.getpid(),
        }