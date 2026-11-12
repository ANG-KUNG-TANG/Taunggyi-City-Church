from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )


class RefreshSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        allow_blank=False,
    )
