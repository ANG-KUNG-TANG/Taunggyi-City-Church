from rest_framework import serializers

from apps.accounts.models.users import User


class StaffCreateSerializer(serializers.ModelSerializer):
    """
    Validate data required to create a staff account.

    Passwords and role assignments are deliberately excluded.
    """

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
        )

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "An account with this email address already exists."
            )

        return value


class StaffUpdateSerializer(serializers.ModelSerializer):
    """
    Allow authorised administrators to update staff account details.
    """

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "is_active",
        )

    def validate_email(self, value):
        queryset = User.objects.filter(email__iexact=value)

        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "An account with this email address already exists."
            )

        return value


class StaffListSerializer(serializers.ModelSerializer):
    """
    Safe representation for staff account listings.
    """

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "created_at",
        )
        read_only_fields = fields


class StaffDetailSerializer(serializers.ModelSerializer):
    """
    Read-only representation of an individual staff account.
    """

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "created_at",
            "last_login",
        )
        read_only_fields = fields
