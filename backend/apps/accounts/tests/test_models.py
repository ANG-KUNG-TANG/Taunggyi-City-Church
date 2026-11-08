import uuid

from apps.accounts.models.users import User


def test_user_string_representation():
    user = User(
        first_name="Test",
        last_name="User",
        email="test@example.com",
    )

    assert str(user) == "Test User"


def test_user_string_representation_falls_back_to_email():
    user = User(email="test@example.com")

    assert str(user) == "test@example.com"


def test_user_has_uuid_primary_key():
    user = User(email="test@example.com")

    assert isinstance(user.id, uuid.UUID)


def test_user_default_is_active():
    user = User(email="test@example.com")

    assert user.is_active is True


def test_user_names_are_optional():
    user = User(email="test@example.com")

    assert user.first_name == ""
    assert user.last_name == ""
