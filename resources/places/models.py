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

    class Meta:
        verbose_name_plural = "Countries"


class Province(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=8, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="provinces"
    )

    def __str__(self) -> str:
        return f"{self.name} ({self.code})" if self.code else self.name


class District(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=16, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    province = models.ForeignKey(
        Province,
        on_delete=models.CASCADE,
        related_name="districts"
    )

    def __str__(self) -> str:
        return f"{self.name} ({self.code})" if self.code else self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "province"],
                name="unique_district"
            )
        ]
