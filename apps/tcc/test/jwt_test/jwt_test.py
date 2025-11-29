# apps/core/jwt/tests.py
from django.test import TestCase
from . import get_jwt_backend

class JWTSystemTest(TestCase):
    async def test_jwt_creation_and_verification(self):
        """Test that JWT tokens can be created and verified"""
        jwt_backend = get_jwt_backend()
        
        # Create tokens
        tokens = await jwt_backend.create_tokens(
            user_id="test-user-123", 
            email="test@example.com",
            roles=["user"]
        )
        
        # Verify the access token
        is_valid, payload = await jwt_backend.verify_token(tokens['access_token'])
        
        self.assertTrue(is_valid)
        self.assertEqual(payload['sub'], "test-user-123")
        self.assertEqual(payload['email'], "test@example.com")
        print("✅ JWT System Test PASSED!")