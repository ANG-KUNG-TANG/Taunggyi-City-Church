"""
Attendance business services for Taunggyi City Church.

Responsibilities:
- Attendance session creation and lifecycle management.
- Member attendance recording.
- Aggregate visitor count recording.
- Pastor and Zone Leader authorization.
- Zone and member eligibility validation.
- Transactional audit logging.
"""

from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models.users import User
from apps.activities.models.activity import Activity
from apps.attendance.models.attendance_session import AttendanceSession
from apps.attendance.models.member_attendance import MemberAttendance
from apps.attendance.models.visitor_count import VisitorCount
from apps.audit.models.audit_log import AuditLog
from apps.audit.services.audit_service import AuditService
from apps.members.models import Member
from apps.zones.models.zones import Zone, ZoneLeaderAssignment


PASTOR_ROLE = "PASTOR"
ZONE_LEADER_ROLE = "ZONE_LEADER"


class AttendanceService:
    """Business logic for managing Attendance."""

    SESSION_ENTITY = "AttendanceSession"
    MEMBER_ATTENDANCE_ENTITY = "MemberAttendance"
    VISITOR_COUNT_ENTITY = "VisitorCount"

    # ---------------------------------------------------------
    # Authorization
    # ---------------------------------------------------------

    @staticmethod
    def _require_active_user(actor):
        """Require a valid, active authenticated user."""

        if not isinstance(actor, User):
            raise ValidationError("A valid user is required.")

        if not actor.is_active:
            raise ValidationError("An inactive user cannot manage Attendance.")

    @staticmethod
    def _has_active_role(actor, role_code):
        """Return whether the actor has an unrevoked role."""

        return actor.role_assignments.filter(
            role__code=role_code,
            revoked_at__isnull=True,
        ).exists()

    @staticmethod
    def _require_attendance_actor(actor):
        """Require an active Pastor or Zone Leader."""

        AttendanceService._require_active_user(actor)

        if not (
            AttendanceService._has_active_role(actor, PASTOR_ROLE)
            or AttendanceService._has_active_role(
                actor,
                ZONE_LEADER_ROLE,
            )
        ):
            raise ValidationError(
                "Only an active Pastor or Zone Leader " "can manage Attendance."
            )

    @staticmethod
    def _require_pastor(actor):
        """Require an active Pastor."""

        AttendanceService._require_active_user(actor)

        if not AttendanceService._has_active_role(
            actor,
            PASTOR_ROLE,
        ):
            raise ValidationError("Only an active Pastor can perform this operation.")

    @staticmethod
    def _require_zone_access(*, zone, actor):
        """
        Require access to an active zone.

        Pastors:
            May access every active zone.

        Zone Leaders:
            Must have a current assignment to the zone.
        """

        if not isinstance(zone, Zone):
            raise ValidationError("A valid zone is required.")

        if not zone.is_active:
            raise ValidationError("Attendance cannot be managed in an inactive zone.")

        if AttendanceService._has_active_role(
            actor,
            PASTOR_ROLE,
        ):
            return

        if not AttendanceService._has_active_role(
            actor,
            ZONE_LEADER_ROLE,
        ):
            raise ValidationError("Only a Pastor or Zone Leader can manage Attendance.")

        now = timezone.now()

        has_assignment = (
            ZoneLeaderAssignment.objects.filter(
                zone=zone,
                user=actor,
                effective_from__lte=now,
            )
            .filter(Q(effective_to__isnull=True) | Q(effective_to__gt=now))
            .exists()
        )

        if not has_assignment:
            raise ValidationError("You are not currently assigned to this zone.")

    @staticmethod
    def _require_session_access(*, session, actor):
        """Validate access to a session's scope."""

        AttendanceService._require_attendance_actor(actor)

        if session.scope == AttendanceSession.Scope.CHURCH_WIDE:
            AttendanceService._require_pastor(actor)
            return

        if session.scope == AttendanceSession.Scope.ZONE:
            AttendanceService._require_zone_access(
                zone=session.zone,
                actor=actor,
            )
            return

        raise ValidationError("Invalid attendance session scope.")

    # ---------------------------------------------------------
    # Validation and snapshots
    # ---------------------------------------------------------

    @staticmethod
    def _validate_uuid(value, field_name):
        """Validate UUID identifiers."""

        if not isinstance(value, UUID):
            try:
                value = UUID(str(value))
            except (ValueError, TypeError, AttributeError):
                raise ValidationError(f"{field_name} must be a valid UUID.")

        return value

    @staticmethod
    def _validate_reason(reason):
        """Require a meaningful correction reason."""

        if not isinstance(reason, str):
            raise ValidationError("A correction reason is required.")

        reason = reason.strip()

        if not reason:
            raise ValidationError("A correction reason is required.")

        if len(reason) > 500:
            raise ValidationError("Correction reason cannot exceed 500 characters.")

        return reason

    @staticmethod
    def _session_snapshot(session):
        """Return a safe session audit snapshot."""

        return {
            "id": str(session.id),
            "activity_id": (str(session.activity_id) if session.activity_id else None),
            "date": session.date.isoformat(),
            "start_time": session.start_time.isoformat(),
            "scope": session.scope,
            "zone_id": (str(session.zone_id) if session.zone_id else None),
            "status": session.status,
        }

    @staticmethod
    def _attendance_snapshot(record):
        """Return a member attendance audit snapshot."""

        return {
            "id": str(record.id),
            "session_id": str(record.session_id),
            "member_id": str(record.member_id),
            "status": record.status,
        }

    @staticmethod
    def _visitor_snapshot(record):
        """Return a visitor count audit snapshot."""

        return {
            "id": str(record.id),
            "session_id": str(record.session_id),
            "count": record.count,
        }

    @staticmethod
    def _validate_session_status(session, expected_status):
        """Require the session to have the expected status."""

        if session.status != expected_status:
            raise ValidationError(
                f"Attendance session must be " f"{expected_status.lower()}."
            )

    @staticmethod
    def _get_session(session_id):
        """Retrieve a session by UUID."""

        session_id = AttendanceService._validate_uuid(
            session_id,
            "Session ID",
        )

        try:
            return AttendanceSession.objects.get(
                pk=session_id,
            )
        except AttendanceSession.DoesNotExist:
            raise ValidationError("Attendance session does not exist.")

    @staticmethod
    def _get_member(member_id):
        """Retrieve a member by UUID."""

        member_id = AttendanceService._validate_uuid(
            member_id,
            "Member ID",
        )

        try:
            return Member.objects.select_related(
                "zone",
            ).get(pk=member_id)
        except Member.DoesNotExist:
            raise ValidationError("Member does not exist.")

    @staticmethod
    def _validate_member_for_session(*, member, session, actor):
        """Validate member eligibility for the session."""

        if not member.is_active:
            raise ValidationError("Inactive members cannot be recorded.")

        if not member.zone.is_active:
            raise ValidationError("Members in inactive zones cannot be recorded.")

        if session.scope == AttendanceSession.Scope.ZONE:
            if member.zone_id != session.zone_id:
                raise ValidationError(
                    "The member does not belong to this session's zone."
                )

        elif session.scope == AttendanceSession.Scope.CHURCH_WIDE:
            if not AttendanceService._has_active_role(
                actor,
                PASTOR_ROLE,
            ):
                raise ValidationError(
                    "Only a Pastor can record church-wide Attendance."
                )

        else:
            raise ValidationError("Invalid attendance session scope.")

    @staticmethod
    def _validate_member_status(status):
        """Validate the member attendance status."""

        valid_statuses = {choice[0] for choice in MemberAttendance.Status.choices}

        if status not in valid_statuses:
            raise ValidationError("Status must be PRESENT or ABSENT.")

        return status

    @staticmethod
    def _validate_visitor_count(count):
        """Validate a non-negative integer visitor count."""

        if isinstance(count, bool) or not isinstance(count, int):
            raise ValidationError("Visitor count must be a non-negative integer.")

        if count < 0:
            raise ValidationError("Visitor count cannot be negative.")

        return count

    # ---------------------------------------------------------
    # Session creation
    # ---------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def create_session(
        *,
        actor,
        date,
        start_time,
        scope,
        zone=None,
        activity=None,
        correlation_id=None,
    ):
        """Create an Attendance session in DRAFT status."""

        AttendanceService._require_attendance_actor(actor)

        valid_scopes = {choice[0] for choice in AttendanceSession.Scope.choices}

        if scope not in valid_scopes:
            raise ValidationError("Invalid Attendance scope.")

        if scope == AttendanceSession.Scope.ZONE:
            if zone is None:
                raise ValidationError("A zone is required for zone Attendance.")

            AttendanceService._require_zone_access(
                zone=zone,
                actor=actor,
            )

        elif scope == AttendanceSession.Scope.CHURCH_WIDE:
            AttendanceService._require_pastor(actor)

            if zone is not None:
                raise ValidationError("Church-wide Attendance cannot have a zone.")

        if activity is not None:
            if not isinstance(activity, Activity):
                raise ValidationError("A valid activity is required.")

            if activity.pk is None:
                raise ValidationError("The activity must be saved.")

        session = AttendanceSession.objects.create(
            activity=activity,
            date=date,
            start_time=start_time,
            scope=scope,
            zone=zone,
            status=AttendanceSession.Status.DRAFT,
            created_by=actor,
        )

        AuditService.record_event(
            actor=actor,
            entity_type=AttendanceService.SESSION_ENTITY,
            entity_id=session.id,
            action=AuditLog.Action.CREATE,
            after_data=AttendanceService._session_snapshot(
                session,
            ),
            correlation_id=correlation_id,
        )

        return session

    @staticmethod
    @transaction.atomic
    def update_session(
        *,
        actor,
        session_id,
        date=None,
        start_time=None,
        activity=None,
        correlation_id=None,
    ):
        """Update an accessible DRAFT session and record an audit event."""

        AttendanceService._require_attendance_actor(actor)

        session = AttendanceService._get_session(session_id)

        session = AttendanceSession.objects.select_for_update().get(
            pk=session.pk,
        )

        AttendanceService._require_session_access(
            session=session,
            actor=actor,
        )

        AttendanceService._validate_session_status(
            session,
            AttendanceSession.Status.DRAFT,
        )

        if activity is not None and not isinstance(activity, Activity):
            raise ValidationError("A valid activity is required.")

        if activity is not None and activity.pk is None:
            raise ValidationError("The activity must be saved.")

        before_data = AttendanceService._session_snapshot(session)

        if date is not None:
            session.date = date

        if start_time is not None:
            session.start_time = start_time

        if activity is not None:
            session.activity = activity

        session.updated_by = actor
        session.save(
            update_fields=[
                "date",
                "start_time",
                "activity",
                "updated_by",
                "updated_at",
            ],
        )

        AuditService.record_event(
            actor=actor,
            entity_type=AttendanceService.SESSION_ENTITY,
            entity_id=session.id,
            action=AuditLog.Action.UPDATE,
            before_data=before_data,
            after_data=AttendanceService._session_snapshot(session),
            correlation_id=correlation_id,
        )

        return session

    # ---------------------------------------------------------
    # Session lifecycle
    # ---------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def open_session(
        *,
        actor,
        session_id,
        correlation_id=None,
    ):
        """Open a DRAFT session."""

        AttendanceService._require_attendance_actor(actor)

        session = AttendanceService._get_session(
            session_id,
        )

        session = AttendanceSession.objects.select_for_update().get(
            pk=session.pk,
        )

        AttendanceService._require_session_access(
            session=session,
            actor=actor,
        )

        AttendanceService._validate_session_status(
            session,
            AttendanceSession.Status.DRAFT,
        )

        before_data = AttendanceService._session_snapshot(
            session,
        )

        session.status = AttendanceSession.Status.OPEN
        session.updated_by = actor

        session.save(
            update_fields=[
                "status",
                "updated_by",
                "updated_at",
            ],
        )

        AuditService.record_event(
            actor=actor,
            entity_type=AttendanceService.SESSION_ENTITY,
            entity_id=session.id,
            action=AuditLog.Action.UPDATE,
            before_data=before_data,
            after_data=AttendanceService._session_snapshot(
                session,
            ),
            correlation_id=correlation_id,
        )

        return session

    @staticmethod
    @transaction.atomic
    def close_session(
        *,
        actor,
        session_id,
        correlation_id=None,
    ):
        """Close an OPEN session."""

        AttendanceService._require_attendance_actor(actor)

        session = AttendanceService._get_session(
            session_id,
        )

        session = AttendanceSession.objects.select_for_update().get(
            pk=session.pk,
        )

        AttendanceService._require_session_access(
            session=session,
            actor=actor,
        )

        AttendanceService._validate_session_status(
            session,
            AttendanceSession.Status.OPEN,
        )

        before_data = AttendanceService._session_snapshot(
            session,
        )

        session.status = AttendanceSession.Status.CLOSED
        session.updated_by = actor

        session.save(
            update_fields=[
                "status",
                "updated_by",
                "updated_at",
            ],
        )

        AuditService.record_event(
            actor=actor,
            entity_type=AttendanceService.SESSION_ENTITY,
            entity_id=session.id,
            action=AuditLog.Action.UPDATE,
            before_data=before_data,
            after_data=AttendanceService._session_snapshot(
                session,
            ),
            correlation_id=correlation_id,
        )

        return session

    @staticmethod
    @transaction.atomic
    def archive_session(
        *,
        actor,
        session_id,
        correlation_id=None,
    ):
        """Archive a CLOSED session."""

        AttendanceService._require_pastor(actor)

        session = AttendanceService._get_session(
            session_id,
        )

        session = AttendanceSession.objects.select_for_update().get(
            pk=session.pk,
        )

        AttendanceService._validate_session_status(
            session,
            AttendanceSession.Status.CLOSED,
        )

        before_data = AttendanceService._session_snapshot(
            session,
        )

        session.status = AttendanceSession.Status.ARCHIVED
        session.updated_by = actor

        session.save(
            update_fields=[
                "status",
                "updated_by",
                "updated_at",
            ],
        )

        AuditService.record_event(
            actor=actor,
            entity_type=AttendanceService.SESSION_ENTITY,
            entity_id=session.id,
            action=AuditLog.Action.UPDATE,
            before_data=before_data,
            after_data=AttendanceService._session_snapshot(
                session,
            ),
            correlation_id=correlation_id,
        )

        return session

    # ---------------------------------------------------------
    # Member attendance
    # ---------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def record_member_attendance(
        *,
        actor,
        session_id,
        member_id,
        status,
        correlation_id=None,
    ):
        """Create or update member attendance in an OPEN session."""

        AttendanceService._require_attendance_actor(actor)

        session = AttendanceService._get_session(
            session_id,
        )

        session = AttendanceSession.objects.select_for_update().get(
            pk=session.pk,
        )

        AttendanceService._require_session_access(
            session=session,
            actor=actor,
        )

        AttendanceService._validate_session_status(
            session,
            AttendanceSession.Status.OPEN,
        )

        member = AttendanceService._get_member(
            member_id,
        )

        AttendanceService._validate_member_for_session(
            member=member,
            session=session,
            actor=actor,
        )

        status = AttendanceService._validate_member_status(
            status,
        )

        record = MemberAttendance.objects.filter(
            session=session,
            member=member,
        ).first()

        if record is None:
            record = MemberAttendance.objects.create(
                session=session,
                member=member,
                status=status,
                recorded_by=actor,
            )

            AuditService.record_event(
                actor=actor,
                entity_type=AttendanceService.MEMBER_ATTENDANCE_ENTITY,
                entity_id=record.id,
                action=AuditLog.Action.CREATE,
                after_data=AttendanceService._attendance_snapshot(
                    record,
                ),
                correlation_id=correlation_id,
            )

            return record

        record = MemberAttendance.objects.select_for_update().get(
            pk=record.pk,
        )

        before_data = AttendanceService._attendance_snapshot(
            record,
        )

        if record.status == status:
            return record

        record.status = status
        record.updated_by = actor

        record.save(
            update_fields=[
                "status",
                "updated_by",
                "updated_at",
            ],
        )

        AuditService.record_event(
            actor=actor,
            entity_type=AttendanceService.MEMBER_ATTENDANCE_ENTITY,
            entity_id=record.id,
            action=AuditLog.Action.UPDATE,
            before_data=before_data,
            after_data=AttendanceService._attendance_snapshot(
                record,
            ),
            correlation_id=correlation_id,
        )

        return record

    # ---------------------------------------------------------
    # Visitor count
    # ---------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def record_visitor_count(
        *,
        actor,
        session_id,
        count,
        correlation_id=None,
    ):
        """Create or update the aggregate visitor count."""

        AttendanceService._require_attendance_actor(actor)

        session = AttendanceService._get_session(
            session_id,
        )

        session = AttendanceSession.objects.select_for_update().get(
            pk=session.pk,
        )

        AttendanceService._require_session_access(
            session=session,
            actor=actor,
        )

        AttendanceService._validate_session_status(
            session,
            AttendanceSession.Status.OPEN,
        )

        count = AttendanceService._validate_visitor_count(
            count,
        )

        record = VisitorCount.objects.filter(
            session=session,
        ).first()

        if record is None:
            record = VisitorCount.objects.create(
                session=session,
                count=count,
                recorded_by=actor,
            )

            AuditService.record_event(
                actor=actor,
                entity_type=AttendanceService.VISITOR_COUNT_ENTITY,
                entity_id=record.id,
                action=AuditLog.Action.CREATE,
                after_data=AttendanceService._visitor_snapshot(
                    record,
                ),
                correlation_id=correlation_id,
            )

            return record

        record = VisitorCount.objects.select_for_update().get(
            pk=record.pk,
        )

        before_data = AttendanceService._visitor_snapshot(
            record,
        )

        if record.count == count:
            return record

        record.count = count
        record.updated_by = actor

        record.save(
            update_fields=[
                "count",
                "updated_by",
                "updated_at",
            ],
        )

        AuditService.record_event(
            actor=actor,
            entity_type=AttendanceService.VISITOR_COUNT_ENTITY,
            entity_id=record.id,
            action=AuditLog.Action.UPDATE,
            before_data=before_data,
            after_data=AttendanceService._visitor_snapshot(
                record,
            ),
            correlation_id=correlation_id,
        )

        return record

    # ---------------------------------------------------------
    # Corrections
    # ---------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def correct_member_attendance(
        *,
        actor,
        session_id,
        member_id,
        status,
        reason,
        correlation_id=None,
    ):
        """
        Correct member attendance after session closure.

        Only an active Pastor may perform a correction.
        A correction reason is mandatory.
        """

        AttendanceService._require_pastor(actor)

        reason = AttendanceService._validate_reason(
            reason,
        )

        session = AttendanceService._get_session(
            session_id,
        )

        session = AttendanceSession.objects.select_for_update().get(
            pk=session.pk,
        )

        AttendanceService._validate_session_status(
            session,
            AttendanceSession.Status.CLOSED,
        )

        member = AttendanceService._get_member(
            member_id,
        )

        AttendanceService._validate_member_status(
            status,
        )

        record = (
            MemberAttendance.objects.select_for_update()
            .filter(
                session=session,
                member=member,
            )
            .first()
        )

        if record is None:
            raise ValidationError("Attendance record does not exist.")

        before_data = AttendanceService._attendance_snapshot(
            record,
        )

        record.status = status
        record.updated_by = actor

        record.save(
            update_fields=[
                "status",
                "updated_by",
                "updated_at",
            ],
        )

        after_data = AttendanceService._attendance_snapshot(
            record,
        )

        after_data["correction_reason"] = reason

        AuditService.record_event(
            actor=actor,
            entity_type=AttendanceService.MEMBER_ATTENDANCE_ENTITY,
            entity_id=record.id,
            action=AuditLog.Action.CORRECT,
            before_data=before_data,
            after_data=after_data,
            correlation_id=correlation_id,
        )

        return record

    @staticmethod
    @transaction.atomic
    def correct_visitor_count(
        *,
        actor,
        session_id,
        count,
        reason,
        correlation_id=None,
    ):
        """
        Correct a visitor count after session closure.

        Only an active Pastor may perform a correction.
        A correction reason is mandatory.
        """

        AttendanceService._require_pastor(actor)

        reason = AttendanceService._validate_reason(
            reason,
        )

        session = AttendanceService._get_session(
            session_id,
        )

        session = AttendanceSession.objects.select_for_update().get(
            pk=session.pk,
        )

        AttendanceService._validate_session_status(
            session,
            AttendanceSession.Status.CLOSED,
        )

        count = AttendanceService._validate_visitor_count(
            count,
        )

        record = (
            VisitorCount.objects.select_for_update()
            .filter(
                session=session,
            )
            .first()
        )

        if record is None:
            raise ValidationError("Visitor count record does not exist.")

        before_data = AttendanceService._visitor_snapshot(
            record,
        )

        record.count = count
        record.updated_by = actor

        record.save(
            update_fields=[
                "count",
                "updated_by",
                "updated_at",
            ],
        )

        after_data = AttendanceService._visitor_snapshot(
            record,
        )

        after_data["correction_reason"] = reason

        AuditService.record_event(
            actor=actor,
            entity_type=AttendanceService.VISITOR_COUNT_ENTITY,
            entity_id=record.id,
            action=AuditLog.Action.CORRECT,
            before_data=before_data,
            after_data=after_data,
            correlation_id=correlation_id,
        )

        return record
