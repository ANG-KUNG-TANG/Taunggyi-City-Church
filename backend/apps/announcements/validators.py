"""
Validation rules for the Taunggyi City Church announcement module.
"""

from django.core.exceptions import ValidationError


def validate_announcement_content(*, title, body):
    """Validate and normalise announcement title and body."""

    if not isinstance(title, str) or not title.strip():
        raise ValidationError({"title": "Title is required."})

    if len(title.strip()) > 200:
        raise ValidationError({"title": "Title must not exceed 200 characters."})

    if not isinstance(body, str) or not body.strip():
        raise ValidationError({"body": "Announcement body is required."})

    return {
        "title": title.strip(),
        "body": body.strip(),
    }
