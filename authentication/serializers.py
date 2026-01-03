from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""

    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)
