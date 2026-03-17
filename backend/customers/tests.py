import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from customers.views import LoginView, LogoutView, SessionView


class JwtAuthenticationTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='strong-password-123',
        )

    def test_login_returns_access_and_refresh_tokens(self):
        request = self.factory.post(
            '/auth/login/',
            {'username': 'testuser', 'password': 'strong-password-123'},
            format='json',
        )
        response = LoginView.as_view()(request)
        payload = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertIn('access', payload)
        self.assertIn('refresh', payload)

    def test_session_endpoint_requires_and_accepts_jwt(self):
        login_request = self.factory.post(
            '/auth/login/',
            {'username': 'testuser', 'password': 'strong-password-123'},
            format='json',
        )
        login_response = LoginView.as_view()(login_request)
        access_token = json.loads(login_response.content)['access']

        request = self.factory.get(
            '/auth/session/',
            HTTP_AUTHORIZATION=f'Bearer {access_token}',
        )
        response = SessionView.as_view()(request)
        payload = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload['user'], self.user.username)

    def test_logout_blacklists_refresh_token(self):
        login_request = self.factory.post(
            '/auth/login/',
            {'username': 'testuser', 'password': 'strong-password-123'},
            format='json',
        )
        login_response = LoginView.as_view()(login_request)
        payload = json.loads(login_response.content)

        logout_request = self.factory.post(
            '/auth/logout/',
            {'refresh': payload['refresh']},
            format='json',
            HTTP_AUTHORIZATION=f"Bearer {payload['access']}",
        )
        logout_response = LogoutView.as_view()(logout_request)

        self.assertEqual(logout_response.status_code, 200)

        second_logout_request = self.factory.post(
            '/auth/logout/',
            {'refresh': payload['refresh']},
            format='json',
            HTTP_AUTHORIZATION=f"Bearer {payload['access']}",
        )
        second_logout_response = LogoutView.as_view()(second_logout_request)

        self.assertEqual(second_logout_response.status_code, 400)
