"""
Member API views.

Provides authenticated member listing, creation, retrieval and updates.
All business operations are delegated to the member service layer.
"""

import uuid

from django.core.exceptions import (
    PermissionDenied as DjangoPermissionDenied,
    ValidationError as DjangoValidationError,
)

from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions.role_permission import IsPastor
from apps.members.permissions.member_permission import CanAccessMembers
from apps.members.selectors.member_selector import get_members_for_user
from apps.members.serializers.member_detail_serializer import (
    MemberDetailSerializer,
)
from apps.members.serializers.member_serializer import (
    MemberCreateSerializer,
    MemberListSerializer,
    MemberTransferSerializer,
    MemberUpdateSerializer,
)
from apps.members.services.member_service import (
    MemberVersionConflict,
    create_member,
    update_member,
)
from apps.members.services.member_transfer_service import transfer_member


class MemberConflict(APIException):
    """Return HTTP 409 when a member update uses a stale version."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "The member record has changed. Please refresh and try again."
    default_code = "member_version_conflict"


def _raise_service_error(exc):
    """Translate service-layer exceptions into REST API errors."""

    if isinstance(exc, MemberVersionConflict):
        raise MemberConflict() from exc

    if isinstance(exc, DjangoValidationError):
        detail = getattr(exc, "message_dict", None) or exc.messages
        raise ValidationError(detail)

    if isinstance(exc, (DjangoPermissionDenied, PermissionError)):
        raise PermissionDenied(str(exc))

    raise exc


def _get_member_or_404(request, member_id):
    """
    Retrieve a member only from the requesting user's accessible queryset.

    Returning 404 for inaccessible members avoids revealing their existence.
    """

    members = get_members_for_user(request.user)
    member = members.filter(pk=member_id).first()

    if member is None:
        raise NotFound("Member not found.")

    return member


class MemberPagination(PageNumberPagination):
    """Standard page-number pagination for member listings."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class MemberListCreateView(APIView):
    """
    List accessible members or create a new member.

    Pastor:
        Can access members in all active zones.

    Zone Leader:
        Can access members in currently assigned active zones.
    """

    permission_classes = [CanAccessMembers]

    def get(self, request):
        search = request.query_params.get("search")
        zone_id = request.query_params.get("zone_id")

        if zone_id:
            try:
                zone_id = uuid.UUID(zone_id)
            except (ValueError, TypeError, AttributeError):
                raise ValidationError({"zone_id": "A valid UUID is required."})

        members = get_members_for_user(
            request.user,
            search=search,
            zone_id=zone_id,
        )

        paginator = MemberPagination()
        page = paginator.paginate_queryset(
            members,
            request,
            view=self,
        )

        serializer = MemberListSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = MemberCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            member = create_member(
                actor=request.user,
                **serializer.validated_data,
            )
        except (
            DjangoValidationError,
            DjangoPermissionDenied,
            PermissionError,
        ) as exc:
            _raise_service_error(exc)

        return Response(
            MemberDetailSerializer(member).data,
            status=status.HTTP_201_CREATED,
        )


class MemberDetailView(APIView):
    """
    Retrieve or update a member within the user's authorised zone scope.
    """

    permission_classes = [CanAccessMembers]

    def get(self, request, member_id):
        member = _get_member_or_404(request, member_id)
        self.check_object_permissions(request, member)

        serializer = MemberDetailSerializer(member)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request, member_id):
        member = _get_member_or_404(request, member_id)
        self.check_object_permissions(request, member)

        serializer = MemberUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = dict(serializer.validated_data)
        expected_version = validated_data.pop("expected_version")

        try:
            updated_member = update_member(
                member=member,
                actor=request.user,
                expected_version=expected_version,
                **validated_data,
            )
        except (
            MemberVersionConflict,
            DjangoValidationError,
            DjangoPermissionDenied,
            PermissionError,
        ) as exc:
            _raise_service_error(exc)

        return Response(
            MemberDetailSerializer(updated_member).data,
            status=status.HTTP_200_OK,
        )


class MemberTransferView(APIView):
    """
    Transfer a member to another active zone.

    Only users with an active Pastor role may perform transfers.
    """

    permission_classes = [IsPastor]

    def post(self, request, member_id):
        member = _get_member_or_404(request, member_id)

        serializer = MemberTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_member = transfer_member(
                member=member,
                actor=request.user,
                **serializer.validated_data,
            )
        except (
            MemberVersionConflict,
            DjangoValidationError,
            DjangoPermissionDenied,
            PermissionError,
        ) as exc:
            _raise_service_error(exc)

        return Response(
            MemberDetailSerializer(updated_member).data,
            status=status.HTTP_200_OK,
        )
