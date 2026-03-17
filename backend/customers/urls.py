from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Frontend'deki LOGIN_ENDPOINT için
    path('auth/login/', views.LoginView.as_view(), name='api-login'),
    
    # Frontend'deki LOGOUT_ENDPOINT için
    path('auth/logout/', views.LogoutView.as_view(), name='api-logout'),
    
    # Frontend'deki SESSION/ME endpointleri
    path('auth/session/', views.SessionView.as_view(), name='api-session'),
    path('auth/me/', views.SessionView.as_view(), name='api-me'),

    path('auth/refresh/', TokenRefreshView.as_view(), name='api-refresh-token'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='api-token-refresh'),
    
    # Frontend'deki CSRF_ENDPOINT için
    path('auth/csrf/', views.get_csrf_token, name='api-set-csrf'),
]