"""API tests for finance endpoints."""

from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.finance.models import FinancialCategory, FinancialAuthorization


class FinanceAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pastor = User.objects.create_user(
            email="finance-api-pastor@example.com",
            password="test-password",
        )
        cls.administrator = User.objects.create_user(
            email="finance-api-admin@example.com",
            password="test-password",
        )
        cls.zone_leader = User.objects.create_user(
            email="finance-api-zone@example.com",
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

        cls.donation_category = FinancialCategory.objects.create(
            code="API_DONATION",
            name="API Test Donations",
            scope=FinancialCategory.Scope.DONATION,
            created_by=cls.pastor,
        )

        cls.fund_category = FinancialCategory.objects.create(
            code="API_FUND",
            name="API Test Fund",
            scope=FinancialCategory.Scope.FUND,
            created_by=cls.pastor,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.pastor)

    def donation_payload(self, **overrides):
        payload = {
            "transaction_date": "2026-11-11",
            "amount": "100.00",
            "currency_code": "MMK",
            "category_id": str(self.donation_category.id),
            "payment_method": "CASH",
        }
        payload.update(overrides)
        return payload

    def fund_payload(self, **overrides):
        payload = {
            "transaction_date": "2026-11-11",
            "amount": "200.00",
            "currency_code": "MMK",
            "category_id": str(self.fund_category.id),
            "transaction_type": "INCOME",
        }
        payload.update(overrides)
        return payload

    def create_authorised_donation(self):
        response = self.client.post(
            reverse("donation-list-create"),
            self.donation_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        donation_id = response.data["id"]

        authorisation_response = self.client.post(
            reverse(
                "donation-authorise",
                kwargs={"target_id": donation_id},
            ),
            {"decision": FinancialAuthorization.Decision.AUTHORISE},
            format="json",
        )
        self.assertEqual(
            authorisation_response.status_code,
            status.HTTP_200_OK,
        )

        return donation_id

    def test_pastor_can_access_donation_list(self):
        response = self.client.get(reverse("donation-list-create"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_administrator_can_access_donation_list(self):
        self.client.force_authenticate(user=self.administrator)

        response = self.client.get(reverse("donation-list-create"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_zone_leader_cannot_access_finance_api(self):
        self.client.force_authenticate(user=self.zone_leader)

        response = self.client.get(reverse("donation-list-create"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_cannot_access_finance_api(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(reverse("donation-list-create"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_donation_returns_pending_record(self):
        response = self.client.post(
            reverse("donation-list-create"),
            self.donation_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "PENDING")
        self.assertEqual(response.data["amount"], Decimal("100.00"))

    def test_anonymous_donation_does_not_return_donor_identity(self):
        response = self.client.post(
            reverse("donation-list-create"),
            self.donation_payload(
                is_anonymous=True,
                donor_identity="Private Donor",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["is_anonymous"])
        self.assertIsNone(response.data["donor_identity"])

    def test_donation_rejects_invalid_currency(self):
        response = self.client.post(
            reverse("donation-list-create"),
            self.donation_payload(currency_code="mmk"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_donation_rejects_zero_amount(self):
        response = self.client.post(
            reverse("donation-list-create"),
            self.donation_payload(amount="0.00"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pending_donation_can_be_updated(self):
        create_response = self.client.post(
            reverse("donation-list-create"),
            self.donation_payload(),
            format="json",
        )
        donation_id = create_response.data["id"]

        response = self.client.patch(
            reverse(
                "donation-detail",
                kwargs={"donation_id": donation_id},
            ),
            {"amount": "150.00"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["amount"], Decimal("150.00"))

    def test_donation_can_be_authorised(self):
        create_response = self.client.post(
            reverse("donation-list-create"),
            self.donation_payload(),
            format="json",
        )
        donation_id = create_response.data["id"]

        response = self.client.post(
            reverse(
                "donation-authorise",
                kwargs={"target_id": donation_id},
            ),
            {"decision": FinancialAuthorization.Decision.AUTHORISE},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["decision"],
            FinancialAuthorization.Decision.AUTHORISE,
        )

    def test_rejection_requires_a_reason(self):
        create_response = self.client.post(
            reverse("donation-list-create"),
            self.donation_payload(),
            format="json",
        )
        donation_id = create_response.data["id"]

        response = self.client.post(
            reverse(
                "donation-authorise",
                kwargs={"target_id": donation_id},
            ),
            {"decision": FinancialAuthorization.Decision.REJECT},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_fund_transaction_returns_pending_record(self):
        response = self.client.post(
            reverse("fund-transaction-list-create"),
            self.fund_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "PENDING")
        self.assertEqual(response.data["transaction_type"], "INCOME")

    def test_create_adjustment_for_authorised_donation(self):
        donation_id = self.create_authorised_donation()

        response = self.client.post(
            reverse("financial-adjustment-list-create"),
            {
                "donation_id": donation_id,
                "adjustment_type": "CORRECTION",
                "amount_delta": "25.00",
                "reason": "Correction of the recorded donation amount.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "PENDING")
        self.assertEqual(response.data["amount_delta"], Decimal("25.00"))

    def test_adjustment_requires_exactly_one_target(self):
        response = self.client.post(
            reverse("financial-adjustment-list-create"),
            {
                "donation_id": "00000000-0000-0000-0000-000000000001",
                "fund_transaction_id": "00000000-0000-0000-0000-000000000002",
                "adjustment_type": "CORRECTION",
                "amount_delta": "25.00",
                "reason": "Invalid multiple targets.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_summary_report_rejects_invalid_date_range(self):
        response = self.client.get(
            reverse("financial-summary-report"),
            {
                "start_date": "2026-11-12",
                "end_date": "2026-11-11",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_summary_report_returns_confirmed_groups(self):
        response = self.client.get(
            reverse("financial-summary-report"),
            {
                "start_date": "2026-11-01",
                "end_date": "2026-11-30",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("confirmed", response.data)
        self.assertIn("donations", response.data["confirmed"])
        self.assertIn("fund_income", response.data["confirmed"])
        self.assertIn("fund_expenses", response.data["confirmed"])
