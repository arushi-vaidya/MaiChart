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
    """Base class for all workers"""

    def __init__(self, worker_name=None, config_name="default"):
        self.config = config[config_name]
        self.worker_name = worker_name or self.__class__.__name__
        self.consumer_name = f"{self.worker_name}_{os.getpid()}"
        self.running = True

        # Redis connection
        self.redis_client = RedisClient(
            host=self.config.REDIS_HOST,
            port=self.config.REDIS_PORT,
            password=self.config.REDIS_PASSWORD, 
            db=self.config.REDIS_DB,
        )

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
        updates.update(
            {"worker": self.consumer_name, "last_update": datetime.utcnow().isoformat()}
        )
        self.redis_client.update_session_status(session_id, updates)

    def handle_message_error(self, session_id: str, error: Exception):
        """Handle message processing errors"""
        error_msg = str(error)
        logger.error(f"Error processing session {session_id}: {error_msg}")

        self.update_session_status(
            session_id,
            {
                "status": "error",
                "error": error_msg,
                "error_timestamp": datetime.utcnow().isoformat(),
            },
        )

    def run(self):
        """Main worker loop"""
        logger.info(f"Starting {self.worker_name}...")

        # Check dependencies
        if not self.check_dependencies():
            logger.error("Dependency check failed. Exiting.")
            return 1

        # Main processing loop
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
                    continue

                # Process each message
                for stream, stream_messages in messages:
                    for message_id, fields in stream_messages:
                        logger.info(f"Processing message {message_id}")

                        try:
                            # Process the message
                            success = self.process_message(fields)

                            if success:
                                # Acknowledge the message
                                self.redis_client.acknowledge_message(
                                    self.stream_name, self.consumer_group, message_id
                                )
                                logger.info(
                                    f"Message {message_id} processed and acknowledged"
                                )
                            else:
                                logger.error(f"Failed to process message {message_id}")
                                # Message not acknowledged, will be retried

                        except Exception as e:
                            logger.error(f"Error processing message {message_id}: {e}")

                            # Try to update session status if we have session_id
                            session_id = fields.get("session_id")
                            if session_id:
                                self.handle_message_error(session_id, e)

            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
                break
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                time.sleep(5)  # Wait before retrying

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
