from apps.church_info.models.church_information import ChurchInformation


def get_published_church_information():
    """
    Retrieve the single church-information record only if it is published.

    Returns:
        ChurchInformation | None: The published record, or None.
    """
    return ChurchInformation.objects.filter(
        pk=1,
        is_published=True,
    ).first()
