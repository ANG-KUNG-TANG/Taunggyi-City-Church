from backend.apps.accounts.models.users import User
from apps.tcc.models.base.enums import UserRole, UserStatus


def test_user_string_representation():
    user = User(
        name="Test User",
        email="test@example.com",
    )

    assert str(user) == "Test User (test@example.com)"


def test_user_age_is_none_when_date_of_birth_is_missing():
    user = User(
        name="Test User",
        email="test@example.com",
        date_of_birth=None,
    )

    assert user.age_in_years is None


def test_user_default_values():
    user = User(
        name="Test User",
        email="test@example.com",
    )

    assert user.role == UserRole.VISITOR
    assert user.status == UserStatus.PENDING
    assert user.is_active is True


def test_user_age_is_calculated_correctly():
    from datetime import date

    today = date.today()
    birth_date = date(today.year - 20, 1, 1)

    user = User(
        name="Test User",
        email="test@example.com",
        date_of_birth=birth_date,
    )

    assert user.age_in_years == 20
