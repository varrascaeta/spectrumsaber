# Standard imports
import logging
# Django imports
from django.db import models
from django.utils import timezone
# Project imports
from resources.places.models import District

logger = logging.getLogger(__name__)


# Common utils
class BaseFile(models.Model):
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=255)
    description = models.TextField(null=True)
    date = models.DateField(null=True)
    metadata = models.JSONField(null=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

    @classmethod
    def matches_pattern(cls, filename: str) -> bool:
        raise NotImplementedError

    class Meta:
        abstract = True


# Measurements
class CategoryType():
    RAW_DATA = "Raw Data"
    RADIANCE = "Radiance"
    AVG_RADIANCE = "Average Radiance"
    TXT_RADIANCE = "Text Radiance"
    REFLECTANCE = "Reflectance"
    AVG_REFLECTANCE = "Average Reflectance"
    TXT_REFLECTANCE = "Text Reflectance"

    CHOICES = (
        (RAW_DATA, "RAW"),
        (RADIANCE, "RAD"),
        (AVG_RADIANCE, "AVG_RAD"),
        (TXT_RADIANCE, "TXT_RAD"),
        (REFLECTANCE, "REF"),
        (AVG_REFLECTANCE, "AVG_REF"),
        (TXT_REFLECTANCE, "TXT_REF"),
    )


class Category(models.Model):
    name = models.CharField(max_length=128, choices=CategoryType.CHOICES)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return self.get_name_display()


class Measurement(BaseFile):
    # Relationships
    category = models.ForeignKey(Category, on_delete=models.CASCADE)


class MeasuringTool(models.Model):
    name = models.CharField(max_length=255)
    model_name = models.CharField(max_length=255, null=True)
    fov = models.FloatField(null=True)
    measure_height = models.FloatField(null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return self.name + ' ' + self.model_name


# Campaigns
class Coverage(BaseFile):
    @classmethod
    def matches_pattern(cls, filename: str) -> bool:
        return filename.isupper()


class DataPoint(BaseFile):
    # Fields
    order = models.IntegerField()
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    # Relationships
    campaign = models.ForeignKey(
        'Campaign', on_delete=models.CASCADE, related_name='data_points'
    )
    measurements = models.ManyToManyField(
        Measurement, blank=True, related_name='data_points'
    )


class Campaign(BaseFile):
    # Fields
    external_id = models.CharField(max_length=255, null=True)
    # Relationships
    coverage = models.ForeignKey(
        Coverage, on_delete=models.CASCADE, related_name='coverage_campaigns'
    )
    district = models.ForeignKey(
        District, null=True, on_delete=models.SET_NULL
    )
    measuring_tool = models.ForeignKey(
        MeasuringTool, null=True, related_name='campaigns',
        on_delete=models.SET_NULL
    )
    spreadsheets = models.ManyToManyField(
        'Spreadsheet', blank=True, related_name='campaigns'
    )

    def __str__(self) -> str:
        return f"{self.name} of {self.coverage}"


# Spreadsheets
class SheetType():
    OFFICE = "Office Sheet"
    FIELD = "Field Sheet"

    CHOICES = (
        (OFFICE, "OFC"),
        (FIELD, "FLD"),
    )


class Spreadsheet(BaseFile):
    sheet_type = models.CharField(max_length=16, choices=SheetType.CHOICES)
    delimiter = models.CharField(max_length=1, default=';')
