from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer, UserCreateSerializer

User = get_user_model()


class IsAuthenticatedOrCreate(BasePermission):
    """Allow unauthenticated access for create/register, authenticated for others"""

    def has_permission(self, request, view):
        if view.action in ["create", "register", "list"]:
            return True
        return request.user and request.user.is_authenticated


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedOrCreate]

    def get_permissions(self):
        if self.action in ["register", "login"]:
            return [AllowAny()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    # TODO: fix permission classes for register action
    @action(detail=False, methods=["post"])
    def register(self, request):
        """Register a new user with profile details"""
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "user": UserSerializer(user).data,
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=["post"])
    def verify_email(self, request):
        """Verify user's email by sending a one-time token to the user's email address"""
        email = request.data.get("email")
        random_token = get_random_string(length=6)
        if not email:
            return Response(
                {"detail": "Email is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"detail": "User with this email does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )
        # Here you would send the random_token to the user's email address
        # For example, using Django's send_mail function or any email service
        send_mail(
            'Your verification token',
            f'Your verification token is: {random_token}',
            'from@example.com',
            [email],
            fail_silently=False,
        )
        return Response(
            {"detail": "Verification token sent to email"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def login(self, request):
        """Login user and return JWT token"""
        from django.contrib.auth import authenticate

        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "user": UserSerializer(user).data,
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
        )

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Get current user's profile"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
