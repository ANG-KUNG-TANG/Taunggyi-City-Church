from rest_framework_simplejwt.tokens import RefreshToken

class JWTProvider:

    @staticmethod
    def generate_tokens(user):
        refresh = RefreshToken.for_user(user)
        refresh['email'] = user.email
        refresh['role'] = user.role

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }
