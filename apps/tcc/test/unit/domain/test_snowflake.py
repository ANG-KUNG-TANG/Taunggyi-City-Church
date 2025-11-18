import time
import pytest
from apps.tcc.utils.snowflake import SnowflakeGenerator, ClockDriftException

class TestSnowflakeGenerator:
    def test_snowflake_initialization(self):
        """Test Snowflake generator initialization with valid parameters."""
        generator = SnowflakeGenerator(datacenter_id=1, machine_id=1)
        assert generator.datacenter_id == 1
        assert generator.machine_id == 1
    
    def test_invalid_datacenter_id(self):
        """Test initialization with invalid datacenter ID."""
        with pytest.raises(ValueError):
            SnowflakeGenerator(datacenter_id=32, machine_id=1)
    
    def test_invalid_machine_id(self):
        """Test initialization with invalid machine ID."""
        with pytest.raises(ValueError):
            SnowflakeGenerator(datacenter_id=1, machine_id=32)
    
    def test_generate_id(self):
        """Test ID generation."""
        generator = SnowflakeGenerator(datacenter_id=1, machine_id=1)
        id1 = generator.generate_id()
        id2 = generator.generate_id()
        
        assert id1 != id2  # IDs should be unique
        assert id1 > 0 and id2 > 0  # IDs should be positive
    
    def test_batch_generate_ids(self):
        """Test batch ID generation."""
        generator = SnowflakeGenerator(datacenter_id=1, machine_id=1)
        ids = generator.batch_generate_ids(10)
        
        assert len(ids) == 10
        assert len(set(ids)) == 10  # All IDs should be unique
    
    def test_decompose_id(self):
        """Test ID decomposition."""
        generator = SnowflakeGenerator(datacenter_id=1, machine_id=1)
        snowflake_id = generator.generate_id()
        
        components = generator.decompose_id(snowflake_id)
        
        assert 'timestamp' in components
        assert 'datacenter_id' in components
        assert 'machine_id' in components
        assert 'sequence' in components
        assert components['datacenter_id'] == 1
        assert components['machine_id'] == 1
