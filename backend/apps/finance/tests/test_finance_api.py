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

    def test_create_adjustment_accepts_reason_with_exactly_500_characters(self):
        donation_id = self.create_authorised_donation()

        response = self.client.post(
            reverse("financial-adjustment-list-create"),
            {
                "donation_id": donation_id,
                "adjustment_type": "CORRECTION",
                "amount_delta": "25.00",
                "reason": "R" * 500,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["reason"]), 500)

    def test_create_adjustment_rejects_reason_with_more_than_500_characters(self):
        donation_id = self.create_authorised_donation()

        response = self.client.post(
            reverse("financial-adjustment-list-create"),
            {
                "donation_id": donation_id,
                "adjustment_type": "CORRECTION",
                "amount_delta": "25.00",
                "reason": "R" * 501,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_adjustment_rejects_blank_reason(self):
        donation_id = self.create_authorised_donation()

        response = self.client.post(
            reverse("financial-adjustment-list-create"),
            {
                "donation_id": donation_id,
                "adjustment_type": "CORRECTION",
                "amount_delta": "25.00",
                "reason": "   ",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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

    def create_fund_transaction_with_status(
        self,
        amount,
        target_status,
        transaction_type="INCOME",
    ):
        """Create a fund transaction and apply its requested decision."""
        response = self.client.post(
            reverse("fund-transaction-list-create"),
            self.fund_payload(
                amount=amount,
                transaction_type=transaction_type,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        transaction_id = response.data["id"]

        if target_status == "PENDING":
            return transaction_id

        decision = (
            FinancialAuthorization.Decision.AUTHORISE
            if target_status == "AUTHORISED"
            else FinancialAuthorization.Decision.REJECT
        )

        payload = {"decision": decision}

        if decision == FinancialAuthorization.Decision.REJECT:
            payload["reason"] = "Rejected for API reporting test."

        decision_response = self.client.post(
            reverse(
                "fund-transaction-authorise",
                kwargs={"target_id": transaction_id},
            ),
            payload,
            format="json",
        )
        self.assertEqual(
            decision_response.status_code,
            status.HTTP_200_OK,
        )

        return transaction_id

    def create_fund_adjustment(self, transaction_id, amount_delta, authorise):
        """Create an adjustment and optionally authorise it."""
        response = self.client.post(
            reverse("financial-adjustment-list-create"),
            {
                "fund_transaction_id": transaction_id,
                "adjustment_type": "CORRECTION",
                "amount_delta": amount_delta,
                "reason": "Daily fund reporting API test adjustment.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        adjustment_id = response.data["id"]

        if authorise:
            decision_response = self.client.post(
                reverse(
                    "financial-adjustment-authorise",
                    kwargs={"target_id": adjustment_id},
                ),
                {
                    "decision": FinancialAuthorization.Decision.AUTHORISE,
                },
                format="json",
            )
            self.assertEqual(
                decision_response.status_code,
                status.HTTP_200_OK,
            )

        return adjustment_id

    def test_daily_fund_report_requires_date(self):
        response = self.client.get(
            reverse("financial-daily-funds-report"),
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_daily_fund_report_rejects_invalid_date(self):
        response = self.client.get(
            reverse("financial-daily-funds-report"),
            {"date": "not-a-valid-date"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_daily_fund_report_separates_transaction_statuses(self):
        self.create_fund_transaction_with_status("200.00", "AUTHORISED")
        self.create_fund_transaction_with_status("50.00", "PENDING")
        self.create_fund_transaction_with_status("30.00", "REJECTED")

        response = self.client.get(
            reverse("financial-daily-funds-report"),
            {"date": "2026-11-11"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["date"], date(2026, 11, 11))
        self.assertEqual(len(response.data["results"]), 1)

        result = response.data["results"][0]

        self.assertEqual(result["transaction_type"], "INCOME")
        self.assertEqual(result["currency_code"], "MMK")
        self.assertEqual(result["authorised_total"], Decimal("200.00"))
        self.assertEqual(result["pending_total"], Decimal("50.00"))
        self.assertEqual(result["rejected_total"], Decimal("30.00"))
        self.assertEqual(
            result["authorised_adjustment_total"],
            Decimal("0.00"),
        )
        self.assertEqual(result["confirmed_total"], Decimal("200.00"))

    def test_daily_fund_report_includes_only_authorised_adjustments(self):
        transaction_id = self.create_fund_transaction_with_status(
            "200.00",
            "AUTHORISED",
        )

        self.create_fund_adjustment(
            transaction_id,
            "25.00",
            authorise=True,
        )
        self.create_fund_adjustment(
            transaction_id,
            "50.00",
            authorise=False,
        )

        response = self.client.get(
            reverse("financial-daily-funds-report"),
            {"date": "2026-11-11"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        result = response.data["results"][0]

        self.assertEqual(result["authorised_total"], Decimal("200.00"))
        self.assertEqual(
            result["authorised_adjustment_total"],
            Decimal("25.00"),
        )
        self.assertEqual(result["confirmed_total"], Decimal("225.00"))

    def create_donation_with_status(
        self,
        amount,
        target_status,
        currency_code="MMK",
    ):
        """Create a donation and apply its requested decision."""
        response = self.client.post(
            reverse("donation-list-create"),
            self.donation_payload(
                amount=amount,
                currency_code=currency_code,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        donation_id = response.data["id"]

        if target_status == "PENDING":
            return donation_id

        decision = (
            FinancialAuthorization.Decision.AUTHORISE
            if target_status == "AUTHORISED"
            else FinancialAuthorization.Decision.REJECT
        )

        payload = {"decision": decision}

        if decision == FinancialAuthorization.Decision.REJECT:
            payload["reason"] = "Rejected for monthly reporting test."

        decision_response = self.client.post(
            reverse(
                "donation-authorise",
                kwargs={"target_id": donation_id},
            ),
            payload,
            format="json",
        )
        self.assertEqual(
            decision_response.status_code,
            status.HTTP_200_OK,
        )

        return donation_id

    def create_donation_adjustment(
        self,
        donation_id,
        amount_delta,
        authorise,
    ):
        """Create a donation adjustment and optionally authorise it."""
        response = self.client.post(
            reverse("financial-adjustment-list-create"),
            {
                "donation_id": donation_id,
                "adjustment_type": "CORRECTION",
                "amount_delta": amount_delta,
                "reason": "Monthly donation reporting test adjustment.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        adjustment_id = response.data["id"]

        if authorise:
            decision_response = self.client.post(
                reverse(
                    "financial-adjustment-authorise",
                    kwargs={"target_id": adjustment_id},
                ),
                {
                    "decision": FinancialAuthorization.Decision.AUTHORISE,
                },
                format="json",
            )
            self.assertEqual(
                decision_response.status_code,
                status.HTTP_200_OK,
            )

        return adjustment_id

    def test_monthly_donation_report_separates_statuses(self):
        self.create_donation_with_status("100.00", "AUTHORISED")
        self.create_donation_with_status("50.00", "PENDING")
        self.create_donation_with_status("30.00", "REJECTED")

        response = self.client.get(
            reverse("financial-monthly-donations-report"),
            {"year": 2026, "month": 11},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["year"], 2026)
        self.assertEqual(response.data["month"], 11)
        self.assertEqual(len(response.data["results"]), 1)

        result = response.data["results"][0]

        self.assertEqual(result["currency_code"], "MMK")
        self.assertEqual(result["authorised_total"], Decimal("100.00"))
        self.assertEqual(result["pending_total"], Decimal("50.00"))
        self.assertEqual(result["rejected_total"], Decimal("30.00"))
        self.assertEqual(
            result["authorised_adjustment_total"],
            Decimal("0.00"),
        )
        self.assertEqual(result["confirmed_total"], Decimal("100.00"))

    def test_monthly_donation_report_includes_authorised_adjustments(self):
        donation_id = self.create_donation_with_status(
            "100.00",
            "AUTHORISED",
        )

        self.create_donation_adjustment(
            donation_id,
            "25.00",
            authorise=True,
        )
        self.create_donation_adjustment(
            donation_id,
            "50.00",
            authorise=False,
        )

        response = self.client.get(
            reverse("financial-monthly-donations-report"),
            {"year": 2026, "month": 11},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        result = response.data["results"][0]

        self.assertEqual(result["authorised_total"], Decimal("100.00"))
        self.assertEqual(
            result["authorised_adjustment_total"],
            Decimal("25.00"),
        )
        self.assertEqual(result["confirmed_total"], Decimal("125.00"))

    def test_monthly_donation_report_preserves_currency_separation(self):
        self.create_donation_with_status(
            "100.00",
            "AUTHORISED",
            currency_code="MMK",
        )
        self.create_donation_with_status(
            "50.00",
            "AUTHORISED",
            currency_code="USD",
        )

        response = self.client.get(
            reverse("financial-monthly-donations-report"),
            {"year": 2026, "month": 11},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

        results = {item["currency_code"]: item for item in response.data["results"]}

        self.assertEqual(
            results["MMK"]["confirmed_total"],
            Decimal("100.00"),
        )
        self.assertEqual(
            results["USD"]["confirmed_total"],
            Decimal("50.00"),
        )

    def test_administrator_can_access_monthly_donation_report(self):
        self.client.force_authenticate(user=self.administrator)

        response = self.client.get(
            reverse("financial-monthly-donations-report"),
            {"year": 2026, "month": 11},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_zone_leader_cannot_access_monthly_donation_report(self):
        self.client.force_authenticate(user=self.zone_leader)

        response = self.client.get(
            reverse("financial-monthly-donations-report"),
            {"year": 2026, "month": 11},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_cannot_access_monthly_donation_report(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            reverse("financial-monthly-donations-report"),
            {"year": 2026, "month": 11},
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_monthly_donation_report_requires_year_and_month(self):
        response = self.client.get(
            reverse("financial-monthly-donations-report"),
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_monthly_donation_report_rejects_invalid_month(self):
        response = self.client.get(
            reverse("financial-monthly-donations-report"),
            {"year": 2026, "month": 13},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_monthly_donation_report_rejects_invalid_year(self):
        response = self.client.get(
            reverse("financial-monthly-donations-report"),
            {"year": 0, "month": 11},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pastor_can_access_monthly_income_report(self):
        response = self.client.get(
            reverse("financial-monthly-income-report"),
            {"year": 2026, "month": 11},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["year"], 2026)
        self.assertEqual(response.data["month"], 11)
        self.assertIn("results", response.data)

    def test_administrator_can_access_monthly_income_report(self):
        self.client.force_authenticate(user=self.administrator)

        response = self.client.get(
            reverse("financial-monthly-income-report"),
            {"year": 2026, "month": 11},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_zone_leader_cannot_access_monthly_income_report(self):
        self.client.force_authenticate(user=self.zone_leader)

        response = self.client.get(
            reverse("financial-monthly-income-report"),
            {"year": 2026, "month": 11},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_cannot_access_monthly_income_report(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            reverse("financial-monthly-income-report"),
            {"year": 2026, "month": 11},
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_monthly_income_report_requires_year_and_month(self):
        response = self.client.get(
            reverse("financial-monthly-income-report"),
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_monthly_income_report_rejects_invalid_month(self):
        response = self.client.get(
            reverse("financial-monthly-income-report"),
            {"year": 2026, "month": 13},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_monthly_income_report_rejects_invalid_year(self):
        response = self.client.get(
            reverse("financial-monthly-income-report"),
            {"year": 0, "month": 11},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pending_authorisations_report_returns_all_pending_record_types(self):
        self.create_donation_with_status("100.00", "PENDING")
        self.create_donation_with_status("30.00", "REJECTED")

        self.create_fund_transaction_with_status("200.00", "PENDING")
        self.create_fund_transaction_with_status("40.00", "REJECTED")

        authorised_donation_id = self.create_authorised_donation()
        self.create_donation_adjustment(
            authorised_donation_id,
            "25.00",
            authorise=False,
        )

        response = self.client.get(
            reverse("financial-pending-authorisations-report"),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        pending = response.data["pending"]

        self.assertEqual(len(pending["donations"]), 1)
        self.assertEqual(len(pending["fund_transactions"]), 1)
        self.assertEqual(len(pending["adjustments"]), 1)

        self.assertEqual(pending["donations"][0]["status"], "PENDING")
        self.assertEqual(
            pending["fund_transactions"][0]["status"],
            "PENDING",
        )
        self.assertEqual(pending["adjustments"][0]["status"], "PENDING")

    def test_pending_authorisations_report_filters_by_date_range(self):
        self.client.post(
            reverse("donation-list-create"),
            self.donation_payload(transaction_date="2026-11-10"),
            format="json",
        )
        self.client.post(
            reverse("donation-list-create"),
            self.donation_payload(transaction_date="2026-11-11"),
            format="json",
        )

        response = self.client.get(
            reverse("financial-pending-authorisations-report"),
            {
                "start_date": "2026-11-11",
                "end_date": "2026-11-11",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["pending"]["donations"]), 1)
        self.assertEqual(
            response.data["pending"]["donations"][0]["transaction_date"],
            "2026-11-11",
        )

    def test_pending_authorisations_report_rejects_invalid_date_range(self):
        response = self.client.get(
            reverse("financial-pending-authorisations-report"),
            {
                "start_date": "2026-11-12",
                "end_date": "2026-11-11",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_administrator_can_access_pending_authorisations_report(self):
        self.client.force_authenticate(user=self.administrator)

        response = self.client.get(
            reverse("financial-pending-authorisations-report"),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_zone_leader_cannot_access_pending_authorisations_report(self):
        self.client.force_authenticate(user=self.zone_leader)

        response = self.client.get(
            reverse("financial-pending-authorisations-report"),
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_cannot_access_pending_authorisations_report(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            reverse("financial-pending-authorisations-report"),
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_daily_donation_report_requires_date(self):
        response = self.client.get(
            reverse("financial-daily-donations-report"),
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_daily_donation_report_rejects_invalid_date(self):
        response = self.client.get(
            reverse("financial-daily-donations-report"),
            {"date": "invalid-date"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_daily_donation_report_separates_statuses(self):
        self.create_donation_with_status("100.00", "AUTHORISED")
        self.create_donation_with_status("50.00", "PENDING")
        self.create_donation_with_status("30.00", "REJECTED")

        response = self.client.get(
            reverse("financial-daily-donations-report"),
            {"date": "2026-11-11"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        result = response.data["results"][0]

        self.assertEqual(result["currency_code"], "MMK")
        self.assertEqual(result["payment_method"], "CASH")
        self.assertEqual(result["authorised_total"], Decimal("100.00"))
        self.assertEqual(result["pending_total"], Decimal("50.00"))
        self.assertEqual(result["rejected_total"], Decimal("30.00"))
        self.assertEqual(result["confirmed_total"], Decimal("100.00"))
        self.assertEqual(len(result["donations"]), 3)

    def test_daily_donation_report_preserves_currency_separation(self):
        self.create_donation_with_status("100.00", "AUTHORISED", currency_code="MMK")
        self.create_donation_with_status("50.00", "AUTHORISED", currency_code="USD")

        response = self.client.get(
            reverse("financial-daily-donations-report"),
            {"date": "2026-11-11"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

        totals = {
            item["currency_code"]: item["confirmed_total"]
            for item in response.data["results"]
        }

        self.assertEqual(totals["MMK"], Decimal("100.00"))
        self.assertEqual(totals["USD"], Decimal("50.00"))

    def test_daily_donation_report_excludes_adjustments(self):
        donation_id = self.create_donation_with_status("100.00", "AUTHORISED")

        self.create_donation_adjustment(
            donation_id,
            "25.00",
            authorise=True,
        )

        response = self.client.get(
            reverse("financial-daily-donations-report"),
            {"date": "2026-11-11"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        result = response.data["results"][0]

        self.assertEqual(result["authorised_total"], Decimal("100.00"))
        self.assertEqual(result["confirmed_total"], Decimal("100.00"))

    def test_administrator_can_access_daily_donation_report(self):
        self.client.force_authenticate(user=self.administrator)

        response = self.client.get(
            reverse("financial-daily-donations-report"),
            {"date": "2026-11-11"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_zone_leader_cannot_access_daily_donation_report(self):
        self.client.force_authenticate(user=self.zone_leader)

        response = self.client.get(
            reverse("financial-daily-donations-report"),
            {"date": "2026-11-11"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_cannot_access_daily_donation_report(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            reverse("financial-daily-donations-report"),
            {"date": "2026-11-11"},
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
