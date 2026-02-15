import email
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import JSONParser
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta

from .models import OTP
from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    OTPSerializer,
    OTPVerificationSerializer,
)


class AuthenticationViewSet(viewsets.ViewSet):
    """Handle authentication including login, logout, and OTP"""

    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        """Handle user login and return JWT tokens"""
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        username = serializer.validated_data.get("username")
        password = serializer.validated_data.get("password")

        user = get_user_model().objects.filter(username=username).first()
        if user and user.check_password(password):
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user": {
                        "id": user.id,
                        "username": user.username,
                    },
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="logout",
        permission_classes=[IsAuthenticated],
    )
    def logout(self, request):
        """
        Handle user logout by blacklisting JWT refresh tokens.

        Requires authentication to access this endpoint.

        Request body:\n
            - refresh: JWT refresh token to blacklist (required)\n
        Response:\n
            - detail: Success or error message
        """
        try:

            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"detail": "Logout successful."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["post"], url_path="request-otp")
    def request_otp(self, request):
        """Request an OTP to be sent to email"""

        email = request.data.get("email")
        if not email:
            return Response(
                {"detail": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Rate limiting: Check if OTP was requested recently
        otp = OTP.objects.filter(email=email).first()
        if otp and otp.created_at > timezone.now() - timedelta(minutes=1):
            return Response(
                {"detail": "OTP already sent. Please wait before requesting another."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Create or regenerate OTP
        otp, created = OTP.objects.get_or_create(email=email)
        if not created:
            otp.token = OTP.generate_token()
            otp.created_at = timezone.now()  # Reset timestamp
            otp.save()

        # Send email
        try:
            send_mail(
                subject="Your Grupus OTP Token",
                message=f"Your OTP token is: {otp.token}",
                from_email="noreply@grupus.com",
                recipient_list=[email],
                fail_silently=False,
            )
            return Response(
                {"detail": "OTP sent to your email."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"detail": "Failed to send OTP. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="verify-otp")
    def verify_otp(self, request):
        """Verify an OTP token"""

        email = request.data.get("email")
        token = request.data.get("token")

        if not email or not token:
            return Response(
                {"detail": "Email and token are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # DEBUG: Check what exists for this email
        otp_record = OTP.objects.filter(email=email).first()
        if otp_record:
            print(f"Found OTP for {email}")
            print(f"Stored token: {otp_record.token} (type: {type(otp_record.token)})")
            print(f"Received token: {token} (type: {type(token)})")
            print(f"Converted token: {int(token)} (type: {type(int(token))})")
            print(f"Tokens match: {otp_record.token == int(token)}")
            print(f"Is expired: {otp_record.is_expired()}")
            print(f"Expires at: {otp_record.expires_at}")
            print(f"Current time: {timezone.now()}")
        else:
            print(f"No OTP found for email: {email}")

        otp = OTP.objects.filter(email=email, token=int(token)).first()

        if otp and not otp.is_expired():
            return Response(
                {"detail": "OTP is valid."},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"detail": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )
