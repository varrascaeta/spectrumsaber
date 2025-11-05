# users/models.py
from django.contrib.auth.models import AbstractUser


class SpectrumsaberUser(AbstractUser):
    USERNAME_FIELD = "username"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["email", "first_name", "last_name"]

    def __str__(self):
        return self.username
