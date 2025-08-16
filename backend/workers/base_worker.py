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
                        # Claim the message
                        claimed = self.redis_client.client.xclaim(
                            self.stream_name,
                            self.consumer_group,
                            self.consumer_name,
                            min_idle_time=0,
                            message_id=message_id
                        )
                        
                        if claimed:
                            # Acknowledge it
                            self.redis_client.acknowledge_message(
                                self.stream_name, self.consumer_group, message_id
                            )
                            logger.debug(f"🧹 Cleaned up pending message: {message_id}")
                            
                    except Exception as e:
                        logger.warning(f"⚠️ Could not clean up message {message_id}: {e}")
                        
                logger.info(f"✅ Consumer group cleanup completed")
            else:
                logger.info(f"✅ No pending messages to clean up")
                
        except Exception as e:
            logger.warning(f"⚠️ Error during consumer group cleanup: {e}")

    def run(self):
        """Main worker loop with enhanced error handling"""
        logger.info(f"Starting {self.worker_name}...")

        # Check dependencies
        if not self.check_dependencies():
            logger.error("Dependency check failed. Exiting.")
            return 1

        # Clean up any pending messages from previous runs
        self.cleanup_consumer_group()

        # Main processing loop
        consecutive_errors = 0
        max_consecutive_errors = 5

        while self.running:
            try:
                # Read messages from Redis stream
                messages = self.redis_client.read_stream(
                    self.stream_name,
                    self.consumer_group,
                    self.consumer_name,
                    count=1,
                    block=self.block_time,
                )

                if not messages:
                    consecutive_errors = 0  # Reset error counter on successful read
                    continue

                # Process each message
                for stream, stream_messages in messages:
                    for message_id, fields in stream_messages:
                        logger.info(f"📨 Processing message {message_id}")

                        try:
                            # Process the message
                            success = self.process_message(fields)

                            # FIXED: Always acknowledge the message to prevent blocking
                            self.redis_client.acknowledge_message(
                                self.stream_name, self.consumer_group, message_id
                            )
                            
                            if success:
                                logger.info(f"✅ Message {message_id} processed successfully")
                                consecutive_errors = 0  # Reset error counter
                            else:
                                logger.error(f"❌ Message {message_id} failed but acknowledged")

                        except Exception as e:
                            logger.error(f"❌ Error processing message {message_id}: {e}")

                            # Try to update session status if we have session_id
                            session_id = fields.get("session_id")
                            if session_id:
                                self.handle_message_error(session_id, e)

                            # FIXED: Still acknowledge the message to prevent queue blocking
                            try:
                                self.redis_client.acknowledge_message(
                                    self.stream_name, self.consumer_group, message_id
                                )
                                logger.info(f"❌ Failed message {message_id} acknowledged to prevent blocking")
                            except Exception as ack_error:
                                logger.error(f"❌ Failed to acknowledge message {message_id}: {ack_error}")

                            consecutive_errors += 1

            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
                break
            except Exception as e:
                logger.error(f"❌ Error in worker loop: {e}")
                consecutive_errors += 1
                
                # If we have too many consecutive errors, exit
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"❌ Too many consecutive errors ({consecutive_errors}), exiting")
                    break
                    
                time.sleep(min(5 * consecutive_errors, 30))  # Exponential backoff with max

        logger.info(f"{self.worker_name} stopped")
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