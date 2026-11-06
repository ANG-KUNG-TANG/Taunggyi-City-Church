import pytest

from backend.apps.accounts.models.users import User


def test_create_user_requires_email():
    with pytest.raises(ValueError, match="The email must be set"):
        User.objects.create_user(
            email="",
            name="Test User",
        )


def test_create_user_requires_name():
    with pytest.raises(ValueError, match="The name must be set"):
        User.objects.create_user(
            email="test@example.com",
            name="",
        )


def test_create_superuser_requires_staff_status():
    with pytest.raises(ValueError, match="is_staff=True"):
        User.objects.create_superuser(
            email="admin@example.com",
            name="Admin User",
            password="test-password",
            is_staff=False,
        )


def test_create_superuser_requires_superuser_status():
    with pytest.raises(ValueError, match="is_superuser=True"):
        User.objects.create_superuser(
            email="admin@example.com",
            name="Admin User",
            password="test-password",
            is_superuser=False,
        )
