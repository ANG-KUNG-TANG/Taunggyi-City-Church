"""
Member query selectors.

Access is restricted by the user's active church role
and current zone assignments.
"""

from django.db.models import Q
from django.utils import timezone

from apps.members.models import Member
from apps.zones.models.zones import Zone


def get_members_for_user(user, search=None, zone_id=None):
    """
    Return Members accessible to the supplied user.

    Pastor:
        Can access Members in all active zones.

    Zone Leader:
        Can access Members in currently assigned active zones.

    Other users:
        Receive an empty queryset.

    Optional filters:
        search: Match Member name or phone.
        zone_id: Restrict results to a specific zone.
    """

    if not user or not user.is_authenticated:
        return Member.objects.none()

    if not user.is_active:
        return Member.objects.none()

    active_roles = user.role_assignments.filter(
        revoked_at__isnull=True,
    ).values_list(
        "role__code",
        flat=True,
    )

    role_codes = set(active_roles)

    if "PASTOR" in role_codes:
        accessible_zones = Zone.objects.filter(
            is_active=True,
        )

    elif "ZONE_LEADER" in role_codes:
        now = timezone.now()

        accessible_zones = (
            Zone.objects.filter(
                is_active=True,
                leader_assignments__user=user,
                leader_assignments__effective_from__lte=now,
            )
            .filter(
                Q(leader_assignments__effective_to__isnull=True)
                | Q(leader_assignments__effective_to__gt=now)
            )
            .distinct()
        )

    else:
        return Member.objects.none()

    members = Member.objects.filter(
        zone__in=accessible_zones,
    )

    if search:
        search = search.strip()

        if search:
            members = members.filter(
                Q(full_name__icontains=search) | Q(phone__icontains=search)
            )

    if zone_id:
        members = members.filter(
            zone_id=zone_id,
        )

    return members.distinct()
