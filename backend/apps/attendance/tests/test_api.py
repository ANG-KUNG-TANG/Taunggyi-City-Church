from datetime import date, time

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.attendance.models.attendance_session import AttendanceSession
from apps.attendance.services.attendance_service import AttendanceService
from apps.zones.models.zones import Zone, ZoneLeaderAssignment


class AttendanceSessionAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.pastor = self.create_user("pastor@example.com")
        self.leader = self.create_user("leader@example.com")
        self.other_leader = self.create_user("other-leader@example.com")
        self.ordinary_user = self.create_user("ordinary@example.com")

        self.pastor_role = Role.objects.get(code="PASTOR")
        self.leader_role = Role.objects.get(code="ZONE_LEADER")

        self.assign_role(self.pastor, self.pastor_role)
        self.assign_role(self.leader, self.leader_role)
        self.assign_role(self.other_leader, self.leader_role)

        self.zone = Zone.objects.create(name="Zone A")
        self.other_zone = Zone.objects.create(name="Zone B")

        self.assign_zone_leader(self.leader, self.zone)
        self.assign_zone_leader(self.other_leader, self.other_zone)

        self.list_url = reverse("attendance-session-list-create")

    def create_user(self, email):
        return User.objects.create_user(
            email=email,
            password="test-password",
        )

    def assign_role(self, user, role):
        return UserRole.objects.create(
            user=user,
            role=role,
        )

    def assign_zone_leader(self, user, zone):
        return ZoneLeaderAssignment.objects.create(
            zone=zone,
            user=user,
            assigned_by=self.pastor,
            effective_from=timezone.now(),
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def create_session(self, actor, zone=None):
        return AttendanceService.create_session(
            actor=actor,
            date=date.today(),
            start_time=time(10, 0),
            scope=AttendanceSession.Scope.ZONE,
            zone=zone or self.zone,
        )

    def test_unauthenticated_user_cannot_list_sessions(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 401)

    def test_ordinary_user_cannot_list_sessions(self):
        self.authenticate(self.ordinary_user)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 403)

    def test_pastor_can_create_zone_session(self):
        self.authenticate(self.pastor)

        response = self.client.post(
            self.list_url,
            {
                "date": date.today().isoformat(),
                "start_time": "10:00:00",
                "scope": AttendanceSession.Scope.ZONE,
                "zone_id": str(self.zone.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["scope"],
            AttendanceSession.Scope.ZONE,
        )
        self.assertEqual(
            str(response.data["zone"]),
            str(self.zone.id),
        )
        self.assertEqual(
            response.data["status"],
            AttendanceSession.Status.DRAFT,
        )

    def test_pastor_can_create_church_wide_session(self):
        self.authenticate(self.pastor)

        response = self.client.post(
            self.list_url,
            {
                "date": date.today().isoformat(),
                "start_time": "10:00:00",
                "scope": AttendanceSession.Scope.CHURCH_WIDE,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["scope"],
            AttendanceSession.Scope.CHURCH_WIDE,
        )
        self.assertIsNone(response.data["zone"])

    def test_zone_leader_can_create_session_in_assigned_zone(self):
        self.authenticate(self.leader)

        response = self.client.post(
            self.list_url,
            {
                "date": date.today().isoformat(),
                "start_time": "10:00:00",
                "scope": AttendanceSession.Scope.ZONE,
                "zone_id": str(self.zone.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

    def test_zone_leader_cannot_create_session_in_unassigned_zone(self):
        self.authenticate(self.leader)

        response = self.client.post(
            self.list_url,
            {
                "date": date.today().isoformat(),
                "start_time": "10:00:00",
                "scope": AttendanceSession.Scope.ZONE,
                "zone_id": str(self.other_zone.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(AttendanceSession.objects.count(), 0)

    def test_zone_leader_cannot_create_church_wide_session(self):
        self.authenticate(self.leader)

        response = self.client.post(
            self.list_url,
            {
                "date": date.today().isoformat(),
                "start_time": "10:00:00",
                "scope": AttendanceSession.Scope.CHURCH_WIDE,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(AttendanceSession.objects.count(), 0)

    def test_zone_leader_only_sees_assigned_zone_sessions(self):
        own_session = self.create_session(self.leader, self.zone)
        self.create_session(self.other_leader, self.other_zone)

        self.authenticate(self.leader)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        returned_ids = {str(item["id"]) for item in response.data}

        self.assertEqual(returned_ids, {str(own_session.id)})

    def test_zone_leader_cannot_retrieve_another_zone_session(self):
        other_session = self.create_session(
            self.other_leader,
            self.other_zone,
        )

        self.authenticate(self.leader)

        response = self.client.get(
            reverse(
                "attendance-session-detail",
                kwargs={"session_id": other_session.id},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_pastor_can_retrieve_session(self):
        session = self.create_session(self.leader)

        self.authenticate(self.pastor)

        response = self.client.get(
            reverse(
                "attendance-session-detail",
                kwargs={"session_id": session.id},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["id"]), str(session.id))

    def test_zone_leader_can_open_and_close_own_session(self):
        session = self.create_session(self.leader)
        self.authenticate(self.leader)

        open_response = self.client.post(
            reverse(
                "attendance-session-open",
                kwargs={"session_id": session.id},
            ),
            {},
            format="json",
        )

        self.assertEqual(open_response.status_code, 200)
        self.assertEqual(
            open_response.data["status"],
            AttendanceSession.Status.OPEN,
        )

        close_response = self.client.post(
            reverse(
                "attendance-session-close",
                kwargs={"session_id": session.id},
            ),
            {},
            format="json",
        )

        self.assertEqual(close_response.status_code, 200)
        self.assertEqual(
            close_response.data["status"],
            AttendanceSession.Status.CLOSED,
        )

    def test_zone_leader_cannot_open_another_zone_session(self):
        session = self.create_session(
            self.other_leader,
            self.other_zone,
        )

        self.authenticate(self.leader)

        response = self.client.post(
            reverse(
                "attendance-session-open",
                kwargs={"session_id": session.id},
            ),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        session.refresh_from_db()
        self.assertEqual(
            session.status,
            AttendanceSession.Status.DRAFT,
        )

    def test_invalid_request_id_is_rejected(self):
        self.authenticate(self.pastor)

        response = self.client.post(
            self.list_url,
            {
                "date": date.today().isoformat(),
                "start_time": "10:00:00",
                "scope": AttendanceSession.Scope.ZONE,
                "zone_id": str(self.zone.id),
            },
            format="json",
            HTTP_X_REQUEST_ID="not-a-uuid",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(AttendanceSession.objects.count(), 0)
