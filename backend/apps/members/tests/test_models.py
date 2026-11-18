from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models.users import User
from apps.members.models import Member
from apps.zones.models.zones import Zone


class MemberModelTests(TestCase):
    def setUp(self):
        self.pastor = User.objects.create_user(
            email="pastor@example.com",
            password="test-password",
        )

        self.updated_by_user = User.objects.create_user(
            email="updater@example.com",
            password="test-password",
        )

        self.zone = Zone.objects.create(name="Zone A")

    def create_member(self, **overrides):
        data = {
            "zone": self.zone,
            "full_name": "Test Member",
            "created_by": self.pastor,
        }
        data.update(overrides)
        return Member.objects.create(**data)

    # Identity and default values

    def test_member_has_automatically_generated_uuid(self):
        member = self.create_member()

        self.assertIsNotNone(member.id)
        self.assertEqual(member.id.version, 4)

    def test_each_member_has_a_unique_uuid(self):
        first = self.create_member()
        second = self.create_member(full_name="Another Member")

        self.assertNotEqual(first.id, second.id)

    def test_member_defaults_are_correct(self):
        member = self.create_member()

        self.assertTrue(member.is_active)
        self.assertEqual(member.version, 1)
        self.assertEqual(member.phone, "")
        self.assertEqual(member.address, "")
        self.assertEqual(member.notes, "")
        self.assertIsNone(member.updated_by)

    def test_version_field_is_not_editable(self):
        field = Member._meta.get_field("version")

        self.assertFalse(field.editable)
        self.assertEqual(field.default, 1)

    # Required and optional relationships

    def test_member_belongs_to_its_zone(self):
        member = self.create_member()

        self.assertEqual(member.zone, self.zone)
        self.assertEqual(member.zone_id, self.zone.id)

    def test_member_records_creator(self):
        member = self.create_member()

        self.assertEqual(member.created_by, self.pastor)

    def test_updated_by_is_optional(self):
        member = self.create_member()

        self.assertIsNone(member.updated_by)

    def test_updated_by_can_reference_a_user(self):
        member = self.create_member(
            updated_by=self.updated_by_user,
        )

        self.assertEqual(member.updated_by, self.updated_by_user)

    # Field and metadata behaviour

    def test_member_string_representation_returns_full_name(self):
        member = self.create_member()

        self.assertEqual(str(member), "Test Member")

    def test_member_table_name_is_correct(self):
        self.assertEqual(Member._meta.db_table, "members")

    def test_members_are_ordered_by_full_name(self):
        self.create_member(full_name="Zoe")
        self.create_member(full_name="Adam")
        self.create_member(full_name="Peter")

        names = list(Member.objects.values_list("full_name", flat=True))

        self.assertEqual(names, ["Adam", "Peter", "Zoe"])

    def test_member_timestamps_are_created_automatically(self):
        before_creation = timezone.now()

        member = self.create_member()

        self.assertIsNotNone(member.created_at)
        self.assertIsNotNone(member.updated_at)
        self.assertGreaterEqual(
            member.created_at,
            before_creation,
        )
        self.assertGreaterEqual(
            member.updated_at,
            member.created_at,
        )

    def test_version_does_not_increment_on_direct_model_save(self):
        member = self.create_member()

        member.full_name = "Direct Model Update"
        member.save()

        member.refresh_from_db()

        self.assertEqual(member.full_name, "Direct Model Update")
        self.assertEqual(member.version, 1)

    # Protected deletion behaviour

    def test_zone_cannot_be_deleted_while_members_reference_it(self):
        self.create_member()

        with self.assertRaises(ProtectedError):
            self.zone.delete()

        self.assertTrue(Zone.objects.filter(id=self.zone.id).exists())

    def test_creator_cannot_be_deleted_while_members_reference_them(self):
        self.create_member()

        with self.assertRaises(ProtectedError):
            self.pastor.delete()

        self.assertTrue(User.objects.filter(id=self.pastor.id).exists())

    def test_updater_cannot_be_deleted_while_members_reference_them(self):
        self.create_member(updated_by=self.updated_by_user)

        with self.assertRaises(ProtectedError):
            self.updated_by_user.delete()

        self.assertTrue(User.objects.filter(id=self.updated_by_user.id).exists())
