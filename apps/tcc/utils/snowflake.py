import time
import threading
import logging
from django.conf import settings
from django.core.cache import cache
from asgiref.local import Local

logger = logging.getLogger(__name__)

try:
    from django_redis import get_redis_connection
except Exception:
    get_redis_connection = None


class SnowflakeException(Exception):
    """Custom exception for Snowflake generator errors"""
    pass


class ClockDriftException(SnowflakeException):
    """Raised when the system clock moves backwards"""
    pass


class DjangoSnowflakeGenerator:
    """
    Distributed Snowflake ID generator for Django.

    64-bit ID structure:
    - 41 bits timestamp (ms since epoch)
    - 5 bits datacenter ID
    - 5 bits machine ID
    - 12 bits sequence
    """

    # bit allocation
    TIMESTAMP_BITS = 41
    DATACENTER_BITS = 5
    MACHINE_BITS = 5
    SEQUENCE_BITS = 12

    # max values
    MAX_DATACENTER_ID = (1 << DATACENTER_BITS) - 1
    MAX_MACHINE_ID = (1 << MACHINE_BITS) - 1
    MAX_SEQUENCE = (1 << SEQUENCE_BITS) - 1

    # bit shifts
    TIMESTAMP_SHIFT = SEQUENCE_BITS + MACHINE_BITS + DATACENTER_BITS
    DATACENTER_SHIFT = SEQUENCE_BITS + MACHINE_BITS
    MACHINE_SHIFT = SEQUENCE_BITS

    def __init__(self):
        """Initialize generator using Django settings."""
        self.datacenter_id = getattr(settings, "SNOWFLAKE_DATACENTER_ID", 1)
        self.machine_id = getattr(settings, "SNOWFLAKE_MACHINE_ID", 1)
        self.epoch = getattr(settings, "SNOWFLAKE_EPOCH", 1672531200000)  # Jan 1, 2023

        # validate IDs
        if not (0 <= self.datacenter_id <= self.MAX_DATACENTER_ID):
            raise ValueError(f"Datacenter ID must be between 0 and {self.MAX_DATACENTER_ID}")
        if not (0 <= self.machine_id <= self.MAX_MACHINE_ID):
            raise ValueError(f"Machine ID must be between 0 and {self.MAX_MACHINE_ID}")

        # thread-local variables
        self._local = Local()
        self._lock = threading.RLock()

        # corrected cache key prefix
        self._cache_key_prefix = f"snowflake_{self.datacenter_id}_{self.machine_id}_seq"

        logger.info(
            "DjangoSnowflake initialized datacenter=%s machine=%s epoch=%s",
            self.datacenter_id,
            self.machine_id,
            self.epoch,
        )

    def _init_local(self):
        """Prepare thread-local defaults."""
        if not hasattr(self._local, "sequence"):
            self._local.sequence = 0
        if not hasattr(self._local, "last_timestamp"):
            self._local.last_timestamp = -1

    def _current_timestamp(self) -> int:
        """Get current timestamp in ms relative to epoch."""
        return int(time.time() * 1000) - int(self.epoch)

    def _wait_for_next_millis(self, last_timestamp: int) -> int:
        """Wait for next millisecond when sequence is exhausted."""
        timestamp = self._current_timestamp()
        wait_count = 0
        max_wait_ms = 100

        while timestamp <= last_timestamp and wait_count < max_wait_ms:
            time.sleep(0.001)
            timestamp = self._current_timestamp()
            wait_count += 1

        if timestamp <= last_timestamp:
            raise ClockDriftException("Clock did not move forward after 100ms wait")

        return timestamp

    def _get_redis_client(self):
        """Return a direct Redis client if available."""
        if get_redis_connection:
            try:
                return get_redis_connection("default")
            except Exception as e:
                logger.warning("Could not get Redis connection: %s", e)
        return None

    def _get_distributed_sequence(self, timestamp: int) -> int:
        """
        Distributed sequence using Redis for uniqueness across instances.
        """
        # FIXED: use correct prefix
        cache_key = f"{self._cache_key_prefix}_{timestamp}"

        try:
            sequence = cache.incr(cache_key)

            if sequence > self.MAX_SEQUENCE:
                cache.delete(cache_key)
                sequence = cache.incr(cache_key)

            cache.expire(cache_key, 1)
            return sequence

        except Exception as e:
            logger.warning(f"Redis sequence failed, using local fallback: {e}")
            self._local.sequence = (self._local.sequence + 1) & self.MAX_SEQUENCE
            return self._local.sequence

    def generate_id(self) -> int:
        """Generate a new 64-bit Snowflake ID."""
        self._init_local()

        with self._lock:
            timestamp = self._current_timestamp()

            # clock moved backwards
            if timestamp < self._local.last_timestamp:
                drift_ms = self._local.last_timestamp - timestamp
                logger.error(f"Clock drift: {drift_ms}ms")
                raise ClockDriftException(
                    f"Clock moved backwards by {drift_ms}ms"
                )

            # same millisecond
            if timestamp == self._local.last_timestamp:
                sequence = self._get_distributed_sequence(timestamp)

                if sequence == 0:
                    timestamp = self._wait_for_next_millis(self._local.last_timestamp)
                    sequence = self._get_distributed_sequence(timestamp)

            else:
                sequence = self._get_distributed_sequence(timestamp)

            self._local.last_timestamp = timestamp

            snowflake_id = (
                (timestamp << self.TIMESTAMP_SHIFT)
                | (self.datacenter_id << self.DATACENTER_SHIFT)
                | (self.machine_id << self.MACHINE_SHIFT)
                | sequence
            )

            return snowflake_id

    def batch_generate_ids(self, count: int) -> list:
        """Generate multiple IDs in a batch."""
        if not 1 <= count <= 1000:
            raise ValueError("Count must be between 1 and 1000")

        return [self.generate_id() for _ in range(count)]

    def decompose_id(self, snowflake_id: int) -> dict:
        """Break a Snowflake ID into readable parts."""
        timestamp = (snowflake_id >> self.TIMESTAMP_SHIFT)
        datacenter_id = (
            (snowflake_id >> self.DATACENTER_SHIFT) & self.MAX_DATACENTER_ID
        )
        machine_id = (
            (snowflake_id >> self.MACHINE_SHIFT) & self.MAX_MACHINE_ID
        )
        sequence = snowflake_id & self.MAX_SEQUENCE

        return {
            "timestamp": timestamp,
            "datetime": time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.gmtime((timestamp + self.epoch) / 1000),
            ),
            "datacenter_id": datacenter_id,
            "machine_id": machine_id,
            "sequence": sequence,
            "snowflake_id": snowflake_id,
        }


# ------------ Singleton Functions ------------ #

_snowflake_instance = None


def get_snowflake_generator():
    """Get or create singleton handler."""
    global _snowflake_instance
    if _snowflake_instance is None:
        _snowflake_instance = DjangoSnowflakeGenerator()
    return _snowflake_instance


def generate_snowflake_id():
    return get_snowflake_generator().generate_id()


def batch_generate_snowflake_ids(count: int):
    return get_snowflake_generator().batch_generate_ids(count)


def decompose_snowflake_id(snowflake_id: int):
    return get_snowflake_generator().decompose_id(snowflake_id)
