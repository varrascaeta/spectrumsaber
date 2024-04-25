# Standard imports
import logging
# Django imports
from django.db import models


logger = logging.getLogger(__name__)


class Country(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=8, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.code})" if self.code else self.name


class City(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=8, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    country = models.ForeignKey(Country, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.name} ({self.code})" if self.code else self.name


class District(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=8, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    city = models.ForeignKey(City, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.name} ({self.code})" if self.code else self.name
