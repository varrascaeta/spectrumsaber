from typing import Optional

import strawberry_django
from strawberry import auto

from src.campaigns.models import (
    Campaign,
    Category,
    Coverage,
    DataPoint,
    District,
    Measurement,
)


# Filters
@strawberry_django.filter_type(Coverage)
class CoverageFilter:
    id: auto
    name: auto

    class Meta:
        lookups = True


@strawberry_django.filter_type(Campaign)
class CampaignFilter:
    id: auto
    name: auto
    date: auto
    external_id: auto
    district: Optional["DistrictFilter"]
    coverage: Optional["CoverageFilter"]

    class Meta:
        lookups = True


@strawberry_django.filter_type(Category)
class CategoryFilter:
    id: auto
    name: auto

    class Meta:
        lookups = True


@strawberry_django.filter_type(DataPoint)
class DataPointFilter:
    id: auto
    name: auto
    campaign: Optional[CampaignFilter]

    class Meta:
        lookups = True


@strawberry_django.filter_type(Measurement)
class MeasurementFilter:
    id: auto
    name: auto
    category: Optional[CategoryFilter]
    data_point: Optional[DataPointFilter]

    class Meta:
        lookups = True


@strawberry_django.filter_type(District)
class DistrictFilter:
    id: auto
    name: auto

    class Meta:
        lookups = True


# Types


@strawberry_django.type(District)
class DistrictType:
    id: auto
    name: auto
    campaigns: list["CampaignType"]


@strawberry_django.type(Coverage)
class CoverageType:
    id: auto
    name: auto
    campaigns: list["CampaignType"]


@strawberry_django.type(Campaign)
class CampaignType:
    id: auto
    name: auto
    date: auto
    external_id: auto
    metadata: auto
    district: DistrictType
    coverage: CoverageType
    data_points: list["DataPointType"]


@strawberry_django.type(DataPoint)
class DataPointType:
    id: auto
    name: auto
    campaign: CampaignType
    measurements: list["MeasurementType"]


@strawberry_django.type(Category)
class CategoryType:
    id: auto
    name: auto
    campaigns: list[CampaignType]


@strawberry_django.type(Measurement)
class MeasurementType:
    id: auto
    name: auto
    category: CategoryType
    data_point: DataPointType
