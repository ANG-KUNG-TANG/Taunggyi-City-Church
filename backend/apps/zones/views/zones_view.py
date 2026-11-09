from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions.role_permission import IsPastor
from apps.zones.models.zones import Zone, ZoneLeaderAssignment
from apps.zones.permissions.zone_permissions import (
    CanReadZones,
    has_active_role,
)
from apps.zones.serializers import (
    ZoneLeaderAssignmentCreateSerializer,
    ZoneLeaderAssignmentSerializer,
    ZoneSerializer,
)
from apps.zones.services.zone_service import (
    assign_zone_leader,
    create_zone,
    deactivate_zone,
    end_zone_leader_assignment,
    update_zone,
)


def get_accessible_zones(user):
    """
    Return zones the user is authorised to read.

    A Zone Leader must have a current assignment and an active
    ZONE_LEADER role. Pastors can access all zones.
    """
    if has_active_role(user, "PASTOR"):
        return Zone.objects.all()

    if not has_active_role(user, "ZONE_LEADER"):
        return Zone.objects.none()

    now = timezone.now()

    return (
        Zone.objects.filter(
            leader_assignments__user=user,
            leader_assignments__effective_from__lte=now,
        )
        .filter(
            Q(leader_assignments__effective_to__isnull=True)
            | Q(leader_assignments__effective_to__gt=now)
        )
        .distinct()
    )


def get_zone_or_404(user, zone_id):
    return get_object_or_404(
        get_accessible_zones(user),
        pk=zone_id,
    )


def service_error_response(exc):
    """
    Convert service validation errors into DRF validation errors.

    The project's centralized exception handler will format the response.
    """
    if isinstance(exc, DjangoValidationError):
        raise ValidationError(exc.messages)

    raise exc


class ZoneListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsPastor()]

        return [CanReadZones()]

    def get(self, request):
        zones = get_accessible_zones(request.user)

        serializer = ZoneSerializer(
            zones,
            many=True,
        )

        return Response(serializer.data)

    def post(self, request):
        serializer = ZoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            zone = create_zone(
                name=serializer.validated_data["name"],
                description=serializer.validated_data.get(
                    "description",
                    "",
                ),
                actor=request.user,
            )
        except DjangoValidationError as exc:
            service_error_response(exc)

        return Response(
            ZoneSerializer(zone).data,
            status=status.HTTP_201_CREATED,
        )


class ZoneDetailView(APIView):
    def get_permissions(self):
        if self.request.method in ("PATCH", "PUT"):
            return [IsPastor()]

        return [CanReadZones()]

    def get(self, request, zone_id):
        zone = get_zone_or_404(
            request.user,
            zone_id,
        )

        return Response(ZoneSerializer(zone).data)

    def patch(self, request, zone_id):

        zone = get_object_or_404(
            Zone.objects.all(),
            pk=zone_id,
        )

        serializer = ZoneSerializer(
            zone,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        try:
            zone = update_zone(
                zone=zone,
                actor=request.user,
                name=serializer.validated_data.get("name"),
                description=serializer.validated_data.get("description"),
            )
        except DjangoValidationError as exc:
            service_error_response(exc)

        return Response(ZoneSerializer(zone).data)

    def put(self, request, zone_id):
        if "name" not in request.data or "description" not in request.data:
            raise ValidationError({"detail": "PUT requires both name and description."})
        zone = get_object_or_404(
            Zone.objects.all(),
            pk=zone_id,
        )

        serializer = ZoneSerializer(
            zone,
            data=request.data,
            partial=False,
        )
        serializer.is_valid(raise_exception=True)

        try:
            zone = update_zone(
                zone=zone,
                actor=request.user,
                name=serializer.validated_data["name"],
                description=serializer.validated_data["description"],
            )
        except DjangoValidationError as exc:
            service_error_response(exc)

        return Response(ZoneSerializer(zone).data)


class ZoneDeactivateView(APIView):
    permission_classes = [IsPastor]

    def post(self, request, zone_id):
        zone = get_object_or_404(
            Zone.objects.all(),
            pk=zone_id,
        )

        try:
            zone = deactivate_zone(
                zone=zone,
                actor=request.user,
            )
        except DjangoValidationError as exc:
            service_error_response(exc)

        return Response(ZoneSerializer(zone).data)


class ZoneLeaderAssignmentListCreateView(APIView):
    permission_classes = [IsPastor]

    def get_zone(self, zone_id):
        return get_object_or_404(
            Zone.objects.all(),
            pk=zone_id,
        )

    def get(self, request, zone_id):
        zone = self.get_zone(zone_id)

        assignments = ZoneLeaderAssignment.objects.filter(
            zone=zone,
        ).select_related(
            "user",
            "assigned_by",
            "zone",
        )

        return Response(
            ZoneLeaderAssignmentSerializer(
                assignments,
                many=True,
            ).data
        )

    def post(self, request, zone_id):
        zone = self.get_zone(zone_id)

        serializer = ZoneLeaderAssignmentCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        from apps.accounts.models.users import User

        user = get_object_or_404(
            User.objects.all(),
            pk=serializer.validated_data["user_id"],
        )

        try:
            assignment = assign_zone_leader(
                zone=zone,
                user=user,
                actor=request.user,
                effective_from=serializer.validated_data.get("effective_from"),
            )
        except DjangoValidationError as exc:
            service_error_response(exc)

        return Response(
            ZoneLeaderAssignmentSerializer(assignment).data,
            status=status.HTTP_201_CREATED,
        )


class ZoneLeaderAssignmentEndView(APIView):
    permission_classes = [IsPastor]

    def post(self, request, zone_id, assignment_id):
        assignment = get_object_or_404(
            ZoneLeaderAssignment.objects.select_related("zone"),
            pk=assignment_id,
            zone_id=zone_id,
        )

        effective_to = request.data.get("effective_to")

        if effective_to is not None:
            from rest_framework.fields import DateTimeField

            try:
                effective_to = DateTimeField().run_validation(effective_to)
            except ValidationError:
                raise

        try:
            assignment = end_zone_leader_assignment(
                assignment=assignment,
                actor=request.user,
                effective_to=effective_to,
            )
        except DjangoValidationError as exc:
            service_error_response(exc)

        return Response(ZoneLeaderAssignmentSerializer(assignment).data)
