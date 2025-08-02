import redis
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(
        self, host="localhost", port=6379, password=None, db=0, decode_responses=True
    ):
        """Initialize Redis client with optional password support"""
        self.host = host
        self.port = port
        self.password = password
        self.db = db

        try:
            # Redis Cloud connection - no SSL needed for this instance
            self.client = redis.Redis(
                host=host,
                port=port,
                password=password,
                db=db,
                decode_responses=decode_responses,
                socket_connect_timeout=10,
                socket_timeout=10,
                ssl=False,  # SSL not needed for this Redis Cloud instance
            )

            # Test connection
            self.client.ping()
            logger.info(f"Connected to Redis at {host}:{port}")

        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def ping(self) -> bool:
        """Test Redis connection"""
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    def add_to_stream(self, stream_name: str, data: Dict[str, Any]) -> str:
        """Add data to Redis stream"""
        try:
            # Convert complex data to JSON strings
            stream_data = {}
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    stream_data[key] = json.dumps(value)
                else:
                    stream_data[key] = str(value)

            # Add to stream
            stream_id = self.client.xadd(stream_name, stream_data)
            logger.info(f"Added to stream {stream_name}: {stream_id}")

            return stream_id

        except Exception as e:
            logger.error(f"Error adding to stream {stream_name}: {e}")
            raise

    def read_stream(
        self,
        stream_name: str,
        consumer_group: str,
        consumer_name: str,
        count: int = 1,
        block: int = 1000,
    ) -> list:
        """Read from Redis stream with consumer group"""
        try:
            # Create consumer group if it doesn't exist
            try:
                self.client.xgroup_create(
                    stream_name, consumer_group, id="0", mkstream=True
                )
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise

            # Read from stream
            messages = self.client.xreadgroup(
                consumer_group,
                consumer_name,
                {stream_name: ">"},
                count=count,
                block=block,
            )

            return messages

        except Exception as e:
            logger.error(f"Error reading from stream {stream_name}: {e}")
            raise

    def acknowledge_message(
        self, stream_name: str, consumer_group: str, message_id: str
    ):
        """Acknowledge processed message"""
        try:
            self.client.xack(stream_name, consumer_group, message_id)
            logger.debug(f"Acknowledged message {message_id} in {stream_name}")
        except Exception as e:
            logger.error(f"Error acknowledging message {message_id}: {e}")
            raise

    def set_session_status(
        self, session_id: str, status_data: Dict[str, Any], expire_seconds: int = 3600
    ):
        """Set session status data - FIXED"""
        try:
            key = f"session_status:{session_id}"
            
            # FIXED: Ensure all values are strings for Redis
            string_data = {}
            for k, v in status_data.items():
                if isinstance(v, (dict, list)):
                    string_data[k] = json.dumps(v)
                else:
                    string_data[k] = str(v)
            
            self.client.hset(key, mapping=string_data)
            self.client.expire(key, expire_seconds)
            logger.debug(f"Set status for session {session_id}")
        except Exception as e:
            logger.error(f"Error setting session status: {e}")
            raise

    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session status data - FIXED"""
        try:
            key = f"session_status:{session_id}"
            data = self.client.hgetall(key)

            if not data:
                return None

            # Convert back from Redis strings
            result = {}
            for k, v in data.items():
                try:
                    # FIXED: Handle different data types properly
                    if isinstance(v, str):
                        # Try to parse as JSON if it's a string
                        result[k] = json.loads(v)
                    elif isinstance(v, (list, dict)):
                        # Already parsed, use as-is
                        result[k] = v
                    else:
                        # Keep as original type
                        result[k] = v
                except (json.JSONDecodeError, TypeError):
                    # Keep as string if not JSON
                    result[k] = v

            return result

        except Exception as e:
            logger.error(f"Error getting session status: {e}")
            return None

    def update_session_status(self, session_id: str, updates: Dict[str, Any]):
        """Update specific fields in session status"""
        try:
            key = f"session_status:{session_id}"

            # Convert values to strings
            string_updates = {}
            for k, v in updates.items():
                if isinstance(v, (dict, list)):
                    string_updates[k] = json.dumps(v)
                else:
                    string_updates[k] = str(v)

            self.client.hset(key, mapping=string_updates)
            logger.debug(
                f"Updated status for session {session_id}: {list(updates.keys())}"
            )

        except Exception as e:
            logger.error(f"Error updating session status: {e}")
            raise

    def get_stream_info(self, stream_name: str) -> Dict[str, Any]:
        """Get information about a stream"""
        try:
            info = self.client.xinfo_stream(stream_name)
            return info
        except Exception as e:
            logger.error(f"Error getting stream info for {stream_name}: {e}")
            return {}

    def get_pending_messages(self, stream_name: str, consumer_group: str) -> list:
        """Get pending messages for a consumer group"""
        try:
            pending = self.client.xpending_range(
                stream_name, consumer_group, "-", "+", 10
            )
            return pending
        except Exception as e:
            logger.error(f"Error getting pending messages: {e}")
            return []
