import uuid

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models.users import User
from apps.audit.models.audit_log import AuditLog
from apps.audit.services.audit_service import AuditService


class AuditServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = User.objects.create_user(
            email="audit-test@example.com",
            password="test-password",
        )

    def test_record_event_creates_audit_log(self):
        entity_id = uuid.uuid4()
        correlation_id = uuid.uuid4()

        event = AuditService.record_event(
            actor=self.actor,
            entity_type="Member",
            entity_id=entity_id,
            action=AuditLog.Action.CREATE,
            after_data={"full_name": "Audit Test Member"},
            correlation_id=correlation_id,
        )

        self.assertIsInstance(event, AuditLog)
        self.assertEqual(event.actor, self.actor)
        self.assertEqual(event.entity_type, "Member")
        self.assertEqual(event.entity_id, entity_id)
        self.assertEqual(event.action, AuditLog.Action.CREATE)
        self.assertEqual(
            event.after_data,
            {"full_name": "Audit Test Member"},
        )
        self.assertIsNone(event.before_data)
        self.assertEqual(event.correlation_id, correlation_id)
        self.assertIsNotNone(event.occurred_at)

        self.assertTrue(AuditLog.objects.filter(pk=event.pk).exists())

    def test_record_event_preserves_before_and_after_snapshots(self):
        before_data = {
            "full_name": "Previous Name",
            "is_active": True,
        }
        after_data = {
            "full_name": "Updated Name",
            "is_active": False,
        }

        event = AuditService.record_event(
            actor=self.actor,
            entity_type="Member",
            entity_id=uuid.uuid4(),
            action=AuditLog.Action.UPDATE,
            before_data=before_data,
            after_data=after_data,
        )

        self.assertEqual(event.before_data, before_data)
        self.assertEqual(event.after_data, after_data)

    def test_sensitive_fields_are_removed_from_snapshots(self):
        event = AuditService.record_event(
            actor=self.actor,
            entity_type="User",
            entity_id=uuid.uuid4(),
            action=AuditLog.Action.UPDATE,
            after_data={
                "email": "audit-test@example.com",
                "password": "should-not-be-stored",
                "access_token": "secret-token",
                "profile": {
                    "first_name": "Test",
                    "secret": "private-value",
                },
                "roles": [
                    {"name": "Pastor", "token": "hidden-token"},
                ],
            },
        )

        self.assertEqual(
            event.after_data,
            {
                "email": "audit-test@example.com",
                "profile": {
                    "first_name": "Test",
                },
                "roles": [
                    {"name": "Pastor"},
                ],
            },
        )

    def test_uuid_values_are_serialized_in_snapshots(self):
        zone_id = uuid.uuid4()

        event = AuditService.record_event(
            actor=self.actor,
            entity_type="Member",
            entity_id=uuid.uuid4(),
            action=AuditLog.Action.CREATE,
            after_data={"zone_id": zone_id},
        )

        self.assertEqual(
            event.after_data["zone_id"],
            str(zone_id),
        )

    def test_empty_entity_type_is_rejected(self):
        with self.assertRaises(ValidationError):
            AuditService.record_event(
                actor=self.actor,
                entity_type="",
                entity_id=uuid.uuid4(),
                action=AuditLog.Action.CREATE,
            )

    def test_entity_type_over_80_characters_is_rejected(self):
        with self.assertRaises(ValidationError):
            AuditService.record_event(
                actor=self.actor,
                entity_type="M" * 81,
                entity_id=uuid.uuid4(),
                action=AuditLog.Action.CREATE,
            )

    def test_non_uuid_entity_id_is_rejected(self):
        with self.assertRaises(ValidationError):
            AuditService.record_event(
                actor=self.actor,
                entity_type="Member",
                entity_id="not-a-uuid",
                action=AuditLog.Action.CREATE,
            )

    def test_invalid_action_is_rejected(self):
        with self.assertRaises(ValidationError):
            AuditService.record_event(
                actor=self.actor,
                entity_type="Member",
                entity_id=uuid.uuid4(),
                action="INVALID_ACTION",
            )

    def test_non_uuid_correlation_id_is_rejected(self):
        with self.assertRaises(ValidationError):
            AuditService.record_event(
                actor=self.actor,
                entity_type="Member",
                entity_id=uuid.uuid4(),
                action=AuditLog.Action.CREATE,
                correlation_id="not-a-uuid",
            )

    def test_audit_record_cannot_be_updated(self):
        event = AuditService.record_event(
            actor=self.actor,
            entity_type="Member",
            entity_id=uuid.uuid4(),
            action=AuditLog.Action.CREATE,
        )

        event.action = AuditLog.Action.UPDATE

        with self.assertRaises(ValidationError):
            event.save()

    def test_audit_record_cannot_be_deleted(self):
        event = AuditService.record_event(
            actor=self.actor,
            entity_type="Member",
            entity_id=uuid.uuid4(),
            action=AuditLog.Action.CREATE,
        )

        with self.assertRaises(ValidationError):
            event.delete()

    def test_queryset_update_is_rejected(self):
        AuditService.record_event(
            actor=self.actor,
            entity_type="Member",
            entity_id=uuid.uuid4(),
            action=AuditLog.Action.CREATE,
        )

        with self.assertRaises(ValidationError):
            AuditLog.objects.all().update(
                action=AuditLog.Action.UPDATE,
            )

    def test_queryset_delete_is_rejected(self):
        AuditService.record_event(
            actor=self.actor,
            entity_type="Member",
            entity_id=uuid.uuid4(),
            action=AuditLog.Action.CREATE,
        )

        with self.assertRaises(ValidationError):
            AuditLog.objects.all().delete()
