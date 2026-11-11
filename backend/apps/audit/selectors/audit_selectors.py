"""Database selectors for audit history."""

from apps.audit.models.audit_log import AuditLog


FINANCIAL_ENTITY_TYPES = (
    "Donation",
    "FundTransaction",
    "FinancialAdjustment",
)


def get_financial_audit_history(filters=None):
    """Return audit events belonging exclusively to financial entities."""

    filters = filters or {}

    queryset = AuditLog.objects.filter(
        entity_type__in=FINANCIAL_ENTITY_TYPES,
    ).select_related("actor")

    if filters.get("entity_type"):
        queryset = queryset.filter(entity_type=filters["entity_type"])

    if filters.get("entity_id"):
        queryset = queryset.filter(entity_id=filters["entity_id"])

    if filters.get("actor_id"):
        queryset = queryset.filter(actor_id=filters["actor_id"])

    if filters.get("action"):
        queryset = queryset.filter(action=filters["action"])

    if filters.get("correlation_id"):
        queryset = queryset.filter(
            correlation_id=filters["correlation_id"],
        )

    if filters.get("start_date"):
        queryset = queryset.filter(
            occurred_at__date__gte=filters["start_date"],
        )

    if filters.get("end_date"):
        queryset = queryset.filter(
            occurred_at__date__lte=filters["end_date"],
        )

    return queryset.order_by("-occurred_at", "-id")
