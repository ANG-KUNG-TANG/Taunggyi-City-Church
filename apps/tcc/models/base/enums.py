from django.db import models
from django.utils.translation import gettext_lazy as _

class UserRole(models.TextChoices):
    SUPER_ADMIN = "super_admin", _("Super Administrator")
    STAFF = "staff", _("Staff")
    MINISTRY_LEADER = "ministry_leader", _("Ministry Leader")
    MEMBER = "member", _("Member")
    VISITOR = "visitor", _("Visitor")


class UserStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    INACTIVE = "inactive", _("Inactive")
    PENDING = "pending", _("Pending Approval")
    SUSPENDED = "suspended", _("Suspended")


class Gender(models.TextChoices):
    MALE = "male", _("Male")
    FEMALE = "female", _("Female")
    OTHER = "other", _("Other")
    PREFER_NOT_TO_SAY = "prefer_not_to_say", _("Prefer not to say")


class MaritalStatus(models.TextChoices):
    SINGLE = "single", _("Single")
    MARRIED = "married", _("Married")
    DIVORCED = "divorced", _("Divorced")
    WIDOWED = "widowed", _("Widowed")
    SEPARATED = "separated", _("Separated")


class DonationStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    COMPLETED = "completed", _("Completed")
    FAILED = "failed", _("Failed")
    REFUNDED = "refunded", _("Refunded")


class PaymentMethod(models.TextChoices):
    CASH = "cash", _("Cash")
    CHECK = "check", _("Check")
    CREDIT_CARD = "credit_card", _("Credit Card")
    DEBIT_CARD = "debit_card", _("Debit Card")
    BANK_TRANSFER = "bank_transfer", _("Bank Transfer")
    ONLINE = "online", _("Online")


class PrayerPrivacy(models.TextChoices):
    PUBLIC = "public", _("Public")
    CONGREGATION = "congregation", _("Congregation Only")
    LEADERS_ONLY = "leaders_only", _("Leaders Only")
    PRIVATE = "private", _("Private")


class PrayerCategory(models.TextChoices):
    HEALING = "healing", _("Healing")
    GUIDANCE = "guidance", _("Guidance")
    THANKSGIVING = "thanksgiving", _("Thanksgiving")
    FINANCIAL = "financial", _("Financial")
    FAMILY = "family", _("Family")
    OTHER = "other", _("Other")
    GENERAL = "general", _('General')

class PrayerStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    ANSWERED = "answered", _("Answered")
    EXPIRED = "expired", _("Expired")


class EventStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    PUBLISHED = "published", _("Published")
    CANCELLED = "cancelled", _("Cancelled")
    COMPLETED = "completed", _("Completed")
    UPCOMING = 'Upcoming',_('Upcoming')


class EventType(models.TextChoices):
    SERVICE = "service", _("Church Service")
    MEETING = "meeting", _("Meeting")
    STUDY_GROUP = "study_group", _("Study Group")
    SOCIAL = "social", _("Social Event")
    VOLUNTEER = "volunteer", _("Volunteer Event")
    YOUTH = "youth", _("Youth Event")
    PRAYER = "prayer", _("Prayer Meeting")


class RegistrationStatus(models.TextChoices):
    REGISTERED = "registered", _("Registered")
    WAITLISTED = "waitlisted", _("Waitlisted")
    CANCELLED = "cancelled", _("Cancelled")
    CHECKED_IN = "checked_in", _("Checked In")
    PENDING = "pending", _("Pending")


class SermonStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    PUBLISHED = "published", _("Published")
    ARCHIVED = "archived", _("Archived")


class MediaType(models.TextChoices):
    AUDIO = "audio", _("Audio")
    VIDEO = "video", _("Video")
    DOCUMENT = "document", _("Document")
    IMAGE = "image", _("Image")


class FamilyRole(models.TextChoices):
    HEAD = "head", _("Head of Household")
    SPOUSE = "spouse", _("Spouse")
    CHILD = "child", _("Child")
    PARENT = "parent", _("Parent")
    OTHER = "other", _("Other Relative")


# Utility functions for enums
def get_choice_display(choices, value):
    """Get human-readable display value for a choice"""
    return dict(choices.choices).get(value, value)

def get_choice_keys(choices):
    """Get all keys for a choices enum"""
    return [choice[0] for choice in choices.choices]