from rest_framework import serializers
from .models import OTP


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""

    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)


class LogoutSerializer(serializers.Serializer):
    """Serializer for user logout"""

    refresh = serializers.CharField(required=True)


class OTPSerializer(serializers.ModelSerializer):
    """Serializer for OTP model"""

    class Meta:
        model = OTP
        fields = ["email"]


class OTPVerificationSerializer(serializers.Serializer):
    """Serializer for OTP verification"""

    email = serializers.EmailField(required=True)
    token = serializers.CharField(required=True)
