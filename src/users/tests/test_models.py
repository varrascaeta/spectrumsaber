# Standard imports
import pytest

# Django imports
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save

# Project imports
from src.users.signals import auto_verify_user

User = get_user_model()


@pytest.fixture
def disconnect_signals():
    """Fixture to temporarily disconnect signals during setup"""
    post_save.disconnect(auto_verify_user, sender=User)
    yield
    post_save.connect(auto_verify_user, sender=User)


@pytest.mark.django_db
class TestUserModel:
    """Test SpectrumsaberUser model"""

    def test_user_str_representation(self):
        """Test user string representation"""
        user = User.objects.create_user(
            username="struser",
            email="str@example.com",
            password="testpass123",
        )
        assert str(user) == "struser"

    def test_user_username_field(self):
        """Test USERNAME_FIELD is username"""
        assert User.USERNAME_FIELD == "username"

    def test_user_email_field(self):
        """Test EMAIL_FIELD is email"""
        assert User.EMAIL_FIELD == "email"

    def test_user_required_fields(self):
        """Test REQUIRED_FIELDS includes email, first_name, last_name"""
        required = User.REQUIRED_FIELDS
        assert "email" in required
        assert "first_name" in required
        assert "last_name" in required

    def test_user_creation_with_all_fields(self):
        """Test user creation with all required fields"""
        user = User.objects.create_user(
            username="fulluser",
            email="full@example.com",
            password="testpass123",
            first_name="Full",
            last_name="User",
        )

        assert user.username == "fulluser"
        assert user.email == "full@example.com"
        assert user.first_name == "Full"
        assert user.last_name == "User"
        assert user.check_password("testpass123")

    def test_user_is_authenticated(self):
        """Test that created user is authenticated"""
        user = User.objects.create_user(
            username="authuser",
            email="auth@example.com",
            password="testpass123",
        )
        assert user.is_authenticated is True

    def test_user_is_not_staff_by_default(self):
        """Test that regular user is not staff by default"""
        user = User.objects.create_user(
            username="regularuser",
            email="regular@example.com",
            password="testpass123",
        )
        assert user.is_staff is False

    def test_superuser_is_staff(self):
        """Test that superuser is staff"""
        superuser = User.objects.create_superuser(
            username="superuser",
            email="super@example.com",
            password="superpass123",
        )
        assert superuser.is_staff is True
        assert superuser.is_superuser is True
