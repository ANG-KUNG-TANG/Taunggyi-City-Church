from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers.authentication_serializer import (
    LoginSerializer,
    RefreshSerializer,
)
from apps.accounts.services.authentication_service import (
    AuthenticationService,
)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tokens = AuthenticationService.login(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        return Response(
            tokens,
            status=status.HTTP_200_OK,
        )


class RefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tokens = AuthenticationService.refresh(
            refresh_token=serializer.validated_data["refresh_token"],
        )

        return Response(
            tokens,
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    Logout the currently authenticated session.

    User and session identifiers come from the authenticated request,
    never from client-provided data.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = str(request.user.pk)
        session_id = getattr(request, "session_id", None)

        if not session_id:
            return Response(
                {"detail": "Authenticated session information is missing."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        AuthenticationService.logout(
            user_id=user_id,
            session_id=session_id,
        )

        return Response(
            {"detail": "Successfully logged out."},
            status=status.HTTP_200_OK,
        )
