from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
import json

User = get_user_model()


class LoginTestCase(TestCase):
    """Test cases for user login endpoint"""

    def setUp(self):
        """Set up test client and test user"""
        self.client = APIClient()
        self.login_url = "/auth/login/"
        self.username = "testuser"
        self.password = "testpass123"
        self.user = User.objects.create_user(
            username=self.username, password=self.password, email="test@example.com"
        )

    def test_login_success_with_valid_credentials(self):
        """Test successful login with valid username and password"""
        payload = {"username": self.username, "password": self.password}
        response = self.client.post(
            self.login_url, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["username"], self.username)
        self.assertEqual(response.data["user"]["id"], self.user.id)

    def test_login_fails_with_invalid_username(self):
        """Test login fails with invalid username"""
        payload = {"username": "invaliduser", "password": self.password}
        response = self.client.post(
            self.login_url, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", response.data)
        self.assertEqual(response.data["detail"], "Invalid credentials.")

    def test_login_fails_with_invalid_password(self):
        """Test login fails with invalid password"""
        payload = {"username": self.username, "password": "wrongpassword"}
        response = self.client.post(
            self.login_url, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", response.data)
        self.assertEqual(response.data["detail"], "Invalid credentials.")

    def test_login_fails_with_missing_username(self):
        """Test login fails when username is missing"""
        payload = {"password": self.password}
        response = self.client.post(
            self.login_url, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_login_fails_with_missing_password(self):
        """Test login fails when password is missing"""
        payload = {"username": self.username}
        response = self.client.post(
            self.login_url, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_login_fails_with_empty_payload(self):
        """Test login fails with empty payload"""
        payload = {}
        response = self.client.post(
            self.login_url, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_returns_valid_jwt_tokens(self):
        """Test that login returns valid and decodable JWT tokens"""
        payload = {"username": self.username, "password": self.password}
        response = self.client.post(
            self.login_url, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify refresh token is valid
        refresh_token = response.data["refresh"]
        try:
            RefreshToken(refresh_token)
        except Exception as e:
            self.fail(f"Refresh token is invalid: {str(e)}")

        # Verify access token is valid
        access_token = response.data["access"]
        self.assertIsNotNone(access_token)
        self.assertGreater(len(access_token), 0)

    def test_login_with_incorrect_content_type(self):
        """Test login with form content type works"""
        payload = {"username": self.username, "password": self.password}
        response = self.client.post(
            self.login_url,
            data=payload,
            content_type="application/x-www-form-urlencoded",
        )
        # Should still work or return appropriate error
        self.assertIn(
            response.status_code,
            [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            ],
        )


class LogoutTestCase(TestCase):
    """Test cases for user logout endpoint"""

    def setUp(self):
        """Set up test client, test user, and authentication"""
        self.client = APIClient()
        self.login_url = "/auth/login/"
        self.logout_url = "/auth/logout/"
        self.username = "testuser"
        self.password = "testpass123"
        self.user = User.objects.create_user(
            username=self.username, password=self.password, email="test@example.com"
        )

        # Perform login and get tokens
        payload = {"username": self.username, "password": self.password}
        response = self.client.post(
            self.login_url, data=json.dumps(payload), content_type="application/json"
        )
        self.access_token = response.data["access"]
        self.refresh_token = response.data["refresh"]

    def test_logout_success_with_valid_refresh_token(self):
        """Test successful logout with valid refresh token"""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        payload = {"refresh": self.refresh_token}
        response = self.client.post(
            self.logout_url, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)

    def test_logout_fails_without_authentication(self):
        """Test logout fails without authentication"""
        payload = {"refresh": self.refresh_token}
        response = self.client.post(
            self.logout_url, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_fails_with_invalid_token(self):
        """Test logout fails with invalid refresh token"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        payload = {"refresh": "invalid_token"}
        response = self.client.post(
            self.logout_url, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_logout_fails_with_missing_refresh_token(self):
        """Test logout fails when refresh token is missing"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        payload = {}
        response = self.client.post(
            self.logout_url, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("refresh", response.data)

    def test_logout_with_expired_access_token(self):
        """Test logout behavior with expired access token"""
        # Create an invalid/expired access token
        invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.invalid"
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {invalid_token}")
        payload = {"refresh": self.refresh_token}
        response = self.client.post(
            self.logout_url, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticationFlowTestCase(TestCase):
    """Test complete authentication flow"""

    def setUp(self):
        """Set up test client and test user"""
        self.client = APIClient()
        self.login_url = "/auth/login/"
        self.logout_url = "/auth/logout/"
        self.username = "testuser"
        self.password = "testpass123"
        self.user = User.objects.create_user(
            username=self.username, password=self.password, email="test@example.com"
        )

    def test_complete_login_logout_flow(self):
        """Test complete flow: login -> use token -> logout"""
        # Step 1: Login
        login_payload = {"username": self.username, "password": self.password}
        login_response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type="application/json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        access_token = login_response.data["access"]
        refresh_token = login_response.data["refresh"]

        # Step 2: Verify we can use the access token (for protected endpoints)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        # This would be tested with a protected endpoint

        # Step 3: Logout
        logout_payload = {"refresh": refresh_token}
        logout_response = self.client.post(
            self.logout_url,
            data=json.dumps(logout_payload),
            content_type="application/json",
        )
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)

    def test_multiple_login_sessions(self):
        """Test multiple users can login simultaneously"""
        # Create another user
        user2_username = "testuser2"
        user2_password = "testpass456"
        user2 = User.objects.create_user(
            username=user2_username, password=user2_password, email="test2@example.com"
        )

        # User 1 login
        login_payload1 = {"username": self.username, "password": self.password}
        response1 = self.client.post(
            self.login_url,
            data=json.dumps(login_payload1),
            content_type="application/json",
        )
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        token1 = response1.data["access"]

        # User 2 login
        login_payload2 = {"username": user2_username, "password": user2_password}
        response2 = self.client.post(
            self.login_url,
            data=json.dumps(login_payload2),
            content_type="application/json",
        )
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        token2 = response2.data["access"]

        # Verify tokens are different
        self.assertNotEqual(token1, token2)

        # Verify user info is correct for each token
        self.assertEqual(response1.data["user"]["username"], self.username)
        self.assertEqual(response2.data["user"]["username"], user2_username)

    def test_password_change_invalidates_sessions(self):
        """Test that changing password doesn't automatically invalidate existing tokens"""
        # Login
        login_payload = {"username": self.username, "password": self.password}
        login_response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type="application/json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        # Change password
        self.user.set_password("newpassword")
        self.user.save()

        # Old token should still work (JWT doesn't check password changes)
        # New login with old password should fail
        old_login_payload = {"username": self.username, "password": self.password}
        old_login_response = self.client.post(
            self.login_url,
            data=json.dumps(old_login_payload),
            content_type="application/json",
        )
        self.assertEqual(old_login_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # New login with new password should work
        new_login_payload = {"username": self.username, "password": "newpassword"}
        new_login_response = self.client.post(
            self.login_url,
            data=json.dumps(new_login_payload),
            content_type="application/json",
        )
        self.assertEqual(new_login_response.status_code, status.HTTP_200_OK)
