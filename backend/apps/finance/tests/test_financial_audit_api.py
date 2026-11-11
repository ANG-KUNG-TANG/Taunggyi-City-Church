"""API tests for financial audit history."""

import uuid
from datetime import date, timedelta

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.audit.models.audit_log import AuditLog


class FinancialAuditHistoryAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pastor = User.objects.create_user(
            email="audit-pastor@example.com",
            password="test-password",
        )
        cls.administrator = User.objects.create_user(
            email="audit-admin@example.com",
            password="test-password",
        )
        cls.zone_leader = User.objects.create_user(
            email="audit-zone@example.com",
            password="test-password",
        )

        for user, role_code in (
            (cls.pastor, "PASTOR"),
            (cls.administrator, "ADMINISTRATOR"),
            (cls.zone_leader, "ZONE_LEADER"),
        ):
            UserRole.objects.create(
                user=user,
                role=Role.objects.get(code=role_code),
            )

        cls.donation_id = uuid.uuid4()
        cls.fund_transaction_id = uuid.uuid4()
        cls.adjustment_id = uuid.uuid4()
        cls.correlation_id = uuid.uuid4()

        cls.donation_event = AuditLog.objects.create(
            actor=cls.pastor,
            entity_type="Donation",
            entity_id=cls.donation_id,
            action=AuditLog.Action.CREATE,
            after_data={"amount": "100.00"},
            correlation_id=cls.correlation_id,
        )

        AuditLog.objects.create(
            actor=cls.administrator,
            entity_type="FundTransaction",
            entity_id=cls.fund_transaction_id,
            action=AuditLog.Action.UPDATE,
            before_data={"amount": "100.00"},
            after_data={"amount": "150.00"},
        )

        AuditLog.objects.create(
            actor=cls.pastor,
            entity_type="FinancialAdjustment",
            entity_id=cls.adjustment_id,
            action=AuditLog.Action.CREATE,
        )

        AuditLog.objects.create(
            actor=cls.administrator,
            entity_type="Member",
            entity_id=uuid.uuid4(),
            action=AuditLog.Action.UPDATE,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.pastor)
        self.url = reverse("financial-audit-history")

    def test_pastor_can_view_financial_audit_history(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_administrator_can_view_financial_audit_history(self):
        self.client.force_authenticate(user=self.administrator)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_zone_leader_cannot_view_financial_audit_history(self):
        self.client.force_authenticate(user=self.zone_leader)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_unauthenticated_user_cannot_view_financial_audit_history(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_only_financial_entity_types_are_returned(self):
        response = self.client.get(self.url)

        entity_types = {event["entity_type"] for event in response.data}

        self.assertEqual(
            entity_types,
            {
                "Donation",
                "FundTransaction",
                "FinancialAdjustment",
            },
        )
        self.assertNotIn("Member", entity_types)

    def test_filter_by_entity_type(self):
        response = self.client.get(
            self.url,
            {"entity_type": "Donation"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["entity_type"], "Donation")

    def test_filter_by_entity_id(self):
        response = self.client.get(
            self.url,
            {"entity_id": str(self.donation_id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["entity_id"],
            str(self.donation_id),
        )

    def test_filter_by_actor(self):
        response = self.client.get(
            self.url,
            {"actor_id": str(self.pastor.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_filter_by_action(self):
        response = self.client.get(
            self.url,
            {"action": AuditLog.Action.UPDATE},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["action"],
            AuditLog.Action.UPDATE,
        )

    def test_filter_by_correlation_id(self):
        response = self.client.get(
            self.url,
            {"correlation_id": str(self.correlation_id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["correlation_id"],
            str(self.correlation_id),
        )

    def test_invalid_entity_type_is_rejected(self):
        response = self.client.get(
            self.url,
            {"entity_type": "Member"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_invalid_uuid_is_rejected(self):
        response = self.client.get(
            self.url,
            {"entity_id": "not-a-uuid"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_start_date_after_end_date_is_rejected(self):
        response = self.client.get(
            self.url,
            {
                "start_date": date.today().isoformat(),
                "end_date": (date.today() - timedelta(days=1)).isoformat(),
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_post_is_not_allowed(self):
        response = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_response_contains_audit_details(self):
        response = self.client.get(
            self.url,
            {"entity_id": str(self.donation_id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        event = response.data[0]

        self.assertEqual(
            event["id"],
            str(self.donation_event.id),
        )
        self.assertEqual(
            event["actor_email"],
            self.pastor.email,
        )
        self.assertEqual(
            event["action"],
            AuditLog.Action.CREATE,
        )
        self.assertEqual(
            event["after_data"],
            {"amount": "100.00"},
        )
