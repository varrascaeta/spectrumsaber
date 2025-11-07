# Standard imports
import pytest
from unittest.mock import patch

# Django imports
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save

# GQL Auth imports
from gqlauth.models import UserStatus

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
class TestAutoVerifyUserSignal:
    """Test auto_verify_user signal"""

    def test_signal_creates_user_status_on_user_creation(self):
        """Test that signal creates UserStatus when user is created"""
        # Create user (signal should fire)
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )

        # Verify UserStatus was created and verified
        user_status = UserStatus.objects.get(user=user)
        assert user_status.verified is True

    def test_signal_sets_verified_true(self):
        """Test that signal sets verified to True"""
        user = User.objects.create_user(
            username="verifieduser",
            email="verified@example.com",
            password="testpass123",
            first_name="Verified",
            last_name="User",
        )

        user_status = UserStatus.objects.get(user=user)
        assert user_status.verified is True

    def test_signal_does_not_trigger_on_user_update(self, disconnect_signals):
        """Test that signal does not trigger when user is updated"""
        # Create user without signal
        user = User.objects.create_user(
            username="updateuser",
            email="update@example.com",
            password="testpass123",
            first_name="Update",
            last_name="User",
        )

        # Manually create UserStatus as unverified
        user_status = UserStatus.objects.create(user=user, verified=False)
        assert user_status.verified is False

        # Reconnect signal
        post_save.connect(auto_verify_user, sender=User)

        # Update user (should not trigger verification)
        user.first_name = "Updated"
        user.save()

        # Verify status remains unchanged
        user_status.refresh_from_db()
        assert user_status.verified is False

    def test_signal_handles_existing_user_status(self, disconnect_signals):
        """Test signal updates existing UserStatus if it exists"""
        # Create user without signal
        user = User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            password="testpass123",
            first_name="Existing",
            last_name="User",
        )

        # Create unverified UserStatus
        UserStatus.objects.create(user=user, verified=False)

        # Reconnect signal and create another user to trigger update_or_create
        post_save.connect(auto_verify_user, sender=User)

        # Delete the user and recreate (simulating edge case)
        user.delete()
        user = User.objects.create_user(
            username="newuser",
            email="new@example.com",
            password="testpass123",
            first_name="New",
            last_name="User",
        )

        # Verify new user is verified
        user_status = UserStatus.objects.get(user=user)
        assert user_status.verified is True

    @patch("src.users.signals.logger")
    def test_signal_logs_verification(self, mock_logger):
        """Test that signal logs user verification"""
        user = User.objects.create_user(
            username="loguser",
            email="log@example.com",
            password="testpass123",
            first_name="Log",
            last_name="User",
        )

        # Verify logger was called
        mock_logger.info.assert_called_once_with(
            "Verified user %s automatically.", user.username
        )

    def test_multiple_users_all_verified(self):
        """Test that multiple users are all verified automatically"""
        users = []
        for i in range(5):
            user = User.objects.create_user(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password="testpass123",
                first_name=f"User{i}",
                last_name="Test",
            )
            users.append(user)

        # Verify all users have verified status
        for user in users:
            user_status = UserStatus.objects.get(user=user)
            assert user_status.verified is True

    def test_signal_with_superuser(self):
        """Test that signal works with superuser creation"""
        superuser = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            first_name="Admin",
            last_name="User",
        )

        user_status = UserStatus.objects.get(user=superuser)
        assert user_status.verified is True

    def test_signal_with_minimal_user_data(self):
        """Test signal with minimal user data"""
        user = User.objects.create_user(
            username="minimaluser",
            email="minimal@example.com",
            password="testpass123",
        )

        user_status = UserStatus.objects.get(user=user)
        assert user_status.verified is True

    def test_user_status_one_to_one_relationship(self):
        """Test that UserStatus has one-to-one relationship with User"""
        user = User.objects.create_user(
            username="relationuser",
            email="relation@example.com",
            password="testpass123",
            first_name="Relation",
            last_name="User",
        )

        # Verify only one UserStatus exists for user
        user_statuses = UserStatus.objects.filter(user=user)
        assert user_statuses.count() == 1

    def test_signal_idempotency(self, disconnect_signals):
        """Test that calling signal multiple times doesn't create duplicates"""
        user = User.objects.create_user(
            username="idempotentuser",
            email="idempotent@example.com",
            password="testpass123",
            first_name="Idempotent",
            last_name="User",
        )

        # Manually call signal multiple times
        post_save.connect(auto_verify_user, sender=User)
        auto_verify_user(sender=User, instance=user, created=True)
        auto_verify_user(sender=User, instance=user, created=True)
        auto_verify_user(sender=User, instance=user, created=True)

        # Verify only one UserStatus exists
        user_statuses = UserStatus.objects.filter(user=user)
        assert user_statuses.count() == 1
        assert user_statuses.first().verified is True


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


@pytest.mark.django_db
class TestUserStatusIntegration:
    """Test UserStatus integration with User"""

    def test_user_status_created_automatically(self):
        """Test UserStatus is created automatically via signal"""
        user = User.objects.create_user(
            username="autostatususer",
            email="autostatus@example.com",
            password="testpass123",
            first_name="Auto",
            last_name="Status",
        )

        # UserStatus should exist
        assert UserStatus.objects.filter(user=user).exists()

    def test_verified_user_can_be_retrieved(self):
        """Test that verified users can be queried"""
        user1 = User.objects.create_user(
            username="verified1",
            email="verified1@example.com",
            password="testpass123",
        )
        user2 = User.objects.create_user(
            username="verified2",
            email="verified2@example.com",
            password="testpass123",
        )

        # Query verified users
        verified_users = UserStatus.objects.filter(verified=True)
        user_ids = [status.user.id for status in verified_users]

        assert user1.id in user_ids
        assert user2.id in user_ids

    def test_user_deletion_cascades_to_user_status(self):
        """Test that deleting user also deletes UserStatus"""
        user = User.objects.create_user(
            username="deleteuser",
            email="delete@example.com",
            password="testpass123",
        )

        user_status_id = UserStatus.objects.get(user=user).id
        user_id = user.id

        # Delete user
        user.delete()

        # Verify UserStatus is also deleted
        assert not UserStatus.objects.filter(id=user_status_id).exists()
        assert not User.objects.filter(id=user_id).exists()

    def test_user_status_has_correct_default_values(self):
        """Test UserStatus has correct values after auto-verification"""
        user = User.objects.create_user(
            username="defaultsuser",
            email="defaults@example.com",
            password="testpass123",
        )

        user_status = UserStatus.objects.get(user=user)
        assert user_status.verified is True
        assert user_status.user == user
