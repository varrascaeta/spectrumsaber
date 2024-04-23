# Standard imports
import logging
# Django imports
from django.db import models
# Project imports
from resources.places.models import District

logger = logging.getLogger(__name__)


# Common utils
class BaseFile(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    date = models.DateField()
    metadata = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


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
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.get_name_display()


class Measurement(BaseFile):
    # Fields
    filepath = models.FileField(upload_to='measurements/')
    # Relationships
    category = models.ForeignKey(Category, on_delete=models.CASCADE)


class MeasuringTool(models.Model):
    name = models.CharField(max_length=255)
    model_name = models.CharField(max_length=255)
    fov = models.FloatField(null=True)
    measure_height = models.FloatField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name + ' ' + self.model_name


# Campaigns
class Coverage(BaseFile):
    pass


class DataPoint(BaseFile):
    # Fields
    order = models.IntegerField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    # Relationships
    measurements = models.ManyToManyField(Measurement, blank=True, related_name='data_points')


class Campaign(BaseFile):
    # Fields
    external_id = models.CharField(max_length=255)
    # Relationships
    cover = models.ForeignKey(Coverage, on_delete=models.CASCADE, related_name='campaigns')
    data_points = models.ManyToManyField(DataPoint, blank=True, related_name='campaigns')
    district = models.ForeignKey(District, null=True, on_delete=models.SET_NULL)
    measuring_tool = models.ForeignKey(MeasuringTool, null=True, related_name='campaigns', on_delete=models.SET_NULL)
    spreadsheets = models.ManyToManyField('Spreadsheet', blank=True, related_name='campaigns')


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
    filepath = models.FileField(upload_to='spreadsheets/')
    delimiter = models.CharField(max_length=1, default=';')
