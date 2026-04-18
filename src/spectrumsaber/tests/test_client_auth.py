# Standard imports
from unittest.mock import Mock, patch

# Third-party imports
import pytest

# Project imports
from spectrumsaber.cfg import GRAPHQL_JWT_TOKEN
from spectrumsaber.client import SpectrumSaberClient


@pytest.fixture
def mock_requests():
    """Create a mock for requests module"""
    with patch("spectrumsaber.client.requests") as mock_req:
        yield mock_req


@pytest.fixture
def saber_client():
    """Create a SpectrumSaberClient instance"""
    return SpectrumSaberClient()


class TestSpectrumSaberClientAuth:
    """
    Test SpectrumSaberClient initialization, headers, login and auth methods
    """

    def test_saber_client_initialization(self, saber_client):
        """Test SpectrumSaberClient initializes with None tokens"""
        assert saber_client.__token__ == GRAPHQL_JWT_TOKEN
        assert saber_client.__refresh_token__ is None
        assert saber_client.user is None

    def test_get_headers_without_token(self, saber_client):
        """Test __get_headers__ returns basic headers without token"""
        saber_client.__token__ = None
        headers = saber_client.__get_headers__()
        assert headers == {"Content-Type": "application/json"}

    def test_get_headers_with_token(self, saber_client):
        """Test __get_headers__ includes JWT token when available"""
        saber_client.__token__ = "test_token_123"
        headers = saber_client.__get_headers__()
        assert headers == {
            "Content-Type": "application/json",
            "Authorization": "JWT test_token_123",
        }

    def test_login_success(self, saber_client, mock_requests):
        """Test login authenticates user successfully"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "tokenAuth": {
                    "success": True,
                    "token": {"token": "auth_token_123"},
                    "refreshToken": {"token": "refresh_token_456"},
                }
            }
        }
        mock_requests.post.return_value = mock_response

        saber_client.login("testuser", "testpassword")

        assert saber_client.__token__ == "auth_token_123"
        assert saber_client.__refresh_token__ == "refresh_token_456"

    def test_login_failure(self, saber_client, mock_requests):
        """Test login handles authentication failure"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {"tokenAuth": {"success": False}},
            "errors": [{"message": "Invalid credentials"}],
        }
        mock_requests.post.return_value = mock_response

        saber_client.login("baduser", "badpassword")

        assert saber_client.__token__ is None
        assert saber_client.__refresh_token__ is None

    def test_login_handles_missing_tokenAuth(
        self, saber_client, mock_requests
    ):
        """Test login handles missing tokenAuth in response"""
        mock_response = Mock()
        mock_response.json.return_value = {"data": {}}
        mock_requests.post.return_value = mock_response
        saber_client.login("user", "pass")
        assert saber_client.__token__ is None
        assert saber_client.__refresh_token__ is None

    def test_login_handles_missing_token_and_refresh(
        self, saber_client, mock_requests
    ):
        """Test login handles missing token and refreshToken fields"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {"tokenAuth": {"success": True}}
        }
        mock_requests.post.return_value = mock_response
        saber_client.login("user", "pass")
        assert saber_client.__token__ is None
        assert saber_client.__refresh_token__ is None

    def test_login_handles_errors_field(self, saber_client, mock_requests):
        """Test login logs error when errors field is present"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {"tokenAuth": {"success": False}},
            "errors": [{"message": "Some error"}],
        }
        mock_requests.post.return_value = mock_response
        saber_client.login("user", "pass")
        assert saber_client.__token__ is None
        assert saber_client.__refresh_token__ is None

    def test_login_with_valid_env_token(self, saber_client, mock_requests):
        """Test login uses existing valid token from environment"""
        saber_client.__token__ = "env_token_123"

        # Mock verify_token to return True
        with patch.object(saber_client, "__verify_token__", return_value=True):
            saber_client.login("testuser", "testpassword")

        # Should not make any mutation request
        mock_requests.post.assert_not_called()
        assert saber_client.__token__ == "env_token_123"

    def test_login_with_invalid_env_token(self, saber_client, mock_requests):
        """Test login proceeds with credentials when env token is invalid"""
        saber_client.__token__ = "invalid_env_token"

        # Mock login response
        login_response = Mock()
        login_response.json.return_value = {
            "data": {
                "tokenAuth": {
                    "success": True,
                    "token": {"token": "new_token_123"},
                    "refreshToken": {"token": "refresh_token_456"},
                }
            }
        }

        mock_requests.post.return_value = login_response

        with patch.object(
            saber_client, "__verify_token__", return_value=False
        ):
            saber_client.login("testuser", "testpassword")

        assert saber_client.__token__ == "new_token_123"
        assert saber_client.__refresh_token__ == "refresh_token_456"
        assert saber_client.updated_token is True

    def test_logout_clears_tokens(self, saber_client):
        """Test logout clears all authentication data"""
        saber_client.__token__ = "token_123"
        saber_client.__refresh_token__ = "refresh_token_456"
        saber_client.user = "testuser"

        saber_client.logout()

        assert saber_client.__token__ is None
        assert saber_client.__refresh_token__ is None
        assert saber_client.user is None

    def test_is_authenticated_returns_true_with_token(self, saber_client):
        """Test is_authenticated returns True when token exists"""
        saber_client.__token__ = "token_123"
        assert saber_client.is_authenticated() is True

    def test_is_authenticated_returns_false_without_token(self, saber_client):
        """Test is_authenticated returns False without token"""
        saber_client.__token__ = None
        assert saber_client.is_authenticated() is False

    def test_get_token_returns_token(self, saber_client):
        """Test get_token returns current token"""
        saber_client.__token__ = "token_123"
        assert saber_client.get_token() == "token_123"

    def test_get_token_returns_none_when_not_authenticated(self, saber_client):
        """Test get_token returns None when not authenticated"""
        saber_client.__token__ = None
        assert saber_client.get_token() is None

    def test_text2gql_returns_text2gql_instance(self, saber_client):
        """Test text2gql returns a configured Text2GQL instance"""
        from spectrumsaber.text2gql import Text2GQL

        mock_llm = Mock()
        t2gql = saber_client.text2gql(mock_llm)
        assert isinstance(t2gql, Text2GQL)
        assert t2gql.client is saber_client
        assert t2gql.llm is mock_llm

    def test_text2gql_cache_schema_forwarded(self, saber_client):
        """Test text2gql forwards cache_schema flag"""
        from spectrumsaber.text2gql import Text2GQL

        mock_llm = Mock()
        t2gql = saber_client.text2gql(mock_llm, cache_schema=False)
        assert isinstance(t2gql, Text2GQL)
        assert t2gql._cache_schema is False
