# schema.py

import strawberry
import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension

from src.campaigns.types import *

@strawberry.type
class Query:
    # Coverage
    coverage: CoverageType = strawberry_django.field()
    coverages: list[CoverageType] = strawberry_django.field()
    # Campaign
    campaign: CampaignType = strawberry_django.field()
    campaigns: list[CampaignType] = strawberry_django.field()
    # Data Point
    data_point: DataPointType = strawberry_django.field()
    data_points: list[DataPointType] = strawberry_django.field()
    # Category
    category: CategoryType = strawberry_django.field()
    categories: list[CategoryType] = strawberry_django.field()
    # Measurement
    measurement: MeasurementType = strawberry_django.field()
    measurements: list[MeasurementType] = strawberry_django.field()
    # District
    district: DistrictType = strawberry_django.field()
    districts: list[DistrictType] = strawberry_django.field()
    # Measuring Tool
    measuring_tool: MeasuringToolType = strawberry_django.field()
    measuring_tools: list[MeasuringToolType] = strawberry_django.field()
    # Spreadsheet
    spreadsheet: SpreadsheetType = strawberry_django.field()
    spreadsheets: list[SpreadsheetType] = strawberry_django.field()

schema = strawberry.Schema(
    query=Query,
    extensions=[
        DjangoOptimizerExtension,  # not required, but highly recommended
    ],
)
