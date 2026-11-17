from django.test import TestCase

from apps.accounts.models.users import User
from apps.accounts.serializers.user_serializers import (
    StaffCreateSerializer,
    StaffDetailSerializer,
    StaffListSerializer,
    StaffUpdateSerializer,
)


class StaffCreateSerializerTests(TestCase):
    def test_create_valid_staff_account(self):
        serializer = StaffCreateSerializer(
            data={
                "email": "staff@example.com",
                "first_name": "John",
                "last_name": "Smith",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

        user = serializer.save()

        self.assertEqual(user.email, "staff@example.com")
        self.assertEqual(user.first_name, "John")
        self.assertTrue(user.has_usable_password() is False)

    def test_create_account_without_password_has_unusable_password(self):
        serializer = StaffCreateSerializer(data={"email": "nopassword@example.com"})

        self.assertTrue(serializer.is_valid(), serializer.errors)

        user = serializer.save()

        self.assertFalse(user.has_usable_password())

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(
            email="existing@example.com",
            password="test-password",
        )

        serializer = StaffCreateSerializer(data={"email": "existing@example.com"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_case_insensitive_duplicate_email_is_rejected(self):
        User.objects.create_user(
            email="existing@example.com",
            password="test-password",
        )

        serializer = StaffCreateSerializer(data={"email": "EXISTING@example.com"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_password_and_privileged_fields_are_not_applied(self):
        serializer = StaffCreateSerializer(
            data={
                "email": "safe@example.com",
                "password": "attacker-password",
                "is_superuser": True,
                "is_staff": True,
                "role_assignments": ["ADMINISTRATOR"],
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

        self.assertNotIn("password", serializer.validated_data)
        self.assertNotIn("is_superuser", serializer.validated_data)
        self.assertNotIn("is_staff", serializer.validated_data)
        self.assertNotIn("role_assignments", serializer.validated_data)

        user = serializer.save()

        self.assertFalse(user.has_usable_password())


class StaffUpdateSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="staff@example.com",
            password="test-password",
            first_name="John",
            last_name="Smith",
        )

    def test_update_permitted_staff_fields(self):
        serializer = StaffUpdateSerializer(
            instance=self.user,
            data={
                "first_name": "James",
                "last_name": "Brown",
            },
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

        user = serializer.save()

        self.assertEqual(user.first_name, "James")
        self.assertEqual(user.last_name, "Brown")

    def test_update_with_another_accounts_email_is_rejected(self):
        User.objects.create_user(
            email="another@example.com",
            password="test-password",
        )

        serializer = StaffUpdateSerializer(
            instance=self.user,
            data={"email": "another@example.com"},
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_update_with_own_email_is_allowed(self):
        serializer = StaffUpdateSerializer(
            instance=self.user,
            data={"email": self.user.email},
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_privileged_fields_are_not_applied(self):
        serializer = StaffUpdateSerializer(
            instance=self.user,
            data={
                "is_superuser": True,
                "is_staff": True,
                "password": "attacker-password",
                "role_assignments": ["ADMINISTRATOR"],
            },
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

        for field in (
            "is_superuser",
            "is_staff",
            "password",
            "role_assignments",
        ):
            self.assertNotIn(field, serializer.validated_data)

        user = serializer.save()

        self.assertFalse(hasattr(user, "is_superuser"))
        self.assertFalse(hasattr(user, "is_staff"))
        self.assertTrue(user.has_usable_password())


class StaffReadSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="readonly@example.com",
            password="test-password",
            first_name="Jane",
            last_name="Doe",
        )

    def test_list_serializer_does_not_expose_sensitive_fields(self):
        serializer = StaffListSerializer(instance=self.user)

        self.assertNotIn("password", serializer.data)
        self.assertNotIn("role_assignments", serializer.data)
        self.assertNotIn("is_superuser", serializer.data)
        self.assertNotIn("is_staff", serializer.data)

    def test_detail_serializer_does_not_expose_sensitive_fields(self):
        serializer = StaffDetailSerializer(instance=self.user)

        self.assertNotIn("password", serializer.data)
        self.assertNotIn("role_assignments", serializer.data)
        self.assertNotIn("is_superuser", serializer.data)
        self.assertNotIn("is_staff", serializer.data)
