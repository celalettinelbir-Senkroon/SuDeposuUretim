from django.contrib.auth import authenticate
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse, HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

# 1. CSRF Token Sağlayıcı
@ensure_csrf_cookie
def get_csrf_token(request):
    return HttpResponse(status=204)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return JsonResponse({"detail": "Username and password are required."}, status=400)

        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return JsonResponse(
                {
                    "detail": "Successfully logged in.",
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": user.username,
                }
            )
        return JsonResponse({"detail": "Invalid credentials"}, status=400)

# 3. Session Kontrolü
class SessionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return JsonResponse({"isAuthenticated": True, "user": request.user.username})

# 4. Logout İşlemi
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return JsonResponse({"detail": "Refresh token is required."}, status=400)

        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            return JsonResponse({"detail": "Invalid refresh token."}, status=400)

        return JsonResponse({"detail": "Successfully logged out."})