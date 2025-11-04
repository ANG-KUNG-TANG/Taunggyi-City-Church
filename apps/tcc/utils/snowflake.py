import time
import threading
import logging
from django.conf import settings
from django.core.cache import cache
from asgiref.local import Local

logger = logging.getLogger(__name__)

class SnowflakeException(Exception):
    """Custom exception for Snowflake generator errors"""
    pass

class ClockDriftException(SnowflakeException):
    """Raised when clock moves backwards"""
    pass

class DjangoSnowflakeGenerator:
    """
    Distributed ID generation optimized for Django.
    
    ID Structure (64 bits):
    - Timestamp: 41 bits (milliseconds since custom epoch)
    - Datacenter ID: 5 bits (0-31)
    - Machine ID: 5 bits (0-31)  
    - Sequence: 12 bits (0-4095)
    """
    
    # Bit allocations
    TIMESTAMP_BITS = 41
    DATACENTER_BITS = 5
    MACHINE_BITS = 5
    SEQUENCE_BITS = 12
    
    # Maximum values
    MAX_DATACENTER_ID = (1 << DATACENTER_BITS) - 1  # 31
    MAX_MACHINE_ID = (1 << MACHINE_BITS) - 1        # 31
    MAX_SEQUENCE = (1 << SEQUENCE_BITS) - 1         # 4095
    
    # Bit shifts
    TIMESTAMP_SHIFT = SEQUENCE_BITS + MACHINE_BITS + DATACENTER_BITS
    DATACENTER_SHIFT = SEQUENCE_BITS + MACHINE_BITS
    MACHINE_SHIFT = SEQUENCE_BITS
    
    def __init__(self):
        """Initialize with Django settings"""
        self.datacenter_id = getattr(settings, 'SNOWFLAKE_DATACENTER_ID', 1)
        self.machine_id = getattr(settings, 'SNOWFLAKE_MACHINE_ID', 1)
        self.epoch = getattr(settings, 'SNOWFLAKE_EPOCH', 1672531200000)  # Jan 1, 2023
        
        # Validate IDs
        if not (0 <= self.datacenter_id <= self.MAX_DATACENTER_ID):
            raise ValueError(f"Datacenter ID must be between 0 and {self.MAX_DATACENTER_ID}")
        if not (0 <= self.machine_id <= self.MAX_MACHINE_ID):
            raise ValueError(f"Machine ID must be between 0 and {self.MAX_MACHINE_ID}")
        
        # Thread-local storage for sequence and last_timestamp
        self._local = Local()
        self._lock = threading.RLock()
        
        # Cache key for distributed environments
        self._cache_key = f"snowflake_{self.datacenter_id}_{self.machine_id}_sequence"
        
        logger.info(
            f"DjangoSnowflake initialized: "
            f"datacenter_id={self.datacenter_id}, "
            f"machine_id={self.machine_id}, "
            f"epoch={self.epoch}"
        )
    
    def _init_local(self):
        """Initialize thread-local variables"""
        if not hasattr(self._local, 'sequence'):
            self._local.sequence = 0
        if not hasattr(self._local, 'last_timestamp'):
            self._local.last_timestamp = -1
    
    def _current_timestamp(self) -> int:
        """Get current timestamp in milliseconds since epoch."""
        return int(time.time() * 1000) - self.epoch
    
    def _wait_for_next_millis(self, last_timestamp: int) -> int:
        """
        Wait until next millisecond when sequence is exhausted.
        """
        timestamp = self._current_timestamp()
        wait_count = 0
        max_wait_ms = 100  # Maximum wait time in milliseconds
        
        while timestamp <= last_timestamp and wait_count < max_wait_ms:
            time.sleep(0.001)  # Sleep for 1 millisecond
            timestamp = self._current_timestamp()
            wait_count += 1
        
        if timestamp <= last_timestamp:
            raise ClockDriftException(
                f"Unable to generate ID after waiting {max_wait_ms}ms"
            )
        
        return timestamp
    
    def _get_distributed_sequence(self, timestamp: int) -> int:
        """
        Get sequence number for distributed environments using Redis cache.
        This ensures sequence uniqueness across multiple application instances.
        """
        cache_key = f"{self._cache_key}_{timestamp}"
        
        # Use Redis atomic increment
        try:
            sequence = cache.incr(cache_key)
            if sequence > self.MAX_SEQUENCE:
                # Reset sequence for this timestamp and try again
                cache.delete(cache_key)
                sequence = cache.incr(cache_key)
            
            # Set expiration (1 second) to clean up old keys
            cache.expire(cache_key, 1)
            return sequence
            
        except Exception as e:
            logger.warning(f"Redis sequence failed, falling back to local: {e}")
            # Fallback to local sequence
            self._local.sequence = (self._local.sequence + 1) & self.MAX_SEQUENCE
            return self._local.sequence
    
    def generate_id(self) -> int:
        """
        Generate a new Snowflake ID.
        
        Returns:
            64-bit Snowflake ID
        """
        self._init_local()
        
        with self._lock:
            timestamp = self._current_timestamp()
            
            # Check for clock drift
            if timestamp < self._local.last_timestamp:
                drift_ms = self._local.last_timestamp - timestamp
                logger.error(f"Clock drift detected: {drift_ms}ms")
                raise ClockDriftException(f"Clock moved backwards by {drift_ms}ms")
            
            # Handle same timestamp
            if timestamp == self._local.last_timestamp:
                # Try distributed sequence first, then fallback to local
                if cache:
                    sequence = self._get_distributed_sequence(timestamp)
                else:
                    self._local.sequence = (self._local.sequence + 1) & self.MAX_SEQUENCE
                    sequence = self._local.sequence
                    
                if sequence == 0:
                    # Sequence exhausted, wait for next millisecond
                    timestamp = self._wait_for_next_millis(self._local.last_timestamp)
                    # Reset sequence for new timestamp
                    if cache:
                        sequence = self._get_distributed_sequence(timestamp)
                    else:
                        self._local.sequence = 0
                        sequence = 0
            else:
                # New timestamp, reset sequence
                if cache:
                    # Let distributed sequence start from 1 automatically
                    sequence = self._get_distributed_sequence(timestamp)
                else:
                    self._local.sequence = 0
                    sequence = 0
            
            self._local.last_timestamp = timestamp
            
            # Generate ID
            snowflake_id = (
                (timestamp << self.TIMESTAMP_SHIFT) |
                (self.datacenter_id << self.DATACENTER_SHIFT) |
                (self.machine_id << self.MACHINE_SHIFT) |
                sequence
            )
            
            return snowflake_id
    
    def batch_generate_ids(self, count: int) -> list:
        """
        Generate multiple IDs in a batch.
        
        Args:
            count: Number of IDs to generate (1-1000)
        """
        if not 1 <= count <= 1000:
            raise ValueError("Count must be between 1 and 1000")
        
        return [self.generate_id() for _ in range(count)]
    
    def decompose_id(self, snowflake_id: int) -> dict:
        """
        Decompose a Snowflake ID into its components.
        """
        timestamp = (snowflake_id >> self.TIMESTAMP_SHIFT)
        datacenter_id = (
            (snowflake_id >> self.DATACENTER_SHIFT) & 
            self.MAX_DATACENTER_ID
        )
        machine_id = (
            (snowflake_id >> self.MACHINE_SHIFT) & 
            self.MAX_MACHINE_ID
        )
        sequence = snowflake_id & self.MAX_SEQUENCE
        
        return {
            'timestamp': timestamp,
            'datetime': time.strftime('%Y-%m-%d %H:%M:%S', 
                                   time.gmtime((timestamp + self.epoch) / 1000)),
            'datacenter_id': datacenter_id,
            'machine_id': machine_id,
            'sequence': sequence,
            'snowflake_id': snowflake_id
        }


# Global instance
_snowflake_instance = None

def get_snowflake_generator():
    """Get or create singleton Snowflake generator instance"""
    global _snowflake_instance
    if _snowflake_instance is None:
        _snowflake_instance = DjangoSnowflakeGenerator()
    return _snowflake_instance

def generate_snowflake_id():
    """Generate a single Snowflake ID"""
    return get_snowflake_generator().generate_id()

def batch_generate_snowflake_ids(count: int):
    """Generate multiple Snowflake IDs"""
    return get_snowflake_generator().batch_generate_ids(count)

def decompose_snowflake_id(snowflake_id: int):
    """Decompose a Snowflake ID into its components"""
    return get_snowflake_generator().decompose_id(snowflake_id)