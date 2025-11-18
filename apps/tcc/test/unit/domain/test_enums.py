import pytest
from apps.tcc.models.base.enums import UserRole, DonationStatus, PrayerPrivacy

class TestEnums:
    def test_user_role_values(self):
        """Test UserRole enum values."""
        assert UserRole.SUPER_ADMIN == "super_admin"
        assert UserRole.STAFF == "staff"
        assert UserRole.MEMBER == "member"
    
    def test_donation_status_transitions(self):
        """Test valid donation status values."""
        valid_statuses = {status.value for status in DonationStatus}
        expected_statuses = {"pending", "completed", "failed", "refunded", "cancelled"}
        assert valid_statuses == expected_statuses
    
    def test_prayer_privacy_hierarchy(self):
        """Test prayer privacy levels are correctly defined."""
        privacy_levels = [status.value for status in PrayerPrivacy]
        assert "private" in privacy_levels
        assert "public" in privacy_levels