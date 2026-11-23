from apps.church_info.models.church_information import ChurchInformation
from rest_framework import serializers


class PublicChurchInformationSerializer(serializers.ModelSerializer):
    """
    Serialize approved public church information only.
    """

    class Meta:
        model = ChurchInformation
        fields = [
            "church_name",
            "description",
            "address",
            "phone",
            "email",
            "website",
            "service_times",
            "social_links",
            "updated_at",
        ]
        read_only_fields = fields
