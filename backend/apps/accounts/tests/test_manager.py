import pytest

from apps.accounts.models.users import User


def test_create_user_requires_email():
    with pytest.raises(ValueError, match="The email must be set"):
        User.objects.create_user(email="")


def test_create_superuser_is_not_supported():
    with pytest.raises(
        NotImplementedError,
        match="Django superusers are not part",
    ):
        User.objects.create_superuser(
            email="admin@example.com",
            password="test-password",
        )


@pytest.mark.django_db
def test_create_user_sets_unusable_password_when_password_is_omitted():
    user = User.objects.create_user(
        email="test@example.com",
        first_name="Test",
        last_name="User",
    )

    assert user.has_usable_password() is False


@pytest.mark.django_db
def test_create_user_hashes_password():
    password = "test-password"

    user = User.objects.create_user(
        email="test@example.com",
        password=password,
    )

    assert user.has_usable_password() is True
    assert user.check_password(password) is True
    assert user.password != password
