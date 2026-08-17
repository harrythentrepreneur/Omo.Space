import pytest
from app.db.redis_service import RedisService

# Fixture for RedisService
@pytest.fixture
def redis_service():
    service = RedisService()
    if not service.check_connection():
        pytest.fail("Failed to connect to Redis")
    service.client.flushdb()  # Clean Redis before each test
    return service

# Test store_hash and get_hash
def test_store_and_get_hash(redis_service):
    hash_key = "test_hash"
    test_data = {"field1": "value1", "field2": "value2"}
    
    # Store the hash
    redis_service.store_hash(hash_key, test_data)
    
    # Retrieve the hash
    retrieved_data = redis_service.get_hash(hash_key)
    
    # Check if stored and retrieved data match
    assert retrieved_data == {"field1": "value1", "field2": "value2"}